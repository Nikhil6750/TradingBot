@echo off
setlocal
set "WORKDIR=D:\Trading Bot"
set "LOGDIR=%WORKDIR%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

rem YYYYMMDD_HHMMSS compact timestamp
set "ds=%date:~-4%%date:~4,2%%date:~7,2%"
set "ts=%time:~0,2%%time:~3,2%%time:~6,2%"
set "ts=%ts: =0%"

rem Run PowerShell script and append all output to a timestamped log
powershell -NoProfile -ExecutionPolicy Bypass -File "%WORKDIR%\run_all.ps1" >> "%LOGDIR%\run_%ds%_%ts%.log" 2>>&1
endlocal
