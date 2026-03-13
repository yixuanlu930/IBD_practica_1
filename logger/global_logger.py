import pika, os, time, json, csv
from datetime import datetime

time.sleep(15)

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password')
LOG_FILE = '/results/tasks_log.csv'

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
connection = pika.BlockingConnection(pika.ConnectionParameters(
    host=RABBITMQ_HOST, credentials=credentials
))
channel = connection.channel()

# Fanout exchange — recibe de TODOS los agentes
channel.exchange_declare(exchange='logs_exchange', exchange_type='fanout')

# Cola exclusiva y anónima para este servicio
result = channel.queue_declare(queue='logger_queue', durable=True)
channel.queue_bind(exchange='logs_exchange', queue='logger_queue')

def callback(ch, method, properties, body):
    log = json.loads(body)
    print(f" [LOG] {log['task_id']} | {log['agent']} | {log['result']} | {log['confidence']}")

    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, mode='a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['task_id','agent','result','confidence','timestamp'])
        if not file_exists:
            writer.writeheader()
        writer.writerow(log)

    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='logger_queue', on_message_callback=callback, auto_ack=False)

print(' [*] Global Task Logger esperando resultados...')
channel.start_consuming()