#!/bin/zsh
set -e

SOURCE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Library/Application Support/SoundSwipeAbletonBridge"
LABEL="com.soundswipe.abletonbridge"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$DEST/data" "$HOME/Library/LaunchAgents"
cp "$SOURCE/index.html" "$DEST/index.html"
cp "$SOURCE/manifest.json" "$DEST/manifest.json"
cp "$SOURCE/manifest.webmanifest" "$DEST/manifest.webmanifest"
cp "$SOURCE/sw.js" "$DEST/sw.js"
cp "$SOURCE/ableton_bridge.py" "$DEST/ableton_bridge.py"
cp "$SOURCE/data/ableton_core_library_catalog.json" "$DEST/data/ableton_core_library_catalog.json"
chmod 755 "$DEST/ableton_bridge.py"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$DEST/ableton_bridge.py</string>
    <string>--port</string><string>8877</string>
    <string>--no-open</string>
  </array>
  <key>WorkingDirectory</key><string>$DEST</string>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$DEST/launchagent.log</string>
  <key>StandardErrorPath</key><string>$DEST/launchagent-error.log</string>
  <key>ProcessType</key><string>Background</string>
</dict>
</plist>
PLIST

plutil -lint "$PLIST" >/dev/null
chmod 644 "$PLIST"

PIDS=$(lsof -t -nP -iTCP:8877 -sTCP:LISTEN 2>/dev/null || true)
if [ -n "$PIDS" ]; then
  kill $PIDS 2>/dev/null || true
  sleep 1
  LEFT=$(lsof -t -nP -iTCP:8877 -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$LEFT" ]; then
    kill -9 $LEFT 2>/dev/null || true
    sleep 1
  fi
fi

launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

HOST=$(/usr/sbin/scutil --get LocalHostName 2>/dev/null || hostname -s)
URL="http://$HOST.local:8877/"

for _ in 1 2 3 4 5; do
  if curl -fsS "http://127.0.0.1:8877/" >/dev/null 2>&1; then
    printf '\nSoundSwipe Bridge is running and automatic startup is installed.\n'
    open "$URL" || true
    read -k 1 "?Press any key to close..."
    exit 0
  fi
  sleep 1
done

printf '\nBridge did not start. Check: %s/launchagent-error.log\n' "$DEST"
read -k 1 "?Press any key to close..."
exit 1
