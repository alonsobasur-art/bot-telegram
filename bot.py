from bs4 import BeautifulSoup
import os
import time
import logging
import shutil
import asyncio
import subprocess
import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import aria2p
import json 
import psutil
import getpass
import yt_dlp
import threading
import random
import sys
from colorama import init, Fore, Style
from datetime import datetime
import subliminal
from babelfish import Language
import speech_recognition as sr
from pydub import AudioSegment
import glob
from mutagen.id3 import APIC, ID3, TIT2, TPE1, USLT, error
from telegram import InputMediaPhoto
import urllib.parse
import zipfile
import cursor_chat
import voice_orders
import anime_torrent_sources
import imagen_telegram
import hot_chat

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

init(autoreset=True)

# ==========================================
# 🎨 MOTOR DE REGISTROS VISUALES (LOGS 2.0)
# ==========================================
def log_to_file(tipo, mensaje, is_error=False):
    os.makedirs("logs", exist_ok=True)
    fecha = datetime.now().strftime("%Y-%m-%d")
    hora = datetime.now().strftime("%H:%M:%S")
    archivo = "logs/errores.txt" if is_error else f"logs/bot_log_{fecha}.txt"
    try:
        with open(archivo, "a", encoding="utf-8") as f:
            f.write(f"[{hora}] [{tipo}] {mensaje}\n")
    except: pass

def log_accion(usuario, accion, color=Fore.CYAN, dialogo=None):
    hora = datetime.now().strftime("%H:%M:%S")
    texto_pantalla = f"{Fore.LIGHTBLACK_EX}[{hora}]{Style.RESET_ALL} {Fore.MAGENTA}👤 {usuario}{Style.RESET_ALL} {color}➡️ {accion}{Style.RESET_ALL}"
    
    # Si hay un diálogo o enlace, lo ponemos bonito debajo con comillas
    if dialogo:
        texto_pantalla += f"\n   {Fore.LIGHTBLACK_EX}└ 💬 \"{dialogo}\"{Style.RESET_ALL}"
        
    print(texto_pantalla)
    
    # Lo guardamos en el archivo oculto
    log_msg = f"{usuario} -> {accion}" + (f" | Dato: {dialogo}" if dialogo else "")
    log_to_file("USUARIO", log_msg)

def log_sistema(mensaje, color=Fore.YELLOW, is_error=False):
    hora = datetime.now().strftime("%H:%M:%S")
    icono = "❌ ERROR" if is_error else "⚙️ SISTEMA"
    color_icono = Fore.RED if is_error else Fore.BLUE
    print(f"{Fore.LIGHTBLACK_EX}[{hora}]{Style.RESET_ALL} {color_icono}{icono}{Style.RESET_ALL} {color}➡️ {mensaje}{Style.RESET_ALL}")
    log_to_file("ERROR" if is_error else "SISTEMA", mensaje, is_error)


def md(text):
    """Limpia texto libre para que no rompa el Markdown de Telegram."""
    if text is None:
        return ""
    limpio = str(text).replace("`", "'").replace("*", "").replace("_", " ").replace("[", "(").replace("]", ")")
    return limpio


def code(text):
    """Deja un nombre de archivo usable dentro de `código`."""
    return str(text or "").replace("`", "'")


def serie_token(name):
    import hashlib
    return hashlib.sha1(str(name).encode("utf-8")).hexdigest()[:12]


def serie_by_token(token, data):
    if token in data:
        return token
    for name in data:
        if serie_token(name) == token:
            return name
    return None


BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}
MANGA_HEADERS = {"User-Agent": "MiBot/1.0 (personal media library)"}


def manga_title_of(attrs):
    titles = (attrs or {}).get("title") or {}
    if isinstance(titles, str):
        return titles or "Manga"
    for key in ("es-la", "es", "en", "ja-ro", "ja"):
        if titles.get(key):
            return titles[key]
    return next(iter(titles.values()), "Manga")


async def bot_send(update, context, text, **kwargs):
    return await context.bot.send_message(chat_id=update.effective_chat.id, text=text, **kwargs)


async def safe_edit(message, text, send_new=True, **kwargs):
    if getattr(message, "photo", None):
        try:
            await message.edit_caption(caption=str(text)[:1024], **kwargs)
            return message
        except Exception:
            pass
    try:
        await message.edit_text(text, **kwargs)
        return message
    except Exception:
        if not send_new:
            return message
        return await message.get_bot().send_message(chat_id=message.chat_id, text=text, **kwargs)


async def show_text_menu(query, text, **kwargs):
    msg = query.message
    if msg and (msg.photo or msg.video or msg.animation or msg.document):
        try:
            await msg.delete()
        except Exception:
            pass
        return await msg.get_bot().send_message(chat_id=msg.chat_id, text=text, **kwargs)
    return await query.edit_message_text(text, **kwargs)


TRACKING_FILE = "bot_series_tracking.json"

KEYWORDS_ES = ['spani', 'esp', 'castellano', 'latino', 'sub', 'vose', 'multi']


# ==========================================
# ⚙️ CONFIGURACIÓN Y VARIABLES GLOBALES
# ==========================================

# Datos del token de bot de Telegram 
TOKEN = "8271112705:AAG5V7E2NM0tfdl3bDC3RyNas_fPrIiHPTU"

# 🔑 Credenciales EMT Madrid (MobilityLabs)
EMT_EMAIL = "alonsobasur@gmail.com"
EMT_PASSWORD = "Pinpantoma1!"
# ID de mi madre y de Juan
ADMIN_IDS = [1156812303, 5188345207, 7356746702]

BASE_DOWNLOAD_PATH = 'D:/Descargas torrent'
PLEX_FINAL_PATH = 'D:/Plex_Confirmados'

PLEX_URL = "http://127.0.0.1:32400"
PLEX_TOKEN = "X3SsGBPPYvxyuhGs5GCi"

# 🎬 CONEXIÓN RADARR (CINE AUTOMÁTICO ZERO-TOUCH)
RADARR_URL = "http://localhost:7878"
RADARR_API_KEY = "61ddd80788fa4a3b8738c4d39a95225f" # <--- ¡Pega aquí la API Key larga que copiaste antes en Prowlarr!
RADARR_ROOT_FOLDER = r"D:\Plex_Confirmados\Peliculas"

MENU, AWAITING_MAGNET, AWAITING_SEARCH, POST_DOWNLOAD_DECISION, RENAMING, MOVING_CATEGORY, SUBTITLES_SEARCH, PLEX_UPDATE, AWAITING_NEW_SERIES, DEV_MENU, AWAITING_DEV_SEARCH, AWAITING_DEV_REPLACE, AWAITING_ARTIST, AWAITING_APK_SEARCH, AWAITING_MANGA_SEARCH, AWAITING_RADARR_SEARCH, AWAITING_CURSOR, AWAITING_VOICE_CONFIRM, AWAITING_VOICE_EDIT, AWAITING_IMAGEN_PROMPT, AWAITING_IMAGEN_SEED, AWAITING_IMAGEN_REF, AWAITING_HOT = range(23)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ==========================================
# 🚀 INICIALIZACIÓN DEL SISTEMA (ARIA2 & DRIVE)
# ==========================================


def init_system():
    # 1. Matar cualquier motor Aria2 fantasma para liberar el puerto 6800 (crucial si lo que buscamos es que el bot no se quede pillado)
    os.system("taskkill /F /IM aria2c.exe /T 2>NUL")
    time.sleep(1)

    # 2. Crear carpetas si no existen

    for path in [BASE_DOWNLOAD_PATH, PLEX_FINAL_PATH,
                 f"{PLEX_FINAL_PATH}/Peliculas",
                 f"{PLEX_FINAL_PATH}/Series",
                 f"{PLEX_FINAL_PATH}/Anime"]:
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Carpeta creada: {path}")

    # 3. Iniciar Aria2 en modo silencioso y forzando sobreescritura
    try:
        subprocess.Popen([
            'aria2c.exe', 
            '--enable-rpc', 
            '--rpc-listen-all=false', 
            '--rpc-allow-origin-all', 
            '--daemon=false', 
            f'--dir={BASE_DOWNLOAD_PATH}', 
            '--max-connection-per-server=10', 
            '--seed-time=0',
            
'--allow-overwrite=true',                      # <--- ARREGLA EL ERROR 13
            '--auto-file-renaming=false',      # <--- EVITA ARCHIVOS DUPLICADOS
            '--console-log-level=error',       # <--- SILENCIA EL SPAM
            '--file-allocation=none'           # <--- NUEVO: EVITA QUE EL PC SE CONGELE
        ])

        time.sleep(3) 
    except Exception as e:
        print(f"Error iniciando Aria2: {e}")
# Cliente Aria2p
aria2 = aria2p.API(aria2p.Client(host="http://localhost", port=6800, secret=""))

# ==========================================
# 🛠️ FUNCIONES AUXILIARES
# ==========================================


def get_keyboard(menu_type, user_id=None):
    if menu_type == "main":
        keyboard = [
            [InlineKeyboardButton("🖼️ Imagen", callback_data='imagen_menu')],
            [InlineKeyboardButton("⬇️ Bajar", callback_data='menu_bajar')],
            [InlineKeyboardButton("📥 En curso", callback_data='menu_curso')],
            [InlineKeyboardButton("🖥️ PC", callback_data='menu_casa')],
            [InlineKeyboardButton("🤖 Bot", callback_data='menu_bot')],
        ]
    elif menu_type in ("bajar", "gestion_media"):
        keyboard = [
            [InlineKeyboardButton("🍿 Película", callback_data='search_radarr_start')],
            [InlineKeyboardButton("🔍 Serie o anime", callback_data='search')],
            [InlineKeyboardButton("⚡ Pegar enlace", callback_data='magnet')],
            [InlineKeyboardButton("🎵 Música", callback_data='search_artist_start')],
            [InlineKeyboardButton("📖 Manga", callback_data='search_manga_start')],
            [InlineKeyboardButton("📱 App", callback_data='search_apk_start')],
            [InlineKeyboardButton("🎲 Sorpréndeme", callback_data='suggest_movie')],
            [InlineKeyboardButton("🔙 Inicio", callback_data='back_to_main')],
        ]
    elif menu_type == "curso":
        keyboard = [
            [InlineKeyboardButton("📥 Descargas activas", callback_data='dl_manager')],
            [InlineKeyboardButton("📺 Series que sigo", callback_data='tracker')],
            [InlineKeyboardButton("🗂️ Archivos", callback_data='explorer_root')],
            [InlineKeyboardButton("🔙 Inicio", callback_data='back_to_main')],
        ]
    elif menu_type in ("casa", "control_panel"):
        keyboard = [
            [InlineKeyboardButton("🖥️ Estado del PC", callback_data='pc_status')],
            [InlineKeyboardButton("🎮 Parsec y juegos", callback_data='parsec_status')],
            [InlineKeyboardButton("💾 Espacio en Drive", callback_data='space')],
            [InlineKeyboardButton("🚲 BiciMAD", callback_data='bicimad_status')],
            [InlineKeyboardButton("🔙 Inicio", callback_data='back_to_main')],
        ]
    elif menu_type == "bot":
        keyboard = []
        if user_id == ADMIN_IDS[0]:
            keyboard.append([InlineKeyboardButton("🤖 Cursor", callback_data='cursor_open')])
            keyboard.append([InlineKeyboardButton("🖼️ Imagen", callback_data='imagen_menu')])
        keyboard += [
            [InlineKeyboardButton("🛠️ Tocar el código", callback_data='dev_menu')],
            [InlineKeyboardButton("❓ Ayuda", callback_data='help')],
            [InlineKeyboardButton("🔄 Reiniciar el PC", callback_data='restart_pc')],
            [InlineKeyboardButton("🔙 Inicio", callback_data='back_to_main')],
        ]
    elif menu_type == "back":
        keyboard = [[InlineKeyboardButton("🔙 Volver a Bajar", callback_data='menu_bajar')]]
    else:
        keyboard = [[InlineKeyboardButton("🔙 Inicio", callback_data='back_to_main')]]

    return InlineKeyboardMarkup(keyboard)


def texto_inicio(nombre):
    return (
        f"👋 **Hola {md(nombre)}.**\n\n"
        "Elige una puerta. Debajo de cada botón te explico qué hace.\n\n"
        "🖼️ **Imagen** — escribes lo que quieres y te mando la foto.\n"
        "⬇️ **Bajar** — película, serie, música, manga o un enlace.\n"
        "📥 **En curso** — lo que se está descargando y las series que sigues.\n"
        "🖥️ **PC** — el ordenador, los juegos y la bici.\n"
        "🤖 **Bot** — ayuda, cambios y reinicio."
    )


def texto_bajar():
    return (
        "⬇️ **Bajar**\n\n"
        "Elige qué quieres. En la siguiente pantalla te digo qué tienes que escribir.\n\n"
        "🍿 **Película** — la busca y la manda a Plex sola.\n"
        "🔍 **Serie o anime** — escribes el título y eliges un torrent.\n"
        "⚡ **Pegar enlace** — magnet, YouTube, TikTok, Instagram o Spotify.\n"
        "🎵 **Música** — buscas un artista y bajas la canción en MP3.\n"
        "📖 **Manga** — buscas el título y bajas capítulos en CBZ.\n"
        "📱 **App** — buscas una aplicación Android y bajas el APK.\n"
        "🎲 **Sorpréndeme** — te propone una película que está de moda."
    )


def texto_curso():
    return (
        "📥 **En curso**\n\n"
        "Aquí no empiezas nada nuevo. Miras lo que ya está en marcha.\n\n"
        "📥 **Descargas activas** — pausar, reanudar o cancelar.\n"
        "📺 **Series que sigo** — aviso cuando salga un capítulo nuevo.\n"
        "🗂️ **Archivos** — ver o borrar lo que hay en el PC y en Drive."
    )


def texto_casa():
    return (
        "🖥️ **PC**\n\n"
        "Esto no descarga nada. Sirve para ver el ordenador desde el móvil.\n\n"
        "🖥️ **Estado** — procesador, memoria y disco.\n"
        "🎮 **Parsec y juegos** — quién está conectado y abrir un juego.\n"
        "💾 **Drive** — cuánto espacio queda.\n"
        "🚲 **BiciMAD** — bicis libres en la estación de casa."
    )


def texto_bot(user_id):
    lineas = [
        "🤖 **Bot**",
        "",
        "Ayuda y mantenimiento. Reiniciar apaga el PC y lo vuelve a encender.",
        "",
    ]
    if user_id == ADMIN_IDS[0]:
        lineas.append("🤖 **Cursor** — le escribes a la IA para que arregle el bot o mire el PC.")
        lineas.append("🖼️ **Imagen** — generar anime en el PC (tamaño, pasos, NSFW) y te la mando aquí.")
    lineas += [
        "🛠️ **Tocar el código** — cambias un trozo del programa pegando el texto exacto.",
        "❓ **Ayuda** — cómo se usa cada cosa, con ejemplos.",
        "🔄 **Reiniciar el PC** — Windows se reinicia y el bot vuelve solo.",
    ]
    return "\n".join(lineas)

def load_tracked_series():
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_tracked_series(data):
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=4)

async def restricted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Acceso denegado. Este bot es privado propiedad de Viejo/Aarón.")
        return False
    return True

def format_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024

def check_drive_space():
    try:
        from google.colab import auth
        from googleapiclient.discovery import build
        drive_service = build('drive', 'v3')
        about = drive_service.about().get(fields='storageQuota').execute()
        quota = about['storageQuota']
        total = int(quota['limit'])
        used = int(quota['usage'])
        free = total - used
        percent_free = (free / total) * 100

        return format_size(total), format_size(used), format_size(free), percent_free

    except Exception:
        try:
            total, used, free = shutil.disk_usage(BASE_DOWNLOAD_PATH)
            return format_size(total), format_size(used), format_size(free), (free/total)*100
        except:
            return "0B", "0B", "0B", 0

# ==========================================
# 📱 MANEJO DEL BOT
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await restricted(update, context): return

    user_first_name = update.effective_user.first_name
    log_accion(user_first_name, "Ha abierto el bot (/start)", Fore.GREEN)

    welcome_msg = texto_inicio(user_first_name)
    await bot_send(update, context, welcome_msg, reply_markup=get_keyboard("main", update.effective_user.id), parse_mode='Markdown')
    try:
        await update.message.delete()
    except Exception:
        pass
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

# --- CHIVATO MAESTRO 2.0 ---
    usuario = update.effective_user.first_name
    boton_pulsado = query.data
    log_accion(usuario, "Ha tocado un botón del menú", Fore.MAGENTA, dialogo=f"Navegando a: [{boton_pulsado}]")
    # -----------------------

# 1. MENÚ PRINCIPAL (Botón Atrás)
    if query.data == 'back_to_main':
        await show_text_menu(
            query,
            texto_inicio(update.effective_user.first_name),
            reply_markup=get_keyboard("main", update.effective_user.id),
            parse_mode='Markdown'
        )
        return MENU

    elif query.data in ('menu_bajar', 'gestion_media'):
        await show_text_menu(query, texto_bajar(), reply_markup=get_keyboard("bajar"), parse_mode='Markdown')
        return MENU

    elif query.data == 'menu_curso':
        await show_text_menu(query, texto_curso(), reply_markup=get_keyboard("curso"), parse_mode='Markdown')
        return MENU

    elif query.data in ('menu_casa', 'control_panel'):
        await show_text_menu(query, texto_casa(), reply_markup=get_keyboard("casa"), parse_mode='Markdown')
        return MENU

    elif query.data == 'menu_bot':
        await show_text_menu(
            query,
            texto_bot(update.effective_user.id),
            reply_markup=get_keyboard("bot", update.effective_user.id),
            parse_mode='Markdown'
        )
        return MENU

    elif query.data == 'magnet':
        await query.edit_message_text(
            "⚡ **Pegar enlace**\n\n"
            "Pega aquí el enlace y lo bajo a Drive.\n\n"
            "🧲 Un magnet (`magnet:?...`) o un archivo `.torrent`.\n"
            "📺 YouTube, en vídeo o en MP3.\n"
            "📱 TikTok o Instagram, sin marca de agua.\n"
            "🎵 Spotify o YouTube Music.\n\n"
            "Si pesa poco te lo mando al chat. Si pesa mucho se queda en Drive.",
            reply_markup=get_keyboard("back"), parse_mode='Markdown'
        )
        return AWAITING_MAGNET

    elif query.data == 'search':
        await query.edit_message_text(
            "🔍 **Serie o anime**\n\n"
            "Escribe el título. Te enseño torrents y tú eliges cuál bajar.\n"
            "Si lleva 🇪🇸, está en castellano. Priorizo 1080p y 4K.\n\n"
            "Ejemplo: `Jujutsu Kaisen` o `Dune`.",
            reply_markup=get_keyboard("back"), parse_mode='Markdown'
        )
        return AWAITING_SEARCH

        # 4.1 Estado del PC
    elif query.data == 'pc_status':
        # Leemos el hardware en tiempo real
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        
        # Barra visual para la RAM
        ram_bar = "▓" * int(ram.percent // 10) + "░" * (10 - int(ram.percent // 10))
        
        msg = (
            "🖥️ **Estado del PC**\n\n"
            "Así está el ordenador ahora mismo. No cambia nada, solo mira.\n\n"
            f"🧠 **CPU (Ryzen 5 5600X):** {cpu}%\n"
            f"🟢 **RAM (16GB):** {ram.percent}% [{ram_bar}]\n"
            f"💾 **SSD Principal:** {disk.percent}% usado\n"
            f"🎮 **GPU:** RTX 3050\n\n"
            f"⚡ **Estado general:** {'🔥 Alta carga' if cpu > 80 or ram.percent > 85 else '✅ Óptimo'}"
        )
        
        kb_volver = [[InlineKeyboardButton("🔙 Volver al PC", callback_data='menu_casa')]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb_volver), parse_mode='Markdown')
        return MENU

    elif query.data == 'anime_sources_check':
        await query.edit_message_text("📡 **Comprobando fuentes anime…**", parse_mode='Markdown')
        informe = await asyncio.to_thread(anime_torrent_sources.chequeo_rapido)
        lineas = []
        for fuente in informe:
            icono = "🟢" if fuente.get("ok") else "🔴"
            lineas.append(
                f"{icono} **{fuente.get('name')}** — {fuente.get('detail', '?')} ({fuente.get('ms', 0)} ms)"
            )
        texto = (
            "📡 **FUENTES ANIME (motor de descarga)**\n\n"
            + "\n".join(lineas)
            + "\n\n_En el buscador se priorizan castellano, VOSE y 1080p/4K._"
        )
        kb_volver = [[InlineKeyboardButton("🔙 Volver al PC", callback_data='menu_casa')]]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(kb_volver), parse_mode='Markdown')
        return MENU

# 4.4 Estado BiciMAD (Botón a demanda)
    elif query.data == 'bicimad_status':
        await query.edit_message_text("🚲 **Conectando con EMT Madrid...**", parse_mode='Markdown')
        
        bicis, huecos, direccion = await check_bicimad(context, send_alert=False)
        
        if bicis is not None:
            msg = (
                "🚲 **BiciMAD**\n\n"
                "Bicis y huecos libres en la estación de casa. Actualizar vuelve a preguntar a EMT.\n\n"
                f"📍 **Ubicación:** `{direccion}`\n"
                f"✅ **Bicicletas disponibles:** {bicis}\n"
                f"🅿️ **Anclajes libres:** {huecos}\n"
            )
        else:
            msg = direccion # Muestra el mensaje de error si fallan las credenciales
            
        kb_volver = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data='bicimad_status')],
            [InlineKeyboardButton("🔙 Volver al PC", callback_data='menu_casa')]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb_volver), parse_mode='Markdown')
        return MENU
         # 4.2 Monitor Parsec
    elif query.data == 'parsec_status':
        await query.edit_message_text("🕵️‍♂️ Revisando conexiones y juegos en ejecución...", parse_mode='Markdown')
        
        # 1. Buscar a qué está jugando (Lista de juegos populares)
        juegos_conocidos = ["Fortnite", "Valorant", "League of Legends", "Minecraft", "GTA5", "Roblox", "csgo"]
        juego_actual = "Ninguno / En el escritorio"
        
        for p in psutil.process_iter(['name']):
            try:
                nombre_proceso = p.info['name'].lower()
                for j in juegos_conocidos:
                    if j.lower() in nombre_proceso:
                        juego_actual = j
                        break
            except: pass

# 2. Leer el registro secreto de Parsec (Ruta Directa)
        log_path = r"C:\Users\JUEGOS\AppData\Roaming\Parsec\log.txt"
        estado_parsec = "🔴 Nadie conectado"
        ultima_conexion = "Desconocida"

        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lineas = f.readlines()
                # Leemos el archivo de abajo a arriba (800 líneas)
                for linea in reversed(lineas[-800:]): 
                    # Ampliamos la búsqueda de palabras clave
                    if any(x in linea.lower() for x in ["client connected", "connected to", "connection accepted", "authenticated"]):
                        estado_parsec = "🟢 **ALGUIEN ESTÁ CONECTADO**"
                        ultima_conexion = linea[:19] # Saca la fecha y hora del log
                        break
                    elif "disconnected" in linea.lower():
                        estado_parsec = "🔴 Desconectado"
                        ultima_conexion = linea[:19]
                        break

        msg = (
            "🎮 **Parsec y juegos**\n\n"
            "Parsec es el escritorio remoto. Aquí ves si alguien está dentro. "
            "Desde el lanzador puedes abrir un juego o cerrarlo.\n\n"
            f"📡 **Estado:** {estado_parsec}\n"
            f"⏱️ **Última actividad:** {ultima_conexion}\n\n"
            f"🕹️ **Jugando a:** {juego_actual}"
        )
        
        kb_volver = [
            [InlineKeyboardButton("🚀 Lanzador de Juegos", callback_data='game_launcher')],
            [InlineKeyboardButton("🔙 Volver al PC", callback_data='menu_casa')]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb_volver), parse_mode='Markdown')
        return MENU

    # 4.3 Espacio en Drive
    elif query.data == 'space':
        await query.edit_message_text("⏳ Calculando espacio...", parse_mode='Markdown')
        total, used, free, percent_free = check_drive_space()
        alert = "⚠️ **¡Espacio Bajo!**" if percent_free < 10 else "✅ Espacio Saludable"
        msg = (
            "💾 **Espacio en Drive**\n\n"
            "Aquí acaban las descargas grandes. Esto es lo que queda libre.\n\n"
            f"📦 Total: {total}\n❌ Usado: {used}\n✅ Libre: {free}\n\n"
            f"{alert} ({percent_free:.1f}%)"
        )
        
        kb_volver = [[InlineKeyboardButton("🔙 Volver al PC", callback_data='menu_casa')]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb_volver), parse_mode='Markdown')
        return MENU


# 5. Botón SEGUIMIENTO SERIES
    elif query.data == 'tracker':
        return await tracker_menu_handler(update, context)

# 6. Botón AYUDA (Centro de Ayuda Visual)
    elif query.data == 'help':
        try:
            aria_status = "🟢 Online" if aria2.get_version() else "🔴 Offline"
        except:
            aria_status = "🔴 Offline"

        help_text = (
            "❓ **Ayuda**\n\n"
            f"El bot está en línea. El motor de descargas está {aria_status}.\n\n"
            "Elige de qué quieres que te explique el uso:"
        )
        
        kb_ayuda = [
            [InlineKeyboardButton("🧲 Cómo pegar un enlace", callback_data='help_magnet')],
            [InlineKeyboardButton("🔍 Cómo buscar una serie", callback_data='help_search_info')],
            [InlineKeyboardButton("📺 Cómo seguir una serie", callback_data='help_tracker_info')],
            [InlineKeyboardButton("📱 Enlaces de redes", callback_data='help_social_info')],
            [InlineKeyboardButton("🔙 Volver al Bot", callback_data='menu_bot')]
        ]
        await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(kb_ayuda), parse_mode='Markdown')
        return MENU

    # 6.1 Ayuda - Magnet
    elif query.data == 'help_magnet':
        texto = (
            "🧲 **AYUDA: DESCARGAS (MAGNET Y TORRENT)**\n\n"
            "Tienes **2 formas** de bajar algo si ya tienes el archivo:\n\n"
            "1️⃣ **Enlace:** Entra en Bajar → Pegar enlace y manda un enlace que empiece por `magnet:?xt=...`\n"
            "2️⃣ **Archivo .torrent:** Envíalo al chat. El bot lo detecta y empieza a bajarlo.\n\n"
            "💡 _Durante la descarga, verás una barra de progreso. Puedes cancelar la descarga pulsando el botón rojo '❌ Cancelar'._"
        )
        kb = [[InlineKeyboardButton("🔙 Volver a Ayuda", callback_data='help')]]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return MENU

    # 6.2 Ayuda - Buscador
    elif query.data == 'help_search_info':
        texto = (
            "🔍 **AYUDA: BUSCADOR INTEGRADO**\n\n"
            "Si no tienes el enlace, el bot busca por ti.\n\n"
            "• Entra en Bajar → Serie o anime y escribe el nombre (ej: `Matrix` o `Jujutsu Kaisen`).\n"
            "• **Anime:** Nyaa, AnimeTosho, TPB-Anime y EliteTorrent. Prioriza castellano, VOSE y 1080p/4K.\n"
            "• **Cine:** YTS y TPB.\n"
            "• Te mostrará una lista de botones. Si tiene una bandera 🇪🇸, significa que está en castellano.\n"
            "• Usa los botones de Siguiente/Anterior para navegar por los resultados."
        )
        kb = [[InlineKeyboardButton("🔙 Volver a Ayuda", callback_data='help')]]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return MENU

    # 6.3 Ayuda - Rastreador
    elif query.data == 'help_tracker_info':
        texto = (
            "📺 **AYUDA: RASTREADOR DE SERIES**\n\n"
            "Está en En curso → Series que sigo. Si la serie sigue en emisión:\n\n"
            "1️⃣ Añade el nombre (ej: `One Piece`).\n"
            "2️⃣ El bot vigilará internet cada 30 minutos sin que tú hagas nada.\n"
            "3️⃣ Cuando salga un capítulo nuevo, **te mandará un mensaje al móvil** con un botón para descargarlo al instante.\n\n"
            "💡 _Intenta escribir el nombre exacto de la serie para no recibir notificaciones de cosas parecidas._"
        )
        kb = [[InlineKeyboardButton("🔙 Volver a Ayuda", callback_data='help')]]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return MENU
# 6.4 Ayuda - Redes Sociales
    elif query.data == 'help_social_info':
        texto = (
            "📱 **AYUDA: REDES SOCIALES Y MÚSICA**\n\n"
            "¡El bot detecta enlaces automáticamente! Solo tienes que copiar un link y pegarlo en el chat.\n\n"
            "• **YouTube:** Elige si quieres vídeo en 1080p, 720p o pasarlo a MP3.\n"
            "• **YouTube Music:** Descarga canciones sueltas directamente en MP3.\n"
            "• **TikTok / Instagram:** Descarga el vídeo en su calidad original sin marcas de agua raras.\n\n"
            "💡 _Si el archivo pesa menos de 50MB, te lo mandaré por aquí. Si es más grande, lo guardaré en el servidor._"
        )
        kb = [[InlineKeyboardButton("🔙 Volver a Ayuda", callback_data='help')]]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return MENU
    # 7. Lógica para REINICIAR PC
    elif query.data == 'restart_pc':
        await query.edit_message_text(
            "🔄 **REINICIANDO SERVIDOR**\n\n"
            "El PC se reiniciará en 5 segundos.\n"
            "MiBot y el Panel de escritorio volverán solos al iniciar Windows.",
            parse_mode='Markdown'
        )
        # Ejecutamos el comando de Windows (shutdown /r = restart, /t 5 = en 5 segundos)
        os.system("shutdown /r /t 5")
        return MENU

# 8. MODO CINE EN CASA (Sugerencias Inteligentes)
    elif query.data == 'suggest_movie':
        await query.edit_message_text("🎲 **Modo Cine en Casa**\n\nBuscando qué es tendencia ahora mismo...", parse_mode='Markdown')
        try:
            # Plan Maestro: Usar la API pública de Apple (Top 100 Películas en España)
            url = "https://itunes.apple.com/es/rss/topmovies/limit=100/json"
            res = requests.get(url, timeout=10).json()
            
            movies = res['feed']['entry']
            
            movie = random.choice(movies)
            title = movie['im:name']['label']
            
            clean_title = re.sub(r'\(.*?\)', '', title).strip()
            
            synopsis = movie.get('summary', {}).get('label', 'Sin resumen disponible.')
            synopsis = re.sub(r'<[^>]+>', '', synopsis)
            synopsis = md(synopsis)
            if len(synopsis) > 500:
                synopsis = synopsis[:500] + "..."
                
            context.user_data['suggested_title'] = clean_title
            
            msg = (
                f"🎲 **Sorpréndeme**\n\n"
                "Es una película que está de moda. Si te gusta, pulsa Buscar y la bajamos. "
                "Otra sugerencia pide una distinta.\n\n"
                f"🎬 **Título:** `{clean_title}`\n"
                f"🔥 **Top Tendencias en España**\n\n"
                f"📖 **Sinopsis:**\n_{synopsis}_\n"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔍 Buscar y Descargar", callback_data='search_suggested')],
                [InlineKeyboardButton("🎲 Otra sugerencia", callback_data='suggest_movie')],
                [InlineKeyboardButton("🔙 Volver a Bajar", callback_data='menu_bajar')]
            ]
            
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception as e:
            print(f"Error crítico en Sugerencias: {e}") 
            await query.edit_message_text("❌ Hubo un error buscando sugerencias. Revisa tu conexión.", reply_markup=get_keyboard("back"))
        return MENU

# ==========================================
# 🗂️ MOTOR DEL EXPLORADOR DE ARCHIVOS (TODO EL PC)
# ==========================================
async def file_explorer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 1. Mostrar todos los discos duros conectados
    if query.data == 'explorer_root':
        context.user_data['current_path'] = 'ROOT'
        drives = [d.device for d in psutil.disk_partitions() if 'cdrom' not in d.opts and d.fstype != '']
        context.user_data['explorer_items'] = drives
        
        kb = []
        for i, drive in enumerate(drives):
            kb.append([InlineKeyboardButton(f"💾 Disco {drive}", callback_data=f'exp_go_{i}')])
        kb.append([InlineKeyboardButton("🔙 Volver a En curso", callback_data='menu_curso')])
        
        await query.edit_message_text(
            "🗂️ **Archivos**\n\n"
            "Elige un disco. **Z:** es Google Drive. "
            "Dentro puedes abrir carpetas, enviarte un archivo al chat o borrarlo.",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown'
        )
        return MENU
        
    # 2. Navegar hacia adelante (entrar en carpeta o disco)
    elif query.data.startswith('exp_go_'):
        idx = int(query.data.split('_')[2])
        items = context.user_data.get('explorer_items', [])
        if idx >= len(items): return MENU
        
        target = items[idx]
        current_path = context.user_data.get('current_path', 'ROOT')
        
        new_path = target if current_path == 'ROOT' else os.path.join(current_path, target)
            
        if os.path.isdir(new_path):
            try:
                elementos = os.listdir(new_path)
                carpetas = sorted([e for e in elementos if os.path.isdir(os.path.join(new_path, e))])
                archivos = sorted([e for e in elementos if os.path.isfile(os.path.join(new_path, e))])
                
                context.user_data['current_path'] = new_path
                context.user_data['explorer_items'] = carpetas + archivos
                context.user_data['exp_page'] = 0
                await render_explorer(query, context)
            except PermissionError:
                await query.answer("⛔ Acceso denegado a esta carpeta por Windows", show_alert=True)
                
        elif os.path.isfile(new_path):
            size = format_size(os.path.getsize(new_path))
            context.user_data['selected_file'] = new_path
            
            kb = [
                [InlineKeyboardButton("📲 Enviar a Telegram", callback_data='exp_dl')],
                [InlineKeyboardButton("🗑️ Borrar Archivo", callback_data='exp_del')],
                [InlineKeyboardButton("🔙 Volver a la carpeta", callback_data='exp_back')]
            ]
            await query.edit_message_text(
                f"📄 **Archivo**\n\n"
                "Enviar lo manda a este chat si no pesa demasiado. Borrar lo elimina del disco.\n\n"
                f"**Nombre:** `{target}`\n**Ruta:** `{new_path}`\n**Peso:** {size}",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown'
            )

    # 3. Navegar hacia atrás (subir de nivel)
    elif query.data == 'exp_back':
        current = context.user_data.get('current_path', 'ROOT')
        parent = os.path.dirname(current) if current and current != 'ROOT' else 'ROOT'
        if current == 'ROOT' or parent == current or parent == "":
            context.user_data['current_path'] = 'ROOT'
            drives = [d.device for d in psutil.disk_partitions() if 'cdrom' not in d.opts and d.fstype != '']
            if 'Z:\\' not in drives and os.path.exists('Z:\\'):
                drives.append('Z:\\')
            context.user_data['explorer_items'] = drives

            kb = []
            for i, drive in enumerate(drives):
                kb.append([InlineKeyboardButton(f"💾 Disco {drive}", callback_data=f'exp_go_{i}')])
            kb.append([InlineKeyboardButton("🔙 Volver a En curso", callback_data='menu_curso')])

            await query.edit_message_text(
                "🗂️ **Archivos**\n\n"
                "Elige un disco. **Z:** es Google Drive. "
                "Dentro puedes abrir carpetas, enviarte un archivo al chat o borrarlo.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown'
            )
            return MENU

        context.user_data['current_path'] = parent
        try:
            elementos = os.listdir(parent)
            carpetas = sorted([e for e in elementos if os.path.isdir(os.path.join(parent, e))])
            archivos = sorted([e for e in elementos if os.path.isfile(os.path.join(parent, e))])
            context.user_data['explorer_items'] = carpetas + archivos
            context.user_data['exp_page'] = 0
            await render_explorer(query, context)
        except Exception:
            await query.answer("⛔ No puedo leer esa carpeta", show_alert=True)
        return MENU
    
    # 4. Paginación de carpetas con muchos archivos
    elif query.data == 'exp_page_next':
        context.user_data['exp_page'] += 1
        await render_explorer(query, context)
    elif query.data == 'exp_page_prev':
        context.user_data['exp_page'] -= 1
        await render_explorer(query, context)
        
    return MENU

async def render_explorer(query, context):
    path = context.user_data['current_path']
    items = context.user_data['explorer_items']
    page = context.user_data.get('exp_page', 0)
    
    ITEMS_PER_PAGE = 10
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    
    kb = [[InlineKeyboardButton("⬆️ Subir de nivel", callback_data='exp_back')]]
        
    for i, item in enumerate(items[start:end]):
        real_idx = start + i
        full_path = os.path.join(path, item)
        icono = "📁" if os.path.isdir(full_path) else "📄"
        nombre_corto = (item[:30] + '..') if len(item) > 30 else item
        kb.append([InlineKeyboardButton(f"{icono} {nombre_corto}", callback_data=f'exp_go_{real_idx}')])
            
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️ Anterior", callback_data='exp_page_prev'))
    if end < len(items): nav.append(InlineKeyboardButton("Siguiente ➡️", callback_data='exp_page_next'))
    if nav: kb.append(nav)
    
    kb.append([InlineKeyboardButton("🔙 Volver a En curso", callback_data='menu_curso')])
    
    await query.edit_message_text(
        f"🗂️ **Archivos**\n📍 `{path}`\n\n"
        "📁 es carpeta. 📄 es archivo. Si pulsas un archivo puedes enviártelo o borrarlo.\n\n"
        f"_Elementos ({len(items)}):_",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown'
    )

async def file_explorer_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_path = context.user_data.get('selected_file')
    
    if query.data == 'exp_dl':
        if not file_path or not os.path.exists(file_path):
            await query.edit_message_text("❌ El archivo ya no existe.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Atrás", callback_data='exp_back')]]))
            return MENU
        size = os.path.getsize(file_path)
        if size > 49 * 1024 * 1024:
            await query.answer("❌ Pesa más de 50MB. Telegram no permite enviarlo.", show_alert=True)
            return MENU
        
        await query.edit_message_text(f"📤 **Enviando a Telegram...**\n`{os.path.basename(file_path)}`", parse_mode='Markdown')
        try:
            with open(file_path, 'rb') as f:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
            # Refrescamos visualmente la carpeta en la que estábamos
            await render_explorer(query, context)
        except Exception as e:
            await query.edit_message_text(f"❌ Error al enviar: {e}")
            
    elif query.data == 'exp_del':
        try:
            os.remove(file_path)
            await query.answer("✅ Archivo borrado", show_alert=True)
            
            # Recargamos el contenido de la carpeta actual tras el borrado
            parent = context.user_data['current_path']
            elementos = os.listdir(parent)
            carpetas = sorted([e for e in elementos if os.path.isdir(os.path.join(parent, e))])
            archivos = sorted([e for e in elementos if os.path.isfile(os.path.join(parent, e))])
            context.user_data['explorer_items'] = carpetas + archivos
            context.user_data['exp_page'] = 0
            
            await render_explorer(query, context)
        except Exception as e:
            await query.answer(f"❌ Error al borrar: {e}", show_alert=True)
            
    return MENU


async def game_launcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔫 Lanzar Fortnite", callback_data='launch_fortnite')],
        [InlineKeyboardButton("🍄 Juegos de Switch (Ryujinx)", callback_data='menu_ryujinx')], 
        [InlineKeyboardButton("🛑 CERRAR TODO (Kill Switch)", callback_data='kill_games')],
        [InlineKeyboardButton("🔙 Volver a Parsec", callback_data='parsec_status')]
    ]
    
    await query.edit_message_text(
        "🚀 **Lanzador**\n\n"
        "Abre un juego en el PC para jugarlo por Parsec. "
        "Cerrar todo mata Fortnite y el emulador de Switch.\n\n"
        "🔫 **Fortnite** — lo abre en el ordenador.\n"
        "🍄 **Switch** — elige el juego y si juegas con el móvil o con mando.\n"
        "🛑 **Cerrar todo** — cierra lo que esté abierto.",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )
    return MENU

# --- 1. MENÚ: ELEGIR JUEGO DE SWITCH ---
async def ryujinx_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Juego 1 de NS", callback_data='ryudev_juego1')],
        [InlineKeyboardButton("Juego 2 de NS", callback_data='ryudev_juego2')],
        [InlineKeyboardButton("🛑 Kill Switch", callback_data='kill_games')],
        [InlineKeyboardButton("🔙 Volver al Lanzador", callback_data='game_launcher')]
    ]
    
    await query.edit_message_text("🍄 **EMULADOR SWITCH**\n\n¿Qué juego quieres arrancar directamente?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return MENU

# --- 2. MENÚ: ELEGIR DISPOSITIVO ---
async def ryujinx_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    juego_seleccionado = query.data.split('_')[1] 
    
    keyboard = [
        [InlineKeyboardButton("📱 Móvil / Tablet (Controles Táctiles)", callback_data=f'ryuboot_mob_{juego_seleccionado}')],
        [InlineKeyboardButton("💻 PC (Mando físico / Teclado)", callback_data=f'ryuboot_pc_{juego_seleccionado}')],
        [InlineKeyboardButton("🛑 Kill Switch", callback_data='kill_games')],
        [InlineKeyboardButton("🔙 Elegir otro juego", callback_data='menu_ryujinx')]
    ]
    
    await query.edit_message_text("🎮 **Configuración de Controles**\n\n¿Desde qué dispositivo te vas a conectar por Parsec?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return MENU

# --- 3. LANZADOR AVANZADO DE RYUJINX ---
async def ryujinx_boot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    partes = query.data.split('_')
    dispositivo = partes[1] 
    id_juego = partes[2]    
    
    juegos = {
        'juego1': (r"C:\Users\JUEGOS\Desktop\Emulador NS\Juegos\MarioKart.nsp", "Ejemplo de juego 1 Mario kart"),
        'juego2': (r"C:\Users\JUEGOS\Desktop\Emulador NS\Juegos\Zelda.nsp", "Ejemplo de juego 2 Zelda")
    }
    
    ruta_rom, nombre_juego = juegos.get(id_juego, (None, None))
    ruta_ryujinx = r"C:\Users\JUEGOS\Desktop\Emulador NS\Ryujinx.exe"
    
    if not ruta_rom or not os.path.exists(ruta_rom):
        kb = [[InlineKeyboardButton("🔙 Volver", callback_data='menu_ryujinx')]]
        await query.edit_message_text(f"❌ **Error:** No encuentro la ROM en:\n`{ruta_rom}`", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return MENU
        
    context.user_data['kill_signal'] = False 
    comando = f'"{ruta_ryujinx}" "{ruta_rom}" --fullscreen'
    subprocess.Popen(comando, shell=True) 
    
    if dispositivo == 'mob':
        instrucciones = ("📱 **MODO MÓVIL ACTIVADO**\n\n1. Conéctate por Parsec desde tu móvil.\n2. Toca el **icono de Parsec** flotante.\n3. Selecciona el mando (Gamepad) para usar controles táctiles.\n")
    else:
        instrucciones = "💻 **MODO PC ACTIVADO**\n\nTu mando o teclado ya están listos."
        
    asyncio.create_task(animate_game_loading(query.message, f"Ryujinx: {nombre_juego}", 15, context, instrucciones_extra=instrucciones))
    return MENU

# --- 4. LANZADOR NORMAL (Fortnite y Kill Switch) ---
async def launch_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    accion = query.data
    usuario = update.effective_user.first_name
    
    if accion == 'kill_games':
        log_accion(usuario, "Activó el KILL SWITCH de juegos", Fore.RED)
        context.user_data['kill_signal'] = True
        await query.edit_message_text("🛑 **Ejecutando Kill Switch...**")
        
        os.system("taskkill /F /IM FortniteClient-Win64-Shipping.exe /T 2>NUL")
        os.system("taskkill /F /IM FortniteLauncher.exe /T 2>NUL")
        os.system("taskkill /F /IM EpicGamesLauncher.exe /T 2>NUL")
        os.system("taskkill /F /IM Ryujinx.exe /T 2>NUL")
        
        await asyncio.sleep(1)
        kb = [[InlineKeyboardButton("🔙 Volver al Lanzador", callback_data='game_launcher')]]
        await query.edit_message_text("✅ **Juegos cerrados a la fuerza.** El escritorio está limpio.", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return MENU
        
    rutas = { 'launch_fortnite': (r"C:\Users\JUEGOS\Desktop\Fortnite.url", "Fortnite", 35) }
    datos_juego = rutas.get(accion)
    
    if datos_juego and os.path.exists(datos_juego[0]):
        context.user_data['kill_signal'] = False 
        log_accion(usuario, f"Lanzando {datos_juego[1]}", Fore.GREEN)
        os.startfile(datos_juego[0]) 
        asyncio.create_task(animate_game_loading(query.message, datos_juego[1], datos_juego[2], context))
    else:
        kb = [[InlineKeyboardButton("🔙 Volver al Lanzador", callback_data='game_launcher')]]
        await query.edit_message_text(f"❌ **Error:** No encuentro el archivo.", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    return MENU

# --- ANIMADOR VISUAL ---
async def animate_game_loading(message, nombre_juego, tiempo_est, context, instrucciones_extra=""):
    pasos = 20
    tiempo_por_paso = tiempo_est / pasos

    for i in range(pasos + 1):
        if context.user_data.get('kill_signal'): return 
        porcentaje = int((i / pasos) * 100)
        bar = "█" * i + "▒" * (pasos - i)
        tiempo_restante = int(tiempo_est - (i * tiempo_por_paso))
        kb_cancelar = [[InlineKeyboardButton("🛑 CERRAR (Kill Switch)", callback_data='kill_games')]]
        msg = (f"🚀 **INICIANDO SISTEMA DE JUEGO**\n\n🎮 **Juego:** `{nombre_juego}`\n`{bar}` **{porcentaje}%**\n\n⏳ **Arranque estimado:** {tiempo_restante}s\n⚙️ _Preparando motor..._")
        try: await message.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb_cancelar), parse_mode='Markdown')
        except: pass
        if i < pasos: await asyncio.sleep(tiempo_por_paso)

    if not context.user_data.get('kill_signal'):
        kb_final = [[InlineKeyboardButton("🛑 Cerrar Juego", callback_data='kill_games')], [InlineKeyboardButton("🔙 Volver al Monitor Parsec", callback_data='parsec_status')]]
        msg_final = (f"✅ **¡{nombre_juego} ESTÁ LISTO!**\n\n{instrucciones_extra}\n\n🎮 Ya puedes avisar a tu colega o conectarte.")
        try: await message.edit_text(msg_final, reply_markup=InlineKeyboardMarkup(kb_final), parse_mode='Markdown')
        except: pass


# --- MENÚ PRINCIPAL DEL TRACKER ---
async def tracker_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass

    series_list = load_tracked_series()
    keyboard = []

    if not series_list:
        status_text = (
            "📺 **Series que sigo**\n\n"
            "Escribe una serie y la vigilo. Si sale un capítulo nuevo, te aviso aquí con un botón para bajarlo.\n\n"
            "Todavía no sigues ninguna. Pulsa Añadir y escribe el nombre exacto."
        )
    else:
        status_text = (
            "📺 **Series que sigo**\n\n"
            "Las vigilo solas. Si sale un capítulo, te aviso. "
            "Buscar ahora mira ya, sin esperar. El calendario enseña estrenos de hoy.\n\n"
        )
        for name, data in series_list.items():
            last = data.get('last_notified', 'Ninguno')
            status_text += f"🔹 **{md(name)}**\n   └ Último cap: _{md(last[:40])}_\n\n"
            keyboard.append([InlineKeyboardButton(f"❌ Dejar de seguir: {name[:28]}", callback_data=f'del_serie_{serie_token(name)}')])

    keyboard.append([InlineKeyboardButton("➕ Añadir Nueva Serie", callback_data='track_add')])
    keyboard.append([InlineKeyboardButton("🔄 Buscar Capítulos Ahora", callback_data='track_check_now')])
    keyboard.append([InlineKeyboardButton("📅 Calendario Estrenos (Hoy)", callback_data='anime_calendar')])
    keyboard.append([InlineKeyboardButton("🔙 Volver a En curso", callback_data='menu_curso')])

    if update.callback_query:
        await query.edit_message_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    return MENU
# --- PASO 1: PEDIR NOMBRE ---
async def track_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✍️ **Añadir una serie**\n\n"
        "Escribe el nombre exacto. A partir de ahora miro cada 30 minutos si hay capítulo nuevo "
        "y te aviso por aquí.\n\n"
        "Ejemplo: `Jujutsu Kaisen`, `One Piece`.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver a las series", callback_data='tracker_menu')]]),
        parse_mode='Markdown'
    )
    return AWAITING_NEW_SERIES 

# --- PASO 2: GUARDAR SERIE ---
async def track_add_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    serie_name = update.message.text.strip()

    data = load_tracked_series()
    data[serie_name] = {'last_hash': '', 'last_notified': 'Nada aún'}
    save_tracked_series(data)

    await update.message.reply_text(f"✅ **¡Añadida!**\nAhora buscaré capítulos nuevos de `{serie_name}` automáticamente.", parse_mode='Markdown')
    return await tracker_menu_handler(update, context)

async def track_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_tracked_series()
    if not data:
        await query.edit_message_text("❌ No hay series para borrar.", reply_markup=get_keyboard("back"))
        return MENU

    keyboard = []
    for name in data.keys():
        keyboard.append([InlineKeyboardButton(f"❌ {name[:40]}", callback_data=f'del_serie_{serie_token(name)}')])
    
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='tracker_menu')])

    await query.edit_message_text("🗑️ **Selecciona qué serie borrar:**", reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU
async def track_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    token = query.data.replace('del_serie_', '')
    data = load_tracked_series()
    serie_to_del = serie_by_token(token, data)

    if serie_to_del and serie_to_del in data:
        del data[serie_to_del]
        save_tracked_series(data)
        await query.edit_message_text(f"🗑️ `{serie_to_del}` eliminada de la lista.", parse_mode='Markdown')
        await asyncio.sleep(1)
        return await tracker_menu_handler(update, context)
    else:
        await query.edit_message_text("⚠️ Error: Esa serie ya no estaba.", reply_markup=get_keyboard("back"))
        return MENU
async def check_series_updates(context: ContextTypes.DEFAULT_TYPE):
    print("⚡ Ejecutando chequeo ASÍNCRONO multi-hilo de series...")

    data = load_tracked_series()
    if not data: return
    
    # --- 🤖 CLONES RASTREADORES (Funciones para los hilos) ---
    def fetch_tioanime():
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            res = scraper.get("https://tioanime.com/", timeout=10)
            return BeautifulSoup(res.text, 'html.parser').select('.episodes li')
        except: return []

    def fetch_nyaa(serie_name):
        try:
            query_url = serie_name.replace(' ', '+')
            url = f"https://nyaa.si/?f=0&c=0_0&q={query_url}&s=id&o=desc" 
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return serie_name, BeautifulSoup(res.text, 'html.parser')
        except: pass
        return serie_name, None

    # --- 🚀 LANZAMIENTO SIMULTÁNEO (Magia Asíncrona) ---
    # Creamos una tarea para TioAnime y una para CADA serie que sigas
    tareas_nyaa = [asyncio.to_thread(fetch_nyaa, s_name) for s_name in data.keys()]
    tarea_tio = asyncio.to_thread(fetch_tioanime)
    
    # Disparamos todas a la vez y obligamos al bot a esperar a que todas vuelvan
    resultados_nyaa = await asyncio.gather(*tareas_nyaa)
    ultimos_eps_tio = await tarea_tio

    hubo_cambios = False

    # --- 1. PROCESAR RADAR VISUAL (TioAnime) ---
    for ep in ultimos_eps_tio:
        a_tag = ep.find('a')
        if not a_tag: continue
        
        ep_link = "https://tioanime.com" + a_tag['href']
        img_tag = ep.find('img')
        cover_url = "https://tioanime.com" + img_tag['src'] if img_tag else ""
        title_tag = ep.find('h3', class_='title') or ep.find('h3')
        ep_title = title_tag.text.strip() if title_tag else "Anime"
        
        for serie_name, info in data.items():
            if serie_name.lower() in ep_title.lower():
                ep_hash = ep_link.split('/')[-1]
                if ep_hash != info.get('last_hash'):
                    context.application.bot_data[f"track_anime_{ep_hash}"] = ep_link
                    kb = [
                        [InlineKeyboardButton("⬇️ Extraer y Descargar", callback_data=f'dlanime_{ep_hash}')],
                        [InlineKeyboardButton("❌ Dejar de seguir serie", callback_data=f'del_serie_{serie_token(serie_name)}')]
                    ]
                    msg = (f"🌟 **¡NUEVO CAPÍTULO DISPONIBLE!** 🌟\n\n👺 **Anime:** `{serie_name}`\n📺 **Episodio:** `{ep_title}`\n🌐 **Fuente:** TioAnime (Sub Español)\n\n¿Qué hacemos con él?")
                    
                    for user_id in ADMIN_IDS:
                        try:
                            if cover_url: await context.bot.send_photo(chat_id=user_id, photo=cover_url, caption=msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
                            else: await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
                        except Exception as e: print(e)
                    
                    data[serie_name]['last_hash'] = ep_hash
                    data[serie_name]['last_notified'] = ep_title
                    hubo_cambios = True

    # --- 2. PROCESAR TORRENTS (Nyaa) ---
    for serie_name, soup in resultados_nyaa:
        if not soup: continue
        info = data.get(serie_name, {})
        
        rows = soup.select('tr.default, tr.success, tr.danger')
        for row in rows[:5]:
            try:
                cols = row.find_all('td')
                if len(cols) < 3:
                    continue
                link_list = cols[1].find_all('a')
                if not link_list:
                    continue
                title = link_list[-1].text.strip() if len(link_list) > 1 else link_list[0].text.strip()
                links = cols[2].find_all('a')
                magnet = next((l['href'] for l in links if l['href'].startswith('magnet:')), None)
                magnet_hash = re.search(r'btih:([a-zA-Z0-9]+)', magnet).group(1) if magnet else None
            except Exception:
                continue

            if not magnet or not magnet_hash: continue

            title_lower = title.lower()
            if serie_name.lower() not in title_lower: continue
            if magnet_hash == info.get('last_hash'): break 

            is_spanish = any(key in title_lower for key in KEYWORDS_ES)
            is_hd = '1080' in title_lower

            if is_spanish:
                context.application.bot_data[f"hash_{magnet_hash}"] = magnet
                keyboard = [[InlineKeyboardButton("⬇️ Descargar Ahora", callback_data=f'dl_track_{magnet_hash}')]]
                msg = (f"🔔 **¡Nuevo Capítulo Detectado!**\n\n📺 **Serie:** {md(serie_name)}\n📄 **Archivo:** `{code(title)}`\n✨ **Calidad:** {'1080p ✅' if is_hd else 'Estándar'}\n\n¿Quieres descargarlo?")

                for user_id in ADMIN_IDS:
                    try: await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
                    except: pass

                data[serie_name]['last_hash'] = magnet_hash
                data[serie_name]['last_notified'] = title
                hubo_cambios = True
                break 

    if hubo_cambios:
        save_tracked_series(data)

async def manual_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔍 Buscando actualizaciones en todas tus series...")
    await check_series_updates(context) 
    await query.message.reply_text("✅ Búsqueda finalizada.")
    return MENU

async def handle_tracked_anime_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    ep_hash = query.data.replace('dlanime_', '')
    ep_link = context.application.bot_data.get(f"track_anime_{ep_hash}")
    
    if ep_link:
        class FakeMessage:
            def __init__(self, text): self.text = text
            async def reply_text(self, text, **kwargs): return await query.message.reply_text(text, **kwargs)
        
        fake_update = update
        fake_update.message = FakeMessage(ep_link)
        
        await query.edit_message_caption(caption=f"🚀 **Recibido.** Conectando con los servidores ocultos...", reply_markup=None, parse_mode='Markdown')
        return await handle_social_link(fake_update, context)
    else:
        await query.message.reply_text("⚠️ El enlace ha caducado. Búscalo manualmente.")
        return MENU

async def handle_tracked_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    magnet_hash = query.data.replace('dl_track_', '')

    magnet_link = context.application.bot_data.get(f"hash_{magnet_hash}")

    if magnet_link:
        context.user_data['search_magnet'] = magnet_link

        await query.message.reply_text(f"🚀 **Recibido.** Iniciando descarga de la serie...")
        return await process_magnet(update, context)
    else:
        await query.message.reply_text("⚠️ El enlace ha caducado o hay un error. Intenta buscar manualmente.")
        return MENU


def find_largest_file(directory):
    """Busca recursivamente el archivo más grande en una carpeta (el vídeo)."""
    largest_file = None
    max_size = 0

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                size = os.path.getsize(file_path)
                if size > max_size and size > 50 * 1024 * 1024:
                    max_size = size
                    largest_file = file_path
            except OSError:
                continue

    return largest_file
# ==========================================
# ⬇️ LÓGICA DE DESCARGA (MAGNET)
# ==========================================



def añadir_a_aria(enlace):
    """Acepta un magnet, un .torrent publicado en la ficha o un enlace directo."""
    if not enlace:
        raise ValueError("No hay enlace de descarga guardado")
    if str(enlace).startswith("magnet:"):
        return aria2.add_magnet(enlace)
    if ".torrent" in str(enlace).split("?")[0].lower():
        respuesta = requests.get(enlace, headers=BROWSER_HEADERS, timeout=20)
        respuesta.raise_for_status()
        ruta = os.path.join(BASE_DOWNLOAD_PATH, f"ficha_{int(time.time())}.torrent")
        with open(ruta, "wb") as archivo:
            archivo.write(respuesta.content)
        descarga = aria2.add_torrent(ruta)
        try:
            os.remove(ruta)
        except Exception:
            pass
        return descarga
    return aria2.add_uris([enlace])


async def process_magnet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = None
    download = None
    usuario = update.effective_user.first_name
    log_accion(usuario, "Ha iniciado una nueva descarga 🚀", Fore.CYAN)

    try:
        if update.message and update.message.document:
            status_msg = await bot_send(update, context, "📂 **Leyendo archivo .torrent...**", parse_mode='Markdown')
            torrent_file = await update.message.document.get_file()
            file_path = f"{update.message.document.file_name}"
            await torrent_file.download_to_drive(file_path)
            download = aria2.add_torrent(file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
            try:
                await update.message.delete()
            except Exception:
                pass

        elif update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass
            magnet_link = context.user_data.get('search_magnet')
            status_msg = await bot_send(update, context, "⏳ **Recibido. Iniciando descarga...**", parse_mode='Markdown')
            download = añadir_a_aria(magnet_link)

        elif update.message and update.message.text:
            magnet_link = update.message.text.strip()
            status_msg = await bot_send(update, context, "⏳ **Validando enlace...**", parse_mode='Markdown')
            try:
                await update.message.delete()
            except Exception:
                pass
            download = añadir_a_aria(magnet_link)

    except Exception as e:
        msg = f"❌ Error al añadir descarga: {md(e)}"
        if status_msg:
            await status_msg.edit_text(msg)
        else:
            await bot_send(update, context, msg)
        return MENU

    if download is None or status_msg is None:
        await bot_send(update, context, "❌ No he podido preparar la descarga.")
        return MENU

    asyncio.create_task(process_magnet_loop(update, context, download, status_msg))
    return MENU



# ==========================================
# 📥 GESTOR DE DESCARGAS Y CONTROL
# ==========================================
async def dl_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        downloads = aria2.get_downloads()
    except Exception as e:
        await query.edit_message_text(f"❌ Error conectando con Aria2: {e}", reply_markup=get_keyboard("back"))
        return MENU

    if not downloads:
        kb = [[InlineKeyboardButton("🔙 Volver a En curso", callback_data='menu_curso')]]
        await query.edit_message_text(
            "📥 **Descargas activas**\n\n"
            "Aquí salen los torrents y archivos que se están bajando ahora. "
            "Puedes pausarlos, reanudarlos o borrarlos.\n\n"
            "No hay ninguna descarga en este momento.",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown'
        )
        return MENU

    text = (
        "📥 **Descargas activas**\n\n"
        "Pausar para y lo deja a medias. Reanudar sigue. Borrar lo quita de la cola.\n\n"
    )
    keyboard = []

    for d in downloads[:10]:
        status_emoji = "▶️" if d.status == 'active' else "⏸️" if d.status == 'paused' else "⏳" if d.status == 'waiting' else "🛑"
        name = (d.name[:25] + '..') if len(d.name) > 25 else d.name
        
        text += f"{status_emoji} `{name}`\n"
        text += f"├ Progreso: {d.progress_string()} | Vel: {d.download_speed_string()}\n"
        text += f"└ Estado: {d.status.capitalize()}\n\n"

        row = []
        if d.status in ['active', 'waiting']:
            row.append(InlineKeyboardButton(f"⏸️ Pausar", callback_data=f'pause_dl_{d.gid}'))
        elif d.status == 'paused':
            row.append(InlineKeyboardButton(f"▶️ Reanudar", callback_data=f'resume_dl_{d.gid}'))
            
        row.append(InlineKeyboardButton("❌ Borrar", callback_data=f'ask_cancel_{d.gid}'))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔄 Actualizar Estado", callback_data='dl_manager')])
    keyboard.append([InlineKeyboardButton("🔙 Volver a En curso", callback_data='menu_curso')])

    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except Exception as e:
        if "Message is not modified" not in str(e):
            print(f"Error menor en gestor: {e}")
            
    return MENU

async def pause_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    gid = query.data.replace('pause_dl_', '')
    try:
        aria2.get_download(gid).pause()
        await query.answer("⏸️ Descarga pausada")
    except:
        await query.answer("❌ Error al pausar", show_alert=True)
    return await dl_manager(update, context)

async def resume_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    gid = query.data.replace('resume_dl_', '')
    try:
        aria2.get_download(gid).resume()
        await query.answer("▶️ Descarga reanudada")
    except:
        await query.answer("❌ Error al reanudar", show_alert=True)
    return await dl_manager(update, context)

async def hide_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    gid = query.data.replace('hide_dl_', '')
    context.user_data[f'hide_dl_{gid}'] = True
    await query.answer("👀 Ocultado. Sigue descargando en 2º plano.")
    await query.edit_message_text(
        "🏠 **MENÚ PRINCIPAL**\n\nLa descarga sigue activa en segundo plano.\nSelecciona una categoría:",
        reply_markup=get_keyboard("main", update.effective_user.id),
        parse_mode='Markdown'
    )
    return MENU

async def process_magnet_loop(update: Update, context: ContextTypes.DEFAULT_TYPE, download, status_msg):
    last_edit_time = 0
    
    while True:
        if download.status == 'paused':
            kb_cancel = InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Reanudar", callback_data=f'resume_dl_{download.gid}'), InlineKeyboardButton("❌ Cancelar", callback_data=f'ask_cancel_{download.gid}')],
                [InlineKeyboardButton("👀 Ocultar en 2º plano", callback_data=f'hide_dl_{download.gid}')]
            ])
        else:
            kb_cancel = InlineKeyboardMarkup([
                [InlineKeyboardButton("⏸️ Pausar", callback_data=f'pause_dl_{download.gid}'), InlineKeyboardButton("❌ Cancelar", callback_data=f'ask_cancel_{download.gid}')],
                [InlineKeyboardButton("👀 Ocultar en 2º plano", callback_data=f'hide_dl_{download.gid}')]
            ])

        while not download.is_complete:
            try: download.update()
            except:
                is_hidden = context.user_data.get(f'hide_dl_{download.gid}', False)
                if not is_hidden: await status_msg.edit_text("🗑️ La descarga ha sido cancelada.")
                return

            if download.status == 'removed':
                is_hidden = context.user_data.get(f'hide_dl_{download.gid}', False)
                if not is_hidden: await status_msg.edit_text("🛑 **Descarga detenida y eliminada.**", parse_mode='Markdown')
                return
            
            if download.status == 'error':
                is_hidden = context.user_data.get(f'hide_dl_{download.gid}', False)
                if not is_hidden:
                    if float(download.progress) == 0:
                        await status_msg.edit_text("🛑 **Descarga Cancelada o Torrent inactivo.**", parse_mode='Markdown')
                    else:
                        await status_msg.edit_text("❌ Error: Fallo en Aria2 al descargar.")
                return

            progress = float(download.progress)
            speed = download.download_speed_string()
            peers = download.num_seeders
            eta = download.eta_string()
            total_size = download.total_length_string()
            
            if download.status == 'paused':
                state_icon, state_text = "⏸️", "Pausada"
            elif int(peers) == 0 and speed.startswith("0"):
                state_icon, state_text = "⚠️", "Buscando compis..."
            elif int(peers) > 0 and speed.startswith("0"):
                state_icon, state_text = "🐌", "Conectado pero lento..."
            else:
                state_icon, state_text = "🚀", f"Bajando a {speed}"

            current_time = time.time()
            if current_time - last_edit_time >= 4:
                is_prompting = context.user_data.get(f'cancel_prompt_{download.gid}', False)
                is_hidden = context.user_data.get(f'hide_dl_{download.gid}', False)
                
                if not is_prompting and not is_hidden:
                    filled = int(progress / 5)
                    bar = "█" * filled + "▒" * (20 - filled)
                    
                    msg_text = (
                        f"📥 **Gestor de Descarga**\n"
                        f"🎬 `{download.name}`\n\n"
                        f"`{bar}` **{progress:.1f}%**\n\n"
                        f"{state_icon} **Estado:** {state_text}\n"
                        f"👥 **Peers:** {peers} | 📦 **Total:** {total_size}\n"
                        f"⏱️ **Tiempo restante:** {eta}"
                    )
                    try:
                        await status_msg.edit_text(msg_text, reply_markup=kb_cancel, parse_mode='Markdown')
                        last_edit_time = current_time
                    except: pass 
                
            await asyncio.sleep(2)

        # --- VERIFICACIÓN DE FASE (METADATOS vs PELÍCULA REAL) ---
        download.update()
        esperas = 0
        while not download.followed_by_ids and esperas < 25:
            await asyncio.sleep(1)
            try: download.update()
            except: pass
            esperas += 1

        if download.followed_by_ids:
            next_gid = download.followed_by_ids[0]
            download = aria2.get_download(next_gid)
            is_hidden = context.user_data.get(f'hide_dl_{download.gid}', False)
            if not is_hidden:
                await status_msg.edit_text("🔄 **Metadatos leídos.** Asignando espacio en el disco duro...")
            continue
        else:
            break

    is_hidden = context.user_data.get(f'hide_dl_{download.gid}', False)
    if is_hidden:
        status_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="⏳ **Descarga completada en 2º plano.** Procesando el archivo..."
        )
    else:
        await status_msg.edit_text("⏳ **Descarga completada.** Procesando el archivo...")
        
    await asyncio.sleep(2)
    
    real_path = None
    try:
        download.update()
        max_size = 0
        for f in download.files:
            if f.length > max_size and f.path:
                max_size, real_path = f.length, f.path
    except: pass

    if not real_path:
        target_path = os.path.join(BASE_DOWNLOAD_PATH, download.name)
        if os.path.isfile(target_path): real_path = target_path
        elif os.path.isdir(target_path): real_path = find_largest_file(target_path)

    if not real_path:
        await status_msg.edit_text("⚠️ No encontré el archivo de video.")
        return

    real_filename = os.path.basename(real_path)
    context.user_data['filename'] = real_filename
    context.user_data['filepath'] = real_path

    if context.user_data.get('is_apk', False):
        context.user_data['is_apk'] = False 
        await status_msg.edit_text(
            f"✅ **¡APK Descargada con Éxito!**\n\n"
            f"📦 **Archivo:** `{real_filename}`\n"
            f"📂 **Guardado en tu Google Drive** (`D:/Descargas torrent`)\n\n"
            f"📱 _En cuanto se sincronice, abre la app de Drive en tu móvil e instálala desde ahí._", 
            parse_mode='Markdown'
        )
        return MENU

    await status_msg.edit_text(f"✅ **¡Descarga Finalizada!**\n\nArchivo: `{real_filename}`\nVerificando integridad...")
    await asyncio.sleep(1)
    await post_download_menu(update, context)

# ==========================================
# 🎙️ ÓRDENES POR VOZ (transcripción + borrador)
# ==========================================
def teclado_orden_voz(origen="menu"):
    fila_cursor = [InlineKeyboardButton("✅ Enviar a Cursor", callback_data="voice_cursor")]
    fila_buscar = [InlineKeyboardButton("🔎 Buscar torrents", callback_data="voice_search")]
    if origen == "cursor":
        orden = [fila_cursor, fila_buscar]
    elif origen == "search":
        orden = [fila_buscar, fila_cursor]
    else:
        orden = [fila_cursor, fila_buscar]
    orden.append(
        [
            InlineKeyboardButton("✏️ Editar", callback_data="voice_edit"),
            InlineKeyboardButton("🗑 Descartar", callback_data="voice_discard"),
        ]
    )
    return InlineKeyboardMarkup(orden)


def _estado_tras_voz(context, defecto=MENU):
    origen = context.user_data.get("voice_origin", "menu")
    if origen == "cursor":
        return AWAITING_CURSOR
    if origen == "search":
        return AWAITING_SEARCH
    return defecto


async def _mostrar_borrador_voz(update, context, texto, status_msg, motor):
    origen = context.user_data.get("voice_origin", "menu")
    context.user_data["voice_draft"] = texto
    uid = update.effective_user.id
    voice_orders.guardar_borrador(uid, texto, origen=origen, motor=motor)
    aviso = (
        "🎙️ **Transcripción (castellano)**\n\n"
        f"`{code(texto)}`\n\n"
        f"_Motor: {motor}. Revisa el texto. Puedes editarlo o enviarlo tal cual._"
    )
    teclado = teclado_orden_voz(origen)
    if status_msg:
        await status_msg.edit_text(aviso, reply_markup=teclado, parse_mode="Markdown")
    else:
        await update.message.reply_text(aviso, reply_markup=teclado, parse_mode="Markdown")


async def procesar_nota_voz(update: Update, context: ContextTypes.DEFAULT_TYPE, origen="menu"):
    if not update.message:
        return _estado_tras_voz(context)
    context.user_data["voice_origin"] = origen
    usuario = update.effective_user.first_name
    base = f"temp_voice_{update.effective_user.id}"
    entrada = None
    wav_path = f"{base}.wav"

    status_msg = await update.message.reply_text(
        "🎙️ **Transcribiendo audio…**\n_(Whisper en castellano; la primera vez puede tardar un poco)_",
        parse_mode="Markdown",
    )

    try:
        if update.message.voice:
            entrada = f"{base}.ogg"
            archivo = await update.message.voice.get_file()
            await archivo.download_to_drive(entrada)
        elif update.message.audio:
            mime = (update.message.audio.mime_type or "audio/ogg").split("/")[-1]
            mime = mime.replace("mpeg", "mp3")
            entrada = f"{base}.{mime}"
            archivo = await update.message.audio.get_file()
            await archivo.download_to_drive(entrada)
        else:
            await status_msg.edit_text("❌ No he recibido audio.")
            return _estado_tras_voz(context)

        await asyncio.to_thread(voice_orders.preparar_wav, entrada, wav_path)
        texto, motor = await asyncio.to_thread(voice_orders.transcribir_archivo, wav_path)
        texto = voice_orders.pulir_castellano(texto)
        if not texto:
            raise sr.UnknownValueError()

        log_accion(usuario, f"Orden por voz ({motor}): '{texto[:120]}'", Fore.CYAN)
        await _mostrar_borrador_voz(update, context, texto, status_msg, motor)
        return AWAITING_VOICE_CONFIRM

    except sr.UnknownValueError:
        await status_msg.edit_text(
            "❌ **No he entendido el audio.** Habla más claro, sin ruido, y vuelve a enviar la nota.",
            parse_mode="Markdown",
        )
    except Exception as error:
        await status_msg.edit_text(
            f"❌ **Error con el audio:** {md(str(error))}\n"
            "_(¿Tienes FFmpeg instalado? La primera transcripción Whisper descarga el modelo.)_",
            parse_mode="Markdown",
        )
    finally:
        for ruta in (entrada, wav_path):
            if ruta and os.path.exists(ruta):
                try:
                    os.remove(ruta)
                except OSError:
                    pass

    return _estado_tras_voz(context)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await procesar_nota_voz(update, context, origen="search")


async def handle_voice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await procesar_nota_voz(update, context, origen="menu")


async def handle_voice_cursor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await procesar_nota_voz(update, context, origen="cursor")


async def voice_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (update.message.text or "").strip()
    if not texto:
        await update.message.reply_text("Escribe el texto corregido de la orden.")
        return AWAITING_VOICE_EDIT
    texto = voice_orders.pulir_castellano(texto)
    context.user_data["voice_draft"] = texto
    voice_orders.guardar_borrador(update.effective_user.id, texto, origen="edicion")
    await _mostrar_borrador_voz(update, context, texto, status_msg=None, motor="manual")
    return AWAITING_VOICE_CONFIRM


async def voice_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    borrador = (context.user_data.get("voice_draft") or "").strip()
    if not borrador:
        guardado = voice_orders.leer_borrador(update.effective_user.id)
        if guardado:
            borrador = (guardado.get("text") or "").strip()
            context.user_data["voice_draft"] = borrador

    if query.data == "voice_discard":
        context.user_data.pop("voice_draft", None)
        await query.edit_message_text("🗑 Orden descartada.")
        return _estado_tras_voz(context)

    if not borrador:
        await query.edit_message_text("No hay texto guardado. Envía otra nota de voz.")
        return _estado_tras_voz(context)

    if query.data == "voice_edit":
        await query.edit_message_text(
            f"✏️ **Edita la orden**\n\nActual:\n`{code(borrador)}`\n\n"
            "Envíame un mensaje de texto con la versión corregida.",
            parse_mode="Markdown",
        )
        return AWAITING_VOICE_EDIT

    if query.data == "voice_search":
        context.user_data["voice_query"] = borrador
        await query.edit_message_text(f"🔎 Buscando: `{code(borrador)}`", parse_mode="Markdown")
        return await search_content(update, context)

    if query.data == "voice_cursor":
        if not _es_aaron(update):
            await query.answer("Solo Aarón puede usar Cursor.", show_alert=True)
            return AWAITING_VOICE_CONFIRM
        await query.edit_message_text(
            f"⏳ **Enviando a Cursor:**\n`{code(borrador)}`",
            parse_mode="Markdown",
            reply_markup=teclado_cursor(),
        )
        class _MsgProxy:
            def __init__(self, q):
                self.chat = q.message.chat
                self.from_user = q.from_user
                self._bot = q.message.get_bot()

            async def reply_text(self, text, **kwargs):
                return await self._bot.send_message(chat_id=self.chat.id, text=text, **kwargs)

        await _lanzar_cursor(_MsgProxy(query), borrador, context.application)
        return AWAITING_CURSOR

    return AWAITING_VOICE_CONFIRM

# ==========================================
# 🖼️ IMAGEN GENERATIVA (mismo motor que el panel)
# ==========================================
AVISO_IMAGEN_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aviso_imagen_telegram.flag")


async def _imagen_mostrar(query, context):
    texto = imagen_telegram.texto_opciones(context.user_data)
    teclado = imagen_telegram.teclado_imagen(context.user_data)
    await query.edit_message_text(texto, reply_markup=teclado, parse_mode="Markdown")


async def imagen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_aaron(update):
        if update.message:
            await update.message.reply_text("Solo Aarón puede generar imágenes.")
        return MENU
    imagen_telegram.asegurar_opciones(context.user_data)
    texto = imagen_telegram.texto_opciones(context.user_data)
    teclado = imagen_telegram.teclado_imagen(context.user_data)
    await update.message.reply_text(texto, reply_markup=teclado, parse_mode="Markdown")
    return MENU


async def imagen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _es_aaron(update):
        await query.answer("Solo Aarón", show_alert=True)
        return MENU

    data = query.data or ""
    if data == "imagen_menu":
        imagen_telegram.asegurar_opciones(context.user_data)
        await _imagen_mostrar(query, context)
        return MENU

    if data == "img_abort":
        imagen_telegram.cancelar_generacion()
        context.application.bot_data["img_busy"] = False
        await query.edit_message_text("⏹ Generación cancelada.")
        return MENU

    if context.application.bot_data.get("img_busy"):
        await query.answer("Hay una imagen en marcha.", show_alert=True)
        return MENU

    if data.startswith("img_tam_"):
        context.user_data["img_tam"] = data.replace("img_tam_", "", 1)
        await _imagen_mostrar(query, context)
        return MENU

    if data.startswith("img_pasos_"):
        context.user_data["img_pasos"] = int(data.split("_")[-1])
        await _imagen_mostrar(query, context)
        return MENU

    if data == "img_nsfw":
        context.user_data["img_nsfw"] = not context.user_data.get("img_nsfw")
        await _imagen_mostrar(query, context)
        return MENU

    if data == "img_semilla":
        await query.edit_message_text(
            "🎲 **Semilla**\n\nEnvía un número entero o escribe `aleatoria`.",
            parse_mode="Markdown",
        )
        return AWAITING_IMAGEN_SEED

    if data == "img_prompt":
        await query.edit_message_text(
            "✏️ **Prompt**\n\nEscribe qué quieres ver (español o etiquetas).",
            parse_mode="Markdown",
        )
        return AWAITING_IMAGEN_PROMPT

    if data == "img_estilo":
        imagen_telegram.limpiar_referencia(context.user_data)
        await query.edit_message_text(
            "🎨 **Copiar estilo**\n\n"
            "Envía una **foto** (no se guarda en el PC).\n"
            "Luego escribes la escena nueva; copio línea y color, no el contenido.",
            parse_mode="Markdown",
        )
        return AWAITING_IMAGEN_REF

    if data.startswith("img_del_"):
        fid = data.replace("img_del_", "", 1)
        ok, msg = imagen_telegram.borrar_archivo_registrado(context.application, fid)
        await query.edit_message_text(("✅ " if ok else "⚠️ ") + msg)
        return MENU

    if data.startswith("img_keep_"):
        fid = data.replace("img_keep_", "", 1)
        rutas = context.application.bot_data.get("img_archivos") or {}
        if fid in rutas:
            await query.edit_message_text(f"💾 Sigue en el PC:\n`{code(rutas[fid])}`", parse_mode="Markdown")
        else:
            await query.edit_message_text("No encuentro esa imagen en el registro.")
        return MENU

    return MENU


async def imagen_seed_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_aaron(update):
        return MENU
    texto = (update.message.text or "").strip().lower()
    if texto in ("aleatoria", "random", ""):
        context.user_data["img_seed"] = -1
    else:
        try:
            context.user_data["img_seed"] = int(texto)
        except ValueError:
            await update.message.reply_text("Pon un número o la palabra aleatoria.")
            return AWAITING_IMAGEN_SEED
    msg = await update.message.reply_text(
        imagen_telegram.texto_opciones(context.user_data),
        reply_markup=imagen_telegram.teclado_imagen(context.user_data),
        parse_mode="Markdown",
    )
    context.user_data["img_menu_msg"] = msg.message_id
    return MENU


async def _imagen_trabajo(application, chat_id, status_id, user_data, prompt, usuario):
    contexto_bot = application.bot
    loop = asyncio.get_running_loop()
    try:
        res = await imagen_telegram.generar_y_enviar(
            loop, chat_id, status_id, user_data, prompt, contexto_bot
        )
        if not res.get("ok"):
            await contexto_bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_id,
                text=f"❌ {res.get('error', 'Error')}",
            )
            return
        resultado = res["resultado"]
        ruta = resultado["ruta"]
        caption = (
            f"Lista en {int(resultado['segundos'])} s · semilla {resultado['semilla']} · "
            f"{resultado['ancho']}×{resultado['alto']}"
        )
        archivo_id = imagen_telegram.registrar_archivo(application, ruta)
        with open(ruta, "rb") as archivo:
            await contexto_bot.send_photo(
                chat_id=chat_id,
                photo=archivo,
                caption=caption,
                reply_markup=imagen_telegram.teclado_post_envio(archivo_id),
            )
        try:
            await contexto_bot.delete_message(chat_id=chat_id, message_id=status_id)
        except Exception:
            pass
        await contexto_bot.send_message(
            chat_id=chat_id,
            text=(
                "¿Qué hacemos en el PC?\n"
                "En el móvil ya la tienes al abrir la foto."
            ),
            reply_markup=imagen_telegram.teclado_imagen(user_data),
            parse_mode="Markdown",
        )
        log_accion(usuario, "Imagen generada por Telegram", Fore.CYAN, dialogo=prompt[:80])
    except Exception as error:
        try:
            await contexto_bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_id,
                text=f"❌ {error}",
            )
        except Exception:
            pass
    finally:
        application.bot_data["img_busy"] = False


async def imagen_prompt_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_aaron(update):
        return MENU
    if context.application.bot_data.get("img_busy"):
        await update.message.reply_text("Espera a que termine la imagen anterior.")
        return MENU
    prompt = (update.message.text or "").strip()
    if not prompt:
        await update.message.reply_text("Escribe qué quieres ver.")
        return AWAITING_IMAGEN_PROMPT

    cancelar_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⏹ Cancelar", callback_data="img_abort")]]
    )
    status = await update.message.reply_text(
        "🖼️ Preparando generación…",
        reply_markup=cancelar_kb,
    )
    context.application.bot_data["img_busy"] = True
    context.application.create_task(
        _imagen_trabajo(
            context.application,
            update.effective_chat.id,
            status.message_id,
            context.user_data,
            prompt,
            update.effective_user.first_name,
        )
    )
    return MENU


async def imagen_referencia_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_aaron(update):
        return MENU
    if not update.message:
        return MENU
    archivo = update.message.photo[-1] if update.message.photo else update.message.document
    if not archivo:
        await update.message.reply_text("Manda una foto.")
        return AWAITING_IMAGEN_REF
    imagen_telegram.limpiar_referencia(context.user_data)
    try:
        temporal = await imagen_telegram.guardar_foto_temporal(context.bot, archivo)
        context.user_data["img_ref_temp"] = temporal
        context.user_data["img_usar_estilo"] = True
    except Exception as error:
        await update.message.reply_text(f"No pude leer la foto: {error}")
        return AWAITING_IMAGEN_REF
    with open(temporal, "rb") as vista:
        await update.message.reply_photo(
            photo=vista,
            caption=(
                "🎨 **Referencia de estilo** (temporal, no va a la carpeta salida).\n\n"
                "Escribe la **escena nueva**. Si quieres adulto, activa NSFW antes."
            ),
            parse_mode="Markdown",
        )
    return AWAITING_IMAGEN_PROMPT


# ==========================================
# 🔒 CHAT PRIVADO (solo Aarón, chat 1:1 en Telegram)
# ==========================================
def _solo_aaron_app_privada(update):
    usuario = update.effective_user
    chat = update.effective_chat
    if not usuario or usuario.id != ADMIN_IDS[0]:
        return False
    if not chat or getattr(chat, "type", "") != "private":
        return False
    return True


async def hot_entrar(update: Update, context: ContextTypes.DEFAULT_TYPE, *, revelar=False):
    if not _solo_aaron_app_privada(update):
        return MENU
    context.user_data["hot_revelar_a"] = bool(revelar)
    hot_chat.reiniciar_historial()
    await update.message.reply_text(
        "Modo privado activo. Habla con naturalidad.\n/salir para cerrar."
    )
    log_accion(update.effective_user.first_name, "Entró al chat privado", Fore.MAGENTA)
    return AWAITING_HOT


async def hot_entrar_clave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await hot_entrar(update, context, revelar=True)


async def hot_salir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _solo_aaron_app_privada(update):
        return MENU
    context.user_data.pop("hot_revelar_a", None)
    hot_chat.reiniciar_historial()
    await update.message.reply_text(
        "Cerrado.",
        reply_markup=get_keyboard("main", update.effective_user.id),
    )
    return MENU


async def hot_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _solo_aaron_app_privada(update):
        return MENU
    texto = (update.message.text or "").strip()
    if not texto:
        return AWAITING_HOT
    if hot_chat.contiene_clave(texto):
        context.user_data["hot_revelar_a"] = True
    revelar = bool(context.user_data.get("hot_revelar_a"))
    espera = await update.message.reply_text("…")
    try:
        respuesta = await asyncio.to_thread(hot_chat.responder, texto, revelar)
        await espera.edit_text(respuesta[:4000])
    except Exception:
        await espera.edit_text("No he podido contestar. Prueba otra vez.")
    log_accion(update.effective_user.first_name, "Mensaje chat privado", Fore.MAGENTA, dialogo="[privado]")
    return AWAITING_HOT


# ==========================================
# 🔍 LÓGICA DE BÚSQUEDA (MOTOR ASÍNCRONO PARALELO)
# ==========================================
async def search_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name

    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        query = context.user_data.get('suggested_title', '')
        log_accion(usuario, f"Buscando sugerencia: {query}", Fore.YELLOW)
    else:
        query = context.user_data.get('voice_query') or (update.message.text if update.message else "")
        if 'voice_query' in context.user_data:
            del context.user_data['voice_query']
        log_accion(usuario, f"Buscando: {query}", Fore.YELLOW)

    status_msg = await bot_send(
        update, context,
        f"🚀 Buscando '{md(query)}' (anime ES + cine): Nyaa, AnimeTosho, TPB, EliteTorrent, YTS…"
    )
    if update.message and not update.callback_query:
        try:
            await update.message.delete()
        except Exception:
            pass
        
    import urllib.parse
    import cloudscraper

    query_plus = query.replace(" ", "+")
    query_url = urllib.parse.quote(query)

    # --- 🚀 FUNCIONES CLON (HILOS INDEPENDIENTES PARA CADA WEB) ---
    def fetch_nyaa():
        res = []
        try:
            scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
            url = f"https://nyaa.si/?f=0&c=0_0&q={query_plus}&s=seeders&o=desc"
            response = scraper.get(url, timeout=7)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for row in soup.select('tr.default, tr.success')[:10]:
                    cols = row.find_all('td')
                    link_list = cols[1].find_all('a')
                    title = link_list[-1].text.strip() if len(link_list) > 1 else link_list[0].text.strip()
                    magnet = next((l['href'] for l in cols[2].find_all('a') if l['href'].startswith('magnet:')), None)
                    if magnet: res.append({'title': f"🌸 {title[:40]}", 'magnet': magnet, 'source': 'Nyaa'})
        except: pass
        return res

    def fetch_elitetorrent():
        """Catálogo en español. DonTorrent ya no publica el magnet; aquí el .torrent va en la ficha."""
        res = []
        base = "https://www.elitetorrent.wf"
        try:
            session = requests.Session()
            session.headers.update(BROWSER_HEADERS)
            response = session.get(base + "/", params={"s": query}, timeout=12)
            if response.status_code != 200:
                return res
            vistos = []
            for link in BeautifulSoup(response.text, "html.parser").find_all("a", href=True):
                href = link["href"]
                if "/peliculas/" not in href and "/series/" not in href:
                    continue
                if href.rstrip("/").endswith(("/peliculas", "/series")):
                    continue
                if href in vistos:
                    continue
                vistos.append(href)
                if len(vistos) >= 4:
                    break
            for href in vistos:
                ficha = session.get(href, timeout=10)
                soup = BeautifulSoup(ficha.text, "html.parser")
                torrent = next((a["href"] for a in soup.find_all("a", href=True) if ".torrent" in a["href"].lower()), None)
                if not torrent:
                    continue
                if torrent.startswith("/"):
                    torrent = base + torrent
                titulo = soup.find("h1")
                title_es = titulo.get_text(" ", strip=True) if titulo else href.rstrip("/").split("/")[-1]
                res.append({"title": f"🇪🇸 {title_es[:40]}", "magnet": torrent, "source": "EliteTorrent"})
        except Exception:
            pass
        return res

    def fetch_yts():
        res = []
        apis = [
            "https://movies-api.accel.li/api/v2/list_movies.json",
            "https://yts.bz/api/v2/list_movies.json",
        ]
        for api in apis:
            try:
                response = requests.get(f"{api}?query_term={query_url}&limit=5", headers=BROWSER_HEADERS, timeout=8).json()
                data = response.get('data') or {}
                movies = data.get('movies') or []
                if not movies:
                    continue
                for movie in movies[:5]:
                    torrents = movie.get('torrents') or []
                    if not torrents:
                        continue
                    best = next((t for t in torrents if t.get('quality') == '1080p'), torrents[0])
                    title = movie.get('title_long') or movie.get('title') or 'Pelicula'
                    magnet = f"magnet:?xt=urn:btih:{best['hash']}&dn={urllib.parse.quote(title)}"
                    res.append({'title': f"🎬 {title[:40]}", 'magnet': magnet, 'source': 'YTS'})
                if res:
                    return res
            except Exception:
                continue
        return res

    def fetch_tpb():
        res = []
        try:
            scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
            response = scraper.get(f"https://apibay.org/q.php?q={query_url}", timeout=7).json()
            if response and response[0].get('id') != '0':
                for t in response[:5]:
                    res.append({'title': f"🏴‍☠️ {t['name'][:40]}", 'magnet': f"magnet:?xt=urn:btih:{t['info_hash']}", 'source': 'TPB'})
        except: pass
        return res

    # --- ⚡ EJECUCIÓN PARALELA (ASINCRONISMO REAL) ---
    tareas = [
        asyncio.to_thread(fetch_elitetorrent),
        asyncio.to_thread(fetch_nyaa),
        asyncio.to_thread(fetch_yts),
        asyncio.to_thread(fetch_tpb),
        asyncio.to_thread(anime_torrent_sources.buscar_todo_anime, query, BROWSER_HEADERS),
    ]

    resultados_brutos = await asyncio.gather(*tareas)

    results = []
    for r in resultados_brutos:
        results.extend(r)

    vistos_hash = set()

    def _clave(res):
        magnet = res.get("magnet") or ""
        return re.search(r"btih:([a-zA-Z0-9]+)", magnet, re.IGNORECASE).group(1).lower() if re.search(
            r"btih:([a-zA-Z0-9]+)", magnet, re.IGNORECASE
        ) else magnet[:48]

    unicos = []
    for res in sorted(results, key=lambda x: x.get("score", 0), reverse=True):
        clave = _clave(res)
        if clave in vistos_hash:
            continue
        vistos_hash.add(clave)
        unicos.append(res)
    results = unicos

    if not results:
        keyboard = [[InlineKeyboardButton("🔙 Volver al Menú", callback_data='back_to_main')]]
        await status_msg.edit_text(
            f"❌ **No encontré nada para '{md(query)}'.**\n\n"
            "💡 *Consejo:* Prueba el título en inglés si es una película americana.\n\n"
            "👇 **Escribe otro nombre:**",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )
        return AWAITING_SEARCH

    context.user_data['search_results'] = results 
    context.user_data['search_page'] = 0 
    await show_search_page(update, context, status_msg)
    return AWAITING_SEARCH

async def show_search_page(update: Update, context: ContextTypes.DEFAULT_TYPE, status_msg=None):
    results = context.user_data.get('search_results', [])
    page = context.user_data.get('search_page', 0)
    ITEMS_PER_PAGE = 3
    
    # Calcular índices
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_batch = results[start:end]
    
    if not current_batch:
        msg = "⚠️ No hay más resultados."
        if update.callback_query:
            await update.callback_query.answer(msg)
        else:
            await update.message.reply_text(msg)
        return

    keyboard = []
    
    # --- 1. Botones de Resultados ---
    for i, res in enumerate(current_batch):
        global_index = start + i
        btn_text = (res['title'][:40] + '..') if len(res['title']) > 40 else res['title']
        
        # Icono de bandera si es de DonTorrent
        if res.get('source') in ('DonTorrent', 'EliteTorrent') and not btn_text.startswith('🇪🇸'):
             btn_text = "🇪🇸 " + btn_text
             
        keyboard.append([InlineKeyboardButton(f"⬇️ {btn_text}", callback_data=f'dl_index_{global_index}')])

    # --- 2. Fila de Navegación (Anterior / Siguiente) ---
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data='prev_page'))
    
    if end < len(results): 
        nav_buttons.append(InlineKeyboardButton("Siguiente 👉", callback_data='next_page'))
    
    if nav_buttons:
        keyboard.append(nav_buttons)

    # --- 3. Botón Menú Principal (SIEMPRE VISIBLE) ---
    keyboard.append([InlineKeyboardButton("🏠 Menú Principal", callback_data='back_to_main')])

    text = f"🎯 **Resultados encontrados ({len(results)})**\nPágina {page + 1} (Mostrando {start+1}-{min(end, len(results))}):\nSelecciona cual descargar:"

    markup = InlineKeyboardMarkup(keyboard)
    if status_msg is not None:
        await status_msg.edit_text(text, reply_markup=markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await bot_send(update, context, text, reply_markup=markup, parse_mode='Markdown')

async def handle_search_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # --- CASO A: Navegación (Anterior / Siguiente) ---
    if query.data == 'next_page':
        try:
            await query.answer()
        except Exception:
            pass
        context.user_data['search_page'] += 1
        await show_search_page(update, context)
        return AWAITING_SEARCH
        
    elif query.data == 'prev_page':
        try:
            await query.answer()
        except Exception:
            pass
        current_page = context.user_data.get('search_page', 0)
        if current_page > 0:
            context.user_data['search_page'] -= 1
        await show_search_page(update, context)
        return AWAITING_SEARCH

    # --- CASO B: Seleccionar descarga ---
    elif query.data.startswith('dl_index_'):
        index = int(query.data.split('_')[-1]) 
        results = context.user_data.get('search_results', [])
        
        if 0 <= index < len(results):
            selected_magnet = results[index]['magnet']
            context.user_data['search_magnet'] = selected_magnet
            return await process_magnet(update, context)
        else:
            await query.answer("❌ Error: Enlace no encontrado.")

    # --- CASO C: Volver al Menú Principal ---
    elif query.data in ('back_to_main', 'menu_bajar'):
        await query.answer()
        return await menu_handler(update, context)


# ==========================================
# 🧑‍🎤 MOTOR VISUAL DE ARTISTAS (TOP 25)
# ==========================================
async def search_artist_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎵 **Música**\n\n"
        "Escribe un artista. Te enseño sus canciones y puedes bajar la que quieras en MP3.\n\n"
        "Ejemplo: `Queen`, `Bad Bunny`.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver a Bajar", callback_data='menu_bajar')]]),
        parse_mode='Markdown'
    )
    return AWAITING_ARTIST

async def search_artist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    artist = update.message.text.strip()
    status_msg = await update.message.reply_text(f"🔎 Buscando las 25 mejores canciones de `{artist}`...", parse_mode='Markdown')
    
    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(artist)}&entity=song&limit=25"
        res = requests.get(url, timeout=10).json()
        songs = res.get('results', [])
        
        if not songs:
            kb = [[InlineKeyboardButton("🔙 Volver al Menú", callback_data='back_to_main')]]
            await status_msg.edit_text("❌ No he encontrado a ese artista. Prueba con otro nombre.", reply_markup=InlineKeyboardMarkup(kb))
            return AWAITING_ARTIST
            
        context.user_data['artist_top_songs'] = songs
        context.user_data['artist_song_index'] = 0
        
        await status_msg.delete()
        await show_artist_song(update, context, new_message=True)
        return AWAITING_ARTIST
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error en la búsqueda: {e}")
        return MENU

async def show_artist_song(update: Update, context: ContextTypes.DEFAULT_TYPE, new_message=False):
    songs = context.user_data.get('artist_top_songs', [])
    index = context.user_data.get('artist_song_index', 0)
    
    if not songs: return
    
    song = songs[index]
    title = song.get('trackName', 'Desconocido')
    artist = song.get('artistName', 'Desconocido')
    album = song.get('collectionName', 'Sencillo/Desconocido')
    year = song.get('releaseDate', '')[:4]
    
    artwork = song.get('artworkUrl100', '').replace('100x100bb.jpg', '600x600bb.jpg')
    
    caption = (
        f"🎵 **TOP 25 CANCIONES** ({index + 1}/25)\n\n"
        f"👤 **Artista:** `{artist}`\n"
        f"💿 **Canción:** `{title}`\n"
        f"📀 **Álbum:** {album}\n"
        f"📅 **Año:** {year}\n"
    )
    
    nav_row = []
    if index > 0: nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data='artnav_prev'))
    if index < len(songs) - 1: nav_row.append(InlineKeyboardButton("Siguiente ➡️", callback_data='artnav_next'))
    
    keyboard = [
        [InlineKeyboardButton("✨ DESCARGAR CON MAGIA (MP3)", callback_data=f'artdl_{index}')],
        nav_row,
        [InlineKeyboardButton("🔙 Cancelar", callback_data='back_to_main')]
    ]
    
    if new_message:
        if update.message:
            await update.message.reply_photo(photo=artwork, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        query = update.callback_query
        await query.edit_message_media(
            media=InputMediaPhoto(media=artwork, caption=caption, parse_mode='Markdown'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_artist_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'artnav_prev':
        context.user_data['artist_song_index'] -= 1
    elif query.data == 'artnav_next':
        context.user_data['artist_song_index'] += 1
        
    await show_artist_song(update, context)
    return AWAITING_ARTIST

async def handle_artist_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    index = int(query.data.split('_')[1])
    songs = context.user_data.get('artist_top_songs', [])
    song = songs[index]
    
    title = song.get('trackName', '')
    artist = song.get('artistName', '')
    
    await query.edit_message_caption(caption=f"⬇️ **Descargando:** `{title}`...\n_(Esto puede tardar unos segundos)_", reply_markup=None, parse_mode='Markdown')
    
    context.user_data['dl_url'] = f"ytsearch1:{title} {artist} audio"
    context.user_data['dl_format'] = 'mp3_magia'
    context.user_data['song_title'] = title
    context.user_data['song_artist'] = artist
    context.user_data['last_downloaded_artist_index'] = index 
    
    asyncio.create_task(process_ytdlp_download(update, context, query.message))
    return MENU


# ==========================================
# 🍿 MOTOR DE CINE AUTOMÁTICO (RADARR)
# ==========================================
def buscar_peliculas_radarr(titulo):
    headers = {'X-Api-Key': RADARR_API_KEY}
    url = f"{RADARR_URL}/api/v3/movie/lookup?term={urllib.parse.quote(titulo)}"
    respuesta = requests.get(url, headers=headers, timeout=8)
    respuesta.raise_for_status()
    datos = respuesta.json()
    return datos if isinstance(datos, list) else []


def buscar_peliculas_imdb(titulo):
    """Catálogo alternativo cuando Radarr no llega a api.radarr.video."""
    consulta = (titulo or "").strip()
    if not consulta:
        return []
    letra = consulta[0].lower()
    if not ("a" <= letra <= "z"):
        letra = "x"
    url = f"https://v3.sg.media-imdb.com/suggestion/{letra}/{urllib.parse.quote(consulta)}.json"
    datos = requests.get(
        url,
        timeout=12,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    )
    datos.raise_for_status()
    peliculas = []
    for item in datos.json().get("d") or []:
        if item.get("qid") not in ("movie", "tvMovie"):
            continue
        imagen = item.get("i") if isinstance(item.get("i"), dict) else {}
        reparto = (item.get("s") or "").strip()
        peliculas.append({
            "title": item.get("l") or "Desconocido",
            "year": item.get("y") or "N/A",
            "overview": reparto or "Sin reparto en la ficha.",
            "remotePoster": imagen.get("imageUrl") or "https://i.imgur.com/4q2j7vE.png",
            "fuente": "imdb",
            "imdbId": item.get("id") or "",
        })
        if len(peliculas) >= 8:
            break
    return peliculas


async def search_radarr_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🍿 **Película**\n\n"
        "Escribe el título. Primero pregunto a Radarr. "
        "Si su catálogo no responde, te enseño la ficha por IMDb.\n\n"
        "Enviarla a Plex solo sale cuando Radarr contesta.\n\n"
        "Ejemplo: `Titanic`, `Dune`.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver a Bajar", callback_data='menu_bajar')]]),
        parse_mode='Markdown'
    )
    return AWAITING_RADARR_SEARCH

async def search_radarr_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movie_title = update.message.text.strip()
    status_msg = await update.message.reply_text(f"🔎 Buscando `{md(movie_title)}`…", parse_mode='Markdown')

    resultados = []
    origen = ""
    try:
        resultados = await asyncio.to_thread(buscar_peliculas_radarr, movie_title)
        origen = "radarr"
    except Exception as error:
        log_sistema(f"Radarr no pudo buscar '{movie_title}': {error}", is_error=True)
        resultados = []

    if not resultados:
        try:
            await status_msg.edit_text(
                f"🔎 Radarr no tiene catálogo ahora. Buscando `{md(movie_title)}` en IMDb…",
                parse_mode='Markdown',
            )
        except Exception:
            pass
        try:
            resultados = await asyncio.to_thread(buscar_peliculas_imdb, movie_title)
            origen = "imdb"
        except Exception as error:
            kb = [[InlineKeyboardButton("🔙 Volver al Menú", callback_data='back_to_main')]]
            await status_msg.edit_text(
                f"❌ No pude buscar la película.\nRadarr no llega a su catálogo e IMDb también falló.\n\n`{code(str(error))[:180]}`",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode='Markdown',
            )
            return AWAITING_RADARR_SEARCH

    if not resultados:
        kb = [[InlineKeyboardButton("🔙 Volver al Menú", callback_data='back_to_main')]]
        await status_msg.edit_text(
            "❌ No encontré ninguna película con ese nombre.",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return AWAITING_RADARR_SEARCH

    context.user_data['radarr_results'] = resultados
    context.user_data['radarr_index'] = 0
    context.user_data['radarr_origen'] = origen

    await status_msg.delete()
    await show_radarr_result(update, context, new_message=True)
    return AWAITING_RADARR_SEARCH

async def show_radarr_result(update: Update, context: ContextTypes.DEFAULT_TYPE, new_message=False):
    movies = context.user_data.get('radarr_results', [])
    index = context.user_data.get('radarr_index', 0)
    
    if not movies: return
    
    movie = movies[index]
    title = movie.get('title', 'Desconocido')
    year = movie.get('year', 'N/A')
    texto = movie.get('overview') or "Sin sinopsis."
    overview = md(texto[:300]) + ("..." if len(texto) > 300 else "")
    remote_poster = movie.get('remotePoster') or "https://i.imgur.com/4q2j7vE.png"
    de_imdb = movie.get("fuente") == "imdb"
    
    caption = (
        f"🎬 **PELÍCULA ENCONTRADA** ({index + 1}/{len(movies)})\n\n"
        f"🏷️ **Título:** `{title}` ({year})\n\n"
        f"📖 **{'Reparto' if de_imdb else 'Sinopsis'}:**\n_{overview}_\n"
    )
    if de_imdb:
        caption += "\n_Ficha de IMDb. Radarr sigue sin catálogo, así que esta no se puede mandar a Plex._"
    
    nav_row = []
    if index > 0: nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data='radnav_prev'))
    if index < len(movies) - 1: nav_row.append(InlineKeyboardButton("Siguiente ➡️", callback_data='radnav_next'))
    
    keyboard = []
    if not de_imdb:
        keyboard.append([InlineKeyboardButton("⬇️ Descargar a Plex (Automático)", callback_data=f'raddl_{index}')])
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='back_to_main')])
    
    if new_message:
        if update.message: await update.message.reply_photo(photo=remote_poster, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        query = update.callback_query
        await query.edit_message_media(media=InputMediaPhoto(media=remote_poster, caption=caption, parse_mode='Markdown'), reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_radarr_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'radnav_prev': context.user_data['radarr_index'] -= 1
    elif query.data == 'radnav_next': context.user_data['radarr_index'] += 1
    await show_radarr_result(update, context)
    return AWAITING_RADARR_SEARCH

async def handle_radarr_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    index = int(query.data.split('_')[1])
    movie = context.user_data['radarr_results'][index]

    if movie.get("fuente") == "imdb" or not movie.get("tmdbId"):
        await query.answer("Esta ficha viene de IMDb. Radarr no puede añadirla.", show_alert=True)
        return AWAITING_RADARR_SEARCH

    await query.answer()
    
    await query.edit_message_caption(caption="⏳ Mandando orden al servidor...", reply_markup=None)
    
    try:
        headers = {'X-Api-Key': RADARR_API_KEY}
        perfiles = requests.get(f"{RADARR_URL}/api/v3/qualityprofile", headers=headers).json()
        quality_id = perfiles[0]['id'] if perfiles else 1
        
        payload = {
            "title": movie['title'],
            "qualityProfileId": quality_id,
            "tmdbId": movie['tmdbId'],
            "year": movie['year'],
            "rootFolderPath": RADARR_ROOT_FOLDER,
            "minimumAvailability": "released",
            "monitored": True,
            "addOptions": {"searchForMovie": True}
        }
        
        res = requests.post(f"{RADARR_URL}/api/v3/movie", json=payload, headers=headers)
        
        if res.status_code in [200, 201]:
            await query.edit_message_caption(
                caption=f"✅ **¡Película enviada a Radarr!** 🍿\n\nEl sistema la está buscando en español y descargando en segundo plano.\n\n_(Aparecerá sola en Plex cuando termine)_",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menú Principal", callback_data='back_to_main')]]),
                parse_mode='Markdown'
            )
        else:
            err_msg = res.json()
            if isinstance(err_msg, list) and err_msg[0].get('errorCode') == 'MovieExistsValidator':
                 await query.edit_message_caption(caption="⚠️ **¡Esa película ya está en tu biblioteca!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menú Principal", callback_data='back_to_main')]]))
            else:
                 await query.edit_message_caption(caption=f"❌ Error al añadir: {res.text}")
    except Exception as e:
        await query.edit_message_caption(caption=f"❌ Error de conexión: {e}")
    return MENU

# ==========================================
# 📱 PLAY STORE PRIVADA (Buscador de APKs)
# ==========================================
async def search_apk_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📱 **App**\n\n"
        "Escribe el nombre de la aplicación Android. Te enseño resultados y bajas el APK a Drive. "
        "Luego lo instalas desde el móvil.\n\n"
        "Ejemplo: `Spotify`, `VLC`.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver a Bajar", callback_data='menu_bajar')]]),
        parse_mode='Markdown'
    )
    return AWAITING_APK_SEARCH

async def search_apk_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app_name = update.message.text.strip()
    status_msg = await update.message.reply_text(f"🔎 Buscando `{app_name}` en repositorios oficiales...", parse_mode='Markdown')
    
    try:
        url = f"https://ws75.aptoide.com/api/7/apps/search?query={urllib.parse.quote(app_name)}&limit=10"
        res = requests.get(url, timeout=10).json()
        
        apps = res.get('datalist', {}).get('list', [])
        
        if not apps:
            kb = [[InlineKeyboardButton("🔙 Volver al Menú", callback_data='back_to_main')]]
            await status_msg.edit_text("❌ No he encontrado esa aplicación. Prueba con un nombre más exacto.", reply_markup=InlineKeyboardMarkup(kb))
            return AWAITING_APK_SEARCH
            
        context.user_data['apk_search_results'] = apps
        context.user_data['apk_search_index'] = 0
        
        await status_msg.delete()
        await show_apk_result(update, context, new_message=True)
        return AWAITING_APK_SEARCH
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error en la búsqueda de APK: {e}")
        return MENU

async def show_apk_result(update: Update, context: ContextTypes.DEFAULT_TYPE, new_message=False):
    apps = context.user_data.get('apk_search_results', [])
    index = context.user_data.get('apk_search_index', 0)
    
    if not apps: return
    
    app = apps[index]
    title = app.get('name', 'App Desconocida')
    version = app.get('file', {}).get('vername', 'Desconocida')
    size_bytes = app.get('file', {}).get('filesize', 0)
    size_mb = size_bytes / (1024 * 1024)
    downloads = app.get('stats', {}).get('downloads', 0)
    icon = app.get('icon', '')
    
    caption = (
        f"📦 **PLAY STORE PRIVADA** ({index + 1}/{len(apps)})\n\n"
        f"📱 **App:** `{title}`\n"
        f"🏷️ **Versión:** {version} (Original)\n"
        f"⚖️ **Peso:** {size_mb:.1f} MB\n"
        f"⬇️ **Descargas globales:** {downloads:,}\n"
    )
    
    nav_row = []
    if index > 0: nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data='apknav_prev'))
    if index < len(apps) - 1: nav_row.append(InlineKeyboardButton("Siguiente ➡️", callback_data='apknav_next'))
    
    keyboard = [
        [InlineKeyboardButton(f"⬇️ DESCARGAR APK ({size_mb:.1f} MB)", callback_data=f'apkdl_{index}')],
        nav_row,
        [InlineKeyboardButton("🔙 Cancelar", callback_data='back_to_main')]
    ]
    
    if new_message:
        if update.message:
            await update.message.reply_photo(photo=icon, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        query = update.callback_query
        await query.edit_message_media(
            media=InputMediaPhoto(media=icon, caption=caption, parse_mode='Markdown'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_apk_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'apknav_prev': context.user_data['apk_search_index'] -= 1
    elif query.data == 'apknav_next': context.user_data['apk_search_index'] += 1
    await show_apk_result(update, context)
    return AWAITING_APK_SEARCH

async def handle_apk_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    index = int(query.data.split('_')[1])
    apps = context.user_data.get('apk_search_results', [])
    app = apps[index]
    
    title = app.get('name', 'App')
    dl_url = app.get('file', {}).get('path', '')
    
    if not dl_url:
        await query.edit_message_caption(caption="❌ Error: No hay enlace de descarga disponible.", reply_markup=None)
        return MENU
        
    await query.edit_message_caption(caption=f"⬇️ **Aria2 está descargando:** `{title}`...\n_(La barra de progreso aparecerá en un nuevo mensaje)_", reply_markup=None, parse_mode='Markdown')
    
    status_msg = await bot_send(update, context, "⏳ **Iniciando descarga de APK...**", parse_mode='Markdown')
    download = aria2.add_uris([dl_url])
    
    context.user_data['is_apk'] = True 
    
    asyncio.create_task(process_magnet_loop(update, context, download, status_msg))
    return MENU

# ==========================================
# 📖 LECTOR Y DESCARGADOR DE MANGA (.CBZ)
# ==========================================
async def search_manga_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📖 **Manga**\n\n"
        "Escribe el título. Te enseño coincidencias y puedes bajar capítulos en un archivo CBZ, "
        "que se lee como un cómic.\n\n"
        "Ejemplo: `Berserk`, `Chainsaw Man`.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver a Bajar", callback_data='menu_bajar')]]),
        parse_mode='Markdown'
    )
    return AWAITING_MANGA_SEARCH

async def search_manga_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manga_title = update.message.text.strip()
    status_msg = await update.message.reply_text(f"🔎 Buscando `{manga_title}` en la base de datos mundial...", parse_mode='Markdown')
    try:
        url = f"https://api.mangadex.org/manga?title={urllib.parse.quote(manga_title)}&limit=10&includes[]=cover_art&contentRating[]=safe&contentRating[]=suggestive&contentRating[]=erotica&contentRating[]=pornographic"
        res = requests.get(url, headers=MANGA_HEADERS, timeout=15).json()
        mangas = res.get('data', [])
        
        if not mangas:
            kb = [[InlineKeyboardButton("🔙 Volver al Menú", callback_data='back_to_main')]]
            await status_msg.edit_text("❌ No encontré ese manga.", reply_markup=InlineKeyboardMarkup(kb))
            return AWAITING_MANGA_SEARCH
            
        context.user_data['manga_results'] = mangas
        context.user_data['manga_index'] = 0
        
        await status_msg.delete()
        await show_manga_result(update, context, new_message=True)
        return AWAITING_MANGA_SEARCH
    except Exception as e:
        await status_msg.edit_text(f"❌ Error buscando manga: {e}")
        return MENU

async def show_manga_result(update: Update, context: ContextTypes.DEFAULT_TYPE, new_message=False):
    mangas = context.user_data.get('manga_results', [])
    index = context.user_data.get('manga_index', 0)
    if not mangas: return
    
    manga = mangas[index]
    m_id = manga['id']
    attrs = manga.get('attributes', {})
    title = manga_title_of(attrs)
    
    desc = attrs.get('description', {}).get('es-la', attrs.get('description', {}).get('es', attrs.get('description', {}).get('en', 'Sin sinopsis.')))
    desc = md(re.sub(r'<[^>]+>', '', desc or ''))
    desc = desc[:300] + "..." if len(desc) > 300 else desc
    status = attrs.get('status', 'Desconocido').capitalize()
    
    cover_file = ""
    for rel in manga.get('relationships', []):
        if rel['type'] == 'cover_art': cover_file = rel.get('attributes', {}).get('fileName', '')
    cover_url = f"https://uploads.mangadex.org/covers/{m_id}/{cover_file}" if cover_file else "https://i.imgur.com/4q2j7vE.png"
    
    caption = (
        f"📖 **MANGA DETECTADO** ({index + 1}/{len(mangas)})\n\n"
        f"🏷️ **Título:** `{title}`\n"
        f"📡 **Estado:** {status}\n\n"
        f"📝 **Sinopsis:**\n_{desc}_\n"
    )
    
    nav_row = []
    if index > 0: nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data='manganav_prev'))
    if index < len(mangas) - 1: nav_row.append(InlineKeyboardButton("Siguiente ➡️", callback_data='manganav_next'))
    
    keyboard = [
        [InlineKeyboardButton("⬇️ Bajar Último Cap (Español)", callback_data=f'mangalast_{m_id}')],
        [InlineKeyboardButton("🌪️ Aspiradora (Tomo de 10 Caps)", callback_data=f'mangavol_{m_id}')],
        nav_row,
        [InlineKeyboardButton("🔙 Cancelar", callback_data='back_to_main')]
    ]
    
    if new_message:
        if update.message: await update.message.reply_photo(photo=cover_url, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        query = update.callback_query
        await query.edit_message_media(media=InputMediaPhoto(media=cover_url, caption=caption, parse_mode='Markdown'), reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_manga_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'manganav_prev': context.user_data['manga_index'] -= 1
    elif query.data == 'manganav_next': context.user_data['manga_index'] += 1
    await show_manga_result(update, context)
    return AWAITING_MANGA_SEARCH

async def dl_manga_chapter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action, m_id = query.data.split('_')
    limit = 1 if action == 'mangalast' else 10 
    
    status_msg = await query.message.reply_text("⏳ **Buscando traductores al Español...**", parse_mode='Markdown')
    
    try:
        feed_url = f"https://api.mangadex.org/manga/{m_id}/feed?translatedLanguage[]=es&translatedLanguage[]=es-la&order[chapter]=desc&limit={limit}&includeExternalUrl=0&contentRating[]=safe&contentRating[]=suggestive&contentRating[]=erotica&contentRating[]=pornographic"
        res = requests.get(feed_url, headers=MANGA_HEADERS, timeout=15).json()
        chapters = res.get('data', [])
        
        if not chapters:
            await status_msg.edit_text("❌ No hay capítulos traducidos al español para este manga todavía.")
            return MENU
            
        manga_folder = f"{BASE_DOWNLOAD_PATH}/Mangas"
        os.makedirs(manga_folder, exist_ok=True)
        
        await status_msg.edit_text(f"📥 **Descargando {len(chapters)} capítulo(s) de Manga...**\nSe descargarán las imágenes y se compilarán en formato `.cbz` en tu Drive.", parse_mode='Markdown')
        
        asyncio.create_task(process_manga_cbz(update, context, chapters, manga_folder, status_msg))
        return MENU
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")
        return MENU

async def process_manga_cbz(update, context, chapters, base_folder, status_msg):
    chapters.reverse() 
    
    for cap in chapters:
        cap_id = cap['id']
        cap_num = cap.get('attributes', {}).get('chapter', 'Extra')
        mangas_list = context.user_data.get('manga_results', [])
        manga_title = manga_title_of(mangas_list[context.user_data.get('manga_index', 0)]['attributes']) if mangas_list else "Manga"
        
        cbz_name = f"{manga_title} - Cap {cap_num}.cbz"
        cbz_path = os.path.join(base_folder, cbz_name)
        
        try:
            home_res = requests.get(f"https://api.mangadex.org/at-home/server/{cap_id}", headers=MANGA_HEADERS, timeout=20).json()
            base_url = home_res['baseUrl']
            hash_hash = home_res['chapter']['hash']
            pages = home_res['chapter'].get('data') or []
            quality = "data"
            if not pages:
                pages = home_res['chapter'].get('dataSaver') or []
                quality = "data-saver"
            
            with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as cbz:
                for i, page in enumerate(pages):
                    img_url = f"{base_url}/{quality}/{hash_hash}/{page}"
                    img_data = requests.get(img_url, headers=MANGA_HEADERS, timeout=30).content
                    cbz.writestr(f"{i:03d}_{page}", img_data)
                    
        except Exception as e:
            print(f"Error bajando el capítulo {cap_num}: {e}")
            
    await status_msg.edit_text(f"✅ **¡Manga Descargado y Empaquetado!** 📚\n\n📂 Formato: `.cbz` (Alta Calidad)\n📍 Guardado en tu Google Drive: `D:/Descargas torrent/Mangas`", parse_mode='Markdown')

# ==========================================
# 📱 DESCARGADOR MULTIMEDIA (YT, IG, TIKTOK)
# ==========================================

yt_progress = {}

def get_yt_hook(user_id):
    def hook(d):
        if d['status'] == 'downloading':
            info = d.get('info_dict', {})
            yt_progress[user_id] = {
                'percent': d.get('_percent_str', '0%').strip(),
                'speed': d.get('_speed_str', '0KiB/s').strip(),
                'eta': d.get('_eta_str', 'Desconocido').strip(),
                'status': 'downloading',
                'title': info.get('title', 'Audio'),
                'p_index': info.get('playlist_index'), 
                'p_count': info.get('playlist_count')
            }
        elif d['status'] == 'finished':
            pass
    return hook

def extraer_url_reproductor(html):
    """Saca la URL del reproductor. TioAnime publica un array; AnimeAV1, un servidor con URL."""
    # yourupload, dood, filemoon y uqload los rechaza yt-dlp. Si el capítulo los ofrece, se prueba el siguiente.
    preferidos = ['mp4upload', 'ok.ru', 'okru', 'fembed', 'amazon', 'streamwish', 'voe']
    candidatos = []
    marca = "var videos = "
    idx = (html or "").find(marca)
    data = None
    if idx >= 0:
        try:
            data, _ = json.JSONDecoder().raw_decode((html or "")[idx + len(marca):].lstrip())
        except Exception:
            data = None
    if isinstance(data, dict):
        for grupo in ("SUB", "LAT", "ESP"):
            for server in data.get(grupo) or []:
                if isinstance(server, dict):
                    url = server.get("code") or server.get("url") or ""
                    if url:
                        candidatos.append((str(server.get("server") or ""), url))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (list, tuple)) and len(item) >= 2 and item[1]:
                candidatos.append((str(item[0]), str(item[1])))

    for url_publicada in re.findall(r'url\s*:\s*"(https?://[^"]+)"', html or ""):
        candidatos.append(("", url_publicada))

    for preferido in preferidos:
        for nombre, url in candidatos:
            if preferido in f"{nombre} {url}".lower():
                return url
    if candidatos:
        return candidatos[0][1]

    soup = BeautifulSoup(html or "", "html.parser")
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        if any(s in src.lower() for s in preferidos):
            return src
    return None


def alternativa_de_anime(url):
    """AnimeFLV y webs parecidas ya no abren. AnimeAV1 usa el mismo slug; si no, TioAnime."""
    if not any(sitio in url for sitio in ("animeflv.", "animefenix.", "animeblix.", "animeid.")):
        return url
    ruta = urllib.parse.urlparse(url).path.strip("/")
    partes = [p for p in ruta.split("/") if p]
    if len(partes) < 2:
        return url
    resto = partes[1]
    episodio = None
    slug = resto
    numero = re.match(r"(.+)-(\d+)$", resto)
    if partes[0] == "ver" and numero:
        slug, episodio = numero.group(1), numero.group(2)
    candidato = f"https://animeav1.com/media/{slug}" + (f"/{episodio}" if episodio else "")
    try:
        ficha = requests.get(candidato, headers=BROWSER_HEADERS, timeout=12)
        if ficha.status_code == 200 and (not episodio or extraer_url_reproductor(ficha.text)):
            return candidato
    except Exception:
        pass
    try:
        busqueda = requests.get(
            "https://tioanime.com/directorio",
            params={"q": slug.replace("-", " ")},
            headers=BROWSER_HEADERS,
            timeout=12,
        )
        opciones = []
        for enlace in BeautifulSoup(busqueda.text, "html.parser").find_all("a", href=True):
            href = enlace["href"]
            if href.startswith("/anime/"):
                opciones.append(href.split("/anime/", 1)[1].strip("/"))
        elegido = next((op for op in (slug, slug + "-tv") if op in opciones), None)
        if not elegido and opciones:
            elegido = sorted(opciones, key=len)[0]
        if elegido:
            if episodio:
                return f"https://tioanime.com/ver/{elegido}-{episodio}"
            return f"https://tioanime.com/anime/{elegido}"
    except Exception:
        pass
    return url


async def handle_social_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    usuario = update.effective_user.first_name
    log_accion(usuario, "Ha pegado un enlace multimedia", Fore.GREEN, dialogo=url)
    try:
        await update.message.delete()
    except Exception:
        pass
    
    if 'spotify.com' in url:
        context.user_data['dl_url'] = url
        kb = [
            [InlineKeyboardButton("✨ Bajar con SpotDL (Máxima Calidad)", callback_data='spotdl_yes')],
            [InlineKeyboardButton("🔙 Cancelar", callback_data='back_to_main')]
        ]
        await bot_send(update, context, "🎧 **Enlace de Spotify detectado.**\n\nEl motor extraerá la música a 320kbps con metadatos y carátulas originales.\nSi es una playlist grande, se empaquetará en un `.zip`.\n\n¿Procedemos?", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return MENU

    if 'instagram.com' in url or 'tiktok.com' in url:
        context.user_data['dl_url'] = url
        context.user_data['dl_format'] = 'social'
        await bot_send(update, context, "📱 **Red Social detectada.** Extrayendo la máxima calidad original (Si es un carrusel, bajaré todo)...")
        asyncio.create_task(process_ytdlp_download(update, context))
        return MENU

    anime_sites = ['animeflv.', 'animefenix.', 'tioanime.', 'monoschinos', 'jkanime.', 'animeblix.', 'animeid.', 'animeav1.com']
    if any(site in url for site in anime_sites):
        url = alternativa_de_anime(url)
        es_temporada = ('/anime/' in url or '/category/' in url or re.search(r'animeav1\.com/media/[^/]+/?$', url))
        if es_temporada:
            msg = await bot_send(update, context, "🌪️ **Modo Aspiradora Detectado.** Analizando temporada...", parse_mode='Markdown')
            try:
                import cloudscraper
                scraper = cloudscraper.create_scraper()
                res = scraper.get(url, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                raw_title = soup.title.string if soup.title else "Anime"
                clean_title = re.sub(r'(?i)(ver|online|sub|español|castellano|latino|descargar|gratis|hd|1080p|720p|animeflv|tioanime|monoschinos|jkanime|animeblix|animeid)', '', raw_title)
                clean_title = re.sub(r'[\-\|\/\s]+$', '', clean_title).strip()
                
                episodios = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if (('/ver/' in href or '/episodio/' in href or re.search(r'/media/[^/]+/\d+', href)) and href not in episodios):
                        full_link = href if href.startswith('http') else f"https://{url.split('/')[2]}{href}"
                        episodios.append(full_link)
                
                if not episodios and "animeav1.com" in url:
                    slug = url.rstrip("/").split("/")[-1]
                    numeros = sorted(set(re.findall(rf"/media/{re.escape(slug)}/(\d+)", res.text)), key=int)
                    episodios = [f"https://animeav1.com/media/{slug}/{n}" for n in numeros]
                elif episodios:
                    episodios.reverse()

                if not episodios:
                    msg = await safe_edit(msg, "❌ No encontré la lista de episodios. ¿Seguro que es la portada del anime?")
                    return MENU
                
                context.user_data['aspiradora_links'] = episodios
                context.user_data['smart_anime_title'] = clean_title
                
                kb = [
                    [InlineKeyboardButton(f"🌪️ SÍ, Descargar los {len(episodios)} Episodios", callback_data='start_aspiradora')],
                    [InlineKeyboardButton("🔙 Cancelar", callback_data='back_to_main')]
                ]
                msg = await safe_edit(msg, f"👺 **Anime:** `{clean_title}`\n📚 **Episodios encontrados:** {len(episodios)}\n\n¿Activar el Modo Aspiradora? (Los bajará automáticamente en segundo plano)", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
                return MENU
            except Exception as e:
                msg = await safe_edit(msg, f"❌ Error en la aspiradora: {e}")
                return MENU

        msg = await bot_send(update, context, "👺 **Episodio de Anime detectado.** Analizando servidores...", parse_mode='Markdown')
        try:
            import cloudscraper
            import json
            scraper = cloudscraper.create_scraper()
            res = scraper.get(url, timeout=10)
            best_url = None
            
            soup_title = BeautifulSoup(res.text, 'html.parser')
            raw_title = soup_title.title.string if soup_title.title else "Anime"
            
            clean_title = re.sub(r'(?i)(ver|online|sub|español|castellano|latino|descargar|gratis|hd|1080p|720p|animeflv|tioanime|monoschinos|jkanime|animeblix|animeid)', '', raw_title)
            clean_title = re.sub(r'(?i)(episodio|capitulo|capítulo|ep)\s*(\d+)', r'- E\2', clean_title)
            clean_title = re.sub(r'[\-\|\/\s]+$', '', clean_title).strip() 
            clean_title = re.sub(r'\s+', ' ', clean_title).strip() 
            
            context.user_data['smart_anime_title'] = clean_title
            
            try:
                base_url = url.replace('/ver/', '/anime/').replace('/episodio/', '/anime/').rsplit('-', 1)[0]
                context.user_data['suggest_season_url'] = base_url
            except: pass
            
            best_url = extraer_url_reproductor(res.text)
                        
            if best_url:
                if best_url.startswith('//'): best_url = 'https:' + best_url
                context.user_data['dl_url'] = best_url
                context.user_data['dl_format'] = 'best'
                context.user_data['is_anime_web'] = True 
                
                og_image = soup_title.find('meta', property='og:image')
                cover_url = og_image['content'] if og_image else "https://i.imgur.com/4q2j7vE.png"
                
                tag_idioma = "[Sub Español]"
                if re.search(r'(?i)(latino|lat)', raw_title): tag_idioma = "[Audio Latino]"
                elif re.search(r'(?i)(castellano)', raw_title): tag_idioma = "[Audio Castellano]"
                
                context.user_data['smart_anime_title'] = f"{clean_title} {tag_idioma}"
                
                server_name = "Desconocido"
                for s in ['ok.ru', 'mp4upload', 'yourupload', 'amazon', 'dood', 'streamwish', 'sw', 'voe', 'filemoon', 'fembed', 'uqload']:
                    if s in best_url.lower():
                        server_name = s.capitalize()
                        if server_name == 'Sw': server_name = 'Streamwish'
                        break

                mal_score = "N/A"
                mal_synopsis = "Sin resumen disponible."
                mal_genres = ""
                try:
                    search_title = clean_title.split('-')[0].strip()
                    ani_query = {
                        "query": "query ($s: String) { Media(search: $s, type: ANIME) { averageScore description(asHtml: false) genres } }",
                        "variables": {"s": search_title},
                    }
                    ani_res = requests.post("https://graphql.anilist.co", json=ani_query, timeout=8).json()
                    media = ((ani_res.get("data") or {}).get("Media")) or {}
                    if media:
                        score = media.get("averageScore")
                        mal_score = f"⭐ {score}/100" if score else "N/A"
                        raw_desc = re.sub(r"<[^>]+>", "", media.get("description") or "Sin resumen.")
                        mal_synopsis = md(raw_desc)[:200] + "..."
                        mal_genres = md(", ".join(media.get("genres") or []))
                except Exception as e:
                    print(f"Error AniList: {e}")
                
                caption = (
                    f"👺 **{clean_title.split('-')[0].strip().upper()}**\n\n"
                    f"📺 **Episodio:** `{clean_title}`\n"
                    f"🗣️ **Idioma:** {tag_idioma}\n"
                    f"⚙️ **Servidor:** {server_name}\n"
                    f"📊 **Nota MAL:** {mal_score}\n"
                    f"🎭 **Géneros:** {mal_genres}\n\n"
                    f"📖 **Sinopsis:**\n_{mal_synopsis}_\n"
                )
                
                kb = [
                    [InlineKeyboardButton("⬇️ Descargar y Enviar a Plex", callback_data='confirm_anime_dl')],
                    [InlineKeyboardButton("▶️ Ver Ahora (Streaming en el móvil)", url=best_url)],
                    [InlineKeyboardButton("🔙 Cancelar", callback_data='back_to_main')]
                ]
                
                await msg.delete()
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=cover_url, caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
                return MENU
            else:
                msg = await safe_edit(msg, "❌ No encontré un servidor compatible. Prueba otra web.")
                return MENU
        except Exception as e:
            msg = await safe_edit(msg, f"❌ Error extrayendo el anime: {e}")
            return MENU

    if 'youtube.com' in url or 'youtu.be' in url:
        is_playlist = ('list=' in url or '/playlist' in url) and not re.search(r'(?:watch\?v=|youtu\.be/)', url)
        
        if 'music.youtube' in url:
            context.user_data['dl_url'] = url
            kb = [
                [InlineKeyboardButton("✨ Sí, con letra, carátula y metadatos", callback_data='ytmagia_yes')],
                [InlineKeyboardButton("📄 No, audio tal cual", callback_data='ytmagia_no')],
                [InlineKeyboardButton("🔙 Menú Principal", callback_data='back_to_main')]
            ]
            
            if is_playlist:
                texto = "🎧 **PLAYLIST de YouTube Music detectada.**\n\n¿Quieres descargar la LISTA ENTERA con magia (Letras incrustadas, Carátulas, 320kbps)?"
            else:
                texto = "🎧 **YouTube Music detectado.**\n\n¿Quieres hacer magia con esta canción y descargarla con calidad 320kbps, su carátula, LETRA y metadatos oficiales?"
                
            await bot_send(update, context, texto, reply_markup=InlineKeyboardMarkup(kb))
            return MENU
        else:
            context.user_data['dl_url'] = url
            kb = [
                [InlineKeyboardButton("🎥 Original / Alta (1080p+)", callback_data='ytfmt_best')],
                [InlineKeyboardButton("🎥 Media (720p)", callback_data='ytfmt_720')],
                [InlineKeyboardButton("🎵 Solo Audio (MP3)", callback_data='ytfmt_mp3')],
                [InlineKeyboardButton("🔙 Cancelar", callback_data='back_to_main')]
            ]
            await bot_send(update, context, "📺 **YouTube detectado.** ¿En qué calidad lo quieres?", reply_markup=InlineKeyboardMarkup(kb))
            return MENU

# ==========================================
# 👺 GATILLO DE DESCARGA VISUAL DE ANIME
# ==========================================
async def confirm_anime_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_caption(
        caption="⏳ **Conectando con el servidor...**\nPreparando motor de descarga (Aria2 / yt-dlp)...", 
        reply_markup=None, 
        parse_mode='Markdown'
    )
    
    asyncio.create_task(process_ytdlp_download(update, context, query.message))
    return MENU

async def handle_yt_magia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'ytmagia_yes':
        context.user_data['dl_format'] = 'mp3_magia'
    else:
        context.user_data['dl_format'] = 'mp3'
        
    asyncio.create_task(process_ytdlp_download(update, context, query.message))
    return MENU

async def handle_yt_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fmt = query.data.replace('ytfmt_', '')
    context.user_data['dl_format'] = fmt
    asyncio.create_task(process_ytdlp_download(update, context, query.message))
    return MENU

# ==========================================
# 🟢 MOTOR DE SPOTIFY (SPOTDL)
# ==========================================
async def handle_spotify_dl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ **Iniciando motor SpotDL...**\nConectando con servidores de Spotify...", parse_mode='Markdown')
    asyncio.create_task(process_spotify_download(update, context, query.message))
    return MENU

def pistas_de_spotify(url):
    """Lee título y artista en la ficha pública. Sirve cuando SpotDL está limitado."""
    coincidencia = re.search(r"open\.spotify\.com/(?:intl-[a-z]+/)?(track|album|playlist)/([A-Za-z0-9]+)", url or "")
    if not coincidencia:
        return []
    tipo, ident = coincidencia.group(1), coincidencia.group(2)
    try:
        pagina = requests.get(f"https://open.spotify.com/embed/{tipo}/{ident}", headers=BROWSER_HEADERS, timeout=15)
    except Exception:
        return []
    if not pagina.ok:
        return []
    bloque = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', pagina.text)
    if not bloque:
        return []
    try:
        datos = json.loads(bloque.group(1))
    except Exception:
        return []
    pistas = []

    def recorrer(nodo):
        if isinstance(nodo, dict):
            if nodo.get("entityType") == "track" and isinstance(nodo.get("title"), str):
                artista = nodo.get("subtitle") if isinstance(nodo.get("subtitle"), str) else ""
                pistas.append((artista, nodo["title"]))
            for valor in nodo.values():
                recorrer(valor)
        elif isinstance(nodo, list):
            for item in nodo:
                recorrer(item)

    recorrer(datos)
    unicas = []
    vistas = set()
    for artista, titulo in pistas:
        clave = (artista.lower(), titulo.lower())
        if not titulo or clave in vistas:
            continue
        vistas.add(clave)
        unicas.append((artista, titulo))
    return unicas


def bajar_pista_magia(artista, titulo, carpeta):
    """Baja una canción a 320 kbps con miniatura, igual que la magia de YouTube Music."""
    opts = {
        "format": "bestaudio/best",
        "format_sort": ["abr", "asr"],
        "outtmpl": os.path.join(carpeta, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "writethumbnail": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"},
            {"key": "FFmpegMetadata", "add_metadata": True},
        ],
    }
    if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 50:
        opts["cookiefile"] = "cookies.txt"
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([f"ytsearch1:{artista} {titulo} audio"])


def mp3s_en(carpeta):
    encontrados = []
    for raiz, _, ficheros in os.walk(carpeta):
        for fichero in ficheros:
            if fichero.lower().endswith(".mp3"):
                encontrados.append(os.path.join(raiz, fichero))
    return encontrados


async def process_spotify_download(update: Update, context: ContextTypes.DEFAULT_TYPE, status_msg):
    url = context.user_data['dl_url']
    user_id = update.effective_user.id
    
    # Carpeta temporal para no mezclar canciones
    temp_dir = f"{BASE_DOWNLOAD_PATH}/Spotify_{user_id}_{int(time.time())}"
    os.makedirs(temp_dir, exist_ok=True)
    
    await status_msg.edit_text("🎵 **Sincronizando con Spotify...**\nDescargando pistas a 320kbps con carátulas incrustadas.\n_(Esto puede tardar dependiendo de la cantidad de canciones)_", parse_mode='Markdown')
    
    def run_spotdl():
        try:
            comando = [sys.executable, "-m", "spotdl", url, "--output", temp_dir, "--output-format", "mp3", "--use-youtube"]
            print(f"{Fore.CYAN}⚙️ SpotDL trabajando... (Mira el progreso aquí abajo){Style.RESET_ALL}")
            proceso = subprocess.Popen(
                comando, cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
            for linea in proceso.stdout:
                print(linea, end="")
                if "rate/request limit" in linea.lower():
                    proceso.kill()
                    break
            else:
                proceso.wait(timeout=600)
            encontrados = mp3s_en(temp_dir)
            if encontrados:
                return encontrados
            print(f"{Fore.YELLOW}SpotDL no dejó canciones. Sigo con la ficha pública de Spotify.{Style.RESET_ALL}")
            for artista, titulo in pistas_de_spotify(url):
                try:
                    bajar_pista_magia(artista, titulo, temp_dir)
                except Exception as e:
                    print(f"No pude bajar {artista} - {titulo}: {e}")
            return mp3s_en(temp_dir)
        except Exception as e:
            print(f"{Fore.RED}❌ Error fatal ejecutando SpotDL: {e}{Style.RESET_ALL}")
            return mp3s_en(temp_dir)
    archivos = await asyncio.to_thread(run_spotdl)
    
    if not archivos:
        await status_msg.edit_text("❌ **Error:** No se pudo descargar nada. Verifica que la playlist sea pública.")
        try: shutil.rmtree(temp_dir)
        except: pass
        return

    await status_msg.edit_text(f"✅ **¡{len(archivos)} canciones descargadas!**\nMetiendo carátula y letra...", parse_mode='Markdown')
    portadas = {}
    for arch in archivos:
        portadas[arch] = aplicar_caratula_y_letra(arch, "", "")
    
    # Si son más de 4 canciones, hacemos un ZIP para no inundar el chat
    if len(archivos) > 4:
        await status_msg.edit_text(f"📦 **Empaquetando {len(archivos)} canciones en un archivo ZIP...**", parse_mode='Markdown')
        zip_path = f"{temp_dir}/Playlist_Spotify.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for arch in archivos:
                zipf.write(arch, os.path.basename(arch))
                
        file_size = os.path.getsize(zip_path)
        if file_size > 49 * 1024 * 1024:
            # Lo sacamos de la carpeta temporal para que no se borre
            final_zip = f"{BASE_DOWNLOAD_PATH}/Playlist_Spotify_{int(time.time())}.zip"
            shutil.move(zip_path, final_zip)
            await context.bot.send_message(chat_id=user_id, text=f"⚠️ **El ZIP es demasiado grande para Telegram (>50MB).**\n\nLo he guardado seguro en tu servidor:\n`{final_zip}`", parse_mode='Markdown')
        else:
            with open(zip_path, 'rb') as f:
                await context.bot.send_document(chat_id=user_id, document=f, caption="🎁 **Aquí tienes tu Playlist de Spotify**")
    else:
        for arch in archivos:
            file_size = os.path.getsize(arch)
            if file_size < 49 * 1024 * 1024:
                cover = portadas.get(arch)
                with open(arch, 'rb') as f:
                    if cover and os.path.exists(cover):
                        with open(cover, 'rb') as thumb_f:
                            await context.bot.send_audio(chat_id=user_id, audio=f, thumbnail=thumb_f)
                    else:
                        await context.bot.send_audio(chat_id=user_id, audio=f)
            await asyncio.sleep(1.5)

    await status_msg.edit_text("🎉 **¡Descarga de Spotify Completada!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menú Principal", callback_data='back_to_main')]]))
    
    # Limpieza final
    try: shutil.rmtree(temp_dir)
    except: pass

def nombres_cancion(artista, titulo):
    """Quita el 'Official Video' y el canal de YouTube para que la letra se encuentre."""
    titulo = re.sub(r"(?i)\s*[\(\[][^)\]]*(?:official|video|audio|lyric|lyrics|hd|4k|visualizer)[^)\]]*[\)\]]", "", titulo or "")
    titulo = titulo.split("|")[0].strip(" -")
    artista = re.sub(r"(?i)\s*-\s*topic$", "", artista or "").strip()
    if artista and titulo.lower().startswith(artista.lower() + " - "):
        titulo = titulo[len(artista) + 3:].strip()
    if "," in artista and len(artista) > 40:
        artista = artista.split(",")[0].strip()
    if " - " in titulo and (not artista or len(artista) > 50):
        posible, resto = titulo.split(" - ", 1)
        artista, titulo = posible.strip(), resto.split("|")[0].strip(" -")
    return artista.strip(), titulo.strip()


def buscar_letra(artista, titulo):
    """Letra en texto plano. YouTube bloquea los subtítulos, así que se consulta LRCLIB."""
    if not artista and not titulo:
        return ""
    headers = {"User-Agent": "MiBot/1.0 (personal music library)"}
    try:
        res = requests.get(
            "https://lrclib.net/api/search",
            params={"track_name": titulo or "", "artist_name": artista or ""},
            headers=headers,
            timeout=8,
        )
        if not res.ok:
            return ""
        for item in res.json() or []:
            texto = (item.get("plainLyrics") or "").strip()
            if not texto and item.get("syncedLyrics"):
                texto = re.sub(r"\[\d+:\d+\.\d+\]\s*", "", item["syncedLyrics"]).strip()
            if texto:
                return texto
    except Exception as e:
        print(f"Letra no disponible: {e}")
    return ""


def convertir_a_mp3(path):
    """Deja un MP3 a 320 kbps aunque yt-dlp haya guardado el audio original."""
    if not path or not os.path.exists(path):
        return path
    if path.lower().endswith(".mp3"):
        return path
    base, _ = os.path.splitext(path)
    destino = base + ".mp3"
    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        return destino
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-vn", "-c:a", "libmp3lame", "-b:a", "320k", destino],
            capture_output=True,
            check=False,
        )
    except Exception as e:
        print(f"No pude convertir a MP3: {e}")
        return path
    return destino if os.path.exists(destino) else path


def portada_jpeg(audio_path):
    """Busca la miniatura bajada al lado del audio y la convierte a JPEG."""
    carpeta = os.path.dirname(audio_path) or "."
    stem = os.path.splitext(os.path.basename(audio_path))[0]
    imagenes = []
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        imagenes.extend(glob.glob(os.path.join(carpeta, stem + "*" + ext)))
    if not imagenes:
        return None
    origen = imagenes[0]
    destino = os.path.join(carpeta, stem + "_cover.jpg")
    if origen.lower().endswith((".jpg", ".jpeg")):
        return origen
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", origen, "-vf", "scale=600:-1", destino],
            capture_output=True,
            check=False,
        )
    except Exception:
        return None
    return destino if os.path.exists(destino) else None


def asegurar_320(path):
    """Si el MP3 no llega a 320 kbps, lo vuelve a codificar. El de 320 se queda igual."""
    if not path or not os.path.exists(path) or not path.lower().endswith(".mp3"):
        return path
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=bit_rate", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        bitrate = int((probe.stdout or "0").strip() or 0)
    except ValueError:
        bitrate = 0
    if bitrate >= 300000:
        return path
    destino = path + ".320.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", path, "-vn", "-c:a", "libmp3lame", "-b:a", "320k", destino],
        capture_output=True, check=False,
    )
    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        os.replace(destino, path)
    elif os.path.exists(destino):
        os.remove(destino)
    return path


def aplicar_caratula_y_letra(audio_path, artista, titulo):
    """Mete carátula y letra dentro del MP3. Devuelve la ruta del JPEG para Telegram."""
    if not audio_path.lower().endswith(".mp3"):
        return None
    asegurar_320(audio_path)
    try:
        tags = ID3(audio_path)
    except error:
        tags = ID3()

    if artista in ("", None, "Desconocido"):
        artista = str(tags.get("TPE1", "")) if "TPE1" in tags else ""
    if titulo in ("", None, "Desconocido"):
        titulo = str(tags.get("TIT2", "")) if "TIT2" in tags else ""
    artista, titulo = nombres_cancion(artista, titulo)
    if titulo:
        tags.add(TIT2(encoding=3, text=titulo))
    if artista:
        tags.add(TPE1(encoding=3, text=artista))

    cover = portada_jpeg(audio_path)
    if cover:
        with open(cover, "rb") as img:
            tags.delall("APIC")
            tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=img.read()))

    letra = buscar_letra(artista, titulo)
    if letra:
        tags.delall("USLT")
        tags.add(USLT(encoding=3, lang="spa", desc="Lyrics", text=letra))

    tags.save(audio_path, v2_version=3)
    return cover


async def process_ytdlp_download(update: Update, context: ContextTypes.DEFAULT_TYPE, message_obj=None):
    url = context.user_data['dl_url']
    fmt = context.user_data['dl_format']
    user_id = update.effective_user.id
    
    # Un solo mensaje de estado. Si se edita la foto del artista, Telegram acaba soltando un aviso nuevo en cada tick.
    msg = await bot_send(update, context, "Conectando con el servidor...")

    single_video = bool(re.search(r'(?:watch\?v=|youtu\.be/|/shorts/|ytsearch)', url))
    real_playlist = ('list=' in url or '/playlist' in url) and not single_video
    context.user_data['dl_real_playlist'] = real_playlist

    ydl_opts = {
        'outtmpl': f'{BASE_DOWNLOAD_PATH}/%(playlist_title)s/%(title)s_%(id)s.%(ext)s' if real_playlist else f'{BASE_DOWNLOAD_PATH}/%(title)s_%(id)s.%(ext)s',
        'progress_hooks': [get_yt_hook(user_id)],
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extract_flat': False,
        'noplaylist': not real_playlist,
        'ignoreerrors': real_playlist,
        'writethumbnail': True,
        'updatetime': False,
    }
    if os.path.exists('cookies.txt') and os.path.getsize('cookies.txt') > 50:
        ydl_opts['cookiefile'] = 'cookies.txt'

    # Si es Instagram, forzamos que intente descargar todos los elementos (carrusel)
    if 'instagram.com' in url:
        ydl_opts['extract_flat'] = False
        ydl_opts['playlist_items'] = 'all'

    if fmt in ['mp3', 'mp3_magia']:
        ydl_opts['format'] = 'bestaudio/best'
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320' if fmt == 'mp3_magia' else '192',
        }]
        if fmt == 'mp3_magia':
            ydl_opts['writethumbnail'] = True
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['format_sort'] = ['abr', 'asr']
            postprocessors.extend([
                {'key': 'FFmpegMetadata', 'add_metadata': True},
            ])
        ydl_opts['postprocessors'] = postprocessors
    elif fmt == '720':
        ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif fmt == 'best':
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'

    def _collect_downloads(opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            archivos_descargados = []

            if not info:
                return []

            if 'entries' in info:
                for entry in info['entries']:
                    if entry and 'requested_downloads' in entry:
                        archivos_descargados.extend([dl['filepath'] for dl in entry['requested_downloads']])
                    elif entry:
                        archivos_descargados.append(ydl.prepare_filename(entry))
            else:
                if 'requested_downloads' in info:
                    archivos_descargados.extend([dl['filepath'] for dl in info['requested_downloads']])
                else:
                    archivos_descargados.append(ydl.prepare_filename(info))

            return list(set([f for f in archivos_descargados if f and os.path.exists(f)]))

    def run_dl():
        try:
            return _collect_downloads(ydl_opts)
        except Exception as e:
            if fmt == 'mp3_magia' and 'subtitle' in str(e).lower():
                sin_letra = dict(ydl_opts)
                sin_letra.pop('writesubtitles', None)
                sin_letra.pop('writeautomaticsub', None)
                sin_letra.pop('subtitleslangs', None)
                print(f"Letra no disponible ({e}). Sigo con el audio.")
                return _collect_downloads(sin_letra)
            raise

    dl_task = asyncio.create_task(asyncio.to_thread(run_dl))

    # --- ANIMACIÓN VISUAL INTELIGENTE ---
    last_yt_edit = 0
    while not dl_task.done():
        progress = yt_progress.get(user_id, {})
        if progress:
            current_time = time.time()
            if current_time - last_yt_edit >= 4:
                pct_str = progress.get('percent', '0%').replace('%', '').strip()
                try: pct_float = float(pct_str)
                except: pct_float = 0.0
                
                filled = int(pct_float / 5)
                bar = "█" * filled + "▒" * (20 - filled)
                
                p_index = progress.get('p_index')
                p_count = progress.get('p_count')
                titulo = md(progress.get('title', 'Multimedia'))
                
                if p_index and p_count and int(p_count) > 1:
                    header = f"Descargando lista ({p_index}/{p_count}): {titulo[:40]}"
                else:
                    header = f"Descargando: {titulo[:40]}"

                text = (
                    f"{header}\n"
                    f"{bar} {progress.get('percent')}\n"
                    f"Velocidad: {progress.get('speed')} | Queda: {progress.get('eta')}"
                )
                msg = await safe_edit(msg, text, send_new=False)
                last_yt_edit = current_time
        await asyncio.sleep(2)
        
    try:
        filenames = dl_task.result()
        if not filenames: raise Exception("No se encontró el archivo (Puede estar privado).")

        if context.user_data.get('is_anime_web'):
            context.user_data['is_anime_web'] = False
            
            original_path = filenames[0]
            file_ext = os.path.splitext(original_path)[1]
            smart_title = context.user_data.get('smart_anime_title', 'Anime')
            
            new_path = os.path.join(os.path.dirname(original_path), smart_title + file_ext)
            try:
                os.rename(original_path, new_path)
                final_path = new_path
                final_name = smart_title + file_ext
            except:
                final_path = original_path
                final_name = os.path.basename(original_path)
            
            context.user_data['filename'] = final_name
            context.user_data['filepath'] = final_path
            
            season_url = context.user_data.get('suggest_season_url')
            if season_url:
                kb_anime = [
                    [InlineKeyboardButton("🌪️ Bajar Temporada Completa", callback_data='suggest_aspiradora')],
                    [InlineKeyboardButton("⏩ Continuar a Plex (Solo este ep)", callback_data='continue_plex_anime')]
                ]
                msg = await safe_edit(msg, f"✅ **¡Anime Descargado!**\n🏷️ Renombrado: `{smart_title}`\n\n💡 _¿Quieres que extraiga el resto de la temporada automáticamente?_", reply_markup=InlineKeyboardMarkup(kb_anime), parse_mode='Markdown')
                return MENU
            else:
                msg = await safe_edit(msg, f"✅ **¡Anime Descargado!**\n🏷️ Renombrado a: `{smart_title}`\nLanzando gestor de Plex...")
                await asyncio.sleep(1)
                await post_download_menu(update, context)
                return

        msg = await safe_edit(msg, "Descarga completada. Metiendo carátula y letra...", send_new=False)
        kb_volver = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menú Principal", callback_data='back_to_main')]])

        if fmt in ('mp3', 'mp3_magia'):
            filenames = [convertir_a_mp3(f) for f in filenames if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.vtt', '.lrc'))]
            filenames = list(dict.fromkeys(f for f in filenames if f and os.path.exists(f) and f.lower().endswith('.mp3')))

# --- 📦 NUEVA LÓGICA: EMPAQUETAR PLAYLISTS EN ZIP ---
        is_playlist = bool(context.user_data.get('dl_real_playlist')) and len(filenames) > 1
        
        if is_playlist and len(filenames) > 3:
            msg = await safe_edit(msg, f"📦 **Empaquetando {len(filenames)} canciones...**\n_(Esto puede tardar un par de minutos)_", parse_mode='Markdown')
            
            playlist_name = context.user_data.get('dl_url', 'Playlist').split('list=')[-1][:10]
            zip_path = f"{BASE_DOWNLOAD_PATH}/YT_Playlist_{playlist_name}_{int(time.time())}.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for filename in filenames:
                    if fmt == 'mp3_magia' and filename.lower().endswith('.mp3'):
                        aplicar_caratula_y_letra(filename, "", "")
                    # 🧹 Limpiamos el nombre ANTES de meterlo en el ZIP
                    clean_name = re.sub(r'_[A-Za-z0-9_-]{11}\.', '.', os.path.basename(filename))
                    zipf.write(filename, clean_name)
                    try: os.remove(filename) # Borramos el mp3 suelto
                    except: pass
                    
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"🎁 **¡Playlist Completa!**\n\nAl ser tantas canciones, las he metido en un `.zip`.\n📍 **Guardado en tu PC:** `{zip_path}`\n\n💡 _Nota: Abre la app de Google Drive en tu móvil, ve a la carpeta Descargas_Bot y lo tendrás ahí listo para ti._", 
                parse_mode='Markdown'
            )
        else:
            # --- 🪄 RESTAURADA LA MAGIA DE TELEGRAM PARA ARCHIVOS SUELTOS ---
            for filename in filenames:
                file_size = os.path.getsize(filename)
                
                if file_size > 49 * 1024 * 1024:
                    await context.bot.send_message(chat_id=user_id, text=f"⚠️ **Archivo demasiado grande (>50MB).**\n\nGuardado en tu PC:\n`{filename}`", parse_mode='Markdown')
                else:
                    ext = filename.lower().split('.')[-1]
                    
                    # 1. Limpiar el nombre del archivo (Quitar el ID feo de YouTube)
                    clean_name = re.sub(r'_[A-Za-z0-9_-]{11}\.', '.', os.path.basename(filename))
                    new_path = os.path.join(os.path.dirname(filename), clean_name)
                    try: os.rename(filename, new_path)
                    except: new_path = filename
                    
                    # 2. Envío a Telegram con Metadatos Forzados
                    if ext in ['mp3', 'm4a', 'wav']:
                        if context.user_data.get('dl_real_playlist'):
                            titulo, artista = "", ""
                        else:
                            titulo = context.user_data.get('song_title') or ""
                            artista = context.user_data.get('song_artist') or ""
                        thumb_path = None

                        if ext == 'mp3' and fmt == 'mp3_magia':
                            thumb_path = aplicar_caratula_y_letra(new_path, artista, titulo)
                            try:
                                audio_tags = ID3(new_path)
                                if 'TIT2' in audio_tags:
                                    titulo = str(audio_tags['TIT2'])
                                if 'TPE1' in audio_tags:
                                    artista = str(audio_tags['TPE1'])
                            except Exception:
                                pass

                        display_title = titulo if titulo and titulo != "Desconocido" else clean_name.replace('.mp3', '')

                        with open(new_path, 'rb') as f:
                            if thumb_path and os.path.exists(thumb_path):
                                with open(thumb_path, 'rb') as thumb_f:
                                    await context.bot.send_audio(
                                        chat_id=user_id, audio=f, title=display_title,
                                        performer=artista, thumbnail=thumb_f
                                    )
                            else:
                                await context.bot.send_audio(chat_id=user_id, audio=f, title=display_title, performer=artista)
                                
                    elif ext in ['mp4', 'mkv', 'webm']:
                        with open(new_path, 'rb') as f:
                            await context.bot.send_video(chat_id=user_id, video=f)
                    elif ext in ['jpg', 'jpeg', 'png', 'webp']:
                        with open(new_path, 'rb') as f:
                            await context.bot.send_document(chat_id=user_id, document=f) 
                    
                try: os.remove(new_path) 
                except: pass
                await asyncio.sleep(1.5)

        try:
            if filenames and 'list=' in url:
                dir_name = os.path.dirname(filenames[0])
                if not os.listdir(dir_name): os.rmdir(dir_name)
        except: pass

        if 'last_downloaded_artist_index' in context.user_data:
            idx = context.user_data.get('last_downloaded_artist_index')
            songs = context.user_data.get('artist_top_songs', [])
            
            available = [i for i in range(len(songs)) if i != idx]
            recs = random.sample(available, min(3, len(available)))
            
            kb_recs = []
            for r in recs:
                rtitle = songs[r].get('trackName', 'Canción')
                kb_recs.append([InlineKeyboardButton(f"🎵 Bajar: {rtitle[:30]}", callback_data=f'artdl_{r}')])
                
            kb_recs.append([InlineKeyboardButton("🔙 Menú Principal", callback_data='back_to_main')])
            
            msg = await safe_edit(msg, "🎉 **¡Aquí tienes tu canción!**\n\n💡 **Te recomiendo estas joyas del mismo artista:**", reply_markup=InlineKeyboardMarkup(kb_recs), parse_mode='Markdown')
            del context.user_data['last_downloaded_artist_index']
        else:
            if not is_playlist:
                msg = await safe_edit(msg, "🎉 **¡Aquí tienes toda tu multimedia!**", reply_markup=kb_volver)
            else:
                msg = await safe_edit(msg, "🎉 **¡Proceso de Playlist Finalizado!**", reply_markup=kb_volver)

    except Exception as e:
        print(f"Error Social: {e}")
        kb_volver = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menú Principal", callback_data='back_to_main')]])
        await safe_edit(msg, f"❌ No se pudo descargar.\n\n`{code(str(e))[:180]}`", reply_markup=kb_volver, parse_mode='Markdown')
# ==========================================
# 📂 POST-PROCESADO (RENOMBRAR Y PLEX)
# ==========================================

async def post_download_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filename = context.user_data.get('filename', 'desconocido')

    name_base, file_ext = os.path.splitext(filename)

    # --- 🛡️ ESCUDO ANTI-PLEX PARA MÚSICA Y APPS ---
    if file_ext.lower() in ['.mp3', '.m4a', '.wav', '.flac', '.zip', '.apk', '.cbz', '.jpg', '.png']:
        msg_text = f"🎵 **Archivo de audio/datos detectado:** `{code(filename)}`\nGuardado en el servidor. Omitiendo la gestión de Plex."
        await bot_send(update, context, msg_text, parse_mode='Markdown')
        return MENU
    # ----------------------------------------------

    clean_name = re.sub(r'(\.|_)', ' ', name_base)
    clean_name = re.sub(r'\[.*?\]', '', clean_name) 
    clean_name = re.sub(r'\(.*?\)', '', clean_name).strip() 

    clean_name = re.sub(r'\s+', ' ', clean_name)

    context.user_data['clean_name'] = clean_name

    msg = (
        f"📁 **Gestión de Archivo**\n\n"
        f"Original: `{code(filename)}`\n"
        f"Sugerido para Plex: `{code(clean_name)}`\n\n"
        "¿Cómo quieres nombrarlo?"
    )

    keyboard = [
        [InlineKeyboardButton(f"✅ Usar: {clean_name[:36]}", callback_data='use_suggested')],
        [InlineKeyboardButton("📝 Mantener Original", callback_data='keep_original')],
        [InlineKeyboardButton("⌨️ Escribir Manualmente", callback_data='manual_rename')]
    ]

    await bot_send(update, context, msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    return RENAMING

async def renaming_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query:
        await query.answer()
        choice = query.data

        if choice == 'use_suggested':
            final_name = context.user_data['clean_name']
            context.user_data['smart_organize'] = True
        elif choice == 'keep_original':
            final_name = context.user_data['filename']
            context.user_data['smart_organize'] = False 
        elif choice == 'manual_rename':
            context.user_data['smart_organize'] = False 
            await query.edit_message_text("⌨️ **Escribe el nuevo nombre del archivo** (sin extensión):")
            return RENAMING
    else:
        final_name = update.message.text
        context.user_data['smart_organize'] = False

    context.user_data['final_name'] = final_name

    keyboard = [
        [InlineKeyboardButton("🎬 Películas", callback_data='mov_movies')],
        [InlineKeyboardButton("📺 Series", callback_data='mov_series')],
        [InlineKeyboardButton("👺 Anime", callback_data='mov_anime')]
    ]

    msg_text = f"📛 Nombre final: `{final_name}`\n\n📂 **¿A qué carpeta de Plex lo muevo?**"

    if query:
        await query.edit_message_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    return MOVING_CATEGORY

async def move_and_plex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_map = {
        'mov_movies': 'Peliculas',
        'mov_series': 'Series',
        'mov_anime': 'Anime'
    }
    target_folder = category_map.get(query.data, 'Otros')

    source_path = context.user_data.get('filepath')
    final_name_user = context.user_data.get('final_name')
    smart_organize = context.user_data.get('smart_organize', False)

    await query.edit_message_text(f"🚚 Procesando para `{target_folder}`...", parse_mode='Markdown')

    try:
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"No encuentro el archivo en: {source_path}")

        destination_dir = os.path.join(PLEX_FINAL_PATH, target_folder)

        if smart_organize and target_folder in ['Series', 'Anime']:
            match = re.search(r'(.*?)(?:\s-|\s)?\sS(\d+)', final_name_user, re.IGNORECASE)

            if match:
                serie_name = match.group(1).strip() 
                season_num = match.group(2)

                season_folder = f"Season {season_num}"

                destination_dir = os.path.join(destination_dir, serie_name, season_folder)

                os.makedirs(destination_dir, exist_ok=True)
                print(f"📂 Estructura creada: {serie_name} / {season_folder}")


        file_ext = os.path.splitext(source_path)[1]

        if not final_name_user.endswith(file_ext):
            final_name_complete = final_name_user + file_ext
        else:
            final_name_complete = final_name_user

        dest_path = os.path.join(destination_dir, final_name_complete)

        shutil.move(source_path, dest_path)

        path_display = dest_path.replace(PLEX_FINAL_PATH, "") 
        context.user_data['final_video_path'] = dest_path     

        keyboard = [
            [InlineKeyboardButton("📝 Sí, buscar subtítulos en Castellano", callback_data='subs_yes')],
            [InlineKeyboardButton("⏩ No, ir directo a Plex", callback_data='subs_no')]
        ]

        await query.message.reply_text(
            f"✅ **Organizado y Movido**\n\nRuta: `{path_display}`\n\n¿Quieres que busque subtítulos exactos (SRT) para esta versión específica?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return SUBTITLES_SEARCH 

    except Exception as e:
        print(f"Error: {e}")
        await query.message.reply_text(f"❌ Error moviendo archivo: {str(e)}")
        return MENU
    
async def subtitle_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'subs_no':
        keyboard = [
            [InlineKeyboardButton("🔄 Sí, actualizar Plex", callback_data='plex_yes')],
            [InlineKeyboardButton("🏠 No, ir al Menú", callback_data='plex_no')]
        ]
        await query.edit_message_text("¿Quieres actualizar la biblioteca de Plex para que aparezca?", reply_markup=InlineKeyboardMarkup(keyboard))
        return PLEX_UPDATE

    if query.data == 'subs_yes':
        await query.edit_message_text("⏳ **Modo Francotirador Activado...**\nCalculando la huella digital (ADN) del vídeo para evitar desincronizaciones...", parse_mode='Markdown')
        
        video_path = context.user_data.get('final_video_path')
        
        def buscar_y_descargar():
            try:
                video = subliminal.scan_video(video_path)
                
                subs = subliminal.download_best_subtitles([video], {Language('spa')})
                
                if subs and subs.get(video):
                    subliminal.save_subtitles(video, subs[video])
                    return True
                return False
            except Exception as e:
                print(f"Error buscando subs: {e}")
                return False

        exito = await asyncio.to_thread(buscar_y_descargar)

        if exito:
            msg = "✅ **¡Subtítulos exactos encontrados!**\nSe han descargado y colocado automáticamente junto al vídeo."
        else:
            msg = "❌ **No hay subtítulos exactos para esta versión.**\n_El archivo está limpio. Puede que tarden un par de días en salir, o que la peli ya los traiga pegados._"

        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar Plex", callback_data='plex_yes')],
            [InlineKeyboardButton("🏠 Ir al Menú", callback_data='plex_no')]
        ]
        await query.edit_message_text(f"{msg}\n\n¿Quieres actualizar la biblioteca de Plex?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return PLEX_UPDATE

async def plex_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'plex_yes':
        await query.message.reply_text("📡 Enviando señal a Plex...")
        try:
            url = f"{PLEX_URL}/library/sections/all/refresh?X-Plex-Token={PLEX_TOKEN}"
            requests.get(url, timeout=5)
            await query.message.reply_text("✅ Señal enviada. Plex debería estar actualizando.")
        except Exception as e:
            await query.message.reply_text(f"⚠️ No pude contactar con Plex (¿Estás en Colab y Plex en local?): {e}")

    await query.message.reply_text("🏠 Volviendo al menú principal...", reply_markup=get_keyboard("main", update.effective_user.id))
    return MENU

# ==========================================
# 🛑 LÓGICA DE CANCELACIÓN (PAUSE/DELETE)
# ==========================================

async def cancel_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pregunta confirmación antes de borrar"""
    query = update.callback_query
    await query.answer()
    
    gid = query.data.replace("ask_cancel_", "")
    
    context.user_data[f'cancel_prompt_{gid}'] = True 
    
    keyboard = [
        [InlineKeyboardButton("✅ SÍ, BORRAR", callback_data=f'do_cancel_{gid}')],
        [InlineKeyboardButton("🔙 NO, CONTINUAR", callback_data=f'resume_{gid}')]
    ]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))


async def cancel_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecuta el borrado final en Aria2"""
    query = update.callback_query
    await query.answer()
    
    gid = query.data.replace("do_cancel_", "")
    
    try:
        download = aria2.get_download(gid)
        aria2.remove([download], force=True, files=True, clean=True)
        await query.edit_message_text("🛑 **Descarga cancelada y archivos eliminados.**", parse_mode='Markdown')
    except Exception as e:
        await query.edit_message_text("⚠️ No se pudo cancelar (¿ya terminó o se borró?).")
    
    if f'cancel_prompt_{gid}' in context.user_data:
        del context.user_data[f'cancel_prompt_{gid}']
        
    return MENU

async def cancel_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Si el usuario se arrepiente, restauramos el botón original"""
    query = update.callback_query
    await query.answer("Continuando...")
    gid = query.data.replace("resume_", "")
    
    context.user_data[f'cancel_prompt_{gid}'] = False
    
    kb_cancel = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar / Borrar", callback_data=f'ask_cancel_{gid}')]])
    await query.edit_message_reply_markup(reply_markup=kb_cancel)

# ==========================================
# 📅 CALENDARIO DE ANIME (Jikan API)
# ==========================================
async def show_anime_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("📅 **Consultando la agenda de hoy...**", parse_mode='Markdown')
    
    try:
        dias_espanol = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        from zoneinfo import ZoneInfo
        ahora = datetime.now(ZoneInfo("Europe/Madrid"))
        inicio = int(ahora.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        fin = inicio + 86400
        consulta = {
            "query": "query ($start: Int, $end: Int) { Page(page: 1, perPage: 12) { airingSchedules(airingAt_greater: $start, airingAt_lesser: $end, sort: TIME) { episode airingAt media { title { romaji english } averageScore } } } }",
            "variables": {"start": inicio, "end": fin},
        }
        res = requests.post("https://graphql.anilist.co", json=consulta, timeout=12).json()
        animes = ((res.get("data") or {}).get("Page") or {}).get("airingSchedules") or []
        if not animes:
            raise Exception("No hay estrenos publicados para hoy")

        texto = (
            f"📅 **Estrenos de hoy ({dias_espanol[ahora.weekday()]})**\n\n"
            "Son animes que se emiten hoy. No los baja: solo te dice cuáles salen.\n\n"
        )
        for a in animes:
            media = a.get("media") or {}
            titulos = media.get("title") or {}
            titulo = titulos.get("english") or titulos.get("romaji") or "Anime"
            score = media.get("averageScore")
            nota = f"{score}/100" if score else "s/n"
            texto += f"🔹 `{code(titulo)}` ep {a.get('episode', '?')} (⭐ {nota})\n"

        texto += "\n💡 _Fuente: AniList. Los subtítulos en español suelen tardar un rato tras la emisión en Japón._"
        kb = [[InlineKeyboardButton("🔙 Volver al Rastreador", callback_data='tracker_menu')]]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        
    except Exception as e:
        kb = [[InlineKeyboardButton("🔙 Volver al Rastreador", callback_data='tracker_menu')]]
        await query.edit_message_text(f"❌ Error al cargar el calendario: {md(e)}", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    
    return MENU

# ==========================================
# 🌪️ MOTOR ASPIRADORA DE ANIME
# ==========================================
async def handle_aspiradora_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'continue_plex_anime':
        await query.edit_message_text("Lanzando gestor de Plex...")
        await asyncio.sleep(1)
        return await post_download_menu(update, context)
        
    elif query.data == 'suggest_aspiradora':
        season_url = context.user_data.get('suggest_season_url')
        if not season_url: return MENU
        
        class FakeMessage:
            def __init__(self, text): self.text = text
            async def reply_text(self, text, **kwargs): return await query.message.reply_text(text, **kwargs)
                
        fake_update = update
        fake_update.message = FakeMessage(season_url)
        return await handle_social_link(fake_update, context)
        
    elif query.data == 'start_aspiradora':
        episodios = context.user_data.get('aspiradora_links', [])
        title = context.user_data.get('smart_anime_title', 'Anime')
        
        if not episodios: return MENU
        
        await query.edit_message_text(f"🌪️ **MODO ASPIRADORA ACTIVADO**\n\nHe puesto en cola la extracción de {len(episodios)} episodios de `{title}`.\nSe descargarán uno a uno en segundo plano y se dejarán en tu carpeta D:/Descargas torrent.", parse_mode='Markdown')
        
        asyncio.create_task(run_aspiradora_loop(update, context, episodios, title))
        return MENU

async def run_aspiradora_loop(update, context, episodios, title):
    import cloudscraper
    import json
    scraper = cloudscraper.create_scraper()
    chat_id = update.effective_chat.id
    
    for i, ep_url in enumerate(episodios):
        try:
            res = scraper.get(ep_url, timeout=10)
            best_url = extraer_url_reproductor(res.text)
                        
            if best_url:
                if best_url.startswith('//'): best_url = 'https:' + best_url
                
                ydl_opts = {
                    'outtmpl': f'{BASE_DOWNLOAD_PATH}/{title} - E{i+1}.%(ext)s',
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True
                }
                def download_silent(url, opts):
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([url])
                        
                await asyncio.to_thread(download_silent, best_url, ydl_opts)
                
            await asyncio.sleep(3)
        except Exception as e:
            continue
            
    await context.bot.send_message(chat_id, f"✅ **Aspiradora Completada:** Toda la temporada de `{title}` ha sido descargada.")

# ==========================================
# 🛠️ ENTORNO DE DESARROLLO (OTA V2 - MULTIPASO)
# ==========================================
async def dev_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    texto = (
        "🛠️ **Tocar el código**\n\n"
        "Esto cambia el programa del bot. Pega solo el texto exacto que quieres buscar. "
        "Si no coincide letra por letra, no toco nada. Luego te pido el texto nuevo y confirmas antes de guardar."
    )
    kb = [[InlineKeyboardButton("🔙 Volver al Bot", callback_data='menu_bot')]]
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    return AWAITING_DEV_SEARCH

async def receive_dev_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buscar_texto = update.message.text.strip('\r\n')
    status_msg = await update.message.reply_text("🔍 Buscando en mi código...", parse_mode='Markdown')

    with open('bot.py', 'r', encoding='utf-8') as f:
        codigo_actual = f.read()

    if buscar_texto not in codigo_actual:
        kb = [[InlineKeyboardButton("🔙 Volver al Menú", callback_data='back_to_main')]]
        await status_msg.edit_text("❌ **No encontrado.**\nEl código no coincide exactamente con mi cerebro. Revisa los espacios o si falta alguna letra.", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return AWAITING_DEV_SEARCH

    context.user_data['dev_search_text'] = buscar_texto

    kb = [
        [InlineKeyboardButton("🗑️ Solo quiero ELIMINARLO", callback_data='dev_delete_code')],
        [InlineKeyboardButton("🔙 Cancelar", callback_data='back_to_main')]
    ]
    await status_msg.edit_text(
        "✅ **¡Bloque encontrado!**\n\n"
        "🛠️ **Paso 2/3:** Ahora envíame en un nuevo mensaje el **NUEVO CÓDIGO** por el que quieres reemplazarlo.\n\n"
        "_(Si tu intención es simplemente borrar ese bloque de código, pulsa el botón rojo de abajo)_",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown'
    )
    return AWAITING_DEV_REPLACE

async def receive_dev_replace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reemplazar_texto = update.message.text.strip('\r\n')
    status_msg = await update.message.reply_text("⏳ Analizando e inyectando código...", parse_mode='Markdown')
    return await process_ota_injection(context, reemplazar_texto, status_msg)

async def dev_delete_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status_msg = await query.message.reply_text("⏳ Preparando eliminación segura...", parse_mode='Markdown')
    return await process_ota_injection(context, "", status_msg)

async def process_ota_injection(context, reemplazar_texto, status_msg):
    buscar_texto = context.user_data.get('dev_search_text', '')

    with open('bot.py', 'r', encoding='utf-8') as f:
        codigo_actual = f.read()

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    if reemplazar_texto == "":
        bloque_nuevo = f"\n# --- 🗑️ ELIMINADO: {timestamp} ---\n"
    else:
        bloque_nuevo = f"\n# --- 🛠️ MODIFICADO: {timestamp} ---\n{reemplazar_texto}\n"

    codigo_nuevo = codigo_actual.replace(buscar_texto, bloque_nuevo)

    try:
        compile(codigo_nuevo, '<string>', 'exec')
    except SyntaxError as e:
        kb_error = [[InlineKeyboardButton("🔙 Cancelar", callback_data='back_to_main')]]
        mensaje_error = (
            "🛑 **¡ALERTA ROJA! CIRUGÍA ABORTADA** 🛑\n\n"
            "El código nuevo tiene un error crítico de programación. Si lo guardo, moriré.\n\n"
            f"🐞 **Error:** `{e.msg}`\n"
            f"📍 **Línea:** `{e.lineno}`\n\n"
            "Vuelve a enviarme el parche corregido."
        )
        await status_msg.edit_text(mensaje_error, reply_markup=InlineKeyboardMarkup(kb_error), parse_mode='Markdown')
        return AWAITING_DEV_REPLACE

    with open('bot_temp.py', 'w', encoding='utf-8') as f:
        f.write(codigo_nuevo)

    kb = [
        [InlineKeyboardButton("💾 GUARDAR Y REINICIAR", callback_data='confirm_patch')],
        [InlineKeyboardButton("🗑️ CANCELAR", callback_data='cancel_patch')]
    ]
    await status_msg.edit_text("✅ **Paso 3/3: Auditoría superada.**\n\nLa sintaxis es perfecta. ¿Aplicamos al cerebro y reiniciamos el servidor?", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    return DEV_MENU

async def handle_patch_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel_patch':
        if os.path.exists('bot_temp.py'): os.remove('bot_temp.py')
        await query.edit_message_text("🗑️ **Operación cancelada.** Archivos temporales borrados. El bot sigue intacto.", reply_markup=get_keyboard("back"), parse_mode='Markdown')
        return MENU
        
    elif query.data == 'confirm_patch':
        await query.edit_message_text("💾 **Guardando en el cerebro principal...**", parse_mode='Markdown')
        try:
            os.replace('bot_temp.py', 'bot.py')
            with open("reboot_alert.txt", "w", encoding='utf-8') as f:
                f.write(str(update.effective_chat.id))
                
            await query.edit_message_text("🔄 **Código guardado. Reiniciando servidor...**", parse_mode='Markdown')
            await asyncio.sleep(2)
            cursor_chat.asegurar_tarea_en_disco()
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            await query.edit_message_text(f"❌ Error fatal al guardar: {e}", reply_markup=get_keyboard("back"))
            return MENU


def console_manager():
    while True:
        try:
            cmd = input().strip().lower()
            if not cmd: continue
            
            if cmd == 'help':
                print(f"\n{Fore.CYAN}=== 🛠️ PANEL DE CONTROL LOCAL ==={Style.RESET_ALL}")
                print(f"{Fore.YELLOW}status{Style.RESET_ALL}  - Ver todas las descargas activas en Aria2")
                print(f"{Fore.YELLOW}cancel{Style.RESET_ALL}  - Abortar TODAS las descargas actuales")
                print(f"{Fore.YELLOW}logs{Style.RESET_ALL}    - Ver los últimos movimientos del bot")
                print(f"{Fore.YELLOW}errors{Style.RESET_ALL}  - Ver el registro de fallos críticos")
                print(f"{Fore.YELLOW}clear{Style.RESET_ALL}   - Limpiar la pantalla de la consola")
                print(f"{Fore.YELLOW}restart{Style.RESET_ALL} - Reiniciar el bot (Aplicar cambios de código)")
                print(f"{Fore.CYAN}================================={Style.RESET_ALL}\n")
                
            elif cmd == 'status':
                downloads = aria2.get_downloads()
                if not downloads:
                    print(f"{Fore.GREEN}✔️ No hay descargas activas en este momento.{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.MAGENTA}--- 📥 DESCARGAS ACTIVAS ---{Style.RESET_ALL}")
                    for d in downloads:
                        print(f"{Fore.CYAN}ID:{Style.RESET_ALL} {d.gid[:6]} | {Fore.BLUE}{d.name[:40]}{Style.RESET_ALL} | {Fore.GREEN}{d.progress_string()}{Style.RESET_ALL} | 🚀 {d.download_speed_string()}")
                    print("")
                    
            elif cmd == 'cancel':
                downloads = aria2.get_downloads()
                if not downloads:
                    print(f"{Fore.YELLOW}⚠️ No hay nada que cancelar.{Style.RESET_ALL}")
                else:
                    for d in downloads:
                        aria2.remove([d])
                    print(f"{Fore.RED}🛑 TODAS las descargas han sido canceladas y eliminadas.{Style.RESET_ALL}")
                
            elif cmd == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"{Fore.GREEN}✨ Consola Limpia. Escribe 'help' para comandos.{Style.RESET_ALL}")

            elif cmd == 'logs':
                fecha = datetime.now().strftime("%Y-%m-%d")
                archivo = f"logs/bot_log_{fecha}.txt"
                if os.path.exists(archivo):
                    print(f"\n{Fore.MAGENTA}--- 📄 ÚLTIMOS LOGS DE HOY ---{Style.RESET_ALL}")
                    with open(archivo, "r", encoding="utf-8") as f:
                        lineas = f.readlines()[-15:] # Muestra las últimas 15
                        for l in lineas: print(l.strip())
                else: print(f"{Fore.YELLOW}Aún no hay logs hoy.{Style.RESET_ALL}")
                
            elif cmd == 'errors':
                if os.path.exists("logs/errores.txt"):
                    print(f"\n{Fore.RED}--- ❌ REGISTRO DE ERRORES ---{Style.RESET_ALL}")
                    with open("logs/errores.txt", "r", encoding="utf-8") as f:
                        lineas = f.readlines()[-15:]
                        for l in lineas: print(l.strip())
                else: print(f"{Fore.GREEN}¡Todo limpio! No hay errores registrados.{Style.RESET_ALL}")

            elif cmd == 'restart':
                print(f"{Fore.RED}🔄 Reiniciando el código del bot en 2 segundos...{Style.RESET_ALL}")
                time.sleep(2)
                cursor_chat.asegurar_tarea_en_disco()
                os.execv(sys.executable, ['python'] + sys.argv)
                
            else:
                print(f"{Fore.RED}❌ Comando desconocido. Escribe 'help' para ver la lista.{Style.RESET_ALL}")
        except EOFError:
            return
        except Exception as e:
            print(f"{Fore.RED}🚨 Error en consola local: {e}{Style.RESET_ALL}")
            return

# ==========================================
# 🚲 ALERTA MATUTINA BICIMAD
# ==========================================
WHATSAPP_PHONE = "+34618141435"
WHATSAPP_KEY_FILE = "whatsapp_apikey.txt"


def enviar_whatsapp(texto):
    """Aviso personal por WhatsApp. La clave sale al activar CallMeBot desde el propio móvil."""
    if not os.path.exists(WHATSAPP_KEY_FILE):
        print("WhatsApp pendiente: falta whatsapp_apikey.txt")
        return False
    with open(WHATSAPP_KEY_FILE, "r", encoding="utf-8") as archivo:
        clave = archivo.read().strip()
    if not clave:
        print("WhatsApp pendiente: la clave está vacía")
        return False
    limpio = str(texto).replace("**", "*").replace("`", "")
    try:
        respuesta = requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": WHATSAPP_PHONE, "text": limpio, "apikey": clave},
            timeout=25,
        )
        print(f"WhatsApp {respuesta.status_code}: {respuesta.text[:160].strip()}")
        return respuesta.ok and "error" not in respuesta.text.lower()
    except Exception as e:
        print(f"Error WhatsApp: {e}")
        return False


async def check_bicimad(context: ContextTypes.DEFAULT_TYPE, send_alert=True):
    estacion_id = "394"

    def _token_de(respuesta):
        data = respuesta.get("data") or []
        if isinstance(data, dict):
            return data.get("accessToken") or data.get("token")
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0].get("accessToken") or data[0].get("token")
        return None

    def _campo(estacion, *claves):
        for clave in claves:
            if estacion.get(clave) is not None:
                return estacion.get(clave)
        return None

    try:
        token = None
        version_ok = None
        for version in ("v2", "v1"):
            res_login = requests.get(
                f"https://openapi.emtmadrid.es/{version}/mobilitylabs/user/login/",
                headers={"email": EMT_EMAIL, "password": EMT_PASSWORD},
                timeout=15,
            ).json()
            token = _token_de(res_login)
            if token:
                version_ok = version
                break

        if not token:
            return None, None, "❌ EMT no ha aceptado el acceso. Revisa el usuario de MobilityLabs."

        # EMT ya no usa el número pintado en la estación como id. La 394 es Periana 24.
        res_bici = requests.get(
            f"https://openapi.emtmadrid.es/{version_ok}/transport/bicimad/stations/",
            headers={"accessToken": token},
            timeout=20,
        ).json()
        data = res_bici.get("data") or []
        if isinstance(data, dict):
            data = [data]
        estacion = None
        if isinstance(data, list):
            por_numero = next((e for e in data if str(e.get("number")) == estacion_id), None)
            por_id = next((e for e in data if str(e.get("id")) == estacion_id), None)
            estacion = por_numero or por_id
        if not estacion:
            return None, None, "❌ La estación no ha devuelto datos. Puede que EMT haya cambiado el identificador."

        bicis = _campo(estacion, "dock_bikes", "dockBikes", "bikes", "num_bikes")
        huecos = _campo(estacion, "free_bases", "freeBases", "free_docks")
        direccion = _campo(estacion, "address", "name", "direccion") or f"Estación {estacion_id}"
        
        if send_alert:
            msg = (
                f"🚲 **¡Buenos días Aarón!**\n\n"
                f"Son las 08:45. Tienes **{bicis} bicicletas** listas en la estación 394, Periana 24 (`{direccion}`)."
            )
            await context.bot.send_message(chat_id=ADMIN_IDS[0], text=msg, parse_mode='Markdown')
            await asyncio.to_thread(enviar_whatsapp, msg)
            
        return bicis, huecos, direccion
    except Exception as e:
        print(f"Error BiciMAD: {e}")
        return None, None, "❌ Error conectando con la estación. ¿Están caídos los servidores de EMT?"
# ==========================================
# 🚨 SISTEMA DE DESPERTAR (CIRUGÍA)
# ==========================================
RESTART_REQUEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restart_bot.request")
AVISO_IMAGEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aviso_imagen.txt")


async def vigilar_reinicio_solicitado(context: ContextTypes.DEFAULT_TYPE):
    """Reinicio pedido por Cursor o solicitar_reinicio_bot.py sin matar el proceso desde fuera."""
    if not os.path.isfile(RESTART_REQUEST_FILE):
        return
    chat_id = ""
    try:
        with open(RESTART_REQUEST_FILE, "r", encoding="utf-8") as archivo:
            chat_id = archivo.read().strip()
        os.remove(RESTART_REQUEST_FILE)
    except OSError:
        return
    if chat_id.isdigit():
        try:
            with open("reboot_alert.txt", "w", encoding="utf-8") as archivo:
                archivo.write(chat_id)
        except OSError:
            pass
    elif not chat_id:
        try:
            with open("reboot_alert.txt", "w", encoding="utf-8") as archivo:
                archivo.write(str(ADMIN_IDS[0]))
        except OSError:
            pass
    log_sistema("Reinicio del bot solicitado. Recargando código…")
    await asyncio.sleep(0.8)
    cursor_chat.asegurar_tarea_en_disco()
    os.execv(sys.executable, [sys.executable] + sys.argv)


async def _entregar_en_chat(bot, chat_id, message_id, texto):
    partes = cursor_chat.trocear(texto)
    for indice, parte in enumerate(partes):
        teclado = teclado_cursor() if indice == len(partes) - 1 else None
        if indice == 0 and message_id:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=int(message_id),
                    text=parte,
                    reply_markup=teclado,
                )
                continue
            except Exception as error:
                if "not modified" in str(error).lower():
                    continue
        await bot.send_message(chat_id=chat_id, text=parte, reply_markup=teclado)


async def _retomar_cursor(application):
    tarea = cursor_chat.tarea_en_curso()
    destino = {
        "chat_id": tarea.get("chat_id"),
        "message_id": tarea.get("message_id"),
    }

    async def progreso(linea):
        chat_id = destino.get("chat_id")
        if not chat_id:
            return
        texto = (linea or "")[:4000]
        message_id = destino.get("message_id")
        if message_id:
            try:
                await application.bot.edit_message_text(
                    chat_id=int(chat_id),
                    message_id=int(message_id),
                    text=texto,
                    reply_markup=teclado_cursor(),
                )
                return
            except Exception as error:
                if "not modified" in str(error).lower():
                    return
                destino["message_id"] = None
        try:
            enviado = await application.bot.send_message(
                chat_id=int(chat_id),
                text=texto,
                reply_markup=teclado_cursor(),
            )
            destino["chat_id"] = enviado.chat_id
            destino["message_id"] = enviado.message_id
        except Exception:
            pass

    try:
        resultado = await cursor_chat.reanudar_tarea(progreso)
    except Exception as error:
        resultado = f"Se ha cortado al retomar: {error}"
    if not resultado or not destino.get("chat_id"):
        return
    try:
        await _entregar_en_chat(
            application.bot,
            int(destino["chat_id"]),
            destino.get("message_id"),
            resultado,
        )
    except Exception as error:
        log_sistema(f"No pude entregar la tarea retomada: {error}", is_error=True)


async def _avisar_imagen_lista(application):
    """Avisa a Aarón una sola vez de que las imágenes ya salen por Telegram."""
    if not os.path.isfile(AVISO_IMAGEN_FILE):
        return False
    await application.bot.send_message(
        chat_id=ADMIN_IDS[0],
        text=(
            "🖼️ **Ya puedes hacer imágenes desde Telegram.**\n\n"
            "En el menú principal pulsa **Imagen**, o escribe /imagen.\n"
            "Tamaño, detalle, NSFW, semilla y copiar estilo, igual que en el panel. "
            "Te mando la foto a este chat."
        ),
        parse_mode="Markdown",
    )
    try:
        os.remove(AVISO_IMAGEN_FILE)
    except OSError as error:
        log_sistema(f"No pude retirar el aviso de imagen: {error}", is_error=True)
    log_sistema("Aviso de imagen enviado por Telegram.")
    return True


async def post_init(application: Application):
    """Se ejecuta una sola vez cuando el bot arranca por completo"""
    retoma = cursor_chat.preparar_retoma()
    aviso = os.path.isfile(AVISO_IMAGEN_FILE)
    log_sistema(f"Arranque. aviso_imagen={aviso}")
    if os.path.exists("reboot_alert.txt"):
        try:
            with open("reboot_alert.txt", "r", encoding='utf-8') as f:
                chat_id = f.read().strip()
            if aviso:
                await _avisar_imagen_lista(application)
            else:
                texto = "🚀 **¡Bot recargado!**\n\nEl código nuevo ya está en marcha (voz, Cursor, descargas…)."
                if retoma:
                    texto = "🚀 **¡Bot recargado!**\n\nSigo con la tarea que estaba en curso."
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=texto,
                    parse_mode='Markdown'
                )
            os.remove("reboot_alert.txt")
        except Exception as e:
            log_sistema(f"Error en post_init: {e}", is_error=True)
    elif aviso:
        try:
            await _avisar_imagen_lista(application)
        except Exception as error:
            log_sistema(f"Aviso imagen Telegram: {error}", is_error=True)
    if retoma:
        application.create_task(_retomar_cursor(application))
    if os.path.isfile(AVISO_IMAGEN_FLAG):
        try:
            await application.bot.send_message(
                chat_id=ADMIN_IDS[0],
                text=(
                    "🖼️ **Imagen por Telegram, lista**\n\n"
                    "Menú **Bot → Imagen** o comando `/imagen`.\n"
                    "Tamaño, detalle, NSFW y semilla igual que en el panel."
                ),
                parse_mode="Markdown",
            )
            os.remove(AVISO_IMAGEN_FLAG)
        except Exception as error:
            print(f"Aviso imagen Telegram: {error}")


def _es_aaron(update):
    usuario = update.effective_user
    return bool(usuario and usuario.id == ADMIN_IDS[0])


def teclado_cursor():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Nueva conversación", callback_data="cursor_new")],
        [
            InlineKeyboardButton("⏹ Parar", callback_data="cursor_cancel"),
            InlineKeyboardButton("🔄 Reiniciar bot", callback_data="cursor_restart"),
        ],
        [InlineKeyboardButton("🔙 Menú principal", callback_data="cursor_exit")],
    ])


CURSOR_AYUDA = (
    "🤖 **Cursor en este PC**\n\n"
    "Escríbeme lo que quieras hacer en el bot o en el ordenador. "
    "También puedes mandar **nota de voz o audio**: lo transcribo al castellano, "
    "lo guardo como borrador y tú confirmas, editas o lo envías a Cursor.\n\n"
    "Sigo en la misma conversación hasta que pulses Nueva. "
    "Si reinicias el bot mientras trabajo, sigo con esa tarea y te contesto al volver.\n\n"
    "Desde cualquier sitio:\n"
    "`/ia mira cuánto espacio queda en Z:`\n"
    "`/ia nueva` empieza de cero\n"
    "`/ia parar` corta lo que esté haciendo\n\n"
    "Si cambio código del bot, pulsa Reiniciar para cargarlo."
)


async def _publicar_cursor(status_msg, texto):
    partes = cursor_chat.trocear(texto)
    for indice, parte in enumerate(partes):
        teclado = teclado_cursor() if indice == len(partes) - 1 else None
        if indice == 0:
            try:
                await status_msg.edit_text(parte, reply_markup=teclado)
            except Exception:
                await status_msg.get_bot().send_message(
                    chat_id=status_msg.chat_id, text=parte, reply_markup=teclado
                )
        else:
            await status_msg.get_bot().send_message(
                chat_id=status_msg.chat_id, text=parte, reply_markup=teclado
            )


async def _consultar_y_publicar(status, texto):
    ultimo = {"t": 0.0}

    async def progreso(linea):
        ahora = time.monotonic()
        if ahora - ultimo["t"] < 2:
            return
        ultimo["t"] = ahora
        try:
            await status.edit_text(linea[:4000], reply_markup=teclado_cursor())
        except Exception:
            pass

    try:
        resultado = await cursor_chat.consultar(
            texto,
            progreso,
            chat_id=status.chat_id,
            message_id=status.message_id,
        )
    except cursor_chat.Ocupado:
        try:
            await status.edit_text(
                "Sigo con el mensaje anterior. Espera o pulsa Parar.",
                reply_markup=teclado_cursor(),
            )
        except Exception:
            pass
        return
    except Exception as error:
        resultado = f"Se ha cortado: {error}"
    await _publicar_cursor(status, resultado)


async def _lanzar_cursor(mensaje, texto, application):
    quien = mensaje.from_user.first_name if mensaje.from_user else "Aarón"
    log_accion(quien, "Ha hablado con Cursor", Fore.CYAN, dialogo=texto[:180])
    if not cursor_chat.hay_clave():
        await mensaje.reply_text(cursor_chat.texto_sin_clave(), reply_markup=teclado_cursor())
        return
    status = await mensaje.reply_text(
        "⏳ Recibido. Me pongo con ello.",
        reply_markup=teclado_cursor(),
    )
    application.create_task(_consultar_y_publicar(status, texto))


async def cursor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_aaron(update):
        if update.message:
            await update.message.reply_text("Esto solo lo puede usar Aarón.")
        return None
    args = context.args or []
    orden = " ".join(args).strip()
    bajo = orden.lower()
    if cursor_chat.guardar_clave_si_viene(orden):
        await update.message.reply_text(
            "Clave guardada. Ya puedes pedirme cosas del bot o del PC.",
            reply_markup=teclado_cursor(),
        )
        return AWAITING_CURSOR
    if not orden:
        await update.message.reply_text(CURSOR_AYUDA, parse_mode="Markdown", reply_markup=teclado_cursor())
        return AWAITING_CURSOR
    if bajo in ("nueva", "nuevo", "reset"):
        await cursor_chat.reiniciar_conversacion()
        await update.message.reply_text(
            "Conversación nueva. El siguiente mensaje empieza de cero.",
            reply_markup=teclado_cursor(),
        )
        return AWAITING_CURSOR
    if bajo in ("parar", "cancelar", "stop"):
        parado = await cursor_chat.cancelar()
        await update.message.reply_text(
            "Paro la tarea." if parado else "No había nada en marcha.",
            reply_markup=teclado_cursor(),
        )
        return AWAITING_CURSOR
    await _lanzar_cursor(update.message, orden, context.application)
    return AWAITING_CURSOR


async def cursor_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_aaron(update):
        await update.message.reply_text("Esto solo lo puede usar Aarón.")
        return AWAITING_CURSOR
    texto = (update.message.text or "").strip()
    if not texto:
        return AWAITING_CURSOR
    if cursor_chat.guardar_clave_si_viene(texto):
        await update.message.reply_text(
            "Clave guardada. Ya puedes pedirme cosas del bot o del PC.",
            reply_markup=teclado_cursor(),
        )
        return AWAITING_CURSOR
    if texto.lower() in ("nueva", "/nueva"):
        await cursor_chat.reiniciar_conversacion()
        await update.message.reply_text(
            "Conversación nueva. El siguiente mensaje empieza de cero.",
            reply_markup=teclado_cursor(),
        )
        return AWAITING_CURSOR
    await _lanzar_cursor(update.message, texto, context.application)
    return AWAITING_CURSOR


async def cursor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not _es_aaron(update):
        await query.answer("Solo Aarón", show_alert=True)
        return None
    await query.answer()
    if query.data == "cursor_open":
        await show_text_menu(query, CURSOR_AYUDA, reply_markup=teclado_cursor(), parse_mode="Markdown")
        return AWAITING_CURSOR
    if query.data == "cursor_exit":
        await show_text_menu(
            query,
            "🏠 **MENÚ PRINCIPAL**\n\nSelecciona una categoría para empezar:",
            reply_markup=get_keyboard("main", update.effective_user.id),
            parse_mode="Markdown",
        )
        return MENU
    if query.data == "cursor_new":
        await cursor_chat.reiniciar_conversacion()
        await query.edit_message_text(
            "Conversación nueva. El siguiente mensaje empieza de cero.",
            reply_markup=teclado_cursor(),
        )
        return AWAITING_CURSOR
    if query.data == "cursor_cancel":
        parado = await cursor_chat.cancelar()
        await query.edit_message_text(
            "Paro la tarea." if parado else "No había nada en marcha.",
            reply_markup=teclado_cursor(),
        )
        return AWAITING_CURSOR
    if query.data == "cursor_restart":
        await query.edit_message_text("🔄 Reiniciando el bot para cargar el código nuevo...")
        with open("reboot_alert.txt", "w", encoding="utf-8") as archivo:
            archivo.write(str(update.effective_chat.id))
        await asyncio.sleep(1)
        cursor_chat.asegurar_tarea_en_disco()
        os.execv(sys.executable, [sys.executable] + sys.argv)
    return AWAITING_CURSOR


def main():
    init_system()

    application = Application.builder().token(TOKEN).post_init(post_init).build()

    job_queue = application.job_queue
    job_queue.run_repeating(check_series_updates, interval=1800, first=10)
    job_queue.run_repeating(vigilar_reinicio_solicitado, interval=2, first=2)

    import datetime
    from zoneinfo import ZoneInfo
    
    # 🚲 Aviso BiciMAD a las 08:45 (Madrid), todos los días, por Telegram y WhatsApp.
    hora_aviso = datetime.time(hour=8, minute=45, tzinfo=ZoneInfo("Europe/Madrid"))
    # En python-telegram-bot 20+ el día 0 es domingo y el 6 es sábado.
    job_queue.run_daily(check_bicimad, time=hora_aviso, days=(0, 1, 2, 3, 4, 5, 6))

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('ia', cursor_command),
            CommandHandler('imagen', imagen_command),
            CommandHandler('nova', hot_entrar),
            MessageHandler(
                filters.TEXT & filters.Regex(r"(?i)^aaroncuentawow\s*$") & filters.ChatType.PRIVATE,
                hot_entrar_clave,
            ),
        ],
        states={
            MENU: [
                CallbackQueryHandler(imagen_callback, pattern='^(imagen_menu|img_)'),
                CallbackQueryHandler(menu_handler, pattern='^(magnet|search|space|tracker|help|back_to_main|restart_pc|control_panel|pc_status|parsec_status|bicimad_status|anime_sources_check|help_magnet|help_search_info|help_tracker_info|help_social_info|suggest_movie|gestion_media|menu_bajar|menu_curso|menu_casa|menu_bot)$'),
                CallbackQueryHandler(file_explorer, pattern='^(explorer_root|exp_go_.*|exp_back|exp_page_next|exp_page_prev)$'),
                CallbackQueryHandler(file_explorer_actions, pattern='^(exp_dl|exp_del)$'),
                CallbackQueryHandler(manual_check, pattern='^track_check_now$'),
                CallbackQueryHandler(handle_spotify_dl, pattern='^spotdl_yes$'),
                CallbackQueryHandler(handle_aspiradora_actions, pattern='^(continue_plex_anime|suggest_aspiradora|start_aspiradora)$'),
                CallbackQueryHandler(handle_yt_magia, pattern='^ytmagia_'),
                CallbackQueryHandler(handle_yt_format, pattern='^ytfmt_'),
                CallbackQueryHandler(handle_tracked_anime_dl, pattern='^dlanime_'),
                CallbackQueryHandler(show_anime_calendar, pattern='^anime_calendar$'),
                CallbackQueryHandler(confirm_anime_dl, pattern='^confirm_anime_dl$'),
                CallbackQueryHandler(search_radarr_start, pattern='^search_radarr_start$'),
                CallbackQueryHandler(search_apk_start, pattern='^search_apk_start$'),
                CallbackQueryHandler(search_manga_start, pattern='^search_manga_start$'),
                CallbackQueryHandler(dl_manga_chapter, pattern='^(mangalast_|mangavol_)'),
                CallbackQueryHandler(track_add_start, pattern='^track_add$'),
                CallbackQueryHandler(track_delete, pattern='^track_del$'),
                CallbackQueryHandler(dev_menu_handler, pattern='^dev_menu$'),
                CallbackQueryHandler(dl_manager, pattern='^dl_manager$'),
                CallbackQueryHandler(pause_dl, pattern='^pause_dl_'),
                CallbackQueryHandler(resume_dl, pattern='^resume_dl_'),
                CallbackQueryHandler(hide_dl, pattern='^hide_dl_'),
                CallbackQueryHandler(handle_tracked_download, pattern='^dl_track_'),
                CallbackQueryHandler(search_artist_start, pattern='^search_artist_start$'),

                CallbackQueryHandler(track_delete_confirm, pattern='^del_serie_'),
                CallbackQueryHandler(tracker_menu_handler, pattern='^tracker_menu$'),
                MessageHandler(filters.Regex(r'(?i)(youtube\.com|youtu\.be|tiktok\.com|instagram\.com|spotify\.com|animeflv\.|animefenix\.|tioanime\.|monoschinos|jkanime\.|animeblix\.|animeid\.|animeav1\.com)'), handle_social_link),
                CallbackQueryHandler(ryujinx_menu, pattern='^menu_ryujinx$'),
                CallbackQueryHandler(ryujinx_device, pattern='^ryudev_'),
                CallbackQueryHandler(ryujinx_boot, pattern='^ryuboot_'),
                CallbackQueryHandler(search_content, pattern='^search_suggested$'),
                CallbackQueryHandler(process_magnet, pattern='^dl_suggested$'),
                CallbackQueryHandler(renaming_handler, pattern='^(use_suggested|keep_original|manual_rename)$'),
                CallbackQueryHandler(game_launcher, pattern='^game_launcher$'),
                CallbackQueryHandler(launch_game, pattern='^(launch_fortnite|kill_games)$'),
                CallbackQueryHandler(cancel_ask, pattern='^ask_cancel_'),
                CallbackQueryHandler(cancel_confirm, pattern='^do_cancel_'),
                CallbackQueryHandler(cancel_resume, pattern='^resume_'),
                MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_menu),
            ],

            AWAITING_MAGNET: [
                CallbackQueryHandler(cancel_ask, pattern='^ask_cancel_'),
                CallbackQueryHandler(cancel_confirm, pattern='^do_cancel_'),
                CallbackQueryHandler(cancel_resume, pattern='^resume_'),
                MessageHandler(filters.Regex(r'(?i)(youtube\.com|youtu\.be|tiktok\.com|instagram\.com|spotify\.com|music\.youtube|animeflv\.|animefenix\.|tioanime\.|monoschinos|jkanime\.|animeblix\.|animeid\.|animeav1\.com)'), handle_social_link),
                CallbackQueryHandler(handle_yt_magia, pattern='^ytmagia_'),
                CallbackQueryHandler(handle_yt_format, pattern='^ytfmt_'),
                MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.Document.FileExtension("torrent"), process_magnet),
                CallbackQueryHandler(menu_handler)
            ],
            
            AWAITING_SEARCH: [
                CallbackQueryHandler(cancel_ask, pattern='^ask_cancel_'),
                CallbackQueryHandler(cancel_confirm, pattern='^do_cancel_'),
                CallbackQueryHandler(cancel_resume, pattern='^resume_'),
                MessageHandler(filters.VOICE | filters.AUDIO, handle_voice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_content), 
                CallbackQueryHandler(handle_search_click)
            ],
            AWAITING_NEW_SERIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, track_add_save), CallbackQueryHandler(tracker_menu_handler)],

            RENAMING: [CallbackQueryHandler(renaming_handler), MessageHandler(filters.TEXT & ~filters.COMMAND, renaming_handler)],
            MOVING_CATEGORY: [CallbackQueryHandler(move_and_plex)],
            SUBTITLES_SEARCH: [CallbackQueryHandler(subtitle_handler, pattern='^subs_')],
            PLEX_UPDATE: [CallbackQueryHandler(plex_trigger)],
            AWAITING_DEV_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_dev_search),
                CallbackQueryHandler(menu_handler, pattern='^(back_to_main|menu_bot)$')
            ],
            AWAITING_DEV_REPLACE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_dev_replace),
                CallbackQueryHandler(dev_delete_action, pattern='^dev_delete_code$'),
                CallbackQueryHandler(menu_handler, pattern='^(back_to_main|menu_bot)$')
            ],
            AWAITING_ARTIST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_artist),
                CallbackQueryHandler(handle_artist_nav, pattern='^artnav_'),
                CallbackQueryHandler(handle_artist_dl, pattern='^artdl_'),
                CallbackQueryHandler(menu_handler, pattern='^(back_to_main|menu_bajar)$')
            ],   
            AWAITING_APK_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_apk_query),
                CallbackQueryHandler(handle_apk_nav, pattern='^apknav_'),
                CallbackQueryHandler(handle_apk_dl, pattern='^apkdl_'),
                CallbackQueryHandler(menu_handler, pattern='^(back_to_main|menu_bajar)$')
            ],   
            AWAITING_MANGA_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_manga_query),
                CallbackQueryHandler(handle_manga_nav, pattern='^manganav_'),
                CallbackQueryHandler(dl_manga_chapter, pattern='^(mangalast_|mangavol_)'),
                CallbackQueryHandler(menu_handler, pattern='^(back_to_main|menu_bajar)$')
            ],
            AWAITING_RADARR_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_radarr_query),
                CallbackQueryHandler(handle_radarr_nav, pattern='^radnav_'),
                CallbackQueryHandler(handle_radarr_dl, pattern='^raddl_'),
                CallbackQueryHandler(menu_handler, pattern='^(back_to_main|menu_bajar)$')
            ],
            DEV_MENU: [
                CallbackQueryHandler(handle_patch_decision, pattern='^(confirm_patch|cancel_patch)$')
            ],
            AWAITING_CURSOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cursor_message),
                MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_cursor),
                CallbackQueryHandler(menu_handler, pattern='^back_to_main$'),
            ],
            AWAITING_VOICE_CONFIRM: [
                CallbackQueryHandler(voice_order_callback, pattern='^voice_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, voice_edit_message),
                MessageHandler(
                    filters.VOICE | filters.AUDIO,
                    lambda u, c: procesar_nota_voz(
                        u, c, c.user_data.get("voice_origin", "menu")
                    ),
                ),
            ],
            AWAITING_VOICE_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, voice_edit_message),
                CallbackQueryHandler(voice_order_callback, pattern='^voice_discard$'),
            ],
            AWAITING_IMAGEN_PROMPT: [
                CallbackQueryHandler(imagen_callback, pattern='^(imagen_menu|img_)'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, imagen_prompt_message),
            ],
            AWAITING_IMAGEN_SEED: [
                CallbackQueryHandler(imagen_callback, pattern='^(imagen_menu|img_)'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, imagen_seed_message),
            ],
            AWAITING_IMAGEN_REF: [
                CallbackQueryHandler(imagen_callback, pattern='^(imagen_menu|img_)'),
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, imagen_referencia_message),
            ],
            AWAITING_HOT: [
                CommandHandler("salir", hot_salir),
                MessageHandler(filters.TEXT & ~filters.COMMAND, hot_mensaje),
            ],
        },
        fallbacks=[CommandHandler('start', start), CommandHandler('salir', hot_salir)]
    )

    for lista in conv_handler.states.values():
        lista.insert(0, CallbackQueryHandler(cursor_callback, pattern='^cursor_'))
        lista.insert(0, CommandHandler('ia', cursor_command))
        lista.insert(0, CommandHandler('imagen', imagen_command))

    application.add_handler(conv_handler)

    print(f"\n{Fore.CYAN}======================================================{Style.RESET_ALL}")
    print(f"{Fore.GREEN} 🚀 SERVIDOR BOT INICIADO Y LISTO PARA LA ACCIÓN 🚀 {Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================================{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}💡 Escribe 'help' y pulsa ENTER para ver el Panel de Control.{Style.RESET_ALL}\n")
    
    console_thread = threading.Thread(target=console_manager, daemon=True)
    console_thread.start()

    application.run_polling()

if __name__ == '__main__':
    main()
