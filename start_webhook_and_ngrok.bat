@echo off
setlocal

:: ====== EDIT THESE 4 VALUES ONCE ======
set TELEGRAM_BOT_TOKEN=8342134407:AAEya-u1F7pqF4MxyTWDbUjKbUo-IiS-eEo
set TELEGRAM_CHAT_ID=1298859545        :: e.g. 123456789 (DM) or -100xxxxxxxxxxxx (channel/supergroup)
set TV_SHARED_SECRET=some_strong_secret          :: must match your Pine 'secret'
set PYTHON_EXE=D:\Trading Bot\venv\Scripts\python.exe
:: ======================================

:: optional: keep sends ON, trading logic DRY
set TELEGRAM_DRY_RUN=0
set DRY_RUN=1

set APPDIR=D:\Trading Bot
set NGROK_EXE=C:\Users\nikhi\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe

:: 1) start uvicorn (server.py) in a new window
start "Samantha API" cmd /c "cd /d %APPDIR% && "%PYTHON_EXE%" -m uvicorn server:app --host 0.0.0.0 --port 8000"

:: 2) small delay so server is up
timeout /t 3 >nul

:: 3) start ngrok in another window (keeps URL visible)
start "ngrok tunnel" cmd /k ""%NGROK_EXE%" http http://localhost:8000"

endlocal
