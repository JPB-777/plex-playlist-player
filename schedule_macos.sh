#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create plist files for each time slot
cat > ~/Library/LaunchAgents/com.user.plexplaylist.morning.plist << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.plexplaylist.morning</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${SCRIPT_DIR}/plex_playlist_player.py</string>
        <string>--time-slot</string>
        <string>morning</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/logs/playlist_morning.log</string>
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/logs/playlist_morning_error.log</string>
</dict>
</plist>
EOL

cat > ~/Library/LaunchAgents/com.user.plexplaylist.afternoon.plist << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.plexplaylist.afternoon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${SCRIPT_DIR}/plex_playlist_player.py</string>
        <string>--time-slot</string>
        <string>afternoon</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>14</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/logs/playlist_afternoon.log</string>
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/logs/playlist_afternoon_error.log</string>
</dict>
</plist>
EOL

cat > ~/Library/LaunchAgents/com.user.plexplaylist.evening.plist << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.plexplaylist.evening</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${SCRIPT_DIR}/plex_playlist_player.py</string>
        <string>--time-slot</string>
        <string>evening</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>19</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/logs/playlist_evening.log</string>
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/logs/playlist_evening_error.log</string>
</dict>
</plist>
EOL

# Create logs directory
mkdir -p "${SCRIPT_DIR}/logs"

# Load the launch agents
launchctl load ~/Library/LaunchAgents/com.user.plexplaylist.morning.plist
launchctl load ~/Library/LaunchAgents/com.user.plexplaylist.afternoon.plist
launchctl load ~/Library/LaunchAgents/com.user.plexplaylist.evening.plist

echo "Tasks scheduled successfully!"
echo "To remove tasks, run:"
echo "launchctl unload ~/Library/LaunchAgents/com.user.plexplaylist.morning.plist"
echo "launchctl unload ~/Library/LaunchAgents/com.user.plexplaylist.afternoon.plist"
echo "launchctl unload ~/Library/LaunchAgents/com.user.plexplaylist.evening.plist"
