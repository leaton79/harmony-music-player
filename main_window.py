"""
Harmony Music Player - Main Window (Part 2)
"""

import sys
import os
import json
from pathlib import Path
from typing import List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QLineEdit,
    QMessageBox, QGridLayout, QScrollArea, QFrame, QSplitter, QMenu,
    QDialog, QInputDialog, QProgressDialog, QSystemTrayIcon, QStyle,
    QStackedWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont, QAction, QKeySequence, QPalette, QColor, QShortcut, QIcon

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

from audio_engine import RepeatMode, create_audio_engine
from database import MusicDatabase
from main import (
    APP_NAME,
    APP_VERSION,
    DARK_STYLE,
    AlbumCard,
    DuplicatesDialog,
    FolderManagerDialog,
    LibraryScanWorker,
    MetadataEditDialog,
    PlayerControls,
    TrackListWidget,
    format_duration,
)
from metadata import MetadataReader, MetadataWriter
from playback_rules import has_meaningful_playback, resolve_playback_queue, should_restore_playback
from themes import APP_THEMES, DEFAULT_THEME, generate_stylesheet


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
        self._play_counted_for_current_track = False
        self._restoring_session = False
        
        # Initialize components
        self.db = MusicDatabase()
        self.audio_engine = create_audio_engine()
        self.metadata_reader = MetadataReader()
        self.metadata_writer = MetadataWriter()
        
        # Current state
        self.current_view = "albums"
        self.current_view_data = {}
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
        self._refresh_up_next()
        self._highlight_playing_track()
        
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
        sidebar_layout.setContentsMargins(18, 20, 18, 20)
        sidebar_layout.setSpacing(10)
        
        # App title
        title_label = QLabel(APP_NAME)
        title_label.setFont(QFont("", 24, QFont.Weight.Bold))
        sidebar_layout.addWidget(title_label)

        subtitle_label = QLabel("Local music, organized simply")
        subtitle_label.setObjectName("secondaryLabel")
        sidebar_layout.addWidget(subtitle_label)
        
        sidebar_layout.addSpacing(12)
        
        # Search
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Search...")
        self.search_edit.textChanged.connect(self._on_search)
        sidebar_layout.addWidget(self.search_edit)

        self.clear_search_btn = QPushButton("Clear Search")
        self.clear_search_btn.setObjectName("subtleButton")
        self.clear_search_btn.clicked.connect(self._clear_search)
        self.clear_search_btn.hide()
        sidebar_layout.addWidget(self.clear_search_btn)
        
        sidebar_layout.addSpacing(16)
        
        # Navigation buttons
        nav_label = QLabel("LIBRARY")
        nav_label.setObjectName("sectionLabel")
        sidebar_layout.addWidget(nav_label)
        
        self.albums_btn = QPushButton("Albums")
        self.albums_btn.setObjectName("navButton")
        self.albums_btn.clicked.connect(lambda: self._show_view("albums"))
        sidebar_layout.addWidget(self.albums_btn)
        
        self.artists_btn = QPushButton("Artists")
        self.artists_btn.setObjectName("navButton")
        self.artists_btn.clicked.connect(lambda: self._show_view("artists"))
        sidebar_layout.addWidget(self.artists_btn)
        
        self.tracks_btn = QPushButton("All Tracks")
        self.tracks_btn.setObjectName("navButton")
        self.tracks_btn.clicked.connect(lambda: self._show_view("tracks"))
        sidebar_layout.addWidget(self.tracks_btn)
        
        self.genres_btn = QPushButton("Genres")
        self.genres_btn.setObjectName("navButton")
        self.genres_btn.clicked.connect(lambda: self._show_view("genres"))
        sidebar_layout.addWidget(self.genres_btn)
        
        sidebar_layout.addSpacing(12)
        
        # Smart Playlists
        smart_label = QLabel("SMART PLAYLISTS")
        smart_label.setObjectName("sectionLabel")
        sidebar_layout.addWidget(smart_label)
        
        self.recent_btn = QPushButton("Recently Added")
        self.recent_btn.setObjectName("navButton")
        self.recent_btn.clicked.connect(lambda: self._show_smart_playlist("recent"))
        sidebar_layout.addWidget(self.recent_btn)
        
        self.most_played_btn = QPushButton("Most Played")
        self.most_played_btn.setObjectName("navButton")
        self.most_played_btn.clicked.connect(lambda: self._show_smart_playlist("most_played"))
        sidebar_layout.addWidget(self.most_played_btn)
        
        self.never_played_btn = QPushButton("Never Played")
        self.never_played_btn.setObjectName("navButton")
        self.never_played_btn.clicked.connect(lambda: self._show_smart_playlist("never_played"))
        sidebar_layout.addWidget(self.never_played_btn)
        
        self.starred_btn = QPushButton("★ Starred")
        self.starred_btn.setObjectName("navButton")
        self.starred_btn.clicked.connect(lambda: self._show_smart_playlist("starred"))
        sidebar_layout.addWidget(self.starred_btn)

        self.history_btn = QPushButton("History")
        self.history_btn.setObjectName("navButton")
        self.history_btn.clicked.connect(lambda: self._show_smart_playlist("history"))
        sidebar_layout.addWidget(self.history_btn)

        self.clear_history_btn = QPushButton("Clear History...")
        self.clear_history_btn.setObjectName("subtleButton")
        self.clear_history_btn.clicked.connect(self._clear_play_history)
        sidebar_layout.addWidget(self.clear_history_btn)
        
        sidebar_layout.addSpacing(12)
        
        # Playlists
        playlist_label = QLabel("PLAYLISTS")
        playlist_label.setObjectName("sectionLabel")
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
        add_playlist_btn.setObjectName("navButton")
        add_playlist_btn.clicked.connect(self._create_playlist)
        sidebar_layout.addWidget(add_playlist_btn)

        queue_card = QFrame()
        queue_card.setObjectName("queueCard")
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(12, 12, 12, 12)
        queue_layout.setSpacing(8)

        queue_title = QLabel("Up Next")
        queue_title.setObjectName("sectionLabel")
        queue_layout.addWidget(queue_title)

        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(160)
        self.queue_list.itemDoubleClicked.connect(self._on_up_next_selected)
        queue_layout.addWidget(self.queue_list)

        self.clear_queue_btn = QPushButton("Clear Queue")
        self.clear_queue_btn.setObjectName("subtleButton")
        self.clear_queue_btn.clicked.connect(self._clear_up_next)
        queue_layout.addWidget(self.clear_queue_btn)

        sidebar_layout.addWidget(queue_card)
        
        sidebar_layout.addStretch()
        
        # Library stats
        stats_card = QFrame()
        stats_card.setObjectName("statsCard")
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(4)

        stats_title = QLabel("Library")
        stats_title.setObjectName("sectionLabel")
        stats_layout.addWidget(stats_title)

        self.stats_label = QLabel("")
        self.stats_label.setObjectName("secondaryLabel")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)
        sidebar_layout.addWidget(stats_card)
        
        # Set scroll area content
        sidebar_scroll.setWidget(sidebar_content)
        sidebar_main_layout.addWidget(sidebar_scroll)
        
        content_splitter.addWidget(sidebar)
        
        # Main content area
        main_content = QWidget()
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)

        self.content_header = QFrame()
        self.content_header.setObjectName("contentHeader")
        header_layout = QVBoxLayout(self.content_header)
        header_layout.setContentsMargins(28, 22, 28, 18)
        header_layout.setSpacing(4)

        self.content_eyebrow_label = QLabel("Library")
        self.content_eyebrow_label.setObjectName("contentEyebrow")
        header_layout.addWidget(self.content_eyebrow_label)

        self.content_title_label = QLabel("Albums")
        self.content_title_label.setObjectName("contentTitle")
        header_layout.addWidget(self.content_title_label)

        self.content_subtitle_label = QLabel("Browse your collection by release.")
        self.content_subtitle_label.setObjectName("contentSubtitle")
        header_layout.addWidget(self.content_subtitle_label)

        main_content_layout.addWidget(self.content_header)

        self.content_stack = QStackedWidget()
        
        # Albums view (grid)
        self.albums_scroll = QScrollArea()
        self.albums_scroll.setWidgetResizable(True)
        self.albums_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.albums_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.albums_container = QWidget()
        self.albums_layout = QGridLayout(self.albums_container)
        self.albums_layout.setSpacing(20)
        self.albums_layout.setContentsMargins(28, 28, 28, 28)
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
        self.tracks_view.request_play_next.connect(self._on_play_next_requested)
        self.tracks_view.request_add_to_queue.connect(self._on_add_to_queue_requested)
        self.content_stack.addWidget(self.tracks_view)
        
        # Album detail view
        self.album_detail = QWidget()
        self.album_detail_layout = QVBoxLayout(self.album_detail)
        self.album_detail_layout.setContentsMargins(24, 24, 24, 24)
        self.album_detail_layout.setSpacing(18)
        
        self.album_header = QWidget()
        self.album_header.setObjectName("albumHero")
        album_header_layout = QHBoxLayout(self.album_header)
        album_header_layout.setSpacing(24)
        album_header_layout.setContentsMargins(24, 24, 24, 24)
        
        self.album_cover = QLabel()
        self.album_cover.setFixedSize(200, 200)
        self.album_cover.setScaledContents(True)
        self.album_cover.setStyleSheet("border-radius: 14px; background-color: #282828;")
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

        self.album_summary_label = QLabel()
        self.album_summary_label.setObjectName("secondaryLabel")
        self.album_summary_label.setWordWrap(True)
        album_info_layout.addWidget(self.album_summary_label)
        
        album_info_layout.addSpacing(16)
        
        album_buttons = QHBoxLayout()
        self.play_album_btn = QPushButton("Play Album")
        self.play_album_btn.setObjectName("primaryButton")
        self.play_album_btn.clicked.connect(self._play_current_album)
        album_buttons.addWidget(self.play_album_btn)

        self.back_to_albums_btn = QPushButton("Back to Albums")
        self.back_to_albums_btn.setObjectName("subtleButton")
        self.back_to_albums_btn.clicked.connect(lambda: self._show_view("albums"))
        album_buttons.addWidget(self.back_to_albums_btn)
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
        self.album_tracks_view.request_play_next.connect(self._on_play_next_requested)
        self.album_tracks_view.request_add_to_queue.connect(self._on_add_to_queue_requested)
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
        
        main_content_layout.addWidget(self.content_stack)
        content_splitter.addWidget(main_content)
        content_splitter.setStretchFactor(0, 0)  # Sidebar doesn't stretch
        content_splitter.setStretchFactor(1, 1)  # Main content stretches
        content_splitter.setSizes([220, 980])    # Initial sizes
        
        main_layout.addWidget(content_splitter)
        
        # Player bar at bottom
        player_bar = QFrame()
        player_bar.setObjectName("playerBar")
        player_bar.setFixedHeight(118)
        
        player_layout = QHBoxLayout(player_bar)
        player_layout.setContentsMargins(20, 8, 20, 10)
        
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
        themes = list(APP_THEMES.keys())
        for theme in themes:
            action = QAction(theme, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, t=theme: self._apply_theme(t))
            theme_menu.addAction(action)
            self.theme_actions[theme] = action
        
        # Set default theme
        self.theme_actions[DEFAULT_THEME].setChecked(True)
        self.current_theme = DEFAULT_THEME
        
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
        self.audio_engine.on_error(self._on_playback_error)
        
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
        self._set_view_context(view)
        self._update_sidebar_selection(view)
        
        if view == "albums":
            self._set_content_header("Library", "Albums", "Browse your collection by release.")
            self._load_albums_view()
            self.content_stack.setCurrentWidget(self.albums_scroll)
        elif view == "tracks":
            track_count = self.db.get_library_stats()['total_tracks']
            self._set_content_header("Library", "All Tracks", f"{track_count} tracks in your library.")
            self._load_tracks_view()
            self.content_stack.setCurrentWidget(self.tracks_view)
        elif view == "artists":
            self._set_content_header("Library", "Artists", "Jump to albums by artist.")
            self._load_artists_view()
            self.content_stack.setCurrentWidget(self.artists_list)
        elif view == "genres":
            self._set_content_header("Library", "Genres", "Browse tagged music by genre.")
            self._load_genres_view()
            self.content_stack.setCurrentWidget(self.genres_list)

    def _set_view_context(self, view: str, data: dict | None = None):
        """Track the current navigation context for session restore."""
        self.current_view = view
        self.current_view_data = data or {}
    
    def _load_albums_view(self):
        """Load albums grid view."""
        # Clear existing
        while self.albums_layout.count():
            child = self.albums_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        albums = self.db.get_albums()
        if not albums:
            self._add_empty_state(
                self.albums_layout,
                "No music in your library yet",
                "Add a folder and scan your music to start browsing albums.",
                primary_action=("Add Music Folder", self._add_music_folder),
                secondary_action=("Scan Library", self._scan_library),
            )
            return
        
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
        if not artists:
            self.artists_list.addItem("No artists yet. Scan a music folder to build your library.")
            self.artists_list.setEnabled(False)
            return
        self.artists_list.setEnabled(True)
        for artist in artists:
            self.artists_list.addItem(artist)
    
    def _load_genres_view(self):
        """Load genres list view."""
        self.genres_list.clear()
        genres = self.db.get_genres()
        if not genres:
            self.genres_list.addItem("No genres yet. Tagged music will appear here after a scan.")
            self.genres_list.setEnabled(False)
            return
        self.genres_list.setEnabled(True)
        for genre in genres:
            self.genres_list.addItem(genre)

    def _update_sidebar_selection(self, current_view: str):
        """Highlight the active section in the sidebar."""
        button_map = {
            "albums": self.albums_btn,
            "artists": self.artists_btn,
            "tracks": self.tracks_btn,
            "genres": self.genres_btn,
            "smart_recent": self.recent_btn,
            "smart_most_played": self.most_played_btn,
            "smart_never_played": self.never_played_btn,
            "smart_starred": self.starred_btn,
            "smart_history": self.history_btn,
        }
        for name, button in button_map.items():
            button.setProperty("active", name == current_view)
            button.style().unpolish(button)
            button.style().polish(button)

    def _set_content_header(self, eyebrow: str, title: str, subtitle: str):
        """Update the main content header."""
        self.content_eyebrow_label.setText(eyebrow)
        self.content_title_label.setText(title)
        self.content_subtitle_label.setText(subtitle)

    def _add_empty_state(self, layout, title: str, body: str, primary_action=None, secondary_action=None):
        """Add a simple empty state to a layout."""
        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setContentsMargins(32, 48, 32, 48)
        empty_layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("emptyStateTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(title_label)

        body_label = QLabel(body)
        body_label.setObjectName("emptyStateBody")
        body_label.setWordWrap(True)
        body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(body_label)

        if primary_action or secondary_action:
            button_row = QHBoxLayout()
            button_row.setSpacing(10)
            button_row.addStretch()

            if primary_action:
                label, callback = primary_action
                primary_button = QPushButton(label)
                primary_button.setObjectName("primaryButton")
                primary_button.clicked.connect(callback)
                button_row.addWidget(primary_button)

            if secondary_action:
                label, callback = secondary_action
                secondary_button = QPushButton(label)
                secondary_button.setObjectName("subtleButton")
                secondary_button.clicked.connect(callback)
                button_row.addWidget(secondary_button)

            button_row.addStretch()
            empty_layout.addLayout(button_row)

        layout.addWidget(empty, 0, 0, 1, 5)
    
    def _show_smart_playlist(self, playlist_type: str):
        """Show a smart playlist."""
        if playlist_type == "recent":
            tracks = self.db.get_recently_added(100)
            title = "Recently Added"
            subtitle = "The newest music added to your library."
        elif playlist_type == "most_played":
            tracks = self.db.get_most_played(100)
            title = "Most Played"
            subtitle = "Your most-listened tracks."
        elif playlist_type == "never_played":
            tracks = self.db.get_never_played(100)
            title = "Never Played"
            subtitle = "Tracks you have not played yet."
        elif playlist_type == "starred":
            tracks = self.db.get_starred_tracks()
            title = "★ Starred"
            subtitle = "Tracks you marked for quick access."
        elif playlist_type == "history":
            tracks = self.db.get_play_history()
            title = "History"
            subtitle = "Meaningfully played tracks in exact playback order."
        else:
            return
        
        self._set_view_context("smart_playlist", {"playlist_type": playlist_type})
        self.current_tracks = tracks
        self._set_content_header("Smart Playlist", title, f"{len(tracks)} tracks. {subtitle}")
        self.tracks_view.set_tracks(tracks)
        self.content_stack.setCurrentWidget(self.tracks_view)
        self._update_sidebar_selection(f"smart_{playlist_type}")

    def _clear_play_history(self):
        """Clear play history for a user-selected period."""
        options = ["1 day", "1 week", "1 month", "3 months", "6 months", "1 year", "All"]
        period, ok = QInputDialog.getItem(
            self,
            "Clear History",
            "Delete history from:",
            options,
            0,
            False,
        )
        if not ok:
            return

        normalized_period = period.lower()
        removed = self.db.clear_play_history(normalized_period)
        if self.current_view == "smart_playlist" and self.current_view_data.get("playlist_type") == "history":
            self._show_smart_playlist("history")
        QMessageBox.information(self, "History Cleared", f"Deleted {removed} history entr{'y' if removed == 1 else 'ies'}.")
    
    def _on_album_clicked(self, album_info: dict):
        """Handle album card click - show album detail."""
        album = album_info.get('album')
        artist = album_info.get('artist')
        self._set_view_context("album", {"album": album, "artist": artist})
        
        # Load album tracks
        tracks = self.db.get_album_tracks(album, artist)
        self.current_tracks = tracks
        
        # Update header
        self._set_content_header("Album", album or "Unknown Album", artist or "Unknown Artist")
        self.album_title_label.setText(album or "Unknown Album")
        self.album_artist_label.setText(artist or "Unknown Artist")
        
        year = album_info.get('year', '')
        track_count = len(tracks)
        total_duration = sum(t.get('duration', 0) or 0 for t in tracks)
        self.album_meta_label.setText(
            f"{year} • {track_count} tracks • {format_duration(total_duration)}"
        )
        self.album_summary_label.setText(
            "Press play to hear the full album in order, or double-click any track to start from there."
        )
        
        # Load cover art
        cover_path = album_info.get('cover_art_path')
        if cover_path and os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            self.album_cover.setPixmap(pixmap.scaled(200, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        else:
            self.album_cover.setText("♪")
            self.album_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Load tracks
        self.album_tracks_view.set_tracks(tracks)
        
        self.content_stack.setCurrentWidget(self.album_detail)
    
    def _on_artist_selected(self, item):
        """Handle artist selection."""
        artist = item.text()
        self._set_view_context("artist_albums", {"artist": artist})
        albums = self.db.get_albums(artist)
        self._set_content_header("Artist", artist, f"{len(albums)} album{'s' if len(albums) != 1 else ''} in your library.")
        
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
        self._set_view_context("genre", {"genre": genre})
        tracks = self.db.get_tracks_by_genre(genre)
        self.current_tracks = tracks
        self._set_content_header("Genre", genre, f"{len(tracks)} matching track{'s' if len(tracks) != 1 else ''}.")
        self.tracks_view.set_tracks(tracks)
        self.content_stack.setCurrentWidget(self.tracks_view)
    
    def _on_search(self, text: str):
        """Handle search input."""
        self.clear_search_btn.setVisible(bool(text))
        if not text:
            fallback_view = self.current_view_data.get("previous_view", "albums") if self.current_view == "search" else self.current_view
            self._show_view(fallback_view if fallback_view in ['albums', 'tracks', 'artists', 'genres'] else 'albums')
            return
        
        previous_view = self.current_view if self.current_view != "search" else self.current_view_data.get("previous_view", "albums")
        self._set_view_context("search", {"query": text, "previous_view": previous_view})
        tracks = self.db.search_tracks(text)
        self.current_tracks = tracks
        artist_count = len({t.get('artist') for t in tracks if t.get('artist')})
        album_count = len({(t.get('album'), t.get('artist')) for t in tracks if t.get('album')})
        if tracks:
            subtitle = f"{len(tracks)} track{'s' if len(tracks) != 1 else ''} across {artist_count} artist{'s' if artist_count != 1 else ''} and {album_count} album{'s' if album_count != 1 else ''}."
        else:
            subtitle = "No tracks, artists, or albums matched your search."
        self._set_content_header("Search", f"Results for “{text}”", subtitle)
        self.tracks_view.set_tracks(tracks)
        self.content_stack.setCurrentWidget(self.tracks_view)

    def _clear_search(self):
        """Clear the active search query and return to the current view."""
        self.search_edit.clear()
        self.search_edit.clearFocus()

    def _refresh_up_next(self):
        """Refresh the visible Up Next list from the current playback queue."""
        self.queue_list.clear()
        up_next = self.audio_engine.get_up_next()

        if not up_next:
            self.queue_list.addItem("Nothing queued after the current track.")
            self.queue_list.setEnabled(False)
            self.clear_queue_btn.setEnabled(False)
            return

        for track in up_next:
            item = QListWidgetItem(f"{track.get('title', 'Unknown')} - {track.get('artist', 'Unknown Artist')}")
            item.setData(Qt.ItemDataRole.UserRole, track)
            self.queue_list.addItem(item)

        self.queue_list.setEnabled(True)
        self.clear_queue_btn.setEnabled(True)

    def _clear_up_next(self):
        """Remove all tracks after the current one from the queue."""
        self.audio_engine.clear_up_next()
        self._refresh_up_next()

    def _on_up_next_selected(self, item):
        """Jump to a queued track from the Up Next list."""
        track = item.data(Qt.ItemDataRole.UserRole)
        if not track:
            return

        playlist = self.audio_engine.get_playlist()
        target_index = next((i for i, t in enumerate(playlist) if t.get('id') == track.get('id')), -1)
        if target_index >= 0:
            self.audio_engine.play_index(target_index)

    def _on_play_next_requested(self, tracks: list):
        """Insert tracks immediately after the current one."""
        if not tracks:
            return

        for track in reversed(tracks):
            self.audio_engine.play_next(track)
        self._refresh_up_next()
        QMessageBox.information(self, "Queued Next", f"{len(tracks)} track(s) will play next.")

    def _on_add_to_queue_requested(self, tracks: list):
        """Append tracks to the end of the queue."""
        if not tracks:
            return

        for track in tracks:
            self.audio_engine.add_to_queue(track)
        self._refresh_up_next()
        QMessageBox.information(self, "Added to Queue", f"{len(tracks)} track(s) were added to Up Next.")
    
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
        if ok:
            name = name.strip()
            if not name:
                QMessageBox.information(self, "Playlist Name Needed", "Enter a name for the new playlist.")
                return
            playlist_id = self.db.create_playlist(name)
            if playlist_id:
                self._refresh_playlists()
                QMessageBox.information(self, "Playlist Created", f"Created playlist “{name}”.")
            else:
                QMessageBox.warning(self, "Could Not Create Playlist", "The playlist could not be created.")
    
    def _on_playlist_selected(self, item):
        """Handle playlist double-click."""
        pl = item.data(Qt.ItemDataRole.UserRole)
        if pl:
            self._set_view_context("playlist", {"playlist_id": pl['id']})
            tracks = self.db.get_playlist_tracks(pl['id'])
            self.current_tracks = tracks
            self._set_content_header("Playlist", pl['name'], f"{len(tracks)} track{'s' if len(tracks) != 1 else ''} in this playlist.")
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
            name = name.strip()
            if not name:
                QMessageBox.information(self, "Playlist Name Needed", "Enter a new name for the playlist.")
                return
            if self.db.rename_playlist(playlist['id'], name):
                self._refresh_playlists()
                QMessageBox.information(self, "Playlist Renamed", f"Renamed playlist to “{name}”.")
            else:
                QMessageBox.warning(self, "Could Not Rename Playlist", "The playlist could not be renamed.")
    
    def _delete_playlist(self, playlist: dict):
        """Delete a playlist."""
        reply = QMessageBox.question(
            self, "Delete Playlist",
            f"Delete playlist '{playlist.get('name', '')}'?\n\n"
            "The tracks will not be deleted from your library.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.db.delete_playlist(playlist['id']):
                self._refresh_playlists()
                QMessageBox.information(self, "Playlist Deleted", f"Deleted playlist “{playlist.get('name', '')}”.")
            else:
                QMessageBox.warning(self, "Could Not Delete Playlist", "The playlist could not be deleted.")
    
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
        self._refresh_up_next()
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
        self._refresh_up_next()
        self.player_controls.update_track_info(track)
        self.player_controls.update_play_state(True)
        self._current_playing_id = track.get('id')
    
    def _play_current_album(self):
        """Play all tracks in current album view."""
        playlist = self.album_tracks_view.get_all_tracks_in_order()
        if playlist:
            self.current_tracks = playlist
            self.audio_engine.set_playlist(playlist, 0)
            self._refresh_up_next()
            self.player_controls.update_track_info(playlist[0])
            self.player_controls.update_play_state(True)
            self._current_playing_id = playlist[0].get('id')
    
    def _toggle_play(self):
        """Toggle play/pause."""
        # If no track is currently loaded, start playing the first track from current view
        if not self.audio_engine.get_current_track():
            if self.current_tracks:
                self.audio_engine.set_playlist(self.current_tracks, 0)
                self._refresh_up_next()
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
                    self._refresh_up_next()
                    self.player_controls.update_track_info(tracks[0])
                    self.player_controls.update_play_state(True)
                    self._current_playing_id = tracks[0].get('id')
                    return

        self._ensure_playback_queue_for_current_track()
        
        # Toggle play/pause if a track is loaded
        self.audio_engine.toggle_play_pause()
        self.player_controls.update_play_state(self.audio_engine.is_playing)
    
    def _next_track(self):
        """Play next track."""
        self._ensure_playback_queue_for_current_track()
        self.audio_engine.next()
        # Update UI after track change
        track = self.audio_engine.get_current_track()
        if track:
            self.player_controls.update_track_info(track)
            self.player_controls.update_play_state(True)
            self._current_playing_id = track.get('id')
            self._highlight_playing_track()
            self._refresh_up_next()
    
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
        self._refresh_up_next()
    
    def _toggle_repeat(self):
        """Cycle repeat mode."""
        mode = self.audio_engine.cycle_repeat_mode()
        self.player_controls.update_repeat_state(mode)
        self._refresh_up_next()
    
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
            self._maybe_record_play_count(position, duration)
    
    def _on_engine_track_change(self, track: dict, index: int):
        """Handle track change from audio engine."""
        self.player_controls.update_track_info(track)
        self.player_controls.update_play_state(self.audio_engine.is_playing)
        self._play_counted_for_current_track = False
        
        if track.get('id'):
            self._current_playing_id = track.get('id')
            self._highlight_playing_track()
            self._refresh_up_next()
    
    def _highlight_playing_track(self):
        """Highlight the currently playing track in track lists."""
        for track_list in [self.tracks_view, self.album_tracks_view]:
            track_list.set_playing_track(self._current_playing_id)
            if not self._current_playing_id:
                continue
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
        self._play_counted_for_current_track = False
        self._refresh_up_next()

    def _on_playback_error(self, message: str):
        """Show playback errors to the user."""
        self.player_controls.update_play_state(False)
        QMessageBox.warning(self, "Playback Error", message)

    def _maybe_record_play_count(self, position: float, duration: float):
        """Only count a play after the track has been meaningfully listened to."""
        if self._play_counted_for_current_track or self._restoring_session:
            return

        track = self.audio_engine.get_current_track()
        if not track or not track.get('id') or not self.audio_engine.is_playing:
            return

        if has_meaningful_playback(position, duration):
            self.db.update_play_count(track['id'])
            self._play_counted_for_current_track = True
            if self.current_view == "smart_playlist" and self.current_view_data.get("playlist_type") == "history":
                self._show_smart_playlist("history")

    def _ensure_playback_queue_for_current_track(self):
        """Expand a single-track restored session into a usable queue when possible."""
        current_track = self.audio_engine.get_current_track()
        if not current_track:
            return

        playlist = self.audio_engine.get_playlist()
        if len(playlist) > 1:
            return

        preferred_tracks = self.current_tracks if len(self.current_tracks) > 1 else []
        library_tracks = self.db.get_all_tracks() if not preferred_tracks else []
        restored_playlist, restored_index = resolve_playback_queue(
            current_track.get('id'),
            preferred_tracks,
            library_tracks,
        )

        if restored_index < 0 or len(restored_playlist) <= 1:
            return

        current_position = self.audio_engine.get_position() or 0
        was_playing = self.audio_engine.is_playing

        self.current_tracks = restored_playlist
        self.audio_engine.set_playlist_state(restored_playlist, restored_index, autoplay=was_playing)
        if current_position:
            self.audio_engine.seek(current_position)
        self._refresh_up_next()
    
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
        if self.current_view == "smart_playlist":
            playlist_type = self.current_view_data.get("playlist_type")
            if playlist_type:
                self._show_smart_playlist(playlist_type)
            return

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

        theme = APP_THEMES.get(theme_name, APP_THEMES[DEFAULT_THEME])
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
        progress.canceled.connect(self.scan_worker.cancel)
        self.scan_worker.progress.connect(lambda p, f: progress.setLabelText(f"Scanning: {f}"))
        self.scan_worker.finished.connect(
            lambda tracks: self._on_scan_finished(tracks, progress, self.scan_worker._cancelled)
        )
        self.scan_worker.error.connect(lambda e: self._on_scan_error(e, progress))
        self.scan_worker.start()
    
    def _on_scan_finished(self, tracks: List[dict], progress: QProgressDialog, cancelled: bool = False):
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
            self,
            "Scan Cancelled" if cancelled else "Scan Complete",
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

    def _restore_view_context(self, view: str, view_data: dict):
        """Restore the screen context the user was last in."""
        if view in ['albums', 'tracks', 'artists', 'genres']:
            self._show_view(view)
            return

        if view == "smart_playlist":
            playlist_type = view_data.get("playlist_type")
            if playlist_type:
                self._show_smart_playlist(playlist_type)
                return

        if view == "playlist":
            playlist_id = view_data.get("playlist_id")
            if playlist_id:
                playlists = self.db.get_playlists()
                playlist = next((pl for pl in playlists if pl.get('id') == playlist_id), None)
                if playlist:
                    item = QListWidgetItem(playlist['name'])
                    item.setData(Qt.ItemDataRole.UserRole, playlist)
                    self._on_playlist_selected(item)
                    return

        if view == "album":
            album = view_data.get("album")
            artist = view_data.get("artist")
            if album is not None:
                self._on_album_clicked({"album": album, "artist": artist})
                return

        if view == "artist_albums":
            artist = view_data.get("artist")
            if artist:
                self._on_artist_selected(QListWidgetItem(artist))
                return

        if view == "genre":
            genre = view_data.get("genre")
            if genre:
                self._on_genre_selected(QListWidgetItem(genre))
                return

        if view == "search":
            query = view_data.get("query", "")
            if query:
                self.search_edit.setText(query)
                return

        self._show_view("albums")
    
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
            raw_view_data = state.get('current_view_data')
            try:
                saved_view_data = json.loads(raw_view_data) if raw_view_data else {}
            except json.JSONDecodeError:
                saved_view_data = {}
            self._restore_view_context(saved_view, saved_view_data)
            
            # Restore track - load it into the engine so pressing play resumes
            if state.get('current_track_id'):
                track = self.db.get_track(state['current_track_id'])
                saved_position = state.get('position', 0) or 0
                if track:
                    self._restoring_session = True
                    restore_playlist, restore_index = resolve_playback_queue(
                        track.get('id'),
                        self.current_tracks,
                        self.db.get_all_tracks(),
                    )

                    if restore_index >= 0:
                        self.current_tracks = restore_playlist
                        self.audio_engine.set_playlist_state(restore_playlist, restore_index, autoplay=False)
                        if should_restore_playback(saved_position, track.get('duration', 0) or 0):
                            self.audio_engine.seek(saved_position)
                    else:
                        self.current_tracks = [track]
                        self.audio_engine.load_track_for_resume(
                            track,
                            saved_position if should_restore_playback(saved_position, track.get('duration', 0) or 0) else 0,
                        )
                    self.player_controls.update_track_info(track)
                    self.player_controls.update_progress(
                        saved_position if should_restore_playback(saved_position, track.get('duration', 0) or 0) else 0,
                        track.get('duration', 0) or 0,
                    )
                    self.player_controls.update_play_state(False)
                    self._current_playing_id = track.get('id')
                    self._restoring_session = False
                    self._refresh_up_next()
    
    def _save_playback_state(self):
        """Save current playback state."""
        track = self.audio_engine.get_current_track()
        position = self.audio_engine.get_position() or 0
        duration = self.audio_engine.get_duration() or (track.get('duration', 0) if track else 0)
        should_resume = bool(track and should_restore_playback(position, duration or 0))
        
        self.db.save_playback_state(
            track_id=track.get('id') if track else None,
            position=position if should_resume else 0,
            volume=self.audio_engine.get_volume() / 100,
            shuffle=self.audio_engine.get_shuffle(),
            repeat_mode=self.audio_engine.get_repeat_mode().value,
            current_view=self.current_view,
            current_view_data=json.dumps(self.current_view_data) if self.current_view_data else None,
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

    icon_path = Path(__file__).resolve().parent / "Harmony.icns"
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)

        if sys.platform == 'darwin':
            try:
                from AppKit import NSApplication, NSImage
                ns_image = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
                if ns_image:
                    NSApplication.sharedApplication().setApplicationIconImage_(ns_image)
            except Exception:
                pass
    
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
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    
    # Run
    exit_code = app.exec()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
