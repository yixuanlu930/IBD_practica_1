import pika, os, time, socket, json, csv
from datetime import datetime
from huggingface_hub import InferenceClient

# Espera inicial y configuración base
time.sleep(10)  # Esperamos a que el contenedor de RabbitMQ se inicialice
hostname = socket.gethostname()
csv_file = f"/results/text_results_{hostname}.csv"
hf_token = "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"

# Si el token está vacío, el programa se cierra para no saturar RabbitMQ
if not hf_token:
    print("¡ERROR CRÍTICO! No se ha proporcionado el token HF_TOKEN.")
    exit(1)

# Inicializamos el cliente
client = InferenceClient(token=hf_token)

# Conexión a RabbitMQ 
rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
rabbitmq_credentials = pika.PlainCredentials(os.getenv('RABBITMQ_USER', 'user'), os.getenv('RABBITMQ_PASS', 'password'))

connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, credentials=rabbitmq_credentials))
channel = connection.channel()

# Declaración de cola y reglas de escalado
channel.queue_declare(queue='text_tasks', durable=True)
channel.basic_qos(prefetch_count=1) # Obliga a repartir las tareas de 1 en 1 a los agentes libres

# Función de procesamiento
def callback(ch, method, properties, body):
    task = json.loads(body)
    print(f" [*] Received {task['task_id']} in agent {hostname}")

    time.sleep(4) # Simula procesamiento de 3-5 seg
    
    # Inferencia con Hugging Face
    res = client.text_classification(task['content'], model="cardiffnlp/twitter-roberta-base-sentiment-latest")
    
    # Guardado en archivo CSV propio
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['task_id', 'sentiment', 'confidence', 'timestamp'])
        writer.writerow([task['task_id'], res[0].label, round(res[0].score, 4), datetime.now().isoformat()])
    
    print(f" [x] Done {task['task_id']}")
    ch.basic_ack(delivery_tag=method.delivery_tag) # Confirmación manual

# Arranque del consumidor
# auto_ack=False para no perder tareas
channel.basic_qos(prefetch_count=1)

# Configuramos quién va a procesar los mensajes

print(" [*] text_agent esperando mensajes. Para salir presiona CTRL+C")
channel.basic_consume(queue='text_tasks', on_message_callback=callback, auto_ack=False)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()