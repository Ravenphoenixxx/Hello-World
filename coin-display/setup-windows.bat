@echo off
rem One-time setup on Windows. Needs Python 3.10+ from python.org ("Add to PATH" ticked).
cd /d "%~dp0"
py -3 -m venv .venv || python -m venv .venv
if errorlevel 1 ( echo Python was not found. Install it from https://www.python.org/downloads/ & pause & exit /b 1 )
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 ( echo Installing packages failed. & pause & exit /b 1 )
rem Let phones on the home network reach the admin page.
netsh advfirewall firewall add rule name="Coin Display" dir=in action=allow protocol=TCP localport=8080 >nul 2>&1
echo.
echo Setup finished. Double-click start-windows.bat to run the display.
echo To start it automatically: press Win+R, type shell:startup, and put a shortcut to start-windows.bat there.
pause
