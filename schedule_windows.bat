@echo off
REM Schedule tasks for different times of day

REM Morning Playlist (8 AM)
SCHTASKS /CREATE /SC DAILY /TN "PlexPlayer_Morning" /TR "python %~dp0plex_playlist_player.py --time-slot morning" /ST 08:00

REM Afternoon Playlist (2 PM)
SCHTASKS /CREATE /SC DAILY /TN "PlexPlayer_Afternoon" /TR "python %~dp0plex_playlist_player.py --time-slot afternoon" /ST 14:00

REM Evening Playlist (7 PM)
SCHTASKS /CREATE /SC DAILY /TN "PlexPlayer_Evening" /TR "python %~dp0plex_playlist_player.py --time-slot evening" /ST 19:00

echo Tasks scheduled successfully!
echo To remove tasks:
echo SCHTASKS /DELETE /TN "PlexPlayer_Morning" /F
echo SCHTASKS /DELETE /TN "PlexPlayer_Afternoon" /F
echo SCHTASKS /DELETE /TN "PlexPlayer_Evening" /F
