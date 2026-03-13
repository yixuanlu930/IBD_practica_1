import pika, os, time, json, socket, csv, threading
from datetime import datetime
import numpy as np
import tensorflow as tf
import tensorflow_addons as tfa 
from huggingface_hub import from_pretrained_keras
from flask import Flask, request, jsonify

app = Flask(__name__)
tasks_history = {}  # Memoria interna para consultas vía API
hostname = socket.gethostname()
filename = f"/results/image_results_{hostname}.csv"

# Variables de entorno
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password')

# Carga global del modelo EANet
print(f"[{hostname}] Cargando modelo EANet desde Hugging Face...")
try:
    custom_objects = {'AdamW': tfa.optimizers.AdamW}
    with tf.keras.utils.custom_object_scope(custom_objects):
        model = from_pretrained_keras("keras-io/Image-Classification-using-EANet")
    print("Modelo cargado correctamente.")
except Exception as e:
    print(f"Error crítico cargando el modelo: {e}")
    exit(1)

# Lógica central para procesar la imagen, predecir, guardar resultados y actualizar historial
def procesar_imagen_logic(task_id, content):
    """
    Realiza el pre-procesamiento, predicción, guardado en CSV 
    y actualización del historial.
    """
    try:
        # Convertir contenido a matriz numpy
        img_array = np.array(content, dtype=np.float32)
        
        # Ajustar dimensiones para el modelo (batch, 32, 32, 3) y normalizar
        if img_array.ndim == 3:
            img_array = np.expand_dims(img_array, axis=0)
        
        # El modelo EANet espera típicamente (1, 32, 32, 3) y valores [0, 1]
        img_array = img_array / 255.0
        
        # Realizar predicción
        predictions = model.predict(img_array)
        label_index = np.argmax(predictions[0])
        confidence = float(np.max(predictions[0]))

        result_data = {
            "task_id": task_id,
            "agent": hostname,
            "result": f"Clase_{label_index}",
            "confidence": round(confidence, 4),
            "timestamp": datetime.now().isoformat()
        }

        # Guardado en CSV local (usando DictWriter para consistencia)
        file_exists = os.path.isfile(filename)
        with open(filename, mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=result_data.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(result_data)
        
        # Actualizar historial interno para la API
        tasks_history[task_id] = result_data
        return result_data
    except Exception as e:
        print(f"Error en procesar_imagen_logic: {e}")
        raise e

# API REST para procesamiento síncrono

@app.route('/tasks', methods=['POST'])
def create_task_sync():
    data = request.json
    if not data or 'task_id' not in data or 'content' not in data:
        return jsonify({"error": "Datos insuficientes (task_id, content)"}), 400
    
    try:
        result = procesar_imagen_logic(data['task_id'], data['content'])
        return jsonify({"status": "processed", "result": result}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tasks', methods=['GET'])
def list_tasks():
    return jsonify(list(tasks_history.values())), 200

@app.route('/tasks/<task_id>', methods=['GET'])
def get_task_detail(task_id):
    task = tasks_history.get(task_id)
    if not task:
        return jsonify({"error": "Tarea no encontrada"}), 404
    return jsonify(task), 200

# Lógica para consumir tareas de RabbitMQ de forma asíncrona

def consume_tasks_async():
    print(f" [*] Agente {hostname} conectando a RabbitMQ...")
    
    connection = None
    while not connection:
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=RABBITMQ_HOST, 
                credentials=credentials,
                heartbeat=600))
        except Exception:
            print("Esperando a RabbitMQ...")
            time.sleep(5)

    channel = connection.channel()
    
    # Declaración de colas y exchange de logs
    channel.queue_declare(queue='image_tasks', durable=True)
    channel.exchange_declare(exchange='logs_exchange', exchange_type='fanout')
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        task = json.loads(body)
        print(f" [x] Procesando asíncronamente: {task['task_id']}")
        try:
            # Ejecutar lógica central
            result = procesar_imagen_logic(task['task_id'], task['content'])
            
            # Publicar resultado en exchange de logs
            log_message = {
                "task_id": result["task_id"],
                "agent": "Image_agent",
                "result": result["result"],
                "confidence": result["confidence"], 
                "timestamp": result["timestamp"]
            }
            channel.basic_publish(
                exchange='logs_exchange',
                routing_key='',
                body=json.dumps(log_message),
                properties=pika.BasicProperties(delivery_mode=2)
            )

            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f" [OK] Tarea {task['task_id']} finalizada y log enviado.")
        except Exception as e:
            print(f"Error asíncrono: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_consume(queue='image_tasks', on_message_callback=callback)
    channel.start_consuming()


if __name__ == "__main__":
    # Iniciar RabbitMQ en segundo plano
    async_thread = threading.Thread(target=consume_tasks_async)
    async_thread.daemon = True
    async_thread.start()

    # Iniciar Flask
    print(f" [*] API Flask escuchando en puerto 5000...")
    app.run(host='0.0.0.0', port=5000, threaded=True)