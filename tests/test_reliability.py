import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from PyQt6.QtWidgets import QApplication

from audio_engine import AudioEngineStub
from database import MusicDatabase
from main import TrackListWidget
from main_window import MainWindow
from playback_rules import has_meaningful_playback, resolve_playback_queue, should_restore_playback


class PlaybackRulesTests(unittest.TestCase):
    def test_meaningful_playback_reaches_half_of_short_track(self):
        self.assertTrue(has_meaningful_playback(11, 20))
        self.assertFalse(has_meaningful_playback(9, 20))

    def test_meaningful_playback_reaches_thirty_seconds_for_long_track(self):
        self.assertTrue(has_meaningful_playback(30, 240))
        self.assertFalse(has_meaningful_playback(29, 240))

    def test_resolve_playback_queue_prefers_current_view_when_track_is_present(self):
        preferred_tracks = [
            {"id": 2, "title": "Second"},
            {"id": 3, "title": "Third"},
        ]
        library_tracks = [
            {"id": 1, "title": "First"},
            {"id": 2, "title": "Second"},
            {"id": 3, "title": "Third"},
        ]

        queue, index = resolve_playback_queue(3, preferred_tracks, library_tracks)

        self.assertEqual([track["id"] for track in queue], [2, 3])
        self.assertEqual(index, 1)

    def test_resolve_playback_queue_falls_back_to_library_when_needed(self):
        preferred_tracks = [{"id": 9, "title": "Other"}]
        library_tracks = [
            {"id": 1, "title": "First"},
            {"id": 2, "title": "Second"},
        ]

        queue, index = resolve_playback_queue(2, preferred_tracks, library_tracks)

        self.assertEqual([track["id"] for track in queue], [1, 2])
        self.assertEqual(index, 1)

    def test_should_restore_playback_requires_meaningful_progress(self):
        self.assertFalse(should_restore_playback(2, 240))
        self.assertTrue(should_restore_playback(45, 240))

    def test_should_restore_playback_ignores_tracks_at_the_end(self):
        self.assertFalse(should_restore_playback(238, 240))
        self.assertTrue(should_restore_playback(200, 240))


class MusicDatabaseReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "library.db"
        self.db = MusicDatabase(str(self.db_path))

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_delete_track_from_disk_removes_db_row_after_file_delete(self):
        track_path = Path(self.temp_dir.name) / "song.mp3"
        track_path.write_bytes(b"test mp3 data")

        track_id = self.db.add_track({
            "file_path": str(track_path),
            "title": "Song",
            "artist": "Artist",
        })

        success, _ = self.db.delete_track_from_disk(track_id)

        self.assertTrue(success)
        self.assertFalse(track_path.exists())
        self.assertIsNone(self.db.get_track(track_id))

    def test_delete_track_from_disk_preserves_db_row_if_file_missing(self):
        track_path = Path(self.temp_dir.name) / "missing.mp3"
        track_id = self.db.add_track({
            "file_path": str(track_path),
            "title": "Missing Song",
            "artist": "Artist",
        })

        success, message = self.db.delete_track_from_disk(track_id)

        self.assertFalse(success)
        self.assertIn("already missing", message)
        self.assertIsNotNone(self.db.get_track(track_id))

    def test_playback_state_round_trip_persists_position(self):
        self.db.save_playback_state(
            track_id=42,
            position=123.5,
            volume=0.7,
            shuffle=True,
            repeat_mode=2,
            current_view="tracks",
            current_view_data=json.dumps({"playlist_id": 7}),
        )

        state = self.db.get_playback_state()

        self.assertEqual(state["current_track_id"], 42)
        self.assertEqual(state["position"], 123.5)
        self.assertEqual(state["volume"], 0.7)
        self.assertEqual(state["shuffle"], 1)
        self.assertEqual(state["repeat_mode"], 2)
        self.assertEqual(state["current_view"], "tracks")
        self.assertEqual(state["current_view_data"], json.dumps({"playlist_id": 7}))


class QueueReliabilityTests(unittest.TestCase):
    def test_play_next_inserts_track_after_current(self):
        engine = AudioEngineStub()
        tracks = [
            {"id": 1, "title": "One", "file_path": "/tmp/1.mp3"},
            {"id": 2, "title": "Two", "file_path": "/tmp/2.mp3"},
            {"id": 3, "title": "Three", "file_path": "/tmp/3.mp3"},
        ]

        engine.set_playlist(tracks[:2], 0)
        engine.play_next(tracks[2])

        queue_ids = [track["id"] for track in engine.get_playlist()]
        up_next_ids = [track["id"] for track in engine.get_up_next()]

        self.assertEqual(queue_ids, [1, 3, 2])
        self.assertEqual(up_next_ids, [3, 2])

    def test_clear_up_next_keeps_current_track_only(self):
        engine = AudioEngineStub()
        tracks = [
            {"id": 1, "title": "One", "file_path": "/tmp/1.mp3"},
            {"id": 2, "title": "Two", "file_path": "/tmp/2.mp3"},
        ]

        engine.set_playlist(tracks, 0)
        engine.clear_up_next()

        queue_ids = [track["id"] for track in engine.get_playlist()]
        self.assertEqual(queue_ids, [1])
        self.assertEqual(engine.get_up_next(), [])


class TrackHighlightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_set_playing_track_marks_row_and_indicator(self):
        widget = TrackListWidget()
        widget.set_tracks([
            {"id": 1, "title": "First", "artist": "Artist A", "album": "Album", "duration": 120},
            {"id": 2, "title": "Second", "artist": "Artist B", "album": "Album", "duration": 180},
        ])

        widget.set_playing_track(2)

        self.assertEqual(widget.item(1, 0).text(), "▶")
        self.assertTrue(widget.item(1, 2).font().bold())
        self.assertNotEqual(widget.item(1, 2).background().color().alpha(), 0)


class LibraryRemovalTests(unittest.TestCase):
    def test_remove_from_library_skips_confirmation_dialog(self):
        window = MainWindow.__new__(MainWindow)
        window.db = Mock()
        window._refresh_current_view = Mock()
        window._update_stats = Mock()

        with patch("main_window.QMessageBox.question", side_effect=AssertionError("confirmation should not be shown")):
            window._on_delete_from_library({"id": 7, "title": "Song"})

        window.db.delete_track.assert_called_once_with(7)
        window._refresh_current_view.assert_called_once_with()
        window._update_stats.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
