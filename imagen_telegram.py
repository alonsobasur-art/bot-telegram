"""Mismo generador de imágenes que el panel, llamado desde Telegram."""

import asyncio
import time
import uuid
from pathlib import Path
import sys

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

PANEL = Path(r"C:\Servicios\Panel Bots")
if str(PANEL) not in sys.path:
    sys.path.insert(0, str(PANEL))

from imagen.servicio import (  # noqa: E402
    TAMANOS,
    Cancelado,
    ErrorImagen,
    TextoRechazado,
    estimar_segundos,
    motor,
)

REFS = PANEL / "imagen" / "salida" / ".refs"
TAMANO_NOMBRE = {
    "rapida": "Rápida",
    "retrato": "Retrato",
    "cuadrada": "Cuadrada",
    "paisaje": "Paisaje",
}
PASOS_NOMBRE = {16: "Rápido", 20: "Normal", 28: "Fino"}


def asegurar_opciones(datos):
    datos.setdefault("img_tam", "retrato")
    datos.setdefault("img_pasos", 20)
    datos.setdefault("img_nsfw", False)
    datos.setdefault("img_seed", -1)
    datos.setdefault("img_usar_estilo", False)
    if datos["img_tam"] not in TAMANOS:
        datos["img_tam"] = "retrato"
    if datos["img_pasos"] not in PASOS_NOMBRE:
        datos["img_pasos"] = 20
    try:
        datos["img_seed"] = int(datos["img_seed"])
    except (TypeError, ValueError):
        datos["img_seed"] = -1
    return datos


def _marca(activo, texto):
    return f"● {texto}" if activo else texto


def texto_opciones(datos):
    datos = asegurar_opciones(datos)
    ancho, alto = TAMANOS[datos["img_tam"]]
    segundos = max(1, int(round(estimar_segundos(ancho, alto, datos["img_pasos"]))))
    semilla = "aleatoria" if datos["img_seed"] < 0 else str(datos["img_seed"])
    estilo = "sí" if datos.get("img_usar_estilo") and datos.get("img_ref_temp") else "no"
    return (
        "🖼️ **Imagen**\n\n"
        "Pulsa **Escribir** y dime qué quieres ver. Te mando la foto a este chat.\n\n"
        f"Tamaño: **{TAMANO_NOMBRE[datos['img_tam']]}** ({ancho}×{alto})\n"
        f"Detalle: **{PASOS_NOMBRE[datos['img_pasos']]}**\n"
        f"NSFW: **{'sí' if datos['img_nsfw'] else 'no'}**\n"
        f"Semilla: **{semilla}**\n"
        f"Copiar estilo: **{estilo}**\n"
        f"En este PC, unos {segundos} s."
    )


def teclado_imagen(datos):
    datos = asegurar_opciones(datos)
    tamano = datos["img_tam"]
    pasos = datos["img_pasos"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Escribir", callback_data="img_prompt")],
        [
            InlineKeyboardButton(_marca(tamano == "rapida", "Rápida"), callback_data="img_tam_rapida"),
            InlineKeyboardButton(_marca(tamano == "retrato", "Retrato"), callback_data="img_tam_retrato"),
        ],
        [
            InlineKeyboardButton(_marca(tamano == "cuadrada", "Cuadrada"), callback_data="img_tam_cuadrada"),
            InlineKeyboardButton(_marca(tamano == "paisaje", "Paisaje"), callback_data="img_tam_paisaje"),
        ],
        [
            InlineKeyboardButton(_marca(pasos == 16, "Rápido"), callback_data="img_pasos_16"),
            InlineKeyboardButton(_marca(pasos == 20, "Normal"), callback_data="img_pasos_20"),
            InlineKeyboardButton(_marca(pasos == 28, "Fino"), callback_data="img_pasos_28"),
        ],
        [
            InlineKeyboardButton(_marca(datos["img_nsfw"], "NSFW"), callback_data="img_nsfw"),
            InlineKeyboardButton("Semilla", callback_data="img_semilla"),
        ],
        [InlineKeyboardButton(_marca(datos.get("img_usar_estilo"), "Copiar estilo"), callback_data="img_estilo")],
        [InlineKeyboardButton("🔙 Inicio", callback_data="back_to_main")],
    ])


def teclado_post_envio(archivo_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑 Borrar del PC", callback_data=f"img_del_{archivo_id}"),
        InlineKeyboardButton("💾 Dejarla", callback_data=f"img_keep_{archivo_id}"),
    ]])


def cancelar_generacion():
    motor.cancelar()


def limpiar_referencia(datos):
    ruta = datos.pop("img_ref_temp", None)
    datos["img_usar_estilo"] = False
    if ruta:
        try:
            Path(ruta).unlink(missing_ok=True)
        except OSError:
            pass


def registrar_archivo(application, ruta):
    registro = application.bot_data.setdefault("img_archivos", {})
    clave = uuid.uuid4().hex[:10]
    registro[clave] = str(ruta)
    return clave


def borrar_archivo_registrado(application, clave):
    registro = application.bot_data.get("img_archivos") or {}
    ruta = registro.pop(clave, None)
    if not ruta:
        return False, "No encuentro esa imagen."
    archivo = Path(ruta)
    if not archivo.is_file():
        return False, "El archivo ya no estaba."
    try:
        archivo.unlink()
    except OSError as error:
        return False, f"No pude borrarla: {error}"
    return True, "Imagen borrada del PC."


async def guardar_foto_temporal(bot, archivo):
    REFS.mkdir(parents=True, exist_ok=True)
    destino = REFS / f"ref-{time.time_ns()}.jpg"
    telegram = await bot.get_file(archivo.file_id)
    await telegram.download_to_drive(custom_path=str(destino))
    return str(destino)


async def generar_y_enviar(loop, chat_id, status_id, user_data, prompt, bot):
    datos = asegurar_opciones(user_data)
    ancho, alto = TAMANOS[datos["img_tam"]]
    pasos = datos["img_pasos"]
    nsfw = bool(datos["img_nsfw"])
    semilla = datos["img_seed"]
    referencia = datos.get("img_ref_temp") if datos.get("img_usar_estilo") else None
    if referencia and not Path(referencia).is_file():
        referencia = None
    ultimo = {"cuando": 0.0}

    def progreso(fase, fraccion, segundos):
        ahora = time.monotonic()
        if ahora - ultimo["cuando"] < 4 and fraccion < 0.9:
            return
        ultimo["cuando"] = ahora

        async def pintar():
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_id,
                    text=f"{fase}… {int(segundos)} s",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("⏹ Cancelar", callback_data="img_abort")]]
                    ),
                )
            except Exception:
                pass

        asyncio.run_coroutine_threadsafe(pintar(), loop)

    try:
        resultado = await asyncio.to_thread(
            motor.generar,
            prompt,
            ancho,
            alto,
            pasos,
            semilla,
            progreso,
            nsfw,
            init_img=referencia,
            fuerza_estilo=0.7,
            usar_estilo_ref=bool(referencia),
        )
    except Cancelado:
        return {"ok": False, "error": "Cancelado."}
    except (TextoRechazado, ErrorImagen) as error:
        return {"ok": False, "error": str(error)}
    except Exception:
        return {"ok": False, "error": "No se pudo generar la imagen."}
    return {"ok": True, "resultado": resultado}
