"""
Pure playback rules used by the UI and tests.
"""


def resolve_playback_queue(current_track_id, preferred_tracks, library_tracks):
    """Choose a queue that contains the current track and return the queue with its index."""
    candidate_lists = []

    if preferred_tracks:
        candidate_lists.append(preferred_tracks)

    if library_tracks:
        candidate_lists.append(library_tracks)

    for tracks in candidate_lists:
        for index, track in enumerate(tracks):
            if track.get("id") == current_track_id:
                return tracks, index

    return [], -1


def should_restore_playback(position: float, duration: float, min_resume_position: float = 5, end_padding: float = 3) -> bool:
    """Return True when a saved track position is worth restoring on app launch."""
    if position is None or position < min_resume_position:
        return False

    if duration is None or duration <= 0:
        return True

    return position < max(duration - end_padding, min_resume_position)


def has_meaningful_playback(position: float, duration: float, min_seconds: float = 30) -> bool:
    """Return True when playback has gone long enough to count as a real play."""
    if position is None or position <= 0:
        return False

    if duration is None or duration <= 0:
        return position >= min_seconds

    return position >= min(min_seconds, duration * 0.5)
