@echo off
setlocal

:: Kill any old ngrok or uvicorn/python processes
taskkill /IM ngrok.exe /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1

:: === EDIT THESE 3 VALUES ONCE ===
set TELEGRAM_BOT_TOKEN=8342134407:AAEya-u1F7pqF4MxyTWDbUjKbUo-IiS-eEo
set TELEGRAM_CHAT_ID=1298859545
set TV_SHARED_SECRET=some_strong_secret
:: ================================

set TELEGRAM_DRY_RUN=0
set DRY_RUN=1

set APPDIR=D:\Trading Bot
set PYTHON_EXE=%APPDIR%\venv\Scripts\python.exe
set NGROK_EXE=C:\Users\nikhi\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe

:: Start uvicorn (server) in new window
start "Samantha API" cmd /c "cd /d %APPDIR% && %PYTHON_EXE% -m uvicorn server:app --host 0.0.0.0 --port 8000"

:: Wait a few seconds so server is up
timeout /t 5 >nul

:: Start ngrok tunnel in another window
start "ngrok tunnel" cmd /k "%NGROK_EXE% http http://localhost:8000"

endlocal
