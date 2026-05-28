#!/usr/bin/env bash
# Build Tag Center for macOS (.app bundle in dist/).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "==> Tag Center — macOS build"
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

echo "==> Generating icons (.png, .ico, .icns)"
python scripts/generate_icons.py

if [[ ! -f assets/icon.icns ]]; then
  echo "ERROR: assets/icon.icns was not created. Run on macOS with iconutil available."
  exit 1
fi

echo "==> Running PyInstaller"
pyinstaller --noconfirm --clean scripts/tag_central.spec

APP_PATH="dist/Tag Center.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "ERROR: Expected $APP_PATH"
  exit 1
fi

echo ""
echo "Build complete:"
echo "  $ROOT/$APP_PATH"
echo ""
echo "Open with: open \"$APP_PATH\""
echo "User data (when running the .app): ~/Library/Application Support/TagCenter/"
