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

sys.path.insert(0, os.getcwd())

# * Variable global para el cliente
client = None

def interrupted(*_):
    # ! Maneja la señal SIGINT (Ctrl+C) para cerrar el cliente correctamente
    print("\nCerrando cliente...")
    if client:
        try:
            client.disconnect()
        except:
            pass
    print("Cliente cerrado correctamente")
    event.set()
    os._exit(0)

log.setLevel(logging.DEBUG)
signal.signal(signal.SIGINT, interrupted)

# * Crear cliente con base de datos persistente para mantener la sesión
client = NewClient("whatsapp_session.db")

def get_chat_type_and_info(chat_jid):
    # ? Determina si es grupo o contacto individual y extrae información"""
    try:
        chat_str = str(chat_jid)
        if "@g.us" in chat_str:
            return "GRUPO", chat_str.split("@")[0]
        elif "@s.whatsapp.net" in chat_str:
            return "CONTACTO", chat_str.split("@")[0]
        else:
            return "OTRO", chat_str
    except Exception as e:
        return "DESCONOCIDO", str(chat_jid)

def print_message_info(message: MessageEv):
    # * Imprime información básica del mensaje en consola
    chat = message.Info.MessageSource.Chat
    sender = message.Info.MessageSource.Sender or "Desconocido"
    message_id = message.Info.ID
    
    chat_type, chat_id = get_chat_type_and_info(chat)
    
    # * Extraer texto del mensaje
    text = ""
    if message.Message.conversation:
        text = message.Message.conversation
    elif message.Message.extendedTextMessage and message.Message.extendedTextMessage.text:
        text = message.Message.extendedTextMessage.text
    elif message.Message.imageMessage and message.Message.imageMessage.caption:
        text = f"[IMAGEN] {message.Message.imageMessage.caption}"
    elif message.Message.videoMessage and message.Message.videoMessage.caption:
        text = f"[VIDEO] {message.Message.videoMessage.caption}"
    elif message.Message.audioMessage:
        text = "[AUDIO]"
    elif message.Message.documentMessage:
        text = f"[DOCUMENTO] {message.Message.documentMessage.fileName or 'Sin nombre'}"
    elif message.Message.stickerMessage:
        text = "[STICKER]"
    else:
        text = "[MENSAJE MULTIMEDIA O ESPECIAL]"
    
    # * Log simple del mensaje recibido
    print(f"Mensaje de {chat_type}: {text[:50]}...")

def is_youtube_url(url):
    # ? Verifica si una URL es de YouTube"""
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+'
    ]
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def download_youtube_audio(url, chat):
    # TODO: Descarga audio de YouTube y lo envía al chat usando un solo mensaje editado
    try:
        # ! Mensaje inicial que se irá editando
        msg = client.send_message(chat, Message(conversation="Iniciando descarga del video..."))
        id_msg = msg.ID
        time.sleep(1)
        
        # * Configuración de yt-dlp para extraer audio en MP3
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'extractaudio': True,
            'audioformat': 'mp3',
        }
        
        # * Crear directorio de descargas
        os.makedirs('downloads', exist_ok=True)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # ? Primera edición - obteniendo información
            client.edit_message(chat, id_msg, Message(conversation="Obteniendo informacion del video..."))
            time.sleep(1)
            
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Sin titulo')
            duration = info.get('duration', 0)
            
            # ? Segunda edición - mostrar información del video
            info_text = f"Titulo: {title}\nDuracion: {duration//60}:{duration%60:02d}"
            client.edit_message(chat, id_msg, Message(conversation=info_text))
            time.sleep(1)
            
            # ! Verificar duración máxima permitida
            if duration > 600:
                client.edit_message(chat, id_msg, Message(conversation=f"{info_text}\nEl video es demasiado largo (maximo 10 minutos)"))
                return
            
            # ? Tercera edición - descargando
            client.edit_message(chat, id_msg, Message(conversation=f"{info_text}\nDescargando audio..."))
            
            # * Descargar el video
            ydl.download([url])
            
            # * Buscar el archivo MP3 descargado
            filename = None
            for file in os.listdir('downloads'):
                if file.endswith('.mp3'):
                    filename = os.path.join('downloads', file)
                    break
            
            if filename and os.path.exists(filename):
                # ? Cuarta edición - enviando archivo
                client.edit_message(chat, id_msg, Message(conversation=f"{info_text}\nEnviando archivo de audio..."))
                
                # ! Enviar el archivo de audio al chat
                client.send_audio(chat, filename)
                
                # * Mensaje final de confirmación
                client.send_message(chat, "Audio enviado correctamente!")
                
                # * Limpiar archivo temporal
                try:
                    os.remove(filename)
                except:
                    pass
            else:
                client.edit_message(chat, id_msg, Message(conversation=f"{info_text}\nError: No se pudo encontrar el archivo descargado"))
                
    except Exception as e:
        client.send_message(chat, f"Error al descargar: {str(e)}")
        print(f"Error descargando YouTube: {e}")

@client.event(ConnectedEv)
def on_connected(_: NewClient, __: ConnectedEv):
    print("Conectado a WhatsApp")
    log.info("Connected")

@client.event(ReceiptEv)
def on_receipt(_: NewClient, receipt: ReceiptEv):
    log.debug(receipt)

@client.event(CallOfferEv)
def on_call(_: NewClient, call: CallOfferEv):
    print(f"Llamada entrante de: {call}")
    log.debug(call)

@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    # ! Procesar mensajes de cualquier chat
    print_message_info(message)
    handler(client, message)

def handler(client: NewClient, message: MessageEv):
    # TODO: Maneja los comandos del bot y detección de URLs de YouTube
    # * Extraer texto del mensaje
    text = message.Message.conversation or (
        message.Message.extendedTextMessage.text if message.Message.extendedTextMessage else ""
    )
    chat = message.Info.MessageSource.Chat
    
    print(f"Texto recibido: '{text}'")
    
    # ? Comando ping para pruebas
    if text == "ping":
        client.reply_message("pong", message)
        return
    
    # ! Detectar URLs de YouTube y descargar
    if text and is_youtube_url(text):
        print(f"URL de YouTube detectada: {text}")
        download_youtube_audio(text, chat)
    else:
        print("No es URL de YouTube o texto vacio")

@client.event(PairStatusEv)
def PairStatusMessage(_: NewClient, message: PairStatusEv):
    print(f"Logueado como: {message.ID.User}")
    log.info(f"logged as {message.ID.User}")

def main():
    # * Función principal del programa
    print("Iniciando WhatsApp Bot...")
    print("Bot configurado para descargar audios de YouTube")
    print("Para cerrar el bot presiona Ctrl+C")
    print("-" * 50)
    
    try:
        client.connect()
    except KeyboardInterrupt:
        interrupted()
    except Exception as e:
        print(f"Error: {e}")
        if client:
            try:
                client.disconnect()
            except:
                pass

if __name__ == "__main__":
    main()