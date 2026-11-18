#!/bin/bash
# Starts the server and opens the display full-screen. Close this window (or press Ctrl+C) to stop.
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then echo "Run setup-mac.command first."; read -r -p "Press Return to close."; exit 1; fi
URL="http://localhost:${COIN_PORT:-8080}/"
(
  sleep 4
  if [ -d "/Applications/Google Chrome.app" ]; then
    open -na "Google Chrome" --args --kiosk --no-first-run --user-data-dir="$PWD/.browser" "$URL"
  else
    open "$URL"   # default browser; press Ctrl+Cmd+F for full screen
  fi
) &
# caffeinate keeps the screen from sleeping while the display runs
exec caffeinate -d .venv/bin/python app.py
