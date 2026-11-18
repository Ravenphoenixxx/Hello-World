#!/usr/bin/env bash
# Sets up the coin display as a kiosk on Raspberry Pi OS / Debian / Ubuntu (desktop edition).
# Run as the normal desktop user (not root):  bash install.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${COIN_PORT:-8080}"

sudo apt-get update
sudo apt-get install -y python3-venv python3-pip
if ! command -v chromium >/dev/null && ! command -v chromium-browser >/dev/null; then
  sudo apt-get install -y chromium || sudo apt-get install -y chromium-browser
fi
BROWSER="$(command -v chromium || command -v chromium-browser)"

python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install --upgrade pip
"$DIR/.venv/bin/pip" install -r "$DIR/requirements.txt"

# Server: starts at boot, restarts if it ever stops.
sudo tee /etc/systemd/system/coin-display.service >/dev/null <<UNIT
[Unit]
Description=Challenge coin display server
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=$DIR
Environment=COIN_PORT=$PORT
ExecStart=$DIR/.venv/bin/python $DIR/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now coin-display.service

# Kiosk: full-screen browser when the desktop session starts.
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/coin-display.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Coin Display
Exec=sh -c 'sleep 6; exec $BROWSER --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble --disable-pinch --overscroll-history-navigation=0 --check-for-update-interval=31536000 --user-data-dir=$HOME/.coin-display-browser http://localhost:$PORT/'
X-GNOME-Autostart-enabled=true
DESK

IP="$(hostname -I | awk '{print $1}')"
echo
echo "Done. Reboot to start the display in kiosk mode."
echo "Add coins from a phone or PC at:  http://$IP:$PORT/admin"
echo "Tip: turn off screen blanking (on a Pi: raspi-config > Display Options > Screen Blanking)."
