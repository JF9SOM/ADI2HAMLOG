#!/bin/sh
# Build a standalone GUI app with PyInstaller (run on the target OS: macOS -> .app, Windows -> .exe).
# Run from the repository root inside a venv with:  pip install -e ".[gui]" pyinstaller
set -e
pyinstaller --noconfirm --windowed --name adi2hamlog \
  --paths src \
  --add-data "src/adi2hamlog/data:adi2hamlog/data" \
  packaging/gui_launcher.py
