# Harmony Music Player

A modern, Spotify-inspired music player for macOS built with Python and PyQt6.

![Harmony Music Player](https://img.shields.io/badge/Platform-macOS-blue) ![Python](https://img.shields.io/badge/Python-3.12+-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

### Core Playback
- **Reliable local playback** powered by mpv
- **Shuffle & Repeat** modes (Off, All, One)
- **Up Next queue** with Play Next, Add to Queue, and Clear Queue
- **Session restore** that reopens the last track paused at the saved position
- **Click-to-seek** on progress bar
- **Keyboard shortcuts** for core controls

### Library Management
- Scan folders for music (MP3, FLAC, M4A, WAV, OGG, OPUS, WMA, AIFF)
- Automatic metadata extraction (title, artist, album, genre, cover art)
- **Smart Playlists**: Recently Added, Most Played, Never Played, Starred
- **Custom Playlists**: Create and manage your own playlists
- **Star/favorite** tracks for quick access

### Interface
- **Seven built-in themes** with high-contrast text
- Browse by Albums, Artists, Genres, playlists, or All Tracks
- Search results with context headers and summaries
- Album artwork display and polished album detail view
- Stronger current-track highlighting across views
- System tray integration

### Track Management
- **Right-click context menu**:
  - Play Next
  - Add to Queue
  - Edit Metadata
  - Star/Unstar
  - Remove from Library
  - Delete from Disk
- Play counts only after meaningful listening

## Screenshots

*Coming soon*

## Requirements

- macOS 10.15+ (Catalina or later)
- Python 3.12+
- Homebrew (for installing mpv)

## Installation

### 1. Install Dependencies

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install mpv
brew install mpv
```

### 2. Clone the Repository

```bash
git clone https://github.com/leaton79/harmony-music-player.git
cd harmony-music-player
```

### 3. Set Up Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

### 4. Run Harmony

```bash
source .venv/bin/activate
python3 main_window.py
```

## Building the macOS App Bundle

To create a standalone `.app` bundle with the bundled virtual environment:

```bash
./Tools/package_app.sh

# Install or replace the app in /Applications
rm -rf /Applications/Harmony.app
cp -R /tmp/HarmonyAppBuild/Harmony.app /Applications/Harmony.app
```

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Play/Pause | Space |
| Next Track | Ctrl+→ |
| Previous Track | Ctrl+← |
| Volume Up | Ctrl+↑ |
| Volume Down | Ctrl+↓ |
| Search | Ctrl+F |
| Quit | Cmd+Q |
| Minimize | Cmd+M |
| Full Screen | Ctrl+Shift+F |

## File Structure

```
harmony-music-player/
├── main_window.py      # Main application window and entry point
├── main.py             # UI components (widgets, dialogs)
├── audio_engine.py     # mpv-based audio playback engine
├── database.py         # SQLite database for library management
├── metadata.py         # Audio file metadata reading/writing
├── requirements.txt    # Python dependencies
└── README.md
```

## Configuration

Harmony stores its data in `~/.harmony_player/`:
- `library.db` - SQLite database with your music library
- `artwork/` - Cached album artwork
- SQLite playback state inside `library.db`

## Themes

Access themes via **View → Theme**:

- **Spotify Dark**
- **Ocean Blue**
- **Sunset Orange**
- **Forest Green**
- **Purple Haze**
- **Classic Dark**
- **Light Mode**

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Current Focus

- Playback reliability and queue behavior
- Better visual hierarchy and higher contrast text
- Safer library and file-management flows

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [mpv](https://mpv.io/) - Media player engine
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [mutagen](https://mutagen.readthedocs.io/) - Audio metadata library
- [python-mpv](https://github.com/jaseg/python-mpv) - Python bindings for mpv
