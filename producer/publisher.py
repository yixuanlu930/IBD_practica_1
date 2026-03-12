import pika
import json
import os

def get_rabbitmq_connection():
    # Prioriza variables de entorno (Docker), si no usa localhost (WSL directo)
    host = os.getenv('RABBITMQ_HOST', 'localhost')
    user = os.getenv('RABBITMQ_USER', 'user')
    password = os.getenv('RABBITMQ_PASS', 'password')

    credentials = pika.PlainCredentials(user, password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=host, credentials=credentials)
    )
    channel = connection.channel()

    # Declaramos el Exchange tipo 'direct'
    channel.exchange_declare(exchange='tasks_exchange', exchange_type='direct')
    
    # Declaramos y vinculamos las colas para que sean persistentes
    channel.queue_declare(queue='text_tasks', durable=True)
    channel.queue_declare(queue='image_tasks', durable=True)

    channel.queue_bind(exchange='tasks_exchange', queue='text_tasks', routing_key='ruta_texto')
    channel.queue_bind(exchange='tasks_exchange', queue='image_tasks', routing_key='ruta_imagen')

    return connection, channel

def publish_task(channel, task):
    # Usamos la routing_key que ya viene en el objeto task generada por event_generator
    channel.basic_publish(
        exchange='tasks_exchange',
        routing_key=task['routing_key'],
        body=json.dumps(task),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Mensaje persistente
        )
    )