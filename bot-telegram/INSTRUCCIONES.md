# Servicio de Envío de Mensajes Críticos a Telegram

Vamos a crear un servicio el cual va a reaccionar a eventos de notificación de la operación de un servidor con el objetivo de envíar un mensaje a Telegram que informe los errores que se presenten en el proceso.

# Procesamiento de eventos:
- La estructura del evento la puedes encontrar en el README de este repositorio: https://github.com/Azrrael-exe/ops-beacon.
- Solo vamos a enviar mensajes de eventos de tipo ERROR.
- Los eventos se publican en un serivor MQTT, al cual debes conectarte usando url del servidor, puerto,usuario y contraseña. La conexión no usa SSL.
- Este servicio debe ejecutarse en un ciclo constante, de tal forma que estés escuchando constantemente los eventos que se publiquen en el servidor MQTT en el tópico correspondiente.

# Estructura del mensaje a enviar a Telegram:
- El mensaje enviado a Telegram debe ser una tabla donde se muestre el detalle de cada evento según la estructura que estudiaste.

# API:
- Debes crear una API usando FastAPI que tenga dos endpoints:
- GET /health: que debe devolver un estado de NO_CONTENT si el servicio está funcionando correctamente.
- GET /config: que debe devolver la configuración del servicio en formato JSON.

# Lenguaje de Programación:
- El repositorio donde estamos es un monorepo donde van a alojarse muchos proyectos. Por lo tanto, debes crear una carpeta para alojar esta implementación. La carpeta puede llamarse bot-telegram.
- Vamos a programarlo en python usando UV como gestor de paquetes. No uses archivos aparte para las dependencias, todas deben gestionarse desde el archivo pyproject.toml.
- Debes basarte en principios de Clean Architecture.
- Debes desarrollar basado en el Paradigma Orientado a Objetos.

# Despliegue:
- El proyecto debe ser desplegado en un contenedor Docker. Por lo tanto, debes usar un Dockerfile para ello.
- Crea el archivo docker-compose.yml para desplegar el proyecto.

# Configuración:
- La configuración de conexión al MQTT y de Telegram debemos centralizarla en un archivo yaml y cargarlo desde el contenedor.
