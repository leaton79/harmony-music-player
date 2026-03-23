import tempfile
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from audio_engine import AudioEngineStub
from database import MusicDatabase
from main import TrackListWidget
from playback_rules import has_meaningful_playback


class PlaybackRulesTests(unittest.TestCase):
    def test_meaningful_playback_reaches_half_of_short_track(self):
        self.assertTrue(has_meaningful_playback(11, 20))
        self.assertFalse(has_meaningful_playback(9, 20))

    def test_meaningful_playback_reaches_thirty_seconds_for_long_track(self):
        self.assertTrue(has_meaningful_playback(30, 240))
        self.assertFalse(has_meaningful_playback(29, 240))


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
        )

        state = self.db.get_playback_state()

        self.assertEqual(state["current_track_id"], 42)
        self.assertEqual(state["position"], 123.5)
        self.assertEqual(state["volume"], 0.7)
        self.assertEqual(state["shuffle"], 1)
        self.assertEqual(state["repeat_mode"], 2)
        self.assertEqual(state["current_view"], "tracks")


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


if __name__ == "__main__":
    unittest.main()
