# yt-dl-wsp

Este proyecto es un bot para WhatsApp que detecta URLs de YouTube en los mensajes recibidos y descarga el audio de los videos, enviándolo de vuelta como archivo MP3 al chat. Utiliza la librería `neonize` para interactuar con WhatsApp y `yt-dlp` para descargar y convertir videos de YouTube.

A continuación se explica el funcionamiento del archivo principal, casi línea a línea:

---

## Importaciones y configuración inicial

```python
import logging
import os
import signal
import sys
import re
import yt_dlp
import time
from datetime import timedelta
from neonize.client import NewClient
from neonize.events import (
    ConnectedEv,
    MessageEv,
    PairStatusEv,
    event,
    ReceiptEv,
    CallOfferEv,
)
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message
from neonize.utils import log
```
- **Importa** los módulos estándar de Python, las librerías de `neonize` (cliente WhatsApp) y `yt_dlp` (descarga de YouTube).

```python
sys.path.insert(0, os.getcwd())
```
- Asegura que el directorio actual esté en el PATH para importar módulos locales.

---

## Variables globales y manejo de señales

```python
client = None
```
- Variable global para almacenar la instancia del cliente de WhatsApp.

```python
def interrupted(*_):
    ...
```
- Define una función para manejar la señal SIGINT (Ctrl+C), cerrar el cliente y salir limpiamente.

```python
log.setLevel(logging.DEBUG)
signal.signal(signal.SIGINT, interrupted)
```
- Configura el nivel de log en DEBUG y asocia la función anterior a la señal SIGINT.

---

## Inicialización del cliente

```python
client = NewClient("whatsapp_session.db")
```
- Crea un cliente de WhatsApp con persistencia de sesión en una base de datos.

---

## Utilidades para mensajes y chats

```python
def get_chat_type_and_info(chat_jid):
    ...
```
- Determina si el chat es un grupo, contacto o tipo desconocido.

```python
def print_message_info(message: MessageEv):
    ...
```
- Imprime información básica del mensaje recibido (tipo de chat, texto, etc.).

---

## Detección y descarga de YouTube

```python
def is_youtube_url(url):
    ...
```
- Verifica si el texto recibido es una URL de YouTube usando expresiones regulares.

```python
def download_youtube_audio(url, chat):
    ...
```
- Función principal que descarga el audio del video de YouTube y lo envía al chat:
    - Envía un mensaje inicial de "iniciando descarga".
    - Usa `yt_dlp` para obtener info del video y luego descargar el audio en MP3.
    - Edita el mensaje en el chat para mostrar el progreso (información, descarga, envío).
    - Si el video es demasiado largo (>10 min), avisa y cancela.
    - Al terminar, envía el archivo y borra el temporal.
    - Captura y reporta cualquier error.

---

## Manejo de eventos del cliente

```python
@client.event(ConnectedEv)
def on_connected(_: NewClient, __: ConnectedEv):
    ...
```
- Evento: cuando el cliente se conecta, imprime mensaje y log.

```python
@client.event(ReceiptEv)
def on_receipt(_: NewClient, receipt: ReceiptEv):
    ...
```
- Evento: loguea recibos de mensajes.

```python
@client.event(CallOfferEv)
def on_call(_: NewClient, call: CallOfferEv):
    ...
```
- Evento: maneja llamadas entrantes (solo log).

```python
@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    ...
```
- Evento principal: procesa los mensajes nuevos y llama al handler.

---

## Lógica principal del bot

```python
def handler(client: NewClient, message: MessageEv):
    ...
```
- Extrae el texto del mensaje.
- Si el texto es "ping", responde "pong".
- Si detecta una URL de YouTube, llama a la función de descarga.
- Si no, indica que el texto no es una URL de YouTube.

---

## Otros eventos

```python
@client.event(PairStatusEv)
def PairStatusMessage(_: NewClient, message: PairStatusEv):
    ...
```
- Evento: muestra por consola el usuario logueado.

---

## Main

```python
def main():
    ...
```
- Función principal:
    - Muestra mensajes de inicio.
    - Conecta el cliente y maneja excepciones.
    - Cierra sesión correctamente si ocurre un error o Ctrl+C.

```python
if __name__ == "__main__":
    main()
```
- Ejecuta el bot si se lanza el script directamente.

---

## Resumen de uso

1. Inicia el bot.
2. Cuando recibe un mensaje con una URL de YouTube, descarga el audio y lo manda al chat.
3. El usuario puede parar el bot con Ctrl+C.

---

### Requisitos

- Python 3.8+
- `neonize`
- `yt-dlp`
- `ffmpeg` (para conversión de audio)

Instala dependencias con:
```bash
pip install -r requirements.txt
```

---

### Notas finales

- El bot es para uso personal y educativo.
- Asegúrate de cumplir las políticas de uso de WhatsApp y YouTube.
