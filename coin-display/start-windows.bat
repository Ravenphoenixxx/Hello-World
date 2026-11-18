@echo off
rem Starts the server (minimised) and opens the display full-screen in Microsoft Edge.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe ( echo Run setup-windows.bat first. & pause & exit /b 1 )
start "Coin Display Server" /min .venv\Scripts\python app.py
timeout /t 4 /nobreak >nul
start "" msedge --kiosk http://localhost:8080/ --edge-kiosk-type=fullscreen --no-first-run --user-data-dir="%~dp0.browser"
