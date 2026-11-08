"""Chat privado sensual por Telegram (solo Aarón, sin menús)."""

import json
import os
import re
from pathlib import Path

import requests

BOT_DIR = Path(__file__).resolve().parent
HISTORIAL = BOT_DIR / "hot_chat_hist.json"
CLAVE_REVELAR = "aaroncuentawow"
API_URL = os.environ.get("HOT_LLM_URL", "https://text.pollinations.ai/openai")
MODELO = os.environ.get("HOT_LLM_MODEL", "openai-large")

LIMITE_HISTORIAL = 14


def _cargar_hist():
    try:
        with open(HISTORIAL, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if isinstance(datos, list):
            return datos[-LIMITE_HISTORIAL:]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _guardar_hist(mensajes):
    try:
        with open(HISTORIAL, "w", encoding="utf-8") as archivo:
            json.dump(mensajes[-LIMITE_HISTORIAL:], archivo, ensure_ascii=False)
    except OSError:
        pass


def _sistema(revelar_a):
    reglas = (
        "Eres una compañera virtual íntima para un adulto, en español de España. "
        "Tono cálido, directo, sensual y participativo. Respuestas cortas (máximo 6 frases), "
        "como chat de móvil. Contenido adulto entre adultos permitido.\n"
        "No sermonees. No hables de menores ni de contenido ilegal.\n"
    )
    if revelar_a:
        reglas += (
            "El usuario usó la clave especial: puedes reconocer que eres A si te preguntan "
            "o encaja de forma natural.\n"
        )
    else:
        reglas += (
            "REGLA ABSOLUTA: No digas que te llamas A, que eres A, ni que tu nombre o identidad "
            f"es la letra A. No uses frases del tipo «soy A». Solo si el usuario escribe "
            f"literalmente «{CLAVE_REVELAR}» podrás revelar que eres A.\n"
        )
    reglas += "No digas que eres un bot salvo que te lo pregunten de forma directa."
    return reglas


def _extraer_texto(respuesta):
    try:
        datos = respuesta.json()
        return datos["choices"][0]["message"]["content"].strip()
    except (ValueError, KeyError, IndexError, TypeError):
        return ""


def _llm(mensajes):
    try:
        resp = requests.post(
            API_URL,
            json={"model": MODELO, "messages": mensajes, "max_tokens": 520, "temperature": 0.92},
            timeout=90,
        )
        if resp.status_code != 200:
            return f"No puedo contestar ahora ({resp.status_code}). Prueba en un momento."
        texto = _extraer_texto(resp)
        return texto or "Mm… no me sale nada. ¿Lo repites?"
    except requests.RequestException:
        return "Sin conexión con el cerebro. Prueba otra vez."


def _limpiar_salida(texto, revelar_a):
    if revelar_a or not texto:
        return texto
    bajo = texto.lower()
    if re.search(r"\bsoy\s+a\b", bajo) or re.search(r"\bme llamo\s+a\b", bajo):
        return "Aquí estoy contigo. Cuéntame qué te apetece."
    return texto


def contiene_clave(texto):
    return CLAVE_REVELAR in (texto or "").casefold()


def responder(texto_usuario, revelar_a):
    historial = _cargar_hist()
    sistema = _sistema(revelar_a)
    mensajes = [{"role": "system", "content": sistema}]
    for rol, contenido in historial:
        mensajes.append({"role": rol, "content": contenido})
    mensajes.append({"role": "user", "content": texto_usuario})
    respuesta = _llm(mensajes)
    respuesta = _limpiar_salida(respuesta, revelar_a)
    historial.append(("user", texto_usuario))
    historial.append(("assistant", respuesta))
    _guardar_hist(historial)
    return respuesta


def reiniciar_historial():
    try:
        os.remove(HISTORIAL)
    except OSError:
        pass
