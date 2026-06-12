#!/usr/bin/env bash
# Build Tag Central for macOS (.app bundle in dist/).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "==> Tag Central — macOS build"
echo "    Project: $ROOT"

PYTHON="${PYTHON:-python3}"
if [[ ! -d .venv ]]; then
  echo "==> Creating virtual environment"
  "$PYTHON" -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate

echo "==> Installing build dependencies"
pip install -q --upgrade pip
pip install -q -r requirements-build.txt

echo "==> Generating icons"
python scripts/generate_icons.py

if [[ ! -f assets/icon.icns ]]; then
  echo "ERROR: assets/icon.icns was not created. Run on macOS with iconutil available."
  exit 1
fi

echo "==> Running PyInstaller"
pyinstaller --noconfirm --clean scripts/tag_central.spec

APP_PATH="dist/Tag Central.app"
MACOS_BIN="$APP_PATH/Contents/MacOS/Tag Central"
if [[ ! -d "$APP_PATH" ]]; then
  echo "ERROR: Expected $APP_PATH"
  exit 1
fi

chmod +x "$MACOS_BIN"
codesign --force --deep --sign - "$APP_PATH"

ZIP_PATH="dist/Tag-Central-macOS.zip"
rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"

echo ""
echo "Build complete:"
echo "  App:  $ROOT/$APP_PATH"
echo "  Zip:  $ROOT/$ZIP_PATH"
echo ""
echo "User data: ~/Library/Application Support/TagCentral/"
echo "Exports:   <folder containing .app>/Exports/"
