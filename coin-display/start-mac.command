#!/bin/bash
# Starts the server and opens the display full-screen. Close this window (or press Ctrl+C) to stop.
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then echo "Run setup-mac.command first."; read -r -p "Press Return to close."; exit 1; fi
URL="http://localhost:${COIN_PORT:-8080}/"
(
  # wait until the server answers (up to 30 seconds), then open the browser window
  for _ in $(seq 1 60); do curl -s -o /dev/null "${URL}api/version" && break; sleep 0.5; done
  if [ ! -d "/Applications/Google Chrome.app" ] ||
     ! open -na "Google Chrome" --args --kiosk --no-first-run --user-data-dir="$PWD/.browser" "$URL"; then
    open "$URL"   # default browser; press Ctrl+Cmd+F for full screen
  fi
) &
echo "Display: $URL   (if no window opens, type that address into a browser)"
# caffeinate keeps the screen from sleeping while the display runs
exec caffeinate -d .venv/bin/python app.py
