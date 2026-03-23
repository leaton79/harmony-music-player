"""
Harmony Music Player - A modern, gapless music player for macOS.
Main application and GUI.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import json

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QListWidget, QListWidgetItem,
    QStackedWidget, QLineEdit, QFileDialog, QMessageBox,
    QGridLayout, QScrollArea, QFrame, QSplitter, QMenu,
    QDialog, QFormLayout, QSpinBox, QComboBox, QProgressDialog,
    QSystemTrayIcon, QStyle, QSizePolicy, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QToolButton, QInputDialog
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QUrl, QPoint
)
from PyQt6.QtGui import (
    QPixmap, QIcon, QFont, QAction, QKeySequence, QShortcut,
    QPalette, QColor, QImage, QPainter, QBrush, QLinearGradient
)

from database import MusicDatabase
from metadata import MetadataReader, MetadataWriter, LibraryScanner, SUPPORTED_FORMATS
from audio_engine import create_audio_engine, RepeatMode
from themes import APP_THEMES, DEFAULT_STYLESHEET, DEFAULT_THEME, generate_stylesheet


# =========== Constants ===========

APP_NAME = "Harmony"
APP_VERSION = "1.0.1"
DEFAULT_COVER = None  # Will be set to a default image path


# =========== Utility Functions ===========

def format_duration(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    if seconds is None or seconds < 0:
        return "0:00"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_size(bytes_size: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


# =========== Style Constants ===========

# Default theme (can be changed by user)
CURRENT_THEME = DEFAULT_THEME
DARK_STYLE = DEFAULT_STYLESHEET


# =========== Worker Threads ===========

class LibraryScanWorker(QThread):
    """Background worker for scanning music library."""
    
    progress = pyqtSignal(int, str)  # progress percentage, current file
    finished = pyqtSignal(list)  # list of track metadata
    error = pyqtSignal(str)
    
    def __init__(self, folders: List[str]):
        super().__init__()
        self.folders = folders
        self._cancelled = False
    
    def run(self):
        try:
            scanner = LibraryScanner()
            all_tracks = []
            
            for folder in self.folders:
                if self._cancelled:
                    break
                
                self.progress.emit(0, f"Scanning {folder}...")
                tracks = scanner.scan_directory(
                    folder,
                    should_cancel=lambda: self._cancelled,
                    progress_callback=lambda file_path: self.progress.emit(0, file_path),
                )
                all_tracks.extend(tracks)
                
            self.finished.emit(all_tracks)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def cancel(self):
        self._cancelled = True


# =========== Custom Widgets ===========

class AlbumCard(QFrame):
    """Album art card widget for grid view."""
    
    clicked = pyqtSignal(dict)  # album info
    play_clicked = pyqtSignal(dict)
    
    def __init__(self, album_info: dict, parent=None):
        super().__init__(parent)
        self.album_info = album_info
        self.setObjectName("albumCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(196, 268)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        
        # Album art
        self.art_label = QLabel()
        self.art_label.setFixedSize(168, 168)
        self.art_label.setScaledContents(True)
        self.art_label.setStyleSheet("border-radius: 10px; background-color: #282828;")
        
        # Load cover art
        cover_path = album_info.get('cover_art_path')
        if cover_path and os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            self.art_label.setPixmap(pixmap.scaled(168, 168, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                    Qt.TransformationMode.SmoothTransformation))
        else:
            self.art_label.setText("♪")
            self.art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.art_label.setStyleSheet("""
                border-radius: 10px; 
                background-color: #282828;
                color: #8a8a8a;
                font-size: 44px;
            """)
        
        layout.addWidget(self.art_label)
        
        # Album name
        name_label = QLabel(album_info.get('album', 'Unknown Album'))
        name_label.setFont(QFont("", 12, QFont.Weight.Bold))
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(42)
        layout.addWidget(name_label)
        
        # Artist name
        artist_label = QLabel(album_info.get('artist', 'Unknown Artist'))
        artist_label.setObjectName("secondaryLabel")
        artist_label.setFont(QFont("", 10))
        layout.addWidget(artist_label)

        meta_label = QLabel(f"{album_info.get('track_count', 0)} tracks")
        meta_label.setObjectName("secondaryLabel")
        meta_label.setFont(QFont("", 9))
        layout.addWidget(meta_label)
        
        layout.addStretch()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.album_info)
        super().mousePressEvent(event)


class TrackListWidget(QTableWidget):
    """Track list with columns for track info."""
    
    track_double_clicked = pyqtSignal(int, dict)  # index, track info
    request_edit_metadata = pyqtSignal(dict)  # track info
    request_delete_from_playlist = pyqtSignal(dict)  # track info
    request_delete_from_disk = pyqtSignal(dict)  # track info
    request_toggle_star = pyqtSignal(dict)  # track info
    request_add_to_playlist = pyqtSignal(list)  # list of tracks
    request_play_next = pyqtSignal(list)  # list of tracks
    request_add_to_queue = pyqtSignal(list)  # list of tracks
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels(['#', '★', 'Track', 'Artist', 'Album', 'Genre', 'Plays', 'Length'])
        
        # Configure table
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(False)
        self.setWordWrap(True)
        
        # Enable sorting
        self.setSortingEnabled(True)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Enable drag for adding to playlists
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        
        # Configure columns - allow user resizing
        header = self.horizontalHeader()
        header.setStretchLastSection(True)  # Last column stretches to fill
        header.setSectionsMovable(True)  # Allow reordering columns
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Set all columns to interactive (user can resize)
        for i in range(8):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # Set default widths
        self.setColumnWidth(0, 40)    # #
        self.setColumnWidth(1, 30)    # Star
        self.setColumnWidth(2, 250)   # Title
        self.setColumnWidth(3, 0)     # Artist hidden by default
        self.setColumnWidth(4, 180)   # Album
        self.setColumnWidth(5, 0)     # Genre hidden by default
        self.setColumnWidth(6, 50)    # Plays
        self.setColumnWidth(7, 70)    # Duration
        self.setColumnHidden(3, True)
        self.setColumnHidden(5, True)
        
        self.tracks: List[dict] = []
        self._track_map: Dict[int, dict] = {}  # Map row to track for sorting
        self._playing_track_id = None
        
        # Connect double-click
        self.cellDoubleClicked.connect(self._on_double_click)
    
    def set_tracks(self, tracks: List[dict]):
        """Set tracks to display."""
        self.setSortingEnabled(False)  # Disable while populating
        self.tracks = tracks
        self.setRowCount(len(tracks))
        self._track_map.clear()
        
        for i, track in enumerate(tracks):
            self._track_map[i] = track
            
            # Track number
            num_item = QTableWidgetItem()
            num_item.setData(Qt.ItemDataRole.DisplayRole, track.get('track_number') or i + 1)
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(i, 0, num_item)
            
            # Star
            starred = track.get('starred', False)
            star_item = QTableWidgetItem('★' if starred else '☆')
            star_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            star_item.setData(Qt.ItemDataRole.UserRole, starred)
            self.setItem(i, 1, star_item)
            
            # Title
            title_text = track.get('title', 'Unknown')
            artist_text = track.get('artist', 'Unknown Artist')
            title_item = QTableWidgetItem(f"{title_text}\n{artist_text}")
            title_item.setData(Qt.ItemDataRole.UserRole, track)  # Store track data
            title_item.setToolTip(f"{title_text}\n{artist_text}")
            self.setItem(i, 2, title_item)
            
            # Artist
            artist_item = QTableWidgetItem(track.get('artist', 'Unknown'))
            self.setItem(i, 3, artist_item)
            
            # Album
            album_item = QTableWidgetItem(track.get('album', 'Unknown'))
            self.setItem(i, 4, album_item)
            
            # Genre
            genre_item = QTableWidgetItem(track.get('genre', ''))
            self.setItem(i, 5, genre_item)
            
            # Play count
            play_count = track.get('play_count', 0) or 0
            plays_item = QTableWidgetItem()
            plays_item.setData(Qt.ItemDataRole.DisplayRole, play_count)
            plays_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(i, 6, plays_item)
            
            # Duration - store as number for proper sorting
            duration = track.get('duration', 0) or 0
            duration_item = QTableWidgetItem()
            duration_item.setData(Qt.ItemDataRole.DisplayRole, format_duration(duration))
            duration_item.setData(Qt.ItemDataRole.UserRole, duration)  # For sorting
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(i, 7, duration_item)
            
            self.setRowHeight(i, 54)
        
        self.setSortingEnabled(True)  # Re-enable sorting
        self.set_playing_track(self._playing_track_id)

    def set_playing_track(self, track_id: Optional[int]):
        """Apply stronger styling to the currently playing row."""
        self._playing_track_id = track_id
        palette = self.palette()
        default_text = palette.color(self.foregroundRole())
        secondary_text = palette.color(self.foregroundRole()).darker(120)
        active_bg = QColor("#1f3a2a")
        active_text = QColor("#ffffff")

        for row in range(self.rowCount()):
            title_item = self.item(row, 2)
            if not title_item:
                continue

            track = title_item.data(Qt.ItemDataRole.UserRole)
            is_playing = bool(track and track.get('id') == track_id)

            number_item = self.item(row, 0)
            if number_item:
                display_number = track.get('track_number') or row + 1 if track else row + 1
                number_item.setText("▶" if is_playing else str(display_number))
                font = number_item.font()
                font.setBold(is_playing)
                number_item.setFont(font)

            for column in range(self.columnCount()):
                item = self.item(row, column)
                if not item:
                    continue
                font = item.font()
                font.setBold(is_playing and column in (0, 2, 4))
                item.setFont(font)
                if is_playing:
                    item.setBackground(active_bg)
                    item.setForeground(active_text)
                else:
                    item.setBackground(QColor())
                    if column in (0, 1, 6, 7):
                        item.setForeground(secondary_text)
                    else:
                        item.setForeground(default_text)
    
    def _on_double_click(self, row: int, column: int):
        # If clicking star column, toggle star instead of playing
        if column == 1:
            title_item = self.item(row, 2)
            if title_item:
                track = title_item.data(Qt.ItemDataRole.UserRole)
                if track:
                    self.request_toggle_star.emit(track)
            return
        
        # Get track from the title column's UserRole data
        title_item = self.item(row, 2)
        if title_item:
            track = title_item.data(Qt.ItemDataRole.UserRole)
            if track:
                # Build playlist from current visible order
                playlist = []
                for r in range(self.rowCount()):
                    item = self.item(r, 2)
                    if item:
                        t = item.data(Qt.ItemDataRole.UserRole)
                        if t:
                            playlist.append(t)
                self.track_double_clicked.emit(row, track)
    
    def _show_context_menu(self, position):
        """Show right-click context menu."""
        selected = self.get_selected_tracks()
        if not selected:
            return
        
        menu = QMenu(self)

        play_now_action = menu.addAction("Play Next")
        play_now_action.triggered.connect(lambda: self.request_play_next.emit(selected))

        add_queue_action = menu.addAction("Add to Queue")
        add_queue_action.triggered.connect(lambda: self.request_add_to_queue.emit(selected))
        
        menu.addSeparator()

        # Add to Playlist
        add_playlist_action = menu.addAction("Add to Playlist...")
        add_playlist_action.triggered.connect(lambda: self.request_add_to_playlist.emit(selected))
        
        menu.addSeparator()
        
        # Star/Unstar
        track = selected[0]
        is_starred = track.get('starred', False)
        star_text = "Unstar" if is_starred else "Star"
        star_action = menu.addAction(f"{'★ ' if not is_starred else '☆ '}{star_text}")
        star_action.triggered.connect(lambda: self._toggle_star_selected())
        
        menu.addSeparator()
        
        # Edit Metadata
        edit_action = menu.addAction("Edit Metadata...")
        edit_action.triggered.connect(lambda: self.request_edit_metadata.emit(selected[0]))
        
        menu.addSeparator()
        
        # Delete options
        delete_playlist_action = menu.addAction("Remove from Library")
        delete_playlist_action.triggered.connect(lambda: self._delete_from_playlist_selected())
        
        delete_disk_action = menu.addAction("Delete from Disk...")
        delete_disk_action.triggered.connect(lambda: self._delete_from_disk_selected())
        
        menu.exec(self.mapToGlobal(position))
    
    def _toggle_star_selected(self):
        """Toggle star for selected tracks."""
        for track in self.get_selected_tracks():
            self.request_toggle_star.emit(track)
    
    def _delete_from_playlist_selected(self):
        """Delete selected tracks from library."""
        for track in self.get_selected_tracks():
            self.request_delete_from_playlist.emit(track)
    
    def _delete_from_disk_selected(self):
        """Delete selected tracks from disk."""
        for track in self.get_selected_tracks():
            self.request_delete_from_disk.emit(track)
    
    def get_selected_tracks(self) -> List[dict]:
        """Get currently selected tracks."""
        selected = []
        for row in set(item.row() for item in self.selectedItems()):
            title_item = self.item(row, 2)
            if title_item:
                track = title_item.data(Qt.ItemDataRole.UserRole)
                if track:
                    selected.append(track)
        return selected
    
    def get_all_tracks_in_order(self) -> List[dict]:
        """Get all tracks in current display order (after sorting)."""
        tracks = []
        for row in range(self.rowCount()):
            title_item = self.item(row, 2)
            if title_item:
                track = title_item.data(Qt.ItemDataRole.UserRole)
                if track:
                    tracks.append(track)
        return tracks
    
    def mimeData(self, items):
        """Provide mime data for drag operations."""
        from PyQt6.QtCore import QMimeData
        mime = QMimeData()
        # Get selected tracks and store their IDs
        track_ids = []
        for track in self.get_selected_tracks():
            if track.get('id'):
                track_ids.append(str(track['id']))
        mime.setText(','.join(track_ids))
        mime.setData('application/x-harmony-tracks', ','.join(track_ids).encode())
        return mime


class ClickableSlider(QSlider):
    """Slider that allows clicking to seek to any position."""
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._click_position = None
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Store click position to detect click vs drag
            self._click_position = event.position().x()
            # Immediately jump to clicked position
            value = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(), 
                int(event.position().x()), self.width()
            )
            self.setValue(value)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._click_position is not None:
            # Check if it was a click (minimal movement) vs drag
            if abs(event.position().x() - self._click_position) < 5:
                # It's a click - emit sliderMoved to trigger seek
                value = self.value()
                self.sliderMoved.emit(value)
            self._click_position = None
        super().mouseReleaseEvent(event)


class PlayerControls(QWidget):
    """Playback control widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 8)
        layout.setSpacing(8)
        
        # Track info row
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)
        
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(64, 64)
        self.cover_label.setScaledContents(True)
        self.cover_label.setStyleSheet("border-radius: 10px; background-color: #282828;")
        info_layout.addWidget(self.cover_label)
        
        info_text_layout = QVBoxLayout()
        info_text_layout.setSpacing(3)
        
        self.title_label = QLabel("No track playing")
        self.title_label.setFont(QFont("", 13, QFont.Weight.Bold))
        info_text_layout.addWidget(self.title_label)
        
        self.artist_label = QLabel("")
        self.artist_label.setObjectName("secondaryLabel")
        info_text_layout.addWidget(self.artist_label)
        
        info_layout.addLayout(info_text_layout)
        info_layout.addStretch()
        
        # Playback controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        self.shuffle_btn = QPushButton("Mix")
        self.shuffle_btn.setObjectName("pillButton")
        self.shuffle_btn.setFixedHeight(28)
        self.shuffle_btn.setToolTip("Shuffle: OFF")
        controls_layout.addWidget(self.shuffle_btn)
        
        self.prev_btn = QPushButton()
        self.prev_btn.setObjectName("transportButton")
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.prev_btn.setIconSize(QSize(18, 18))
        self.prev_btn.setToolTip("Previous")
        controls_layout.addWidget(self.prev_btn)
        
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("playButton")
        self.play_btn.setFixedSize(44, 44)
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_btn.setIconSize(QSize(20, 20))
        self.play_btn.setToolTip("Play/Pause")
        controls_layout.addWidget(self.play_btn)
        
        self.next_btn = QPushButton()
        self.next_btn.setObjectName("transportButton")
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self.next_btn.setIconSize(QSize(18, 18))
        self.next_btn.setToolTip("Next")
        controls_layout.addWidget(self.next_btn)
        
        self.repeat_btn = QPushButton("Loop")
        self.repeat_btn.setObjectName("pillButton")
        self.repeat_btn.setFixedHeight(28)
        self.repeat_btn.setToolTip("Repeat: OFF")
        controls_layout.addWidget(self.repeat_btn)
        
        info_layout.addLayout(controls_layout)
        info_layout.addStretch()
        
        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(8)
        
        self.volume_btn = QPushButton()
        self.volume_btn.setObjectName("transportButton")
        self.volume_btn.setFixedSize(32, 32)
        self.volume_btn.setEnabled(False)
        volume_layout.addWidget(self.volume_btn)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(112)
        volume_layout.addWidget(self.volume_slider)
        
        info_layout.addLayout(volume_layout)
        
        layout.addLayout(info_layout)
        
        # Progress bar row
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(8)
        
        self.time_label = QLabel("0:00")
        self.time_label.setFixedWidth(50)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.time_label.setObjectName("secondaryLabel")
        progress_layout.addWidget(self.time_label)
        
        self.progress_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        progress_layout.addWidget(self.progress_slider)
        
        self.duration_label = QLabel("0:00")
        self.duration_label.setFixedWidth(50)
        self.duration_label.setObjectName("secondaryLabel")
        progress_layout.addWidget(self.duration_label)
        
        layout.addLayout(progress_layout)
        
        # Initialize button states
        self._shuffle_on = False
        self._repeat_mode = RepeatMode.OFF
        self.update_volume_icon(100)
        self._update_shuffle_style()
        self._update_repeat_style()
    
    def update_track_info(self, track: Optional[dict]):
        """Update displayed track info."""
        if track:
            self.title_label.setText(track.get('title', 'Unknown'))
            self.artist_label.setText(track.get('artist', 'Unknown Artist'))
            
            cover_path = track.get('cover_art_path')
            if cover_path and os.path.exists(cover_path):
                pixmap = QPixmap(cover_path)
                self.cover_label.setPixmap(pixmap.scaled(64, 64, 
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation))
            else:
                self.cover_label.setText("♪")
                self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.cover_label.setStyleSheet("border-radius: 10px; background-color: #282828; color: #8a8a8a; font-size: 22px;")
        else:
            self.title_label.setText("No track playing")
            self.artist_label.setText("")
            self.cover_label.setText("♪")
            self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cover_label.setStyleSheet("border-radius: 10px; background-color: #282828; color: #8a8a8a; font-size: 22px;")
    
    def update_play_state(self, is_playing: bool):
        """Update play button state."""
        icon = QStyle.StandardPixmap.SP_MediaPause if is_playing else QStyle.StandardPixmap.SP_MediaPlay
        self.play_btn.setIcon(self.style().standardIcon(icon))
    
    def update_progress(self, position: float, duration: float):
        """Update progress bar and time labels."""
        self.time_label.setText(format_duration(position))
        self.duration_label.setText(format_duration(duration))
        
        if duration > 0:
            progress = int((position / duration) * 1000)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(progress)
            self.progress_slider.blockSignals(False)
    
    def _update_shuffle_style(self):
        """Update shuffle button style based on state."""
        if self._shuffle_on:
            self.shuffle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1db954;
                    color: white;
                    border-radius: 14px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #1ed760;
                }
            """)
            self.shuffle_btn.setText("Mix On")
            self.shuffle_btn.setToolTip("Shuffle: ON")
        else:
            self.shuffle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #404040;
                    color: #888888;
                    border-radius: 14px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
            """)
            self.shuffle_btn.setText("Mix")
            self.shuffle_btn.setToolTip("Shuffle: OFF")
    
    def _update_repeat_style(self):
        """Update repeat button style based on mode."""
        if self._repeat_mode == RepeatMode.OFF:
            self.repeat_btn.setText("Loop")
            self.repeat_btn.setStyleSheet("""
                QPushButton {
                    background-color: #404040;
                    color: #888888;
                    border-radius: 14px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
            """)
            self.repeat_btn.setToolTip("Repeat: OFF")
        elif self._repeat_mode == RepeatMode.ALL:
            self.repeat_btn.setText("Loop On")
            self.repeat_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1db954;
                    color: white;
                    border-radius: 14px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #1ed760;
                }
            """)
            self.repeat_btn.setToolTip("Repeat: ALL")
        else:  # ONE
            self.repeat_btn.setText("Loop 1")
            self.repeat_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff9800;
                    color: white;
                    border-radius: 14px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #ffb74d;
                }
            """)
            self.repeat_btn.setToolTip("Repeat: ONE")

    def update_volume_icon(self, volume: int):
        """Update volume icon to match loudness."""
        if volume <= 0:
            icon = QStyle.StandardPixmap.SP_MediaVolumeMuted
        else:
            icon = QStyle.StandardPixmap.SP_MediaVolume
        self.volume_btn.setIcon(self.style().standardIcon(icon))
        self.volume_btn.setIconSize(QSize(16, 16))
    
    def update_shuffle_state(self, enabled: bool):
        """Update shuffle button appearance."""
        self._shuffle_on = enabled
        self._update_shuffle_style()
    
    def update_repeat_state(self, mode: RepeatMode):
        """Update repeat button appearance."""
        self._repeat_mode = mode
        self._update_repeat_style()


# =========== Dialogs ===========

class MetadataEditDialog(QDialog):
    """Dialog for editing track metadata."""
    
    def __init__(self, track: dict, parent=None):
        super().__init__(parent)
        self.track = track
        self.setWindowTitle("Edit Metadata")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.title_edit = QLineEdit(track.get('title', ''))
        form_layout.addRow("Title:", self.title_edit)
        
        self.artist_edit = QLineEdit(track.get('artist', ''))
        form_layout.addRow("Artist:", self.artist_edit)
        
        self.album_edit = QLineEdit(track.get('album', ''))
        form_layout.addRow("Album:", self.album_edit)
        
        self.album_artist_edit = QLineEdit(track.get('album_artist', ''))
        form_layout.addRow("Album Artist:", self.album_artist_edit)
        
        self.genre_edit = QLineEdit(track.get('genre', ''))
        form_layout.addRow("Genre:", self.genre_edit)
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, 2100)
        self.year_spin.setValue(track.get('year') or 2024)
        form_layout.addRow("Year:", self.year_spin)
        
        self.track_spin = QSpinBox()
        self.track_spin.setRange(0, 999)
        self.track_spin.setValue(track.get('track_number') or 0)
        form_layout.addRow("Track #:", self.track_spin)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def get_metadata(self) -> dict:
        """Get edited metadata."""
        return {
            'title': self.title_edit.text(),
            'artist': self.artist_edit.text(),
            'album': self.album_edit.text(),
            'album_artist': self.album_artist_edit.text(),
            'genre': self.genre_edit.text(),
            'year': self.year_spin.value() if self.year_spin.value() > 0 else None,
            'track_number': self.track_spin.value() if self.track_spin.value() > 0 else None,
        }


class DuplicatesDialog(QDialog):
    """Dialog for managing duplicate tracks."""
    
    def __init__(self, duplicates: List[List[dict]], parent=None):
        super().__init__(parent)
        self.duplicates = duplicates
        self.setWindowTitle("Duplicate Tracks")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        
        info_label = QLabel(f"Found {len(duplicates)} groups of duplicate tracks:")
        layout.addWidget(info_label)
        
        self.list_widget = QListWidget()
        
        for i, group in enumerate(duplicates):
            header = QListWidgetItem(f"--- Group {i + 1} ---")
            header.setFlags(header.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            header.setBackground(QColor("#282828"))
            self.list_widget.addItem(header)
            
            for track in group:
                item = QListWidgetItem(
                    f"  {track.get('title', 'Unknown')} - {track.get('artist', 'Unknown')}\n"
                    f"    {track.get('file_path', '')}"
                )
                item.setData(Qt.ItemDataRole.UserRole, track)
                self.list_widget.addItem(item)
        
        layout.addWidget(self.list_widget)
        
        button_layout = QHBoxLayout()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)


class FolderManagerDialog(QDialog):
    """Dialog for managing music folders."""
    
    def __init__(self, db: MusicDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Manage Music Folders")
        self.setMinimumSize(500, 300)
        
        layout = QVBoxLayout(self)
        
        self.folder_list = QListWidget()
        self._refresh_folders()
        layout.addWidget(self.folder_list)
        
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Folder")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._add_folder)
        button_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_folder)
        button_layout.addWidget(remove_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _refresh_folders(self):
        self.folder_list.clear()
        folders = self.db.get_music_folders()
        for folder in folders:
            self.folder_list.addItem(folder['folder_path'])
    
    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if folder:
            self.db.add_music_folder(folder)
            self._refresh_folders()
    
    def _remove_folder(self):
        current = self.folder_list.currentItem()
        if current:
            self.db.remove_music_folder(current.text())
            self._refresh_folders()


class PlaylistDialog(QDialog):
    """Dialog for creating/managing playlists."""
    
    def __init__(self, db: MusicDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Playlists")
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        self.playlist_list = QListWidget()
        self._refresh_playlists()
        layout.addWidget(self.playlist_list)
        
        button_layout = QHBoxLayout()
        
        new_btn = QPushButton("New Playlist")
        new_btn.setObjectName("primaryButton")
        new_btn.clicked.connect(self._create_playlist)
        button_layout.addWidget(new_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_playlist)
        button_layout.addWidget(delete_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _refresh_playlists(self):
        self.playlist_list.clear()
        playlists = self.db.get_playlists()
        for pl in playlists:
            item = QListWidgetItem(pl['name'])
            item.setData(Qt.ItemDataRole.UserRole, pl)
            self.playlist_list.addItem(item)
    
    def _create_playlist(self):
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name:
            self.db.create_playlist(name)
            self._refresh_playlists()
    
    def _delete_playlist(self):
        current = self.playlist_list.currentItem()
        if current:
            pl = current.data(Qt.ItemDataRole.UserRole)
            if pl:
                self.db.delete_playlist(pl['id'])
                self._refresh_playlists()
