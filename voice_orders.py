"""Transcripción de audio (castellano), borradores y pulido de texto para órdenes por voz."""

import json
import os
import re
import threading
from datetime import datetime, timezone

import speech_recognition as sr
from pydub import AudioSegment
from pydub.effects import normalize

BOT_DIR = os.path.dirname(os.path.abspath(__file__))
DRAFTS_FILE = os.path.join(BOT_DIR, "voice_orders.json")
MODELO_WHISPER = os.environ.get("VOICE_WHISPER_MODEL", "small").strip() or "small"

_modelo = None
_modelo_lock = threading.Lock()


def _cargar_json():
    try:
        with open(DRAFTS_FILE, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if isinstance(datos, dict):
            return datos
    except (OSError, json.JSONDecodeError):
        pass
    return {"last_by_user": {}, "history": []}


def _guardar_json(datos):
    os.makedirs(BOT_DIR, exist_ok=True)
    with open(DRAFTS_FILE, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)


def guardar_borrador(user_id, texto, origen="voz", motor=""):
    datos = _cargar_json()
    entrada = {
        "text": (texto or "").strip(),
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": origen,
        "engine": motor,
    }
    datos["last_by_user"][str(user_id)] = entrada
    historial = datos.get("history") or []
    historial.append({"user_id": user_id, **entrada})
    datos["history"] = historial[-40:]
    _guardar_json(datos)
    return entrada


def leer_borrador(user_id):
    datos = _cargar_json()
    return datos.get("last_by_user", {}).get(str(user_id))


def preparar_wav(ruta_entrada, ruta_wav):
    audio = AudioSegment.from_file(ruta_entrada)
    audio = audio.set_channels(1).set_frame_rate(16000)
    try:
        audio = normalize(audio)
    except Exception:
        pass
    audio.export(ruta_wav, format="wav")
    return ruta_wav


def _modelo_whisper():
    global _modelo
    if _modelo is not None:
        return _modelo
    with _modelo_lock:
        if _modelo is not None:
            return _modelo
        from faster_whisper import WhisperModel

        dispositivo = os.environ.get("VOICE_WHISPER_DEVICE", "cpu").strip() or "cpu"
        tipo = os.environ.get("VOICE_WHISPER_COMPUTE", "int8").strip() or "int8"
        _modelo = WhisperModel(MODELO_WHISPER, device=dispositivo, compute_type=tipo)
        return _modelo


def _transcribir_whisper(ruta_wav):
    modelo = _modelo_whisper()
    segmentos, _info = modelo.transcribe(
        ruta_wav,
        language="es",
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    partes = [s.text.strip() for s in segmentos if s.text and s.text.strip()]
    return " ".join(partes).strip()


def _transcribir_google(ruta_wav):
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    with sr.AudioFile(ruta_wav) as fuente:
        recognizer.adjust_for_ambient_noise(fuente, duration=0.25)
        muestra = recognizer.record(fuente)
    return recognizer.recognize_google(muestra, language="es-ES")


def transcribir_archivo(ruta_wav):
    motor = "whisper"
    try:
        texto = _transcribir_whisper(ruta_wav)
        if texto:
            return texto, motor
    except Exception:
        motor = "google"
    texto = _transcribir_google(ruta_wav)
    return texto, motor


def pulir_castellano(texto):
    limpio = re.sub(r"\s+", " ", (texto or "").strip())
    if not limpio:
        return ""
    limpio = limpio[0].upper() + limpio[1:]
    if limpio[-1] not in ".!?…":
        limpio += "."
    sustituciones = {
        r"\bpar sec\b": "Parsec",
        r"\bparsik\b": "Parsec",
        r"\bcurso\b(?=\s+(agente|en))": "Cursor",
        r"\bcurzor\b": "Cursor",
    }
    for patron, reemplazo in sustituciones.items():
        limpio = re.sub(patron, reemplazo, limpio, flags=re.IGNORECASE)
    return limpio
