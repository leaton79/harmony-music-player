"""
Database module for music library management.
Handles SQLite storage, smart playlists, and duplicate detection.
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import hashlib


class MusicDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            app_data = Path.home() / ".harmony_player"
            app_data.mkdir(exist_ok=True)
            db_path = str(app_data / "library.db")
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database tables."""
        cursor = self.conn.cursor()
        
        # Main tracks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT,
                title TEXT,
                artist TEXT,
                album TEXT,
                album_artist TEXT,
                genre TEXT,
                year INTEGER,
                track_number INTEGER,
                disc_number INTEGER,
                duration REAL,
                bitrate INTEGER,
                sample_rate INTEGER,
                file_format TEXT,
                file_size INTEGER,
                cover_art_path TEXT,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_modified TIMESTAMP,
                play_count INTEGER DEFAULT 0,
                last_played TIMESTAMP,
                rating INTEGER DEFAULT 0,
                starred INTEGER DEFAULT 0
            )
        ''')
        
        # Add starred column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE tracks ADD COLUMN starred INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Music folders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS music_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_path TEXT UNIQUE NOT NULL,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_scanned TIMESTAMP
            )
        ''')
        
        # Playlists table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_smart INTEGER DEFAULT 0,
                smart_rules TEXT,
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_modified TIMESTAMP
            )
        ''')
        
        # Playlist tracks junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                track_id INTEGER NOT NULL,
                position INTEGER,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
            )
        ''')
        
        # Playback state table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playback_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_track_id INTEGER,
                position REAL DEFAULT 0,
                volume REAL DEFAULT 1.0,
                shuffle INTEGER DEFAULT 0,
                repeat_mode INTEGER DEFAULT 0,
                FOREIGN KEY (current_track_id) REFERENCES tracks(id)
            )
        ''')
        
        # Initialize playback state if not exists
        cursor.execute('''
            INSERT OR IGNORE INTO playback_state (id) VALUES (1)
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_genre ON tracks(genre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_hash ON tracks(file_hash)')
        
        self.conn.commit()
    
    # =========== Music Folders ===========
    
    def add_music_folder(self, folder_path: str) -> bool:
        """Add a music folder to scan."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT OR IGNORE INTO music_folders (folder_path) VALUES (?)',
                (folder_path,)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def remove_music_folder(self, folder_path: str) -> bool:
        """Remove a music folder and optionally its tracks."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM music_folders WHERE folder_path = ?', (folder_path,))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def get_music_folders(self) -> List[Dict]:
        """Get all configured music folders."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM music_folders ORDER BY folder_path')
        return [dict(row) for row in cursor.fetchall()]
    
    def update_folder_scan_time(self, folder_path: str):
        """Update the last scanned timestamp for a folder."""
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE music_folders SET last_scanned = ? WHERE folder_path = ?',
            (datetime.now(), folder_path)
        )
        self.conn.commit()
    
    # =========== Tracks ===========
    
    def add_track(self, track_data: Dict) -> Optional[int]:
        """Add or update a track in the library."""
        try:
            cursor = self.conn.cursor()
            
            # Check if track already exists
            cursor.execute('SELECT id FROM tracks WHERE file_path = ?', (track_data['file_path'],))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing track
                track_data['date_modified'] = datetime.now()
                set_clause = ', '.join(f'{k} = ?' for k in track_data.keys() if k != 'file_path')
                values = [v for k, v in track_data.items() if k != 'file_path']
                values.append(track_data['file_path'])
                
                cursor.execute(
                    f'UPDATE tracks SET {set_clause} WHERE file_path = ?',
                    values
                )
                self.conn.commit()
                return existing['id']
            else:
                # Insert new track
                columns = ', '.join(track_data.keys())
                placeholders = ', '.join('?' * len(track_data))
                cursor.execute(
                    f'INSERT INTO tracks ({columns}) VALUES ({placeholders})',
                    list(track_data.values())
                )
                self.conn.commit()
                return cursor.lastrowid
                
        except sqlite3.Error as e:
            print(f"Database error adding track: {e}")
            return None
    
    def get_track(self, track_id: int) -> Optional[Dict]:
        """Get a track by ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tracks WHERE id = ?', (track_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_track_by_path(self, file_path: str) -> Optional[Dict]:
        """Get a track by file path."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tracks WHERE file_path = ?', (file_path,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_tracks(self, order_by: str = 'artist, album, track_number') -> List[Dict]:
        """Get all tracks in the library."""
        cursor = self.conn.cursor()
        cursor.execute(f'SELECT * FROM tracks ORDER BY {order_by}')
        return [dict(row) for row in cursor.fetchall()]
    
    def search_tracks(self, query: str) -> List[Dict]:
        """Search tracks by title, artist, or album."""
        cursor = self.conn.cursor()
        search_term = f'%{query}%'
        cursor.execute('''
            SELECT * FROM tracks 
            WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
            ORDER BY artist, album, track_number
        ''', (search_term, search_term, search_term))
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_track(self, track_id: int) -> bool:
        """Delete a track from the library."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM tracks WHERE id = ?', (track_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def delete_missing_tracks(self) -> int:
        """Remove tracks whose files no longer exist."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, file_path FROM tracks')
        tracks = cursor.fetchall()
        
        deleted = 0
        for track in tracks:
            if not os.path.exists(track['file_path']):
                cursor.execute('DELETE FROM tracks WHERE id = ?', (track['id'],))
                deleted += 1
        
        self.conn.commit()
        return deleted
    
    def update_play_count(self, track_id: int):
        """Increment play count and update last played time."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE tracks 
            SET play_count = play_count + 1, last_played = ?
            WHERE id = ?
        ''', (datetime.now(), track_id))
        self.conn.commit()
    
    def update_track_metadata(self, track_id: int, metadata: Dict) -> bool:
        """Update track metadata."""
        try:
            cursor = self.conn.cursor()
            metadata['date_modified'] = datetime.now()
            set_clause = ', '.join(f'{k} = ?' for k in metadata.keys())
            values = list(metadata.values()) + [track_id]
            cursor.execute(f'UPDATE tracks SET {set_clause} WHERE id = ?', values)
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def toggle_star(self, track_id: int) -> bool:
        """Toggle starred status for a track. Returns new starred state."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT starred FROM tracks WHERE id = ?', (track_id,))
            row = cursor.fetchone()
            if row:
                new_state = 0 if row['starred'] else 1
                cursor.execute('UPDATE tracks SET starred = ? WHERE id = ?', (new_state, track_id))
                self.conn.commit()
                return bool(new_state)
            return False
        except sqlite3.Error:
            return False
    
    def set_star(self, track_id: int, starred: bool) -> bool:
        """Set starred status for a track."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('UPDATE tracks SET starred = ? WHERE id = ?', (1 if starred else 0, track_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def get_starred_tracks(self, limit: int = None) -> List[Dict]:
        """Get all starred tracks."""
        cursor = self.conn.cursor()
        query = 'SELECT * FROM tracks WHERE starred = 1 ORDER BY artist, album, track_number'
        if limit:
            query += f' LIMIT {limit}'
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_track_from_disk(self, track_id: int) -> Tuple[bool, str]:
        """Delete a track from disk and library. Returns (success, message)."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT file_path FROM tracks WHERE id = ?', (track_id,))
            row = cursor.fetchone()
            if not row:
                return False, "Track not found"
            
            file_path = row['file_path']
            
            # Delete from library first
            cursor.execute('DELETE FROM tracks WHERE id = ?', (track_id,))
            self.conn.commit()
            
            # Delete file from disk
            if os.path.exists(file_path):
                os.remove(file_path)
                return True, f"Deleted: {file_path}"
            else:
                return True, "Track removed from library (file was already missing)"
                
        except OSError as e:
            return False, f"Could not delete file: {e}"
        except sqlite3.Error as e:
            return False, f"Database error: {e}"
        except sqlite3.Error:
            return False
    
    # =========== Browse Library ===========
    
    def get_artists(self) -> List[str]:
        """Get list of all artists."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT artist FROM tracks 
            WHERE artist IS NOT NULL AND artist != ''
            ORDER BY artist
        ''')
        return [row['artist'] for row in cursor.fetchall()]
    
    def get_albums(self, artist: str = None) -> List[Dict]:
        """Get albums, optionally filtered by artist."""
        cursor = self.conn.cursor()
        if artist:
            cursor.execute('''
                SELECT DISTINCT album, album_artist, artist, year, 
                       MIN(cover_art_path) as cover_art_path,
                       COUNT(*) as track_count
                FROM tracks 
                WHERE (artist = ? OR album_artist = ?) AND album IS NOT NULL
                GROUP BY album
                ORDER BY year, album
            ''', (artist, artist))
        else:
            cursor.execute('''
                SELECT DISTINCT album, album_artist, 
                       MIN(artist) as artist, year,
                       MIN(cover_art_path) as cover_art_path,
                       COUNT(*) as track_count
                FROM tracks 
                WHERE album IS NOT NULL AND album != ''
                GROUP BY album
                ORDER BY album
            ''')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_album_tracks(self, album: str, artist: str = None) -> List[Dict]:
        """Get all tracks from an album."""
        cursor = self.conn.cursor()
        if artist:
            cursor.execute('''
                SELECT * FROM tracks 
                WHERE album = ? AND (artist = ? OR album_artist = ?)
                ORDER BY disc_number, track_number
            ''', (album, artist, artist))
        else:
            cursor.execute('''
                SELECT * FROM tracks 
                WHERE album = ?
                ORDER BY disc_number, track_number
            ''', (album,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_genres(self) -> List[str]:
        """Get list of all genres."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT genre FROM tracks 
            WHERE genre IS NOT NULL AND genre != ''
            ORDER BY genre
        ''')
        return [row['genre'] for row in cursor.fetchall()]
    
    def get_tracks_by_genre(self, genre: str) -> List[Dict]:
        """Get all tracks of a specific genre."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tracks WHERE genre = ?
            ORDER BY artist, album, track_number
        ''', (genre,))
        return [dict(row) for row in cursor.fetchall()]
    
    # =========== Smart Playlists ===========
    
    def get_recently_added(self, limit: int = 50) -> List[Dict]:
        """Get recently added tracks."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tracks 
            ORDER BY date_added DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_most_played(self, limit: int = 50) -> List[Dict]:
        """Get most played tracks."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tracks 
            WHERE play_count > 0
            ORDER BY play_count DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_recently_played(self, limit: int = 50) -> List[Dict]:
        """Get recently played tracks."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tracks 
            WHERE last_played IS NOT NULL
            ORDER BY last_played DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_never_played(self, limit: int = 50) -> List[Dict]:
        """Get tracks that have never been played."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tracks 
            WHERE play_count = 0
            ORDER BY date_added DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    # =========== Duplicate Detection ===========
    
    def compute_file_hash(self, file_path: str) -> Optional[str]:
        """Compute MD5 hash of file for duplicate detection."""
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                # Read first and last 64KB for faster comparison
                hasher.update(f.read(65536))
                f.seek(-65536, 2)  # Seek to 64KB before end
                hasher.update(f.read(65536))
            return hasher.hexdigest()
        except (IOError, OSError):
            return None
    
    def find_duplicates(self) -> List[List[Dict]]:
        """Find duplicate tracks based on metadata similarity."""
        cursor = self.conn.cursor()
        
        # Find duplicates by title + artist + duration (within 2 seconds)
        cursor.execute('''
            SELECT t1.*, t2.id as dup_id, t2.file_path as dup_path
            FROM tracks t1
            JOIN tracks t2 ON t1.id < t2.id
            WHERE LOWER(t1.title) = LOWER(t2.title)
              AND LOWER(t1.artist) = LOWER(t2.artist)
              AND ABS(COALESCE(t1.duration, 0) - COALESCE(t2.duration, 0)) < 2
            ORDER BY t1.title, t1.artist
        ''')
        
        results = cursor.fetchall()
        
        # Group duplicates
        duplicates = {}
        for row in results:
            row_dict = dict(row)
            track_id = row_dict['id']
            if track_id not in duplicates:
                duplicates[track_id] = [self.get_track(track_id)]
            dup_track = self.get_track(row_dict['dup_id'])
            if dup_track and dup_track not in duplicates[track_id]:
                duplicates[track_id].append(dup_track)
        
        return list(duplicates.values())
    
    def find_exact_duplicates(self) -> List[List[Dict]]:
        """Find exact duplicate files based on hash."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT file_hash, GROUP_CONCAT(id) as track_ids
            FROM tracks
            WHERE file_hash IS NOT NULL
            GROUP BY file_hash
            HAVING COUNT(*) > 1
        ''')
        
        duplicates = []
        for row in cursor.fetchall():
            track_ids = [int(tid) for tid in row['track_ids'].split(',')]
            tracks = [self.get_track(tid) for tid in track_ids]
            duplicates.append([t for t in tracks if t])
        
        return duplicates
    
    # =========== Playlists ===========
    
    def create_playlist(self, name: str, is_smart: bool = False, smart_rules: str = None) -> Optional[int]:
        """Create a new playlist."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO playlists (name, is_smart, smart_rules) VALUES (?, ?, ?)',
                (name, int(is_smart), smart_rules)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error:
            return None
    
    def get_playlists(self) -> List[Dict]:
        """Get all playlists."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM playlists ORDER BY name')
        return [dict(row) for row in cursor.fetchall()]
    
    def add_to_playlist(self, playlist_id: int, track_id: int) -> bool:
        """Add a track to a playlist."""
        try:
            cursor = self.conn.cursor()
            # Get next position
            cursor.execute(
                'SELECT MAX(position) as max_pos FROM playlist_tracks WHERE playlist_id = ?',
                (playlist_id,)
            )
            result = cursor.fetchone()
            next_pos = (result['max_pos'] or 0) + 1
            
            cursor.execute(
                'INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)',
                (playlist_id, track_id, next_pos)
            )
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def get_playlist_tracks(self, playlist_id: int) -> List[Dict]:
        """Get all tracks in a playlist."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT t.* FROM tracks t
            JOIN playlist_tracks pt ON t.id = pt.track_id
            WHERE pt.playlist_id = ?
            ORDER BY pt.position
        ''', (playlist_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_playlist(self, playlist_id: int) -> bool:
        """Delete a playlist."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM playlists WHERE id = ?', (playlist_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    # =========== Playback State ===========
    
    def save_playback_state(self, track_id: int = None, position: float = 0, 
                           volume: float = 1.0, shuffle: bool = False, repeat_mode: int = 0):
        """Save current playback state for resume functionality."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE playback_state 
            SET current_track_id = ?, position = ?, volume = ?, shuffle = ?, repeat_mode = ?
            WHERE id = 1
        ''', (track_id, position, volume, int(shuffle), repeat_mode))
        self.conn.commit()
    
    def get_playback_state(self) -> Dict:
        """Get saved playback state."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM playback_state WHERE id = 1')
        row = cursor.fetchone()
        return dict(row) if row else {}
    
    # =========== Statistics ===========
    
    def get_library_stats(self) -> Dict:
        """Get library statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM tracks')
        total_tracks = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(DISTINCT artist) as count FROM tracks')
        total_artists = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(DISTINCT album) as count FROM tracks')
        total_albums = cursor.fetchone()['count']
        
        cursor.execute('SELECT SUM(duration) as total FROM tracks')
        total_duration = cursor.fetchone()['total'] or 0
        
        cursor.execute('SELECT SUM(file_size) as total FROM tracks')
        total_size = cursor.fetchone()['total'] or 0
        
        return {
            'total_tracks': total_tracks,
            'total_artists': total_artists,
            'total_albums': total_albums,
            'total_duration': total_duration,
            'total_size': total_size
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()
