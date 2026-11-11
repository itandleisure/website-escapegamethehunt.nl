@echo off
rem Opent het invulscherm voor het fotoboekje in de browser. Sluit dit venster om te stoppen.
cd /d "%~dp0"
python boekje_tool.py
if errorlevel 1 pause
