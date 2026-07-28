@echo off
setlocal
cd /d "%~dp0"

REM Ejemplos:
REM   run.bat
REM   run.bat --list-cameras
REM   run.bat --pick-camera
REM   run.bat -c 1

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" virtual_mouse.py %*
    exit /b %ERRORLEVEL%
)

if exist "Release\AI_Virtual_Mouse.exe" (
    "Release\AI_Virtual_Mouse.exe" %*
    exit /b %ERRORLEVEL%
)

python virtual_mouse.py %*
exit /b %ERRORLEVEL%
