PRÁCTICA 1 - INFRAESTRUCTURAS DE BIG DATA
=========================================

1. Cómo desplegar la infraestructura del sistema
------------------------------------------------
El sistema se despliega con Docker Compose y levanta los siguientes servicios:

- rabbitmq: broker de mensajería
- producer: generador automático de tareas
- text_agent: agente de análisis de sentimientos
- image_agent: agente de clasificación de imágenes
- global_logger: logger global de tareas procesadas

Levantar la infraestructura:
  docker compose up --build

Ejecutarla en segundo plano:
  docker compose up --build -d

Comprobar que los contenedores están activos:
  docker compose ps

Detener la infraestructura:
  docker compose down

Importante sobre Hugging Face:
Para ejecutar correctamente el servicio text_agent es necesario disponer de un token personal de Hugging Face.

Aunque no sea la opción más segura, por simpleza para ejecutar el código se incluye directamente el token en el archivo docker-compose.yml. La opción más limpia es que cada usuario utilice su propio User Access Token de Hugging Face y lo configure en un archivo .env local.

Pasos:
1. Crear una cuenta en https://huggingface.co
2. Ir a https://huggingface.co/settings/tokens
3. Crear un nuevo token con:
   - Type: Read
   - Opción "Make calls to Inference Providers" activada
4. En el archivo docker-compose.yml, sustituir el valor de HF_TOKEN en el servicio text_agent y en image_agent por tu token personal:

  - HF_TOKEN=hf_tu_token_aqui

Sin este token, o con un token sin los permisos correctos, los agentes fallarán con un error 403 Forbidden al intentar conectarse a la Inference API de Hugging Face.

¡Importante sobre procesadores Apple Silicon (M1/M2/M3) u otros errores de arquitectura!:
Si al intentar levantar la infraestructura (al hacer el build) te aparece un error de compatibilidad o un "exec format error" en el contenedor image_agent, es muy probable que estés usando un Mac con procesador ARM (M1/M2/M3). Las librerías de TensorFlow pueden dar problemas al construirse en estas arquitecturas.

Para solucionarlo, debes abrir el archivo docker-compose.yml, buscar el servicio image_agent y descomentar (quitar la almohadilla #) la línea de la plataforma:

  #platform: linux/amd64

Dejándola así:
  platform: linux/amd64

Esto forzará a Docker a "usar" la arquitectura x86_64 para ese contenedor y solucionará el error de compilación.
--------------------------------------------------------------------------------

1. Cómo ejecutar los agentes
----------------------------
Los agentes se ejecutan como servicios definidos en docker-compose.yml, por lo que no es necesario lanzarlos manualmente fuera de Docker Compose.

Al arrancar la infraestructura con:
  docker compose up --build

se inician automáticamente:
- text_agent
- image_agent
- global_logger

Reiniciar un agente concreto:
  docker compose restart text_agent
  docker compose restart image_agent
  docker compose restart global_logger

Ver los logs de cada servicio:
  docker compose logs -f text_agent
  docker compose logs -f image_agent
  docker compose logs -f global_logger

--------------------------------------------------------------------------------

3. Cómo probar el funcionamiento del sistema
--------------------------------------------
Una vez desplegado el sistema, se puede comprobar su funcionamiento de varias formas.

Verificar que RabbitMQ está funcionando:
RabbitMQ dispone de interfaz web en:
  http://localhost:15672

Credenciales:
- usuario: user
- contraseña: password

Desde ahí se puede comprobar que las colas existen y que los mensajes se publican y consumen correctamente.

Verificar que el producer genera tareas:
  docker compose logs -f producer

Deberían aparecer mensajes indicando el envío continuo de tareas.

Verificar que los agentes procesan tareas:
  docker compose logs -f text_agent
  docker compose logs -f image_agent

Deberían verse mensajes de recepción y procesamiento.

Verificar que se generan resultados:
Los resultados se almacenan en la carpeta results/.

Para comprobarlo:
  ls results

Y para ver el contenido de un archivo CSV:
  head results/nombre_del_fichero.csv

Los agentes generan archivos CSV locales, por ejemplo:
- text_results_<hostname>.csv
- image_results_<hostname>.csv

Además, el servicio global_logger genera un archivo global:
- tasks_log.csv

Verificar la API síncrona de los agentes:
- text_agent expone su API en: http://localhost:5001
- image_agent expone su API en: http://localhost:5002

Operaciones disponibles:
- POST /tasks -> enviar una nueva tarea al agente
- GET /tasks -> consultar las tareas conocidas por el agente
- GET /tasks/<task_id> -> consultar una tarea concreta

Ejemplo para probar text_agent:
  curl -X POST http://localhost:5001/tasks \
    -H "Content-Type: application/json" \
    -d '{"task_id":"demo_text_1","content":"This product is amazing"}'

Ejemplo para consultar tareas del text_agent:
  curl http://localhost:5001/tasks

Ejemplo para consultar una tarea concreta:
  curl http://localhost:5001/tasks/demo_text_1

--------------------------------------------------------------------------------

4. Breve descripción de la arquitectura implementada
----------------------------------------------------
La arquitectura implementada sigue un modelo distribuido orientado a eventos.

El producer genera tareas automáticamente y las publica en RabbitMQ. RabbitMQ actúa como intermediario entre la generación de tareas y su procesamiento, permitiendo desacoplar ambos componentes.

Los agentes consumen las tareas desde sus colas correspondientes:
- text_agent procesa tareas de análisis de sentimientos
- image_agent procesa tareas de clasificación de imágenes

Cada agente mantiene el procesamiento asíncrono original mediante RabbitMQ y, además, expone una API HTTP REST para interacción síncrona. De este modo, cada agente puede:
- consumir tareas de forma asíncrona
- aceptar peticiones síncronas vía HTTP
- devolver información en formato JSON sobre las tareas procesadas

Cada agente guarda sus resultados en archivos CSV dentro de la carpeta results/. Para permitir escalabilidad horizontal, cada instancia puede escribir en un fichero distinto usando el hostname del contenedor como parte del nombre del archivo.

Además, se ha añadido un servicio global_logger que recibe los resultados procesados por los agentes a través de RabbitMQ y los registra en un único archivo global (tasks_log.csv) con información de:
- task_id
- agent
- result
- confidence
- timestamp

Esta arquitectura permite:
- procesamiento asíncrono
- interacción síncrona mediante API REST
- separación entre productor y consumidores
- persistencia de resultados locales y globales
- posibilidad de escalar los agentes en paralelo