import pika, os, time, socket, json, csv, threading
from datetime import datetime
from huggingface_hub import InferenceClient
from flask import Flask, request, jsonify

app = Flask(__name__)
tasks_history = {}  # Memoria interna para consultas vía API
hostname = socket.gethostname()
csv_file = f"/results/text_results_{hostname}.csv"

# Configuración de Hugging Face
hf_token = os.getenv('HF_TOKEN')
if not hf_token:
    print("¡ERROR CRÍTICO! No se ha proporcionado el token HF_TOKEN.")
    exit(1)

client = InferenceClient(token=hf_token)

#  LÓGICA DE PROCESAMIENTO ÚNICA 
def procesar_texto_logic(task_id, content):
    """
    Función centralizada que realiza la inferencia, guarda en CSV 
    y actualiza el historial interno.
    """
    # Inferencia con Hugging Face
    res = client.text_classification(content, model="cardiffnlp/twitter-roberta-base-sentiment-latest")
    
    result_data = {
        "task_id": task_id,
        "sentiment": res[0].label,
        "confidence": round(res[0].score, 4),
        "timestamp": datetime.now().isoformat(),
        "agent": hostname
    }

    # Guardado en archivo CSV
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['task_id', 'sentiment', 'confidence', 'timestamp'])
        writer.writerow([result_data["task_id"], result_data["sentiment"], 
                        result_data["confidence"], result_data["timestamp"]])
    
    # Almacenar en el historial para consulta API
    tasks_history[task_id] = result_data
    return result_data

#  REQUISITO 1: API SÍNCRONA (FLASK) 

@app.route('/tasks', methods=['POST'])
def create_task_sync():
    data = request.json
    if not data or 'task_id' not in data or 'content' not in data:
        return jsonify({"error": "Datos insuficientes"}), 400
    
    try:
        result = procesar_texto_logic(data['task_id'], data['content'])
        return jsonify({"status": "completed", "result": result}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tasks', methods=['GET'])
def list_tasks():
    return jsonify(list(tasks_history.values())), 200

@app.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = tasks_history.get(task_id)
    if not task:
        return jsonify({"error": "Tarea no encontrada"}), 404
    return jsonify(task), 200

#  REQUISITO 2: LÓGICA ASÍNCRONA (RABBITMQ)

def consume_tasks_async():
    # Espera inicial para asegurar que RabbitMQ esté listo (del segundo script)
    time.sleep(10)
    
    rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    rabbitmq_credentials = pika.PlainCredentials(
        os.getenv('RABBITMQ_USER', 'user'), 
        os.getenv('RABBITMQ_PASS', 'password')
    )

    # Conexión robusta
    connection = None
    while not connection:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=rabbitmq_host, credentials=rabbitmq_credentials)
            )
        except Exception as e:
            print(f"Esperando a RabbitMQ... ({e})")
            time.sleep(5)

    channel = connection.channel()
    
    # Declaración de colas y exchanges
    channel.queue_declare(queue='text_tasks', durable=True)
    channel.exchange_declare(exchange='logs_exchange', exchange_type='fanout')
    
    # Balanceo de carga: 1 tarea a la vez por agente
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        task = json.loads(body)
        print(f" [*] Asíncrono: procesando {task['task_id']} en {hostname}")
        
        try:
            # Simulación ligera de procesamiento (del segundo script)
            time.sleep(1) 
            
            # Ejecutar lógica común
            result = procesar_texto_logic(task['task_id'], task['content'])
            
            # PUBLICAR LOG (Lo que no estaba en el primer script)
            log_message = {
                "task_id": result["task_id"],
                "agent": "Text_agent",
                "result": result["sentiment"],            
                "confidence": result["confidence"], 
                "timestamp": result["timestamp"]
            }
            channel.basic_publish(
                exchange='logs_exchange',
                routing_key='',
                body=json.dumps(log_message),
                properties=pika.BasicProperties(delivery_mode=2)
            )

            print(f" [x] Done {task['task_id']}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            print(f"Error procesando tarea asíncrona: {e}")
            # nack sin requeue para evitar bucles infinitos en errores de inferencia
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    print(" [*] Esperando mensajes en 'text_tasks'...")
    channel.basic_consume(queue='text_tasks', on_message_callback=callback, auto_ack=False)
    channel.start_consuming()


if __name__ == "__main__":
    # 1. Hilo para RabbitMQ (Asíncrono)
    thread = threading.Thread(target=consume_tasks_async)
    thread.daemon = True
    thread.start()

    # 2. Hilo principal para Flask (Síncrono)
    # Host 0.0.0.0 para ser accesible desde fuera del contenedor
    print(f" [*] Iniciando API Flask en puerto 5000...")
    app.run(host='0.0.0.0', port=5000)