#!/bin/zsh
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.soundswipe.abletonbridge"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$ROOT/ableton_bridge.py</string>
    <string>--port</string><string>8877</string>
    <string>--no-open</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$ROOT/launchagent.log</string>
  <key>StandardErrorPath</key><string>$ROOT/launchagent-error.log</string>
  <key>ProcessType</key><string>Background</string>
</dict>
</plist>
PLIST

plutil -lint "$PLIST" >/dev/null
chmod 644 "$PLIST"

if ! lsof -nP -iTCP:8877 -sTCP:LISTEN >/dev/null 2>&1; then
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
fi

HOST=$(/usr/sbin/scutil --get LocalHostName 2>/dev/null || hostname -s)
TOKEN_FILE="$ROOT/../.soundswipe_ableton_bridge_token"
if [ -f "$TOKEN_FILE" ]; then
  TOKEN=$(cat "$TOKEN_FILE")
  URL="http://$HOST.local:8877/?t=$TOKEN"
else
  URL="http://$HOST.local:8877/"
fi

printf '\nSoundSwipe automatic connection installed.\n'
printf 'The Bridge will start automatically at the next Mac login.\n'
printf 'On iPhone, scan once and choose Add to Home Screen.\n\n'
open "$URL" || true
read -k 1 "?Press any key to close..."
