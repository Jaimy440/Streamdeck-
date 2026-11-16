@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (
  echo Bitte zuerst einmal start.bat ausfuehren.
  pause
  exit /b 1
)
echo Installiere Stimmfilter (PyTorch ist gross, das dauert ein paar Minuten) ...
.venv\Scripts\python -m pip install -r requirements-filter.txt
.venv\Scripts\python -m pip install --no-deps resemblyzer
echo.
echo Fertig! Jetzt noch VB-Audio Virtual Cable installieren: https://vb-audio.com/Cable/
pause
