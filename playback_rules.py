"""
Pure playback rules used by the UI and tests.
"""


def has_meaningful_playback(position: float, duration: float, min_seconds: float = 30) -> bool:
    """Return True when playback has gone long enough to count as a real play."""
    if position is None or position <= 0:
        return False

    if duration is None or duration <= 0:
        return position >= min_seconds

    return position >= min(min_seconds, duration * 0.5)
