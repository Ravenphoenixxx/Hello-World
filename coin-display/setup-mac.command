#!/bin/bash
# One-time setup on macOS. Double-click this file (or run: bash setup-mac.command).
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null; then
  echo "Python 3 was not found. Install it from https://www.python.org/downloads/ and run this again."
  read -r -p "Press Return to close."; exit 1
fi
python3 -m venv .venv && .venv/bin/python -m pip install --upgrade pip && .venv/bin/python -m pip install -r requirements.txt
if [ $? -ne 0 ]; then echo "Setup failed."; read -r -p "Press Return to close."; exit 1; fi
echo
echo "Setup finished. Double-click start-mac.command to run the display."
echo "The first time, macOS may ask whether Python can accept incoming connections: choose Allow"
echo "so phones on your network can reach the admin page."
read -r -p "Press Return to close."
