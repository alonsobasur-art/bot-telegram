@echo off
cd /d "C:\Users\JUEGOS\Desktop\MiBot"
title MiBot Telegram
py bot.py
if /i not "%SESSIONNAME%"=="Console" pause