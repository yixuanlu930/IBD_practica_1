PRÁCTICA 1 - INFRAESTRUCTURAS DE BIG DATA
=========================================

1. CÓMO DESPLEGAR LA INFRAESTRUCTURA DEL SISTEMA
------------------------------------------------
El sistema se despliega con Docker Compose y levanta los siguientes servicios:

- rabbitmq: broker de mensajería
- producer: generador automático de tareas
- text_agent: agente de análisis de sentimientos
- image_agent: agente de clasificación de imágenes

Levantar la infraestructura:
  docker compose up --build

Para ejecutarlo en segundo plano:
  docker compose up --build -d

Comprobar que los contenedores están activos:
  docker compose ps

Detener la infraestructura:
  docker compose down

IMPORTANTE SOBRE HUGGING FACE
-----------------------------
Para ejecutar correctamente el servicio text_agent es necesario disponer de un token personal de Hugging Face.

Por motivos de seguridad, este token no se incluye en el repositorio. La opción más limpia es que cada usuario, incluido el profesor, utilice su propio User Access Token de Hugging Face y lo configure en un archivo .env local.

Pasos:
1. Crear un token en la cuenta personal de Hugging Face.
2. Guardarlo en un archivo .env en la raíz del proyecto con el formato:
   HF_TOKEN=tu_token_aqui
3. Levantar la infraestructura con:
   docker compose up --build

De este modo, el repositorio mantiene el mismo código para todos los integrantes, pero cada usuario gestiona su credencial de forma local y segura.


2. CÓMO EJECUTAR LOS AGENTES
----------------------------
Los agentes se ejecutan como servicios definidos en docker-compose.yml, por lo que no es necesario lanzarlos manualmente fuera de Docker Compose.

Al arrancar la infraestructura con:
  docker compose up --build

se inician automáticamente:
- text_agent
- image_agent

Reiniciar un agente concreto:
  docker compose restart text_agent
  docker compose restart image_agent

Ver los logs de cada agente:
  docker compose logs -f text_agent
  docker compose logs -f image_agent

3. CÓMO PROBAR EL FUNCIONAMIENTO DEL SISTEMA
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
(Deberían aparecer mensajes indicando el envío continuo de tareas).

Verificar que los agentes procesan tareas:
  docker compose logs -f text_agent
  docker compose logs -f image_agent
(Deberían verse mensajes de recepción y procesamiento).

Verificar que se generan resultados:
Los resultados se almacenan en la carpeta results/.

Para comprobarlo:
  ls results

Y para ver el contenido de un archivo CSV:
  head results/nombre_del_fichero.csv


4. BREVE DESCRIPCIÓN DE LA ARQUITECTURA IMPLEMENTADA
----------------------------------------------------
La arquitectura implementada sigue un modelo distribuido orientado a eventos.

El producer genera tareas automáticamente y las publica en RabbitMQ. RabbitMQ actúa como intermediario entre la generación de tareas y su procesamiento, permitiendo desacoplar ambos componentes.

Los agentes consumen las tareas desde sus colas correspondientes:
- text_agent procesa tareas de análisis de sentimientos
- image_agent procesa tareas de clasificación de imágenes

Cada agente guarda sus resultados en archivos CSV dentro de la carpeta results/. Para permitir escalabilidad horizontal, cada instancia puede escribir en un fichero distinto usando el hostname del contenedor como parte del nombre del archivo.

Esta arquitectura permite:
- procesamiento asíncrono
- separación entre productor y consumidores
- persistencia de resultados
- posibilidad de escalar los agentes en paralelo