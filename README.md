# Plex Playlist Player

## Setup Instructions

1. Install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Create a `.env` file with your Plex credentials:
```
PLEX_SERVER_URL=https://your-plex-server-url
PLEX_TOKEN=your_plex_token
PLAYLIST_NAME=Your Desired Playlist Name
```

3. Run the application:
```bash
python plex_playlist_player.py
```

## Dependencies
- PlexAPI for Plex server interaction
- python-vlc for media playback
- python-dotenv for environment configuration
