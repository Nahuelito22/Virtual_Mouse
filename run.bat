@echo off
setlocal
cd /d "%~dp0"

if exist "Release\AI_Virtual_Mouse.exe" (
    start "" "Release\AI_Virtual_Mouse.exe" %*
    exit /b 0
)

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" virtual_mouse.py %*
    exit /b %ERRORLEVEL%
)

python virtual_mouse.py %*
exit /b %ERRORLEVEL%
