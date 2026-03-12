import time
import os
# Importaciones unificadas
from event_generator import generate_task_event
from publisher import get_rabbitmq_connection, publish_task

def main():
    # Tiempo de espera para que el contenedor de RabbitMQ esté listo
    time.sleep(10)
    
    try:
        connection, channel = get_rabbitmq_connection()
        print("[*] Task Producer iniciado. Generando 1 tarea/segundo...")

        while True:
            # Generamos la tarea
            task = generate_task_event()
            # La publicamos
            publish_task(channel, task)
            
            print(f" [x] Enviado {task['type']}: {task['task_id']}")
            
            # Frecuencia obligatoria: 1 segundo
            time.sleep(1) 
            
    except KeyboardInterrupt:
        print("Cerrando productor...")
        if 'connection' in locals():
            connection.close()
    except Exception as e:
        print(f"Error en la conexión: {e}")
        time.sleep(5) # Reintento

if __name__ == "__main__":
    main()