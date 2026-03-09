"""
Harmony Music Player - Main Window (Part 2)
"""

import sys
import os

# Set app name BEFORE importing PyQt6 (fixes menu bar showing "Python")
if sys.platform == 'darwin':
    # macOS-specific: Set the app name in the process
    try:
        from Foundation import NSBundle
        bundle = NSBundle.mainBundle()
        info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        if info:
            info['CFBundleName'] = 'Harmony'
    except:
        pass

from main import *


# =========== Main Window ===========

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(700, 400)
        self.resize(1200, 800)
        
        # Standard window - fully resizable with all controls
        self.setWindowFlags(Qt.WindowType.Window)
        
        # Track the currently playing track id for highlighting
        self._current_playing_id = None
        
        # Initialize components
        self.db = MusicDatabase()
        self.audio_engine = create_audio_engine()
        self.metadata_reader = MetadataReader()
        self.metadata_writer = MetadataWriter()
        
        # Current state
        self.current_view = "albums"
        self.current_tracks: List[dict] = []
        
        # Setup UI
        self._setup_ui()
        self._setup_menu()
        self._setup_shortcuts()
        self._setup_tray()
        self._connect_signals()
        
        # Load library
        self._load_library()
        
        # Restore playback state
        self._restore_playback_state()
        
        # Start position update timer
        self.position_timer = QTimer(self)
        self.position_timer.timeout.connect(self._update_position)
        self.position_timer.start(500)
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Content area (sidebar + main content)
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Sidebar with scroll area
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(180)
        sidebar.setMaximumWidth(300)
        
        sidebar_main_layout = QVBoxLayout(sidebar)
        sidebar_main_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_main_layout.setSpacing(0)
        
        # Scroll area for sidebar content
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        sidebar_content = QWidget()
        sidebar_content.setObjectName("sidebarContent")
        sidebar_layout = QVBoxLayout(sidebar_content)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(8)
        
        # App title
        title_label = QLabel(APP_NAME)
        title_label.setFont(QFont("", 24, QFont.Weight.Bold))
        sidebar_layout.addWidget(title_label)
        
        sidebar_layout.addSpacing(16)
        
        # Search
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Search...")
        self.search_edit.textChanged.connect(self._on_search)
        sidebar_layout.addWidget(self.search_edit)
        
        sidebar_layout.addSpacing(16)
        
        # Navigation buttons
        nav_label = QLabel("LIBRARY")
        nav_label.setObjectName("secondaryLabel")
        nav_label.setFont(QFont("", 10, QFont.Weight.Bold))
        sidebar_layout.addWidget(nav_label)
        
        self.albums_btn = QPushButton("Albums")
        self.albums_btn.clicked.connect(lambda: self._show_view("albums"))
        sidebar_layout.addWidget(self.albums_btn)
        
        self.artists_btn = QPushButton("Artists")
        self.artists_btn.clicked.connect(lambda: self._show_view("artists"))
        sidebar_layout.addWidget(self.artists_btn)
        
        self.tracks_btn = QPushButton("All Tracks")
        self.tracks_btn.clicked.connect(lambda: self._show_view("tracks"))
        sidebar_layout.addWidget(self.tracks_btn)
        
        self.genres_btn = QPushButton("Genres")
        self.genres_btn.clicked.connect(lambda: self._show_view("genres"))
        sidebar_layout.addWidget(self.genres_btn)
        
        sidebar_layout.addSpacing(16)
        
        # Smart Playlists
        smart_label = QLabel("SMART PLAYLISTS")
        smart_label.setObjectName("secondaryLabel")
        smart_label.setFont(QFont("", 10, QFont.Weight.Bold))
        sidebar_layout.addWidget(smart_label)
        
        self.recent_btn = QPushButton("Recently Added")
        self.recent_btn.clicked.connect(lambda: self._show_smart_playlist("recent"))
        sidebar_layout.addWidget(self.recent_btn)
        
        self.most_played_btn = QPushButton("Most Played")
        self.most_played_btn.clicked.connect(lambda: self._show_smart_playlist("most_played"))
        sidebar_layout.addWidget(self.most_played_btn)
        
        self.never_played_btn = QPushButton("Never Played")
        self.never_played_btn.clicked.connect(lambda: self._show_smart_playlist("never_played"))
        sidebar_layout.addWidget(self.never_played_btn)
        
        self.starred_btn = QPushButton("★ Starred")
        self.starred_btn.clicked.connect(lambda: self._show_smart_playlist("starred"))
        sidebar_layout.addWidget(self.starred_btn)
        
        sidebar_layout.addSpacing(16)
        
        # Playlists
        playlist_label = QLabel("PLAYLISTS")
        playlist_label.setObjectName("secondaryLabel")
        playlist_label.setFont(QFont("", 10, QFont.Weight.Bold))
        sidebar_layout.addWidget(playlist_label)
        
        self.playlist_list = QListWidget()
        self.playlist_list.setMaximumHeight(150)
        self.playlist_list.itemDoubleClicked.connect(self._on_playlist_selected)
        # Enable context menu for playlists
        self.playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self._show_playlist_context_menu)
        # Enable drop for drag-and-drop from tracks
        self.playlist_list.setAcceptDrops(True)
        self.playlist_list.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.playlist_list.dragEnterEvent = self._playlist_drag_enter
        self.playlist_list.dragMoveEvent = self._playlist_drag_move
        self.playlist_list.dropEvent = self._playlist_drop
        sidebar_layout.addWidget(self.playlist_list)
        
        add_playlist_btn = QPushButton("+ New Playlist")
        add_playlist_btn.clicked.connect(self._create_playlist)
        sidebar_layout.addWidget(add_playlist_btn)
        
        sidebar_layout.addStretch()
        
        # Library stats
        self.stats_label = QLabel("")
        self.stats_label.setObjectName("secondaryLabel")
        self.stats_label.setWordWrap(True)
        sidebar_layout.addWidget(self.stats_label)
        
        # Set scroll area content
        sidebar_scroll.setWidget(sidebar_content)
        sidebar_main_layout.addWidget(sidebar_scroll)
        
        content_splitter.addWidget(sidebar)
        
        # Main content area
        self.content_stack = QStackedWidget()
        
        # Albums view (grid)
        self.albums_scroll = QScrollArea()
        self.albums_scroll.setWidgetResizable(True)
        self.albums_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.albums_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.albums_container = QWidget()
        self.albums_layout = QGridLayout(self.albums_container)
        self.albums_layout.setSpacing(16)
        self.albums_layout.setContentsMargins(24, 24, 24, 24)
        self.albums_scroll.setWidget(self.albums_container)
        
        self.content_stack.addWidget(self.albums_scroll)
        
        # Tracks view (table)
        self.tracks_view = TrackListWidget()
        self.tracks_view.track_double_clicked.connect(self._on_track_double_clicked)
        self.tracks_view.request_edit_metadata.connect(self._on_edit_metadata)
        self.tracks_view.request_delete_from_playlist.connect(self._on_delete_from_library)
        self.tracks_view.request_delete_from_disk.connect(self._on_delete_from_disk)
        self.tracks_view.request_toggle_star.connect(self._on_toggle_star)
        self.tracks_view.request_add_to_playlist.connect(self._on_add_tracks_to_playlist)
        self.content_stack.addWidget(self.tracks_view)
        
        # Album detail view
        self.album_detail = QWidget()
        self.album_detail_layout = QVBoxLayout(self.album_detail)
        self.album_detail_layout.setContentsMargins(24, 24, 24, 24)
        
        self.album_header = QWidget()
        album_header_layout = QHBoxLayout(self.album_header)
        album_header_layout.setSpacing(24)
        
        self.album_cover = QLabel()
        self.album_cover.setFixedSize(200, 200)
        self.album_cover.setScaledContents(True)
        self.album_cover.setStyleSheet("border-radius: 8px; background-color: #282828;")
        album_header_layout.addWidget(self.album_cover)
        
        album_info_layout = QVBoxLayout()
        album_info_layout.addStretch()
        
        self.album_title_label = QLabel()
        self.album_title_label.setFont(QFont("", 32, QFont.Weight.Bold))
        self.album_title_label.setWordWrap(True)
        album_info_layout.addWidget(self.album_title_label)
        
        self.album_artist_label = QLabel()
        self.album_artist_label.setFont(QFont("", 16))
        album_info_layout.addWidget(self.album_artist_label)
        
        self.album_meta_label = QLabel()
        self.album_meta_label.setObjectName("secondaryLabel")
        album_info_layout.addWidget(self.album_meta_label)
        
        album_info_layout.addSpacing(16)
        
        album_buttons = QHBoxLayout()
        self.play_album_btn = QPushButton("▶ Play")
        self.play_album_btn.setObjectName("primaryButton")
        self.play_album_btn.clicked.connect(self._play_current_album)
        album_buttons.addWidget(self.play_album_btn)
        album_buttons.addStretch()
        album_info_layout.addLayout(album_buttons)
        
        album_info_layout.addStretch()
        album_header_layout.addLayout(album_info_layout)
        album_header_layout.addStretch()
        
        self.album_detail_layout.addWidget(self.album_header)
        
        self.album_tracks_view = TrackListWidget()
        self.album_tracks_view.track_double_clicked.connect(self._on_album_track_double_clicked)
        self.album_tracks_view.request_edit_metadata.connect(self._on_edit_metadata)
        self.album_tracks_view.request_delete_from_playlist.connect(self._on_delete_from_library)
        self.album_tracks_view.request_delete_from_disk.connect(self._on_delete_from_disk)
        self.album_tracks_view.request_toggle_star.connect(self._on_toggle_star)
        self.album_tracks_view.request_add_to_playlist.connect(self._on_add_tracks_to_playlist)
        self.album_detail_layout.addWidget(self.album_tracks_view)
        
        self.content_stack.addWidget(self.album_detail)
        
        # Artists list view
        self.artists_list = QListWidget()
        self.artists_list.itemDoubleClicked.connect(self._on_artist_selected)
        self.content_stack.addWidget(self.artists_list)
        
        # Genres list view
        self.genres_list = QListWidget()
        self.genres_list.itemDoubleClicked.connect(self._on_genre_selected)
        self.content_stack.addWidget(self.genres_list)
        
        content_splitter.addWidget(self.content_stack)
        content_splitter.setStretchFactor(0, 0)  # Sidebar doesn't stretch
        content_splitter.setStretchFactor(1, 1)  # Main content stretches
        content_splitter.setSizes([220, 980])    # Initial sizes
        
        main_layout.addWidget(content_splitter)
        
        # Player bar at bottom
        player_bar = QFrame()
        player_bar.setObjectName("playerBar")
        player_bar.setFixedHeight(100)
        
        player_layout = QHBoxLayout(player_bar)
        player_layout.setContentsMargins(16, 0, 16, 0)
        
        self.player_controls = PlayerControls()
        player_layout.addWidget(self.player_controls)
        
        main_layout.addWidget(player_bar)
        
        # Refresh playlist sidebar
        self._refresh_playlists()
    
    def _setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        add_folder_action = QAction("Add Music Folder...", self)
        add_folder_action.triggered.connect(self._add_music_folder)
        file_menu.addAction(add_folder_action)
        
        manage_folders_action = QAction("Manage Folders...", self)
        manage_folders_action.triggered.connect(self._manage_folders)
        file_menu.addAction(manage_folders_action)
        
        file_menu.addSeparator()
        
        scan_action = QAction("Scan Library", self)
        scan_action.setShortcut(QKeySequence("Ctrl+R"))
        scan_action.triggered.connect(self._scan_library)
        file_menu.addAction(scan_action)
        
        file_menu.addSeparator()
        
        # Quit action for File menu (NoRole keeps it here)
        quit_action = QAction("Quit Harmony", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.setMenuRole(QAction.MenuRole.NoRole)
        quit_action.triggered.connect(self._force_quit)
        file_menu.addAction(quit_action)
        
        # This quit action uses QuitRole - macOS will move it to the app menu
        # and remove it from the File menu, replacing the default non-functional Quit
        macos_quit = QAction("Quit Harmony", self)
        macos_quit.setMenuRole(QAction.MenuRole.QuitRole)
        macos_quit.triggered.connect(self._force_quit)
        file_menu.addAction(macos_quit)
        
        # View menu (themes)
        view_menu = menubar.addMenu("View")
        
        theme_menu = view_menu.addMenu("Theme")
        
        self.theme_actions = {}
        themes = ["Spotify Dark", "Ocean Blue", "Sunset Orange", "Forest Green", "Purple Haze", "Classic Dark", "Light Mode"]
        for theme in themes:
            action = QAction(theme, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, t=theme: self._apply_theme(t))
            theme_menu.addAction(action)
            self.theme_actions[theme] = action
        
        # Set default theme
        self.theme_actions["Spotify Dark"].setChecked(True)
        self.current_theme = "Spotify Dark"
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        edit_metadata_action = QAction("Edit Metadata...", self)
        edit_metadata_action.triggered.connect(self._edit_selected_metadata)
        edit_menu.addAction(edit_metadata_action)
        
        # Playlist menu
        playlist_menu = menubar.addMenu("Playlist")
        
        new_playlist_action = QAction("New Playlist...", self)
        new_playlist_action.setShortcut(QKeySequence("Ctrl+N"))
        new_playlist_action.triggered.connect(self._create_playlist)
        playlist_menu.addAction(new_playlist_action)
        
        add_to_playlist_action = QAction("Add to Playlist...", self)
        add_to_playlist_action.triggered.connect(self._add_selected_to_playlist)
        playlist_menu.addAction(add_to_playlist_action)
        
        playlist_menu.addSeparator()
        
        delete_playlist_action = QAction("Delete Selected Playlist...", self)
        delete_playlist_action.triggered.connect(self._delete_selected_playlist)
        playlist_menu.addAction(delete_playlist_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        duplicates_action = QAction("Find Duplicates...", self)
        duplicates_action.triggered.connect(self._find_duplicates)
        tools_menu.addAction(duplicates_action)
        
        clean_action = QAction("Remove Missing Tracks", self)
        clean_action.triggered.connect(self._remove_missing)
        tools_menu.addAction(clean_action)
        
        # Playback menu
        playback_menu = menubar.addMenu("Playback")
        
        play_action = QAction("Play/Pause", self)
        play_action.setShortcut(QKeySequence("Space"))
        play_action.triggered.connect(self._toggle_play)
        playback_menu.addAction(play_action)
        
        next_action = QAction("Next Track", self)
        next_action.setShortcut(QKeySequence("Ctrl+Right"))
        next_action.triggered.connect(self._next_track)
        playback_menu.addAction(next_action)
        
        prev_action = QAction("Previous Track", self)
        prev_action.setShortcut(QKeySequence("Ctrl+Left"))
        prev_action.triggered.connect(self._prev_track)
        playback_menu.addAction(prev_action)
        
        # Window menu
        window_menu = menubar.addMenu("Window")
        
        minimize_action = QAction("Minimize", self)
        minimize_action.setShortcut(QKeySequence("Ctrl+M"))
        minimize_action.triggered.connect(self.showMinimized)
        window_menu.addAction(minimize_action)
        
        zoom_action = QAction("Zoom", self)
        zoom_action.triggered.connect(self._toggle_zoom)
        window_menu.addAction(zoom_action)
        
        window_menu.addSeparator()
        
        fullscreen_action = QAction("Enter Full Screen", self)
        fullscreen_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        window_menu.addAction(fullscreen_action)
        self._fullscreen_action = fullscreen_action
        
        exit_fullscreen_action = QAction("Exit Full Screen", self)
        exit_fullscreen_action.setShortcut(QKeySequence("Escape"))
        exit_fullscreen_action.triggered.connect(self._exit_fullscreen)
        window_menu.addAction(exit_fullscreen_action)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Volume controls
        vol_up = QShortcut(QKeySequence("Ctrl+Up"), self)
        vol_up.activated.connect(lambda: self._change_volume(10))
        
        vol_down = QShortcut(QKeySequence("Ctrl+Down"), self)
        vol_down.activated.connect(lambda: self._change_volume(-10))
        
        # Search focus
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.search_edit.setFocus)
        
        # Quit - standalone shortcut that bypasses menu system
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        quit_shortcut.activated.connect(self._force_quit)
    
    def _setup_tray(self):
        """Setup system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        
        tray_menu = QMenu()
        
        play_action = tray_menu.addAction("Play/Pause")
        play_action.triggered.connect(self._toggle_play)
        
        next_action = tray_menu.addAction("Next")
        next_action.triggered.connect(self._next_track)
        
        prev_action = tray_menu.addAction("Previous")
        prev_action.triggered.connect(self._prev_track)
        
        tray_menu.addSeparator()
        
        show_action = tray_menu.addAction("Show Window")
        show_action.triggered.connect(self.show)
        
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self._force_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
    
    def _connect_signals(self):
        """Connect UI signals to handlers."""
        # Player controls
        self.player_controls.play_btn.clicked.connect(self._toggle_play)
        self.player_controls.next_btn.clicked.connect(self._next_track)
        self.player_controls.prev_btn.clicked.connect(self._prev_track)
        self.player_controls.shuffle_btn.clicked.connect(self._toggle_shuffle)
        self.player_controls.repeat_btn.clicked.connect(self._toggle_repeat)
        
        self.player_controls.volume_slider.valueChanged.connect(self._set_volume)
        self.player_controls.progress_slider.sliderMoved.connect(self._seek)
        self.player_controls.progress_slider.sliderPressed.connect(self._on_seek_start)
        self.player_controls.progress_slider.sliderReleased.connect(self._on_seek_end)
        
        # Audio engine callbacks
        self.audio_engine.on_track_change(self._on_engine_track_change)
        self.audio_engine.on_playback_end(self._on_playback_end)
        
        self._seeking = False
    
    def _load_library(self):
        """Load library from database."""
        self._update_stats()
        self._show_view("albums")
    
    def _update_stats(self):
        """Update library statistics."""
        stats = self.db.get_library_stats()
        self.stats_label.setText(
            f"{stats['total_tracks']} tracks\n"
            f"{stats['total_albums']} albums\n"
            f"{stats['total_artists']} artists\n"
            f"{format_duration(stats['total_duration'])} total"
        )
    
    # =========== View Management ===========
    
    def _show_view(self, view: str):
        """Switch to a specific view."""
        self.current_view = view
        
        if view == "albums":
            self._load_albums_view()
            self.content_stack.setCurrentWidget(self.albums_scroll)
        elif view == "tracks":
            self._load_tracks_view()
            self.content_stack.setCurrentWidget(self.tracks_view)
        elif view == "artists":
            self._load_artists_view()
            self.content_stack.setCurrentWidget(self.artists_list)
        elif view == "genres":
            self._load_genres_view()
            self.content_stack.setCurrentWidget(self.genres_list)
    
    def _load_albums_view(self):
        """Load albums grid view."""
        # Clear existing
        while self.albums_layout.count():
            child = self.albums_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        albums = self.db.get_albums()
        
        cols = 5
        for i, album in enumerate(albums):
            card = AlbumCard(album)
            card.clicked.connect(self._on_album_clicked)
            self.albums_layout.addWidget(card, i // cols, i % cols)
    
    def _load_tracks_view(self):
        """Load all tracks list view."""
        tracks = self.db.get_all_tracks()
        self.current_tracks = tracks
        self.tracks_view.set_tracks(tracks)
    
    def _load_artists_view(self):
        """Load artists list view."""
        self.artists_list.clear()
        artists = self.db.get_artists()
        for artist in artists:
            self.artists_list.addItem(artist)
    
    def _load_genres_view(self):
        """Load genres list view."""
        self.genres_list.clear()
        genres = self.db.get_genres()
        for genre in genres:
            self.genres_list.addItem(genre)
    
    def _show_smart_playlist(self, playlist_type: str):
        """Show a smart playlist."""
        if playlist_type == "recent":
            tracks = self.db.get_recently_added(100)
            title = "Recently Added"
        elif playlist_type == "most_played":
            tracks = self.db.get_most_played(100)
            title = "Most Played"
        elif playlist_type == "never_played":
            tracks = self.db.get_never_played(100)
            title = "Never Played"
        elif playlist_type == "starred":
            tracks = self.db.get_starred_tracks()
            title = "★ Starred"
        else:
            return
        
        self.current_tracks = tracks
        self.tracks_view.set_tracks(tracks)
        self.content_stack.setCurrentWidget(self.tracks_view)
    
    def _on_album_clicked(self, album_info: dict):
        """Handle album card click - show album detail."""
        album = album_info.get('album')
        artist = album_info.get('artist')
        
        # Load album tracks
        tracks = self.db.get_album_tracks(album, artist)
        self.current_tracks = tracks
        
        # Update header
        self.album_title_label.setText(album or "Unknown Album")
        self.album_artist_label.setText(artist or "Unknown Artist")
        
        year = album_info.get('year', '')
        track_count = len(tracks)
        total_duration = sum(t.get('duration', 0) or 0 for t in tracks)
        self.album_meta_label.setText(
            f"{year} • {track_count} tracks • {format_duration(total_duration)}"
        )
        
        # Load cover art
        cover_path = album_info.get('cover_art_path')
        if cover_path and os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            self.album_cover.setPixmap(pixmap.scaled(200, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        else:
            self.album_cover.setText("🎵")
            self.album_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Load tracks
        self.album_tracks_view.set_tracks(tracks)
        
        self.content_stack.setCurrentWidget(self.album_detail)
    
    def _on_artist_selected(self, item):
        """Handle artist selection."""
        artist = item.text()
        albums = self.db.get_albums(artist)
        
        # Show albums for this artist
        while self.albums_layout.count():
            child = self.albums_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        cols = 5
        for i, album in enumerate(albums):
            card = AlbumCard(album)
            card.clicked.connect(self._on_album_clicked)
            self.albums_layout.addWidget(card, i // cols, i % cols)
        
        self.content_stack.setCurrentWidget(self.albums_scroll)
    
    def _on_genre_selected(self, item):
        """Handle genre selection."""
        genre = item.text()
        tracks = self.db.get_tracks_by_genre(genre)
        self.current_tracks = tracks
        self.tracks_view.set_tracks(tracks)
        self.content_stack.setCurrentWidget(self.tracks_view)
    
    def _on_search(self, text: str):
        """Handle search input."""
        if not text:
            self._show_view(self.current_view)
            return
        
        tracks = self.db.search_tracks(text)
        self.current_tracks = tracks
        self.tracks_view.set_tracks(tracks)
        self.content_stack.setCurrentWidget(self.tracks_view)
    
    # =========== Playlists ===========
    
    def _refresh_playlists(self):
        """Refresh playlist sidebar."""
        self.playlist_list.clear()
        playlists = self.db.get_playlists()
        for pl in playlists:
            item = QListWidgetItem(pl['name'])
            item.setData(Qt.ItemDataRole.UserRole, pl)
            self.playlist_list.addItem(item)
    
    def _create_playlist(self):
        """Create a new playlist."""
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name:
            self.db.create_playlist(name)
            self._refresh_playlists()
    
    def _on_playlist_selected(self, item):
        """Handle playlist double-click."""
        pl = item.data(Qt.ItemDataRole.UserRole)
        if pl:
            tracks = self.db.get_playlist_tracks(pl['id'])
            self.current_tracks = tracks
            self.tracks_view.set_tracks(tracks)
            self.content_stack.setCurrentWidget(self.tracks_view)
    
    def _add_selected_to_playlist(self):
        """Add selected tracks to a playlist."""
        selected = self.tracks_view.get_selected_tracks()
        if not selected:
            selected = self.album_tracks_view.get_selected_tracks()
        
        if not selected:
            QMessageBox.information(self, "No Selection", "Select tracks to add to a playlist.")
            return
        
        playlists = self.db.get_playlists()
        if not playlists:
            QMessageBox.information(self, "No Playlists", "Create a playlist first.")
            return
        
        names = [pl['name'] for pl in playlists]
        name, ok = QInputDialog.getItem(self, "Add to Playlist", "Select playlist:", names, 0, False)
        
        if ok and name:
            # Find playlist id
            for pl in playlists:
                if pl['name'] == name:
                    for track in selected:
                        if track.get('id'):
                            self.db.add_to_playlist(pl['id'], track['id'])
                    QMessageBox.information(self, "Added", f"Added {len(selected)} tracks to {name}")
                    break
    
    def _show_playlist_context_menu(self, position):
        """Show context menu for playlists."""
        item = self.playlist_list.itemAt(position)
        if not item:
            return
        
        pl = item.data(Qt.ItemDataRole.UserRole)
        if not pl:
            return
        
        menu = QMenu(self)
        
        # Open playlist
        open_action = menu.addAction("Open")
        open_action.triggered.connect(lambda: self._on_playlist_selected(item))
        
        menu.addSeparator()
        
        # Rename playlist
        rename_action = menu.addAction("Rename...")
        rename_action.triggered.connect(lambda: self._rename_playlist(pl))
        
        # Delete playlist
        delete_action = menu.addAction("Delete Playlist")
        delete_action.triggered.connect(lambda: self._delete_playlist(pl))
        
        menu.exec(self.playlist_list.mapToGlobal(position))
    
    def _rename_playlist(self, playlist: dict):
        """Rename a playlist."""
        name, ok = QInputDialog.getText(
            self, "Rename Playlist", "New name:", 
            text=playlist.get('name', '')
        )
        if ok and name:
            cursor = self.db.conn.cursor()
            cursor.execute('UPDATE playlists SET name = ? WHERE id = ?', (name, playlist['id']))
            self.db.conn.commit()
            self._refresh_playlists()
    
    def _delete_playlist(self, playlist: dict):
        """Delete a playlist."""
        reply = QMessageBox.question(
            self, "Delete Playlist",
            f"Delete playlist '{playlist.get('name', '')}'?\n\n"
            "The tracks will not be deleted from your library.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_playlist(playlist['id'])
            self._refresh_playlists()
    
    def _delete_selected_playlist(self):
        """Delete the currently selected playlist from sidebar."""
        item = self.playlist_list.currentItem()
        if not item:
            QMessageBox.information(self, "No Selection", "Select a playlist to delete.")
            return
        
        pl = item.data(Qt.ItemDataRole.UserRole)
        if pl:
            self._delete_playlist(pl)
    
    def _on_add_tracks_to_playlist(self, tracks: list):
        """Handle add to playlist request from context menu."""
        if not tracks:
            return
        
        playlists = self.db.get_playlists()
        if not playlists:
            QMessageBox.information(self, "No Playlists", "Create a playlist first.")
            return
        
        names = [pl['name'] for pl in playlists]
        name, ok = QInputDialog.getItem(self, "Add to Playlist", "Select playlist:", names, 0, False)
        
        if ok and name:
            for pl in playlists:
                if pl['name'] == name:
                    for track in tracks:
                        if track.get('id'):
                            self.db.add_to_playlist(pl['id'], track['id'])
                    QMessageBox.information(self, "Added", f"Added {len(tracks)} track(s) to {name}")
                    break
    
    def _playlist_drag_enter(self, event):
        """Handle drag enter on playlist list."""
        if event.mimeData().hasFormat('application/x-harmony-tracks') or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def _playlist_drag_move(self, event):
        """Handle drag move over playlist list."""
        if event.mimeData().hasFormat('application/x-harmony-tracks') or event.mimeData().hasText():
            # Highlight item under cursor
            item = self.playlist_list.itemAt(event.position().toPoint())
            if item:
                self.playlist_list.setCurrentItem(item)
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def _playlist_drop(self, event):
        """Handle drop on playlist list."""
        item = self.playlist_list.itemAt(event.position().toPoint())
        if not item:
            event.ignore()
            return
        
        pl = item.data(Qt.ItemDataRole.UserRole)
        if not pl:
            event.ignore()
            return
        
        # Get track IDs from mime data
        track_ids = []
        if event.mimeData().hasFormat('application/x-harmony-tracks'):
            data = event.mimeData().data('application/x-harmony-tracks').data().decode()
            track_ids = [int(x) for x in data.split(',') if x]
        elif event.mimeData().hasText():
            text = event.mimeData().text()
            track_ids = [int(x) for x in text.split(',') if x.isdigit()]
        
        if track_ids:
            for track_id in track_ids:
                self.db.add_to_playlist(pl['id'], track_id)
            QMessageBox.information(
                self, "Added", 
                f"Added {len(track_ids)} track(s) to {pl.get('name', 'playlist')}"
            )
            event.acceptProposedAction()
        else:
            event.ignore()
    
    # =========== Playback ===========
    
    def _on_track_double_clicked(self, index: int, track: dict):
        """Handle track double-click in list view."""
        # Get all tracks in current display order (respects sorting)
        playlist = self.tracks_view.get_all_tracks_in_order()
        self.current_tracks = playlist
        
        # Find the actual index of this track in the sorted list
        actual_index = next((i for i, t in enumerate(playlist) if t.get('id') == track.get('id')), index)
        
        self.audio_engine.set_playlist(playlist, actual_index)
        self.player_controls.update_track_info(track)
        self.player_controls.update_play_state(True)
        self._current_playing_id = track.get('id')
    
    def _on_album_track_double_clicked(self, index: int, track: dict):
        """Handle track double-click in album view."""
        # Get all tracks in current display order
        playlist = self.album_tracks_view.get_all_tracks_in_order()
        self.current_tracks = playlist
        
        # Find the actual index
        actual_index = next((i for i, t in enumerate(playlist) if t.get('id') == track.get('id')), index)
        
        self.audio_engine.set_playlist(playlist, actual_index)
        self.player_controls.update_track_info(track)
        self.player_controls.update_play_state(True)
        self._current_playing_id = track.get('id')
    
    def _play_current_album(self):
        """Play all tracks in current album view."""
        playlist = self.album_tracks_view.get_all_tracks_in_order()
        if playlist:
            self.current_tracks = playlist
            self.audio_engine.set_playlist(playlist, 0)
            self.player_controls.update_track_info(playlist[0])
            self.player_controls.update_play_state(True)
            self._current_playing_id = playlist[0].get('id')
    
    def _toggle_play(self):
        """Toggle play/pause."""
        # If no track is currently loaded, start playing the first track from current view
        if not self.audio_engine.get_current_track():
            if self.current_tracks:
                self.audio_engine.set_playlist(self.current_tracks, 0)
                self.player_controls.update_track_info(self.current_tracks[0])
                self.player_controls.update_play_state(True)
                self._current_playing_id = self.current_tracks[0].get('id')
                return
            else:
                # No tracks available - try to load from library
                tracks = self.db.get_all_tracks()
                if tracks:
                    self.current_tracks = tracks
                    self.audio_engine.set_playlist(tracks, 0)
                    self.player_controls.update_track_info(tracks[0])
                    self.player_controls.update_play_state(True)
                    self._current_playing_id = tracks[0].get('id')
                    return
        
        # Toggle play/pause if a track is loaded
        self.audio_engine.toggle_play_pause()
        self.player_controls.update_play_state(self.audio_engine.is_playing)
    
    def _next_track(self):
        """Play next track."""
        self.audio_engine.next()
        # Update UI after track change
        track = self.audio_engine.get_current_track()
        if track:
            self.player_controls.update_track_info(track)
            self.player_controls.update_play_state(True)
            self._current_playing_id = track.get('id')
            self._highlight_playing_track()
    
    def _prev_track(self):
        """Play previous track."""
        self.audio_engine.previous()
        # Update UI after track change
        track = self.audio_engine.get_current_track()
        if track:
            self.player_controls.update_track_info(track)
            self.player_controls.update_play_state(True)
            self._current_playing_id = track.get('id')
            self._highlight_playing_track()
    
    def _toggle_shuffle(self):
        """Toggle shuffle mode."""
        self.audio_engine.toggle_shuffle()
        self.player_controls.update_shuffle_state(self.audio_engine.get_shuffle())
    
    def _toggle_repeat(self):
        """Cycle repeat mode."""
        mode = self.audio_engine.cycle_repeat_mode()
        self.player_controls.update_repeat_state(mode)
    
    def _set_volume(self, value: int):
        """Set volume."""
        self.audio_engine.set_volume(value)
    
    def _change_volume(self, delta: int):
        """Change volume by delta."""
        current = self.audio_engine.get_volume()
        new_volume = max(0, min(100, current + delta))
        self.audio_engine.set_volume(new_volume)
        self.player_controls.volume_slider.setValue(new_volume)
    
    def _seek(self, value: int):
        """Seek to position."""
        duration = self.audio_engine.get_duration()
        if duration:
            position = (value / 1000) * duration
            self.audio_engine.seek(position)
    
    def _on_seek_start(self):
        """Handle seek start."""
        self._seeking = True
    
    def _on_seek_end(self):
        """Handle seek end."""
        self._seeking = False
    
    def _update_position(self):
        """Update position display."""
        if self._seeking:
            return
        
        position = self.audio_engine.get_position()
        duration = self.audio_engine.get_duration()
        
        if position is not None and duration is not None:
            self.player_controls.update_progress(position, duration)
    
    def _on_engine_track_change(self, track: dict, index: int):
        """Handle track change from audio engine."""
        self.player_controls.update_track_info(track)
        self.player_controls.update_play_state(True)
        
        # Update play count
        if track.get('id'):
            self.db.update_play_count(track['id'])
            self._current_playing_id = track.get('id')
            # Highlight currently playing track in the list
            self._highlight_playing_track()
    
    def _highlight_playing_track(self):
        """Highlight the currently playing track in track lists."""
        if not self._current_playing_id:
            return
        
        # Check which view is active and highlight accordingly
        for track_list in [self.tracks_view, self.album_tracks_view]:
            for row in range(track_list.rowCount()):
                title_item = track_list.item(row, 2)  # Title is in column 2 (after # and star)
                if title_item:
                    track = title_item.data(Qt.ItemDataRole.UserRole)
                    if track and track.get('id') == self._current_playing_id:
                        track_list.selectRow(row)
                        track_list.scrollToItem(title_item)
                        break
    
    def _on_playback_end(self):
        """Handle end of playlist."""
        self.player_controls.update_play_state(False)
    
    # =========== Context Menu Handlers ===========
    
    def _on_edit_metadata(self, track: dict):
        """Handle edit metadata request from context menu."""
        dialog = MetadataEditDialog(track, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_metadata = dialog.get_metadata()
            
            # Write to file
            if self.metadata_writer.write_metadata(track['file_path'], new_metadata):
                # Update database
                if track.get('id'):
                    self.db.update_track_metadata(track['id'], new_metadata)
                
                # Refresh view
                self._refresh_current_view()
                
                QMessageBox.information(self, "Success", "Metadata updated successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to write metadata to file.")
    
    def _on_delete_from_library(self, track: dict):
        """Handle remove from library request."""
        reply = QMessageBox.question(
            self, "Remove from Library",
            f"Remove '{track.get('title', 'Unknown')}' from your library?\n\n"
            "The file will not be deleted from disk.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if track.get('id'):
                self.db.delete_track(track['id'])
                self._refresh_current_view()
                self._update_stats()
    
    def _on_delete_from_disk(self, track: dict):
        """Handle delete from disk request."""
        reply = QMessageBox.warning(
            self, "Delete from Disk",
            f"Permanently delete '{track.get('title', 'Unknown')}'?\n\n"
            f"File: {track.get('file_path', '')}\n\n"
            "This cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if track.get('id'):
                success, message = self.db.delete_track_from_disk(track['id'])
                if success:
                    self._refresh_current_view()
                    self._update_stats()
                    QMessageBox.information(self, "Deleted", message)
                else:
                    QMessageBox.warning(self, "Error", message)
    
    def _on_toggle_star(self, track: dict):
        """Handle star toggle request."""
        if track.get('id'):
            self.db.toggle_star(track['id'])
            self._refresh_current_view()
    
    def _refresh_current_view(self):
        """Refresh the current view."""
        if self.current_view:
            self._show_view(self.current_view)
    
    # =========== Window Controls ===========
    
    def _toggle_zoom(self):
        """Toggle window zoom (maximize/restore)."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def _toggle_fullscreen(self):
        """Toggle full screen mode."""
        if self.isFullScreen():
            self.showNormal()
            self._fullscreen_action.setText("Enter Full Screen")
        else:
            self.showFullScreen()
            self._fullscreen_action.setText("Exit Full Screen")
    
    def _exit_fullscreen(self):
        """Exit full screen mode."""
        if self.isFullScreen():
            self.showNormal()
            self._fullscreen_action.setText("Enter Full Screen")
    
    def _quit_app(self):
        """Quit the application."""
        self._force_quit()
    
    def _force_quit(self):
        """Force quit - hide tray, cleanup, and exit."""
        self._save_playback_state()
        self.audio_engine.cleanup()
        self.tray_icon.hide()
        QApplication.instance().quit()
    
    def _apply_theme(self, theme_name: str):
        """Apply a color theme."""
        # Uncheck all theme actions
        for name, action in self.theme_actions.items():
            action.setChecked(name == theme_name)
        
        self.current_theme = theme_name
        
        # Theme definitions
        themes = {
            "Spotify Dark": {
                "bg_primary": "#121212",
                "bg_secondary": "#181818",
                "bg_sidebar": "#000000",
                "bg_hover": "#282828",
                "bg_selected": "#3e3e3e",
                "text_primary": "#ffffff",
                "text_secondary": "#b3b3b3",
                "accent": "#1db954",
                "accent_hover": "#1ed760",
                "player_bar": "#181818",
            },
            "Ocean Blue": {
                "bg_primary": "#0a1929",
                "bg_secondary": "#0d2137",
                "bg_sidebar": "#051320",
                "bg_hover": "#132f4c",
                "bg_selected": "#173a5e",
                "text_primary": "#ffffff",
                "text_secondary": "#b2bac2",
                "accent": "#5090d3",
                "accent_hover": "#66b2ff",
                "player_bar": "#0d2137",
            },
            "Sunset Orange": {
                "bg_primary": "#1a1a1a",
                "bg_secondary": "#242424",
                "bg_sidebar": "#0d0d0d",
                "bg_hover": "#333333",
                "bg_selected": "#404040",
                "text_primary": "#ffffff",
                "text_secondary": "#a0a0a0",
                "accent": "#ff6b35",
                "accent_hover": "#ff8c5a",
                "player_bar": "#242424",
            },
            "Forest Green": {
                "bg_primary": "#1a2420",
                "bg_secondary": "#212d28",
                "bg_sidebar": "#0f1613",
                "bg_hover": "#2a3b33",
                "bg_selected": "#344840",
                "text_primary": "#e8f5e9",
                "text_secondary": "#a5d6a7",
                "accent": "#4caf50",
                "accent_hover": "#66bb6a",
                "player_bar": "#212d28",
            },
            "Purple Haze": {
                "bg_primary": "#1a1625",
                "bg_secondary": "#231d30",
                "bg_sidebar": "#0f0c17",
                "bg_hover": "#2d2540",
                "bg_selected": "#3d3354",
                "text_primary": "#f3e5f5",
                "text_secondary": "#ce93d8",
                "accent": "#ab47bc",
                "accent_hover": "#ba68c8",
                "player_bar": "#231d30",
            },
            "Classic Dark": {
                "bg_primary": "#2d2d2d",
                "bg_secondary": "#383838",
                "bg_sidebar": "#1e1e1e",
                "bg_hover": "#454545",
                "bg_selected": "#525252",
                "text_primary": "#ffffff",
                "text_secondary": "#aaaaaa",
                "accent": "#ff5252",
                "accent_hover": "#ff7070",
                "player_bar": "#383838",
            },
            "Light Mode": {
                "bg_primary": "#ffffff",
                "bg_secondary": "#f5f5f5",
                "bg_sidebar": "#e8e8e8",
                "bg_hover": "#e0e0e0",
                "bg_selected": "#d0d0d0",
                "text_primary": "#1a1a1a",
                "text_secondary": "#666666",
                "accent": "#1db954",
                "accent_hover": "#1ed760",
                "player_bar": "#f5f5f5",
            },
        }
        
        theme = themes.get(theme_name, themes["Spotify Dark"])
        stylesheet = generate_stylesheet(theme)
        QApplication.instance().setStyleSheet(stylesheet)
    
    # =========== Library Management ===========
    
    def _add_music_folder(self):
        """Add a music folder to the library."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Music Folder",
            str(Path.home() / "Music")
        )
        
        if folder:
            self.db.add_music_folder(folder)
            self._scan_library()
    
    def _manage_folders(self):
        """Open folder management dialog."""
        dialog = FolderManagerDialog(self.db, self)
        dialog.exec()
    
    def _scan_library(self):
        """Scan music folders for new tracks."""
        folders = self.db.get_music_folders()
        
        if not folders:
            QMessageBox.information(
                self, "No Folders",
                "No music folders configured. Add a folder first."
            )
            return
        
        folder_paths = [f['folder_path'] for f in folders]
        
        progress = QProgressDialog("Scanning library...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        self.scan_worker = LibraryScanWorker(folder_paths)
        self.scan_worker.progress.connect(lambda p, f: progress.setLabelText(f"Scanning: {f}"))
        self.scan_worker.finished.connect(lambda tracks: self._on_scan_finished(tracks, progress))
        self.scan_worker.error.connect(lambda e: self._on_scan_error(e, progress))
        self.scan_worker.start()
    
    def _on_scan_finished(self, tracks: List[dict], progress: QProgressDialog):
        """Handle scan completion."""
        progress.close()
        
        added = 0
        for track in tracks:
            if self.db.add_track(track):
                added += 1
        
        # Update folder scan times
        for folder in self.db.get_music_folders():
            self.db.update_folder_scan_time(folder['folder_path'])
        
        self._update_stats()
        self._show_view(self.current_view)
        
        QMessageBox.information(
            self, "Scan Complete",
            f"Found {len(tracks)} files, added/updated {added} tracks."
        )
    
    def _on_scan_error(self, error: str, progress: QProgressDialog):
        """Handle scan error."""
        progress.close()
        QMessageBox.critical(self, "Scan Error", f"Error scanning library: {error}")
    
    def _edit_selected_metadata(self):
        """Edit metadata for selected track."""
        selected = self.tracks_view.get_selected_tracks()
        if not selected:
            selected = self.album_tracks_view.get_selected_tracks()
        
        if not selected:
            QMessageBox.information(self, "No Selection", "Select a track to edit.")
            return
        
        track = selected[0]
        dialog = MetadataEditDialog(track, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_metadata = dialog.get_metadata()
            
            # Write to file
            if self.metadata_writer.write_metadata(track['file_path'], new_metadata):
                # Update database
                if track.get('id'):
                    self.db.update_track_metadata(track['id'], new_metadata)
                
                # Refresh view
                self._show_view(self.current_view)
                
                QMessageBox.information(self, "Success", "Metadata updated successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to write metadata to file.")
    
    def _find_duplicates(self):
        """Find and show duplicate tracks."""
        duplicates = self.db.find_duplicates()
        
        if not duplicates:
            QMessageBox.information(self, "No Duplicates", "No duplicate tracks found.")
            return
        
        dialog = DuplicatesDialog(duplicates, self)
        dialog.exec()
    
    def _remove_missing(self):
        """Remove tracks with missing files."""
        removed = self.db.delete_missing_tracks()
        
        self._update_stats()
        self._show_view(self.current_view)
        
        QMessageBox.information(
            self, "Cleanup Complete",
            f"Removed {removed} tracks with missing files."
        )
    
    # =========== State Management ===========
    
    def _restore_playback_state(self):
        """Restore playback state from database."""
        state = self.db.get_playback_state()
        
        if state:
            self.audio_engine.set_volume(int(state.get('volume', 1.0) * 100))
            self.player_controls.volume_slider.setValue(int(state.get('volume', 1.0) * 100))
            
            if state.get('shuffle'):
                self.audio_engine.set_shuffle(True)
                self.player_controls.update_shuffle_state(True)
            
            repeat_mode = RepeatMode(state.get('repeat_mode', 0))
            self.audio_engine.set_repeat_mode(repeat_mode)
            self.player_controls.update_repeat_state(repeat_mode)
            
            # Restore view
            saved_view = state.get('current_view', 'albums')
            if saved_view in ['albums', 'tracks', 'artists', 'genres']:
                self.current_view = saved_view
                self._show_view(saved_view)
            
            # Restore track - load it into the engine so pressing play resumes
            if state.get('current_track_id'):
                track = self.db.get_track(state['current_track_id'])
                if track:
                    self.player_controls.update_track_info(track)
                    self._current_playing_id = track.get('id')
                    # Set up the track in the playlist so play button works
                    self.current_tracks = [track]
                    self.audio_engine.set_playlist([track], 0)
                    # Pause immediately - we just want it ready, not playing
                    self.audio_engine.pause()
                    self.player_controls.update_play_state(False)
    
    def _save_playback_state(self):
        """Save current playback state."""
        track = self.audio_engine.get_current_track()
        position = self.audio_engine.get_position() or 0
        
        self.db.save_playback_state(
            track_id=track.get('id') if track else None,
            position=position,
            volume=self.audio_engine.get_volume() / 100,
            shuffle=self.audio_engine.get_shuffle(),
            repeat_mode=self.audio_engine.get_repeat_mode().value,
            current_view=self.current_view
        )
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()
    
    def closeEvent(self, event):
        """Handle window close."""
        self._save_playback_state()
        self.audio_engine.cleanup()
        self.tray_icon.hide()
        event.accept()


# =========== Application Entry Point ===========

def main():
    """Application entry point."""
    # Set app name before creating QApplication (helps with menu bar on macOS)
    if sys.platform == 'darwin':
        # This helps but isn't always sufficient
        os.environ['QT_MAC_WANTS_LAYER'] = '1'
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(True)
    
    # Apply dark theme
    app.setStyleSheet(DARK_STYLE)
    
    # Set dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(18, 18, 18))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(18, 18, 18))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 40))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 40))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(29, 185, 84))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    # Create main window
    window = MainWindow()
    window.show()
    
    # Run
    exit_code = app.exec()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
