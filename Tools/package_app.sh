#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="Harmony.app"
BUILD_DIR="${1:-/tmp/HarmonyAppBuild}"
APP_DIR="$BUILD_DIR/$APP_NAME"
RESOURCES_DIR="$APP_DIR/Contents/Resources"
MACOS_DIR="$APP_DIR/Contents/MacOS"
ICONSET_DIR="$BUILD_DIR/Harmony.iconset"

rm -rf "$APP_DIR"
rm -rf "$ICONSET_DIR"
mkdir -p "$RESOURCES_DIR" "$MACOS_DIR"

cp "$ROOT_DIR"/main.py "$RESOURCES_DIR"/
cp "$ROOT_DIR"/main_window.py "$RESOURCES_DIR"/
cp "$ROOT_DIR"/audio_engine.py "$RESOURCES_DIR"/
cp "$ROOT_DIR"/database.py "$RESOURCES_DIR"/
cp "$ROOT_DIR"/metadata.py "$RESOURCES_DIR"/
cp "$ROOT_DIR"/playback_rules.py "$RESOURCES_DIR"/
cp "$ROOT_DIR"/themes.py "$RESOURCES_DIR"/
cp "$ROOT_DIR"/requirements.txt "$RESOURCES_DIR"/

if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  echo "Missing $ROOT_DIR/.venv. Create the project virtual environment first." >&2
  exit 1
fi

cp -R "$ROOT_DIR/.venv" "$RESOURCES_DIR/.venv"

"$ROOT_DIR/.venv/bin/python3" "$ROOT_DIR/Tools/generate_app_icon.py" "$ICONSET_DIR"
iconutil -c icns "$ICONSET_DIR" -o "$RESOURCES_DIR/Harmony.icns"

cat > "$MACOS_DIR/Harmony" <<'EOF'
#!/bin/zsh
set -euo pipefail
DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
export LC_ALL=C
cd "$DIR"
exec "$DIR/.venv/bin/python3" "$DIR/main_window.py"
EOF
chmod +x "$MACOS_DIR/Harmony"

cat > "$APP_DIR/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Harmony</string>
    <key>CFBundleDisplayName</key>
    <string>Harmony</string>
    <key>CFBundleIdentifier</key>
    <string>com.harmony.musicplayer</string>
    <key>CFBundleVersion</key>
    <string>1.0.1</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.1</string>
    <key>CFBundleIconFile</key>
    <string>Harmony</string>
    <key>CFBundleExecutable</key>
    <string>Harmony</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

echo "$APP_DIR"
