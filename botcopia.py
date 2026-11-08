from bs4 import BeautifulSoup # <--- IMPRESCINDIBLE AÑADIR ESTO ARRIBA
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
import json # <--- AÑADIR ESTO EN LOS IMPORTS

# ... (tus otras variables como TOKEN, ADMIN_ID...)

# AÑADIR ESTO EN LA SECCIÓN DE VARIABLES GLOBALES
TRACKING_FILE = "bot_series_tracking.json"

# Palabras clave para detectar Castellano/Subs (Para filtrar basura)
KEYWORDS_ES = ['spani', 'esp', 'castellano', 'latino', 'sub', 'vose', 'multi']


# ==========================================
# ⚙️ CONFIGURACIÓN Y VARIABLES GLOBALES
# ==========================================

# TUS DATOS (Ya integrados)
TOKEN = "8271112705:AAG5V7E2NM0tfdl3bDC3RyNas_fPrIiHPTU"
ADMIN_ID = 1156812303

# Usa barras normales (/) o dobles barras (\\) en Windows
BASE_DOWNLOAD_PATH = 'Z:/Descargas_Bot'
PLEX_FINAL_PATH = 'Z:/Plex_Confirmados'
# Guardamos el archivo de seguimiento en la misma carpeta que el bot para no perderlo
TRACKING_FILE = 'bot_series_tracking.json'

# Configuración de PLEX (Para actualizar biblioteca)
# NOTA: En Colab, "localhost" no funcionará. Necesitarás tu IP Pública si quieres que el bot de Colab despierte a tu Plex de casa.
# Si mueves el bot a tu PC, pon 'http://127.0.0.1:32400'
PLEX_URL = "http://127.0.0.1:32400"
PLEX_TOKEN = "X3SsGBPPYvxyuhGs5GCi"

# Estados de la Conversación
MENU, AWAITING_MAGNET, AWAITING_SEARCH, POST_DOWNLOAD_DECISION, RENAMING, MOVING_CATEGORY, PLEX_UPDATE, AWAITING_NEW_SERIES = range(8)

# Inicialización de Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 🚀 INICIALIZACIÓN DEL SISTEMA (ARIA2 & DRIVE)
# ==========================================

def init_system():

    # 2. Crear carpetas si no existen
    for path in [BASE_DOWNLOAD_PATH, PLEX_FINAL_PATH,
                 f"{PLEX_FINAL_PATH}/Peliculas",
                 f"{PLEX_FINAL_PATH}/Series",
                 f"{PLEX_FINAL_PATH}/Anime"]:
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Carpeta creada: {path}")

    # 3. Iniciar Aria2 en modo Daemon (segundo plano)
    try:
    # Asumimos que aria2c.exe está en la misma carpeta que el bot
        subprocess.Popen(['aria2c.exe', '--enable-rpc', '--rpc-listen-all=false', '--rpc-allow-origin-all', 
                  '--daemon=false', f'--dir={BASE_DOWNLOAD_PATH}', '--max-connection-per-server=10', 
                  '--seed-time=0'])
        time.sleep(3) # Esperar a que arranque
        print("Aria2 Daemon iniciado.")
    except Exception as e:
        print(f"Error iniciando Aria2: {e}")

# Cliente Aria2p
aria2 = aria2p.API(aria2p.Client(host="http://localhost", port=6800, secret=""))

# ==========================================
# 🛠️ FUNCIONES AUXILIARES
# ==========================================

def get_keyboard(menu_type):
    if menu_type == "main":
        keyboard = [
            [InlineKeyboardButton("🧲 Pega tu Magnet", callback_data='magnet')],
            [InlineKeyboardButton("🔍 Busca tu contenido", callback_data='search')],
            [InlineKeyboardButton("💾 Espacio en Drive", callback_data='space')],
            [InlineKeyboardButton("📺 Seguimiento Series", callback_data='tracker')], # Placeholder
            [InlineKeyboardButton("❓ Ayuda / Estado", callback_data='help')]
        ]
    elif menu_type == "back":
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data='back_to_main')]]
    return InlineKeyboardMarkup(keyboard)

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
    if user_id != ADMIN_ID:
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
        # --- MODO COLAB (API) ---
        # Intentamos importar librerías exclusivas de Google Colab
        # Si esto falla (porque estás en tu PC), saltará al 'except' automáticamente.
        from google.colab import auth
        from googleapiclient.discovery import build

        # Construimos un cliente de API para leer tu cuota real de la nube
        # Utiliza las credenciales de la sesión de Colab
        drive_service = build('drive', 'v3')
        about = drive_service.about().get(fields='storageQuota').execute()
        quota = about['storageQuota']

        total = int(quota['limit'])
        used = int(quota['usage'])
        free = total - used
        percent_free = (free / total) * 100

        return format_size(total), format_size(used), format_size(free), percent_free

    except Exception:
        # --- MODO PC / FALLBACK ---
        # Si estamos en tu PC o falla la API, usamos el método de disco tradicional.
        # En Windows/Linux con Google Drive montado, esto funcionará correctamente.
        try:
            total, used, free = shutil.disk_usage(DRIVE_MOUNT_PATH)
            return format_size(total), format_size(used), format_size(free), (free/total)*100
        except:
            return "0B", "0B", "0B", 0

# ==========================================
# 📱 MANEJO DEL BOT
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await restricted(update, context): return

    user_first_name = update.effective_user.first_name
    welcome_msg = (
        f"👋 **¡Hola {user_first_name}! Bienvenido a tu Gestor de Descargas.**\n\n"
        "Estoy conectado a tu Google Drive y listo para descargar contenido para tu Plex.\n"
        "El motor Aria2 está rugiendo. ¿Qué hacemos hoy?"
    )
    await update.message.reply_text(welcome_msg, reply_markup=get_keyboard("main"), parse_mode='Markdown')
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # 1. Botón ATRÁS
    if query.data == 'back_to_main':
        await query.edit_message_text(
            "🏠 **Menú Principal**\nSelecciona una opción:",
            reply_markup=get_keyboard("main"),
            parse_mode='Markdown'
        )
        return MENU

    # 2. Botón PEGA TU MAGNET
    elif query.data == 'magnet':
        await query.edit_message_text(
            "🧲 **Modo Magnet**\n\nPor favor, pega el enlace Magnet o Torrent ahora.\nLa descarga iniciará automáticamente.",
            reply_markup=get_keyboard("back"), parse_mode='Markdown'
        )
        return AWAITING_MAGNET

    # 3. Botón BUSCA TU CONTENIDO
    elif query.data == 'search':
        await query.edit_message_text(
            "🔍 **Buscador de Contenido**\n\nEscribe el nombre de la Película, Serie o Anime.\n_Buscaré en Nyaa (Anime) y YTS (Cine)._",
            reply_markup=get_keyboard("back"), parse_mode='Markdown'
        )
        return AWAITING_SEARCH

    # 4. Botón ESPACIO EN DRIVE
    elif query.data == 'space':
        await query.edit_message_text("⏳ Calculando espacio real en la nube...", parse_mode='Markdown')

        total, used, free, percent_free = check_drive_space()

        if percent_free < 10:
            alert = "⚠️ **¡Espacio Bajo!**"
            icon_status = "❌"
        else:
            alert = "✅ Espacio Saludable"
            icon_status = "✅"

        msg = (
            f"💾 **Estado de Google Drive**\n\n"
            f"📦 Total: {total}\n"
            f"{icon_status} Usado: {used}\n"
            f"✅ Libre: {free}\n\n"
            f"{alert} (Queda un {percent_free:.1f}%)"
        )
        await query.edit_message_text(msg, reply_markup=get_keyboard("back"), parse_mode='Markdown')
        return MENU

    # 5. Botón SEGUIMIENTO SERIES
    elif query.data == 'tracker':
        return await tracker_menu_handler(update, context)

    # 6. Botón AYUDA
    elif query.data == 'help':
        try:
            aria_status = "🟢 Online" if aria2.get_version() else "🔴 Offline"
        except:
            aria_status = "🔴 Offline"

        help_text = (
            "🤖 **Ayuda y Estado**\n\n"
            f"📡 **Bot:** Online\n"
            f"🚀 **Motor Aria2:** {aria_status}\n\n"
            "**Instrucciones:**\n"
            "1. 🧲 Pega Magnets directos.\n"
            "2. 🔍 Busca por nombre (Anime/Cine).\n"
            "3. 📂 El bot organiza carpetas automáticamente si aceptas la sugerencia de nombre."
        )
# --- CAMBIO AQUÍ ---
        kb_ayuda = [
            [InlineKeyboardButton("🔄 Reiniciar PC", callback_data='restart_pc')],
            [InlineKeyboardButton("🔙 Atrás", callback_data='back_to_main')]
        ]
        await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(kb_ayuda), parse_mode='Markdown')
        return MENU
# 7. Lógica para REINICIAR PC
    elif query.data == 'restart_pc':
        # Avisamos al usuario
        await query.answer("⚠️ Orden recibida")
        await query.edit_message_text(
            "🔄 **REINICIANDO SERVIDOR**\n\n"
            "El PC se reiniciará en 5 segundos.\n"
            "El bot volverá a arrancar automáticamente al iniciar Windows.",
            parse_mode='Markdown'
        )
        # Ejecutamos el comando de Windows (shutdown /r = restart, /t 5 = en 5 segundos)
        os.system("shutdown /r /t 5")
        return MENU
# --- MENÚ PRINCIPAL DEL TRACKER ---
async def tracker_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Intentamos responder, si da error (porque venimos de otro lado) lo ignoramos
    try: await query.answer()
    except: pass

    series_list = load_tracked_series()

    # Texto bonito con la lista
    if not series_list:
        status_text = "📭 **No estás siguiendo ninguna serie.**\nDale a 'Añadir' para empezar."
    else:
        status_text = "📋 **Tus Series en Seguimiento:**\n\n"
        for name, data in series_list.items():
            last = data.get('last_notified', 'Ninguno')
            status_text += f"• **{name}** (Último: {last[:15]}...)\n"

    keyboard = [
        [InlineKeyboardButton("➕ Añadir Serie", callback_data='track_add')],
        [InlineKeyboardButton("🗑️ Borrar Serie", callback_data='track_del')],
        [InlineKeyboardButton("🔄 Buscar Ahora (Forzar)", callback_data='track_check_now')],
        [InlineKeyboardButton("🔙 Volver al Menú", callback_data='back_to_main')]
    ]

    # Truco para editar mensaje o enviar nuevo según de donde vengamos
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
        "✍️ **Escribe el nombre EXACTO de la serie a seguir.**\n\n"
        "Ejemplo: `Jujutsu Kaisen`, `One Piece`, `House of the Dragon`.\n"
        "_(Cuanto más preciso, mejor funcionará el filtro)_",
        parse_mode='Markdown'
    )
    return AWAITING_NEW_SERIES # <--- Nuevo estado

# --- PASO 2: GUARDAR SERIE ---
async def track_add_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    serie_name = update.message.text.strip()

    data = load_tracked_series()
    # Guardamos la serie con un historial vacío
    data[serie_name] = {'last_hash': '', 'last_notified': 'Nada aún'}
    save_tracked_series(data)

    await update.message.reply_text(f"✅ **¡Añadida!**\nAhora buscaré capítulos nuevos de `{serie_name}` automáticamente.", parse_mode='Markdown')

    # Volvemos al menú del tracker
    return await tracker_menu_handler(update, context)

# --- BORRAR SERIE (SIMPLE) ---
async def track_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_tracked_series()
    if not data:
        await query.edit_message_text("❌ No hay series para borrar.", reply_markup=get_keyboard("back"))
        return MENU

    # Creamos botones con los nombres para borrar fácil
    keyboard = []
    for name in data.keys():
        keyboard.append([InlineKeyboardButton(f"❌ {name}", callback_data=f'del_serie_{name}')])
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='tracker_menu')]) # Ojo al callback

    await query.edit_message_text("🗑️ **Selecciona qué serie borrar:**", reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

async def track_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    serie_to_del = query.data.replace('del_serie_', '')
    data = load_tracked_series()

    if serie_to_del in data:
        del data[serie_to_del]
        save_tracked_series(data)
        await query.edit_message_text(f"🗑️ `{serie_to_del}` eliminada de la lista.", parse_mode='Markdown')
        # Pequeña pausa y volvemos al menú
        await asyncio.sleep(1)
        return await tracker_menu_handler(update, context)
    else:
        await query.edit_message_text("⚠️ Error: Esa serie ya no estaba.", reply_markup=get_keyboard("back"))
        return MENU
async def check_series_updates(context: ContextTypes.DEFAULT_TYPE):
    """Esta función se ejecutará automáticamente cada X tiempo"""
    print("🔄 Ejecutando chequeo automático de series...") # Log en Colab

    data = load_tracked_series()
    if not data:
        return

    # Recorremos cada serie que sigues
    for serie_name, info in data.items():
        try:
            # 1. Buscamos en Nyaa (Anime) primero
            query_url = serie_name.replace(' ', '+')
            url = f"https://nyaa.si/?f=0&c=0_0&q={query_url}&s=id&o=desc" # Ordenado por FECHA (id desc) para ver lo nuevo

            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                rows = soup.select('tr.default, tr.success')

                found_new = False

                # Revisamos los primeros 5 resultados
                for row in rows[:5]:
                    cols = row.find_all('td')

                    # Título
                    link_list = cols[1].find_all('a')
                    title = link_list[-1].text.strip() if len(link_list) > 1 else link_list[0].text.strip()

                    # Magnet
                    links = cols[2].find_all('a')
                    magnet = next((l['href'] for l in links if l['href'].startswith('magnet:')), None)

                    # Hash (Identificador único del torrent)
                    # Lo sacamos del magnet: xt=urn:btih:HASH...
                    magnet_hash = re.search(r'btih:([a-zA-Z0-9]+)', magnet).group(1) if magnet else None

                    if not magnet or not magnet_hash: continue

                    # --- FILTROS DE CALIDAD Y IDIOMA ---
                    title_lower = title.lower()

                    # 1. ¿Es lo que buscamos? (A veces las búsquedas traen basura parecida)
                    if serie_name.lower() not in title_lower: continue

                    # 2. ¿Ya lo hemos avisado?
                    if magnet_hash == info.get('last_hash'):
                        break # Si el más nuevo ya lo tenemos, paramos de buscar en esta serie

                    # 3. Filtro de Idioma (Español/Subs)
                    # Comprobamos si alguna palabra clave está en el título
                    is_spanish = any(key in title_lower for key in KEYWORDS_ES)

                    # 4. Filtro de Calidad (Opcional, priorizamos 1080p)
                    is_hd = '1080' in title_lower

                    # Si cumple idioma (o asumimos inglés si no es estricto, pero pediste castellano)
                    # Para ser estrictos:
                    if is_spanish:
                        found_new = True

                        # --- ¡NOTIFICAR AL USUARIO! ---

                        # Guardamos este magnet en el botón para que al pulsarlo se descargue
                        # Usamos el contexto global para pasar el magnet al click handler
                        # TRUCO: Como el callback tiene límite de tamaño, guardamos el magnet en memoria
                        # y pasamos el hash en el botón.
                        context.application.bot_data[f"hash_{magnet_hash}"] = magnet

                        keyboard = [[InlineKeyboardButton("⬇️ Descargar Ahora", callback_data=f'dl_track_{magnet_hash}')]]

                        msg = (
                            f"🔔 **¡Nuevo Capítulo Detectado!**\n\n"
                            f"📺 **Serie:** {serie_name}\n"
                            f"📄 **Archivo:** `{title}`\n"
                            f"✨ **Calidad:** {'1080p ✅' if is_hd else 'Estándar'}\n\n"
                            "¿Quieres descargarlo?"
                        )

                        # Enviamos mensaje proactivo
                        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

                        # Actualizamos la base de datos para no avisar más de este
                        data[serie_name]['last_hash'] = magnet_hash
                        data[serie_name]['last_notified'] = title
                        save_tracked_series(data)
                        break # Solo avisamos del más nuevo encontrado, no de golpe 5 capítulos

        except Exception as e:
            print(f"Error revisando {serie_name}: {e}")

# Función manual para el botón "Buscar Ahora"
async def manual_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔍 Buscando actualizaciones en todas tus series...")
    await check_series_updates(context) # Llamamos a la lógica
    await query.message.reply_text("✅ Búsqueda finalizada.")
    return MENU
async def handle_tracked_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Extraemos el hash del botón
    magnet_hash = query.data.replace('dl_track_', '')

    # Recuperamos el magnet completo de la memoria del bot
    magnet_link = context.application.bot_data.get(f"hash_{magnet_hash}")

    if magnet_link:
        # Preparamos el contexto para usar process_magnet
        context.user_data['search_magnet'] = magnet_link

        # Simulamos que venimos de una búsqueda para reutilizar process_magnet
        # ¡OJO! process_magnet espera que 'update.callback_query' exista, lo cual es cierto aquí.
        await query.message.reply_text(f"🚀 **Recibido.** Iniciando descarga de la serie...")
        return await process_magnet(update, context)
    else:
        await query.message.reply_text("⚠️ El enlace ha caducado o hay un error. Intenta buscar manualmente.")
        return MENU

def main():
    init_system()

    # ⚠️ IMPORTANTE: Añadir job_queue para tareas en segundo plano
    application = Application.builder().token(TOKEN).build()

    # PROGRAMAR TAREA AUTOMÁTICA (Cada 30 minutos = 1800 segundos)
    job_queue = application.job_queue
    job_queue.run_repeating(check_series_updates, interval=1800, first=10) # first=10 ejecuta a los 10s de iniciar

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [
                CallbackQueryHandler(menu_handler, pattern='^(magnet|search|space|tracker|help|back_to_main)$'),
                CallbackQueryHandler(manual_check, pattern='^track_check_now$'),
                CallbackQueryHandler(track_add_start, pattern='^track_add$'),
                CallbackQueryHandler(track_delete, pattern='^track_del$'),
                CallbackQueryHandler(handle_tracked_download, pattern='^dl_track_'), # Clic en descarga automática
                CallbackQueryHandler(track_delete_confirm, pattern='^del_serie_'),
                CallbackQueryHandler(tracker_menu_handler, pattern='^tracker_menu$')
            ],
            AWAITING_MAGNET: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_magnet), CallbackQueryHandler(menu_handler)],
            AWAITING_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_content), CallbackQueryHandler(handle_search_click)],
            # NUEVO ESTADO PARA ESCRIBIR EL NOMBRE DE LA SERIE
            AWAITING_NEW_SERIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, track_add_save), CallbackQueryHandler(tracker_menu_handler)],

            RENAMING: [CallbackQueryHandler(renaming_handler), MessageHandler(filters.TEXT & ~filters.COMMAND, renaming_handler)],
            MOVING_CATEGORY: [CallbackQueryHandler(move_and_plex)],
            PLEX_UPDATE: [CallbackQueryHandler(plex_trigger)]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(conv_handler)

    print("🤖 Bot Iniciado con Tracker...")
    application.run_polling()

def find_largest_file(directory):
    """Busca recursivamente el archivo más grande en una carpeta (el vídeo)."""
    largest_file = None
    max_size = 0

    # Recorremos todas las carpetas y subcarpetas
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # Obtenemos el tamaño
                size = os.path.getsize(file_path)
                # Si es más grande que el anterior y mayor a 50MB (para ignorar fotos o nfo)
                if size > max_size and size > 50 * 1024 * 1024:
                    max_size = size
                    largest_file = file_path
            except OSError:
                continue

    return largest_file
# ==========================================
# ⬇️ LÓGICA DE DESCARGA (MAGNET)
# ==========================================

async def process_magnet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # --- 1. DETECCIÓN DE ORIGEN (TEXTO vs BOTÓN) ---
    if update.callback_query:
        # Caso A: Vienes del botón "Descargar" del buscador
        await update.callback_query.answer()
        magnet_link = context.user_data.get('search_magnet')
        # Respondemos al mensaje donde estaba el botón
        status_msg = await update.callback_query.message.reply_text("⏳ **Recibido. Iniciando descarga...**", parse_mode='Markdown')
    else:
        # Caso B: Has pegado el enlace manualmente
        magnet_link = update.message.text
        status_msg = await update.message.reply_text("⏳ **Validando enlace y buscando Peers...**", parse_mode='Markdown')

    try:
        # Añadir descarga a Aria2
        download = aria2.add_magnet(magnet_link)

        prev_progress = -1

        # Bucle de progreso
        while not download.is_complete:
            download.update() # Actualizar estado

            if download.status == 'error':
                await status_msg.edit_text("❌ Error en la descarga. Verifica el magnet o seeds.")
                return MENU

            progress = download.progress
            speed = download.download_speed_string()

            if int(progress) != prev_progress and int(progress) % 10 == 0:
                bar = "▓" * (int(progress) // 10) + "░" * (10 - (int(progress) // 10))
                try:
                    await status_msg.edit_text(
                        f"📥 **Descargando...**\n"
                        f"Nombre: `{download.name}`\n"
                        f"[{bar}] {progress}%\n"
                        f"🚀 Velocidad: {speed} ⏳ Peers: {download.num_seeders}"
                    )
                except:
                    pass # Evitar error si Telegram se queja de editar muy rápido
                prev_progress = int(progress)

            await asyncio.sleep(2)

        # --- ZONA DE BÚSQUEDA FÍSICA (FIX DRIVER) ---
        await status_msg.edit_text("⏳ **Descarga completada.** Sincronizando Drive (esperando 5s)...")
        await asyncio.sleep(5)

        # Buscamos el archivo REAL en el disco (usando la función auxiliar que ya tienes)
        real_path = find_largest_file(BASE_DOWNLOAD_PATH)

        if not real_path:
            await status_msg.edit_text("⚠️ No encontré el archivo de video. ¿Puede que sea muy pequeño o Drive esté lento?")
            return MENU

        real_filename = os.path.basename(real_path)

        # Guardamos la ruta encontrada
        context.user_data['filename'] = real_filename
        context.user_data['filepath'] = real_path

        print(f"✅ Archivo encontrado físicamente en: {real_path}")

        await status_msg.edit_text(f"✅ **¡Descarga Finalizada!**\n\nArchivo: `{real_filename}`\nVerificando integridad...")
        await asyncio.sleep(1)

        return await post_download_menu(update, context)

    except Exception as e:
        print(f"Error crítico: {e}")
        try:
            await status_msg.edit_text(f"❌ Error crítico: {str(e)}")
        except:
            pass
        return MENU
# ==========================================
# 🔍 LÓGICA DE BÚSQUEDA (MOCK/SIMPLE)
# ==========================================

async def search_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    # Mensaje temporal
    status_msg = await update.message.reply_text(f"🔎 Buscando '{query}' en trackers...")

    results = []

    # --- MOTOR 1: NYAA.SI (Anime) ---
    try:
        url_nyaa = f"https://nyaa.si/?f=0&c=0_0&q={query}&s=seeders&o=desc"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url_nyaa, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.select('tr.default, tr.success')

            # Cogemos hasta 3 resultados
            for row in rows[:3]:
                cols = row.find_all('td')
                link_list = cols[1].find_all('a')
                title = link_list[-1].text.strip() if len(link_list) > 1 else link_list[0].text.strip()

                links = cols[2].find_all('a')
                magnet = next((l['href'] for l in links if l['href'].startswith('magnet:')), None)

                # Tamaño (útil para distinguir)
                size = cols[3].text.strip()

                if magnet:
                    results.append({'title': f"{title} ({size})", 'magnet': magnet, 'source': 'Nyaa'})
    except Exception as e:
        print(f"Error Nyaa: {e}")

    # --- MOTOR 2: YTS (Cine) - Solo si tenemos pocos resultados ---
    if len(results) < 3:
        try:
            res = requests.get(f"https://yts.mx/api/v2/list_movies.json?query_term={query}").json()
            if res['data']['movie_count'] > 0:
                # Rellenar hasta llegar a 3 o los que haya
                for movie in res['data']['movies'][:3-len(results)]:
                    title = movie['title_long']
                    magnet_hash = movie['torrents'][0]['hash']
                    final_magnet = f"magnet:?xt=urn:btih:{magnet_hash}&dn={title}&tr=udp://open.demonii.com:1337/announce"
                    results.append({'title': title, 'magnet': final_magnet, 'source': 'YTS'})
        except:
            pass

# --- MOTOR 3: The Pirate Bay (Ideal para contenido Español) ---
    if len(results) < 3:
        try:
            # Usamos la API libre sin bloqueos
            res_tpb = requests.get(f"https://apibay.org/q.php?q={query}").json()
            # Verificamos que la respuesta sea válida y no devuelva "0" (sin resultados)
            if res_tpb and res_tpb[0].get('id') != '0':
                # Solo cogemos los necesarios para llegar a 3 opciones
                for t in res_tpb[:3-len(results)]:
                    title = t['name']
                    magnet_hash = t['info_hash']
                    # Construimos el magnet link puro
                    final_magnet = f"magnet:?xt=urn:btih:{magnet_hash}&dn={title}"
                    results.append({'title': title, 'magnet': final_magnet})
        except:
            pass

    # --- ESCENARIO A: NO HAY RESULTADOS ---
    if not results:
        keyboard = [[InlineKeyboardButton("🔙 Volver al Menú", callback_data='back_to_main')]]

        await status_msg.edit_text(
            f"❌ **No encontré nada para '{query}'.**\n\n"
            "💡 *Consejo:* Prueba términos más cortos.\n"
            "Ej: 'Jujutsu S02' en vez de 'Jujutsu Kaisen Season 2 Episode 5'.\n\n"
            "👇 **Escribe otro nombre para probar de nuevo:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        # IMPORTANTE: Devolvemos AWAITING_SEARCH para que el bot siga escuchando
        return AWAITING_SEARCH

    # --- ESCENARIO B: HAY RESULTADOS (Mostramos lista) ---
    context.user_data['search_results'] = results # Guardamos la lista

    keyboard = []
    # Creamos un botón por cada resultado
    for i, res in enumerate(results):
        # Recortamos el título si es muy largo para el botón
        btn_text = (res['title'][:40] + '..') if len(res['title']) > 40 else res['title']
        keyboard.append([InlineKeyboardButton(f"⬇️ {btn_text}", callback_data=f'dl_index_{i}')])

    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='back_to_main')])

    await status_msg.edit_text(
        f"🎯 **He encontrado {len(results)} opciones:**\nSelecciona cual descargar:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return AWAITING_SEARCH

async def handle_search_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data.startswith('dl_index_'):
        # El usuario ha pulsado una de las opciones de la lista
        index = int(query.data.split('_')[-1]) # Sacamos el número (0, 1 o 2)

        # Recuperamos el magnet correcto de la lista guardada
        results = context.user_data.get('search_results', [])
        if 0 <= index < len(results):
            selected_magnet = results[index]['magnet']

            # Lo guardamos como "el elegido" para process_magnet
            context.user_data['search_magnet'] = selected_magnet

            # Llamamos a la función de descarga
            return await process_magnet(update, context)
        else:
            await query.answer("❌ Error al recuperar el enlace.")

    elif query.data == 'back_to_main':
        await query.answer()
        return await menu_handler(update, context)

# ==========================================
# 📂 POST-PROCESADO (RENOMBRAR Y PLEX)
# ==========================================

async def post_download_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filename = context.user_data.get('filename', 'desconocido')

    # --- CORRECCIÓN EXTENSIÓN DUPLICADA ---
    # 1. Separamos el nombre de la extensión ANTES de limpiar
    # Así "video.mkv" se convierte en "video" y ".mkv"
    name_base, file_ext = os.path.splitext(filename)

    # 2. Limpiamos SOLO la parte del nombre
    clean_name = re.sub(r'(\.|_)', ' ', name_base) # Quitar puntos y guiones bajos
    clean_name = re.sub(r'\[.*?\]', '', clean_name) # Quitar corchetes
    clean_name = re.sub(r'\(.*?\)', '', clean_name).strip() # Quitar parentesis

    # 3. Quitamos espacios dobles si han quedado
    clean_name = re.sub(r'\s+', ' ', clean_name)

    context.user_data['clean_name'] = clean_name
    # --------------------------------------

    msg = (
        f"📁 **Gestión de Archivo**\n\n"
        f"Original: `{filename}`\n"
        f"Sugerido para Plex: `{clean_name}`\n\n"
        "¿Cómo quieres nombrarlo?"
    )

    keyboard = [
        [InlineKeyboardButton(f"✅ Usar: {clean_name}", callback_data='use_suggested')],
        [InlineKeyboardButton("📝 Mantener Original", callback_data='keep_original')],
        [InlineKeyboardButton("⌨️ Escribir Manualmente", callback_data='manual_rename')]
    ]

    if update.message:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.callback_query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    return RENAMING

async def renaming_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query:
        await query.answer()
        choice = query.data

        # LÓGICA DE ORGANIZACIÓN INTELIGENTE
        if choice == 'use_suggested':
            final_name = context.user_data['clean_name']
            context.user_data['smart_organize'] = True # <--- Activamos el modo carpetas
        elif choice == 'keep_original':
            final_name = context.user_data['filename']
            context.user_data['smart_organize'] = False # <--- Modo normal
        elif choice == 'manual_rename':
            context.user_data['smart_organize'] = False # <--- Modo normal (usuario decide)
            await query.edit_message_text("⌨️ **Escribe el nuevo nombre del archivo** (sin extensión):")
            return RENAMING
    else:
        # Viene de escribir manualmente
        final_name = update.message.text
        context.user_data['smart_organize'] = False

    context.user_data['final_name'] = final_name

    # Preguntar Categoría
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

    # Recuperamos datos
    source_path = context.user_data.get('filepath')
    final_name_user = context.user_data.get('final_name')
    smart_organize = context.user_data.get('smart_organize', False)

    await query.edit_message_text(f"🚚 Procesando para `{target_folder}`...", parse_mode='Markdown')

    try:
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"No encuentro el archivo en: {source_path}")

        # Ruta base de destino (ej: /Plex_Confirmados/Anime)
        destination_dir = os.path.join(PLEX_FINAL_PATH, target_folder)

        # --- LÓGICA DE CREACIÓN DE CARPETAS (SOLO SI ES SUGERIDO Y ES SERIE/ANIME) ---
        if smart_organize and target_folder in ['Series', 'Anime']:
            # Intentamos detectar patrón Nombre - S01E01 o similar
            # Regex busca: (Nombre) seguido de S(numero)
            match = re.search(r'(.*?)(?:\s-|\s)?\sS(\d+)', final_name_user, re.IGNORECASE)

            if match:
                serie_name = match.group(1).strip() # Ej: Jujutsu Kaisen
                season_num = match.group(2)         # Ej: 02

                # Crear nombre de carpeta de temporada
                season_folder = f"Season {season_num}"

                # Actualizamos la ruta de destino añadiendo subcarpetas
                destination_dir = os.path.join(destination_dir, serie_name, season_folder)

                # Creamos las carpetas si no existen
                os.makedirs(destination_dir, exist_ok=True)
                print(f"📂 Estructura creada: {serie_name} / {season_folder}")

        # ---------------------------------------------------------------------------

        # Asegurar extensión y nombre final
        file_ext = os.path.splitext(source_path)[1]

        if not final_name_user.endswith(file_ext):
            final_name_complete = final_name_user + file_ext
        else:
            final_name_complete = final_name_user

        dest_path = os.path.join(destination_dir, final_name_complete)

        # MOVER
        shutil.move(source_path, dest_path)

        # Mensaje final
        path_display = dest_path.replace(PLEX_FINAL_PATH, "") # Para que el mensaje no sea gigante

        keyboard = [
            [InlineKeyboardButton("🔄 Sí, actualizar Plex", callback_data='plex_yes')],
            [InlineKeyboardButton("🏠 No, ir al Menú", callback_data='plex_no')]
        ]

        await query.message.reply_text(
            f"✅ **Organizado y Movido**\n\nRuta: `{path_display}`\n\n¿Quieres actualizar la biblioteca de Plex?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return PLEX_UPDATE

    except Exception as e:
        print(f"Error: {e}")
        await query.message.reply_text(f"❌ Error moviendo archivo: {str(e)}")
        return MENU

async def plex_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'plex_yes':
        await query.message.reply_text("📡 Enviando señal a Plex...")
        try:
            # URL para refrescar todas las librerías
            url = f"{PLEX_URL}/library/sections/all/refresh?X-Plex-Token={PLEX_TOKEN}"
            requests.get(url, timeout=5)
            await query.message.reply_text("✅ Señal enviada. Plex debería estar actualizando.")
        except Exception as e:
            await query.message.reply_text(f"⚠️ No pude contactar con Plex (¿Estás en Colab y Plex en local?): {e}")

    await query.message.reply_text("🏠 Volviendo al menú principal...", reply_markup=get_keyboard("main"))
    return MENU

# ==========================================
# 🏁 MAIN
# ==========================================

def main():
    # Iniciar sistema
    init_system()

    # Configurar Bot con JOB QUEUE (Para tareas automáticas)
    application = Application.builder().token(TOKEN).build()

    # --- TAREA AUTOMÁTICA ---
    # Revisará series cada 30 minutos (1800 segundos)
    # Empezará a los 10 segundos de encender el bot
    job_queue = application.job_queue
    job_queue.run_repeating(check_series_updates, interval=1800, first=10)

    # Conversación Principal
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [
                # Menú principal y submenús
                CallbackQueryHandler(menu_handler, pattern='^(magnet|search|space|tracker|help|back_to_main|restart_pc)$'),
                # Botones del Tracker
                CallbackQueryHandler(manual_check, pattern='^track_check_now$'),
                CallbackQueryHandler(track_add_start, pattern='^track_add$'),
                CallbackQueryHandler(track_delete, pattern='^track_del$'),
                CallbackQueryHandler(handle_tracked_download, pattern='^dl_track_'), # Clic en descarga automática
                CallbackQueryHandler(track_delete_confirm, pattern='^del_serie_'),
                CallbackQueryHandler(tracker_menu_handler, pattern='^tracker_menu$')
            ],
            AWAITING_MAGNET: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_magnet), CallbackQueryHandler(menu_handler)],
            AWAITING_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_content), CallbackQueryHandler(handle_search_click)],

            # ESTADO NUEVO: Escribir nombre de serie
            AWAITING_NEW_SERIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, track_add_save), CallbackQueryHandler(tracker_menu_handler)],

            RENAMING: [CallbackQueryHandler(renaming_handler), MessageHandler(filters.TEXT & ~filters.COMMAND, renaming_handler)],
            MOVING_CATEGORY: [CallbackQueryHandler(move_and_plex)],
            PLEX_UPDATE: [CallbackQueryHandler(plex_trigger)]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(conv_handler)

    # Correr Bot
    print("🤖 Bot Iniciado en Telegram con Sistema de Rastreo...")
    application.run_polling()

if __name__ == '__main__':
    main()