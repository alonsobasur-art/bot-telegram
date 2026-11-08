"""Pide al proceso de bot.py que se reinicie a sí mismo (seguro para Telegram)."""

from pathlib import Path

MARCA = Path(__file__).resolve().parent / "restart_bot.request"
MARCA.write_text("", encoding="utf-8")
print("Reinicio del bot solicitado. Debería recargarse en unos segundos.")
