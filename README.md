# Harmony Music Player

A modern, Spotify-inspired music player for macOS built with Python and PyQt6.

![Harmony Music Player](https://img.shields.io/badge/Platform-macOS-blue) ![Python](https://img.shields.io/badge/Python-3.12+-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

### Core Playback
- **Gapless playback** powered by mpv
- **Shuffle & Repeat** modes (Off, All, One)
- **Click-to-seek** on progress bar
- **Keyboard shortcuts** for all controls

### Library Management
- Scan folders for music (MP3, FLAC, M4A, WAV, OGG, OPUS, WMA, AIFF)
- Automatic metadata extraction (title, artist, album, genre, cover art)
- **Smart Playlists**: Recently Added, Most Played, Never Played, Starred
- **Custom Playlists**: Create and manage your own playlists
- **Star/favorite** tracks for quick access

### Interface
- **Dark theme** with 8 color schemes (Spotify, Blue, Purple, Nord, Dracula, Monokai, Light, Solarized)
- Browse by Albums, Artists, Genres, or All Tracks
- Sortable, resizable columns
- Album artwork display
- System tray integration

### Track Management
- **Right-click context menu**:
  - Edit Metadata
  - Star/Unstar
  - Remove from Library
  - Delete from Disk
- Play count tracking

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
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Run Harmony

```bash
LC_ALL=C python main_window.py
```

## Building the macOS App Bundle

To create a standalone `.app` bundle:

```bash
# Create app structure
mkdir -p Harmony.app/Contents/{MacOS,Resources}

# Copy files
cp -r *.py database.py audio_engine.py metadata.py requirements.txt Harmony.app/Contents/Resources/

# Create launcher script
cat > Harmony.app/Contents/MacOS/Harmony << 'EOF'
#!/bin/bash
DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
cd "$DIR"
source venv/bin/activate 2>/dev/null || {
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
}
export LC_ALL=C
exec python main_window.py
EOF
chmod +x Harmony.app/Contents/MacOS/Harmony

# Create Info.plist
cat > Harmony.app/Contents/Info.plist << 'EOF'
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
    <string>1.0.0</string>
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

# Move to Applications
mv Harmony.app /Applications/
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
- `cover_art/` - Cached album artwork
- `playback_state.json` - Last playback position and settings

## Themes

Access themes via **View → Theme**:

- **Dark (Spotify)** - Green accent (default)
- **Dark (Blue)** - Blue accent
- **Dark (Purple)** - Purple/pink accent
- **Nord** - Nord color palette
- **Dracula** - Dracula theme colors
- **Monokai** - Monokai editor colors
- **Light** - Light theme
- **Solarized Dark** - Solarized dark colors

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Known Issues

- The `LC_ALL=C` environment variable is required for mpv compatibility on some systems
- First launch may take a moment while dependencies are installed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [mpv](https://mpv.io/) - Media player engine
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [mutagen](https://mutagen.readthedocs.io/) - Audio metadata library
- [python-mpv](https://github.com/jaseg/python-mpv) - Python bindings for mpv
