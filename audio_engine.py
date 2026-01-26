"""
Audio engine module using mpv for high-quality gapless playback.
"""

import threading
from typing import Callable, Optional, List
from enum import IntEnum

try:
    import mpv
    MPV_AVAILABLE = True
except ImportError:
    MPV_AVAILABLE = False


class RepeatMode(IntEnum):
    OFF = 0
    ALL = 1
    ONE = 2


class AudioEngine:
    """
    Audio playback engine using mpv.
    Features: gapless playback, crossfade support, format flexibility.
    """
    
    def __init__(self):
        if not MPV_AVAILABLE:
            raise ImportError("python-mpv is required. Install with: pip install python-mpv")
        
        self.player = mpv.MPV(
            video=False,
            ytdl=False,
            input_default_bindings=False,
            input_vo_keyboard=False,
        )
        
        # Enable gapless playback
        self.player['gapless-audio'] = 'yes'
        self.player['audio-buffer'] = 0.2  # 200ms buffer
        
        # Playback state
        self._current_track = None
        self._playlist: List[dict] = []
        self._playlist_index: int = -1
        self._shuffle = False
        self._shuffle_order: List[int] = []
        self._repeat_mode = RepeatMode.OFF
        self._volume = 100
        
        # Callbacks
        self._on_track_change: Optional[Callable] = None
        self._on_playback_end: Optional[Callable] = None
        self._on_position_change: Optional[Callable] = None
        self._on_error: Optional[Callable] = None
        
        # Setup event observers
        self._setup_observers()
        
        # Position update thread
        self._position_thread = None
        self._running = True
    
    def _setup_observers(self):
        """Setup mpv event observers."""
        self._last_position = 0
        self._stuck_count = 0
        
        @self.player.event_callback('end-file')
        def on_end_file(event):
            reason = event.get('event', {}).get('reason', 'unknown')
            if reason == 'eof':
                self._handle_track_end()
            elif reason == 'error':
                if self._on_error:
                    self._on_error("Playback error")
        
        @self.player.property_observer('time-pos')
        def on_time_pos(name, value):
            if value is not None:
                if self._on_position_change:
                    self._on_position_change(value)
                
                # Fallback: detect if playback stopped near end
                try:
                    duration = self.player.duration
                    if duration and value >= duration - 1.5:
                        # Near end - check if we're stuck
                        if abs(value - self._last_position) < 0.1:
                            self._stuck_count += 1
                            if self._stuck_count > 3:
                                self._stuck_count = 0
                                self._handle_track_end()
                        else:
                            self._stuck_count = 0
                    self._last_position = value
                except:
                    pass
    
    def _handle_track_end(self):
        """Handle track ending - advance playlist or repeat."""
        # Prevent double-triggering
        if hasattr(self, '_handling_end') and self._handling_end:
            return
        self._handling_end = True
        
        try:
            if self._repeat_mode == RepeatMode.ONE:
                self.seek(0)
                self.play()
            elif self._playlist_index < len(self._playlist) - 1:
                self.next()
            elif self._repeat_mode == RepeatMode.ALL:
                self.play_index(0)
            elif self._on_playback_end:
                self._on_playback_end()
        finally:
            self._handling_end = False
    
    # =========== Playback Control ===========
    
    def play(self, file_path: str = None):
        """Play a file or resume playback."""
        if file_path:
            self._current_track = file_path
            self.player.play(file_path)
        else:
            self.player.pause = False
    
    def pause(self):
        """Pause playback."""
        self.player.pause = True
    
    def toggle_play_pause(self):
        """Toggle between play and pause."""
        # If we have a track loaded and player is idle, start playing
        if self._current_track and self.player.idle_active:
            self.player.play(self._current_track)
        else:
            self.player.pause = not self.player.pause
    
    def stop(self):
        """Stop playback."""
        self.player.stop()
        self._current_track = None
    
    def seek(self, position: float):
        """Seek to position in seconds."""
        try:
            self.player.seek(position, 'absolute')
        except Exception:
            pass
    
    def seek_relative(self, offset: float):
        """Seek relative to current position."""
        try:
            self.player.seek(offset, 'relative')
        except Exception:
            pass
    
    # =========== Playlist Management ===========
    
    def set_playlist(self, tracks: List[dict], start_index: int = 0):
        """Set the playlist and optionally start playing."""
        self._playlist = tracks
        self._playlist_index = -1
        
        if self._shuffle:
            self._generate_shuffle_order()
        
        if tracks and start_index >= 0:
            self.play_index(start_index)
    
    def add_to_playlist(self, track: dict):
        """Add a track to the end of the playlist."""
        self._playlist.append(track)
        if self._shuffle:
            self._shuffle_order.append(len(self._playlist) - 1)
    
    def clear_playlist(self):
        """Clear the playlist."""
        self._playlist = []
        self._playlist_index = -1
        self._shuffle_order = []
        self.stop()
    
    def play_index(self, index: int):
        """Play track at specific playlist index."""
        if 0 <= index < len(self._playlist):
            if self._shuffle:
                # Find index in shuffle order
                if index in self._shuffle_order:
                    self._playlist_index = self._shuffle_order.index(index)
                    actual_index = index
                else:
                    self._playlist_index = index
                    actual_index = self._shuffle_order[index] if index < len(self._shuffle_order) else index
            else:
                self._playlist_index = index
                actual_index = index
            
            track = self._playlist[actual_index]
            self._current_track = track.get('file_path')
            self.player.play(self._current_track)
            
            if self._on_track_change:
                self._on_track_change(track, actual_index)
    
    def next(self):
        """Play next track in playlist."""
        if not self._playlist:
            return
        
        if self._shuffle:
            next_idx = self._playlist_index + 1
            if next_idx >= len(self._shuffle_order):
                if self._repeat_mode == RepeatMode.ALL:
                    self._generate_shuffle_order()
                    next_idx = 0
                else:
                    return
            self._playlist_index = next_idx
            actual_index = self._shuffle_order[next_idx]
        else:
            next_idx = self._playlist_index + 1
            if next_idx >= len(self._playlist):
                if self._repeat_mode == RepeatMode.ALL:
                    next_idx = 0
                else:
                    return
            self._playlist_index = next_idx
            actual_index = next_idx
        
        track = self._playlist[actual_index]
        self._current_track = track.get('file_path')
        self.player.play(self._current_track)
        
        if self._on_track_change:
            self._on_track_change(track, actual_index)
    
    def previous(self):
        """Play previous track in playlist."""
        if not self._playlist:
            return
        
        # If more than 3 seconds into track, restart it
        pos = self.get_position()
        if pos and pos > 3:
            self.seek(0)
            return
        
        if self._shuffle:
            prev_idx = self._playlist_index - 1
            if prev_idx < 0:
                if self._repeat_mode == RepeatMode.ALL:
                    prev_idx = len(self._shuffle_order) - 1
                else:
                    prev_idx = 0
            self._playlist_index = prev_idx
            actual_index = self._shuffle_order[prev_idx]
        else:
            prev_idx = self._playlist_index - 1
            if prev_idx < 0:
                if self._repeat_mode == RepeatMode.ALL:
                    prev_idx = len(self._playlist) - 1
                else:
                    prev_idx = 0
            self._playlist_index = prev_idx
            actual_index = prev_idx
        
        track = self._playlist[actual_index]
        self._current_track = track.get('file_path')
        self.player.play(self._current_track)
        
        if self._on_track_change:
            self._on_track_change(track, actual_index)
    
    def _generate_shuffle_order(self):
        """Generate random shuffle order."""
        import random
        self._shuffle_order = list(range(len(self._playlist)))
        
        # Keep current track at the beginning if playing
        if self._playlist_index >= 0 and self._playlist_index < len(self._playlist):
            current = self._playlist_index
            self._shuffle_order.remove(current)
            random.shuffle(self._shuffle_order)
            self._shuffle_order.insert(0, current)
        else:
            random.shuffle(self._shuffle_order)
    
    # =========== Playback Properties ===========
    
    @property
    def is_playing(self) -> bool:
        """Check if currently playing."""
        try:
            return not self.player.pause and self._current_track is not None
        except Exception:
            return False
    
    @property
    def is_paused(self) -> bool:
        """Check if paused."""
        try:
            return self.player.pause
        except Exception:
            return True
    
    def get_position(self) -> Optional[float]:
        """Get current playback position in seconds."""
        try:
            return self.player.time_pos
        except Exception:
            return None
    
    def get_duration(self) -> Optional[float]:
        """Get current track duration in seconds."""
        try:
            return self.player.duration
        except Exception:
            return None
    
    def get_current_track(self) -> Optional[dict]:
        """Get current track info."""
        if self._playlist and 0 <= self._playlist_index < len(self._playlist):
            if self._shuffle:
                actual_index = self._shuffle_order[self._playlist_index]
                return self._playlist[actual_index]
            return self._playlist[self._playlist_index]
        return None
    
    def get_playlist(self) -> List[dict]:
        """Get current playlist."""
        return self._playlist.copy()
    
    def get_playlist_index(self) -> int:
        """Get current playlist index."""
        if self._shuffle and self._playlist_index >= 0:
            return self._shuffle_order[self._playlist_index]
        return self._playlist_index
    
    # =========== Volume Control ===========
    
    def set_volume(self, volume: int):
        """Set volume (0-100)."""
        self._volume = max(0, min(100, volume))
        self.player.volume = self._volume
    
    def get_volume(self) -> int:
        """Get current volume."""
        return self._volume
    
    def mute(self):
        """Mute audio."""
        self.player.mute = True
    
    def unmute(self):
        """Unmute audio."""
        self.player.mute = False
    
    def toggle_mute(self):
        """Toggle mute state."""
        self.player.mute = not self.player.mute
    
    # =========== Shuffle & Repeat ===========
    
    def set_shuffle(self, enabled: bool):
        """Enable or disable shuffle."""
        self._shuffle = enabled
        if enabled:
            self._generate_shuffle_order()
    
    def get_shuffle(self) -> bool:
        """Get shuffle state."""
        return self._shuffle
    
    def toggle_shuffle(self):
        """Toggle shuffle."""
        self.set_shuffle(not self._shuffle)
    
    def set_repeat_mode(self, mode: RepeatMode):
        """Set repeat mode."""
        self._repeat_mode = mode
    
    def get_repeat_mode(self) -> RepeatMode:
        """Get repeat mode."""
        return self._repeat_mode
    
    def cycle_repeat_mode(self):
        """Cycle through repeat modes."""
        modes = [RepeatMode.OFF, RepeatMode.ALL, RepeatMode.ONE]
        current_idx = modes.index(self._repeat_mode)
        self._repeat_mode = modes[(current_idx + 1) % len(modes)]
        return self._repeat_mode
    
    # =========== Callbacks ===========
    
    def on_track_change(self, callback: Callable):
        """Set callback for track changes."""
        self._on_track_change = callback
    
    def on_playback_end(self, callback: Callable):
        """Set callback for playlist end."""
        self._on_playback_end = callback
    
    def on_position_change(self, callback: Callable):
        """Set callback for position updates."""
        self._on_position_change = callback
    
    def on_error(self, callback: Callable):
        """Set callback for errors."""
        self._on_error = callback
    
    # =========== Cleanup ===========
    
    def cleanup(self):
        """Cleanup resources."""
        self._running = False
        try:
            self.player.terminate()
        except Exception:
            pass


class AudioEngineStub:
    """
    Stub audio engine for testing without mpv.
    """
    
    def __init__(self):
        self._playing = False
        self._paused = True
        self._volume = 100
        self._shuffle = False
        self._repeat_mode = RepeatMode.OFF
        self._playlist = []
        self._playlist_index = -1
        self._position = 0
        self._duration = 180
        self._current_track = None
    
    def play(self, file_path: str = None):
        self._playing = True
        self._paused = False
        if file_path:
            self._current_track = file_path
    
    def pause(self):
        self._paused = True
    
    def toggle_play_pause(self):
        self._paused = not self._paused
    
    def stop(self):
        self._playing = False
        self._paused = True
        self._position = 0
    
    def seek(self, position: float):
        self._position = position
    
    def seek_relative(self, offset: float):
        self._position += offset
    
    def set_playlist(self, tracks, start_index=0):
        self._playlist = tracks
        if tracks:
            self.play_index(start_index)
    
    def play_index(self, index):
        if 0 <= index < len(self._playlist):
            self._playlist_index = index
            self._current_track = self._playlist[index].get('file_path')
            self._playing = True
            self._paused = False
    
    def next(self):
        if self._playlist_index < len(self._playlist) - 1:
            self.play_index(self._playlist_index + 1)
    
    def previous(self):
        if self._playlist_index > 0:
            self.play_index(self._playlist_index - 1)
    
    @property
    def is_playing(self):
        return self._playing and not self._paused
    
    @property
    def is_paused(self):
        return self._paused
    
    def get_position(self):
        return self._position
    
    def get_duration(self):
        return self._duration
    
    def get_current_track(self):
        if 0 <= self._playlist_index < len(self._playlist):
            return self._playlist[self._playlist_index]
        return None
    
    def set_volume(self, volume):
        self._volume = volume
    
    def get_volume(self):
        return self._volume
    
    def set_shuffle(self, enabled):
        self._shuffle = enabled
    
    def get_shuffle(self):
        return self._shuffle
    
    def toggle_shuffle(self):
        self._shuffle = not self._shuffle
    
    def set_repeat_mode(self, mode):
        self._repeat_mode = mode
    
    def get_repeat_mode(self):
        return self._repeat_mode
    
    def cycle_repeat_mode(self):
        modes = [RepeatMode.OFF, RepeatMode.ALL, RepeatMode.ONE]
        idx = modes.index(self._repeat_mode)
        self._repeat_mode = modes[(idx + 1) % len(modes)]
        return self._repeat_mode
    
    def on_track_change(self, callback): pass
    def on_playback_end(self, callback): pass
    def on_position_change(self, callback): pass
    def on_error(self, callback): pass
    
    def cleanup(self): pass
    def add_to_playlist(self, track): self._playlist.append(track)
    def clear_playlist(self): self._playlist = []
    def get_playlist(self): return self._playlist
    def get_playlist_index(self): return self._playlist_index
    def mute(self): pass
    def unmute(self): pass
    def toggle_mute(self): pass


def create_audio_engine():
    """Factory function to create the appropriate audio engine."""
    if MPV_AVAILABLE:
        try:
            return AudioEngine()
        except Exception as e:
            print(f"Could not create mpv engine: {e}")
            print("Falling back to stub engine")
            return AudioEngineStub()
    else:
        print("mpv not available, using stub engine")
        return AudioEngineStub()
