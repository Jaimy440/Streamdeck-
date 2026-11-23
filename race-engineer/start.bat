@echo off
chcp 65001 >nul
cd /d "%~dp0"
title LMU Race Engineer
if not exist .venv (
  echo Erste Einrichtung - installiere Pakete ...
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements.txt
)
.venv\Scripts\python main.py %*
pause
