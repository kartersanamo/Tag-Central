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
MACOS_BIN="$APP_PATH/Contents/MacOS/Tag Center"
if [[ ! -d "$APP_PATH" ]]; then
  echo "ERROR: Expected $APP_PATH"
  exit 1
fi

echo "==> Ensuring launcher is executable"
chmod +x "$MACOS_BIN"

echo "==> Ad-hoc code signing (local + informal sharing)"
# Does not replace Apple notarization for wide public distribution, but avoids
# some "damaged" errors and is required before zipping for other Macs.
codesign --force --deep --sign - "$APP_PATH"

ZIP_PATH="dist/Tag-Center-macOS.zip"
echo "==> Creating release zip (use this for GitHub — preserves .app structure)"
rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"

echo ""
echo "Build complete:"
echo "  App:  $ROOT/$APP_PATH"
echo "  Zip:  $ROOT/$ZIP_PATH  (upload this to GitHub Releases)"
echo ""
echo "Open locally: open \"$APP_PATH\""
echo "User data:    ~/Library/Application Support/TagCenter/"
echo "Exports:      ~/Library/Application Support/Tag Center Exports/"
echo ""
echo "Downloaders on other Macs must allow the unsigned app once:"
echo "  Right-click the .app → Open → Open"
echo "  Or: xattr -dr com.apple.quarantine \"/path/to/Tag Center.app\""
echo "See README.md → Distributing on macOS for details."
