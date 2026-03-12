import pika, os, time, json, socket, csv
from datetime import datetime
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers
from huggingface_hub import InferenceClient
import tensorflow_addons as tfa 
from huggingface_hub import from_pretrained_keras

# Espera a que RabbitMQ esté listo
time.sleep(10)

# Variables de entorno y Token
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password')

hf_token = "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"
client = InferenceClient(token=hf_token)

# Ruta correcta para que el CSV salga en VS Code
hostname = socket.gethostname()
filename = f"/results/image_results_{hostname}.csv"


# Carga del modelo EANet desde Hugging Face (Legacy Keras)
# Esto se hace fuera del callback para que solo se cargue una vez al arrancar
print("Cargando modelo EANet desde Hugging Face...")
custom_objects = {'AdamW': tfa.optimizers.AdamW}
with tf.keras.utils.custom_object_scope(custom_objects):
    model = from_pretrained_keras("keras-io/Image-Classification-using-EANet")

def callback(ch, method, properties, body):
    task = json.loads(body)
    print(f" [*] Procesando imagen {task['task_id']} con EANet")

    try:
        # Convertimos la lista que viene en el JSON de nuevo a un Array de Numpy
        img_array = np.array(task['content'], dtype=np.float32)
        
        # Pre-procesamiento: El modelo espera un batch (1, 32, 32, 3) y valores normalizados
        img_array = np.expand_dims(img_array, axis=0) / 255.0
        
        # Predicción real
        predictions = model.predict(img_array)
        label_index = np.argmax(predictions[0])
        confidence = float(np.max(predictions[0]))


        result = {
            "task_id": task['task_id'],
            "label": f"Clase_{label_index}",
            "confidence": round(confidence, 4),
            "timestamp": datetime.now().isoformat()
        }
        
        file_exists = os.path.isfile(filename)
        with open(filename, mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=result.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(result)

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f" [x] Tarea {task['task_id']} completada")

    except Exception as e:
        print(f" Error procesando imagen: {e}")
        # En caso de error, rechazamos el mensaje para que no bloquee la cola
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
# Conexión a RabbitMQ
credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials))
channel = connection.channel()
QUEUE_NAME = 'image_tasks'

channel.queue_declare(queue=QUEUE_NAME, durable=True)
channel.basic_qos(prefetch_count=1)

print(f' [*] Agente de Imagen {hostname} esperando tareas en {QUEUE_NAME}...')
channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=False)
channel.start_consuming()