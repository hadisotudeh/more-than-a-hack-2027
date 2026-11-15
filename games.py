"""Match assets and frame boundaries shared by the app, model, and submission validator."""
import os
from pathlib import Path

GAME = 'BAR-ATH'
DATA_DIR = os.environ.get('MTAH_DATA_DIR') or str(Path(__file__).resolve().parent / 'data')
DEFAULT_SOURCE = 'tactical'
GAMES = {
    GAME: {
        'n_video_frames': 199319,
        'fps': 25,
        'pitch': (105.3, 68.0),
    },
}
SOURCES = {
    'tactical': {
        'stem': 'BAR-ATH_tactical',
        'n_video_frames': 199319,
        'assets': ('video', 'atd_meta', 'atd_raw', 'homography', 'smart_tagging'),
    },
    'broadcast': {
        'stem': 'BAR-ATH_broadcast',
        'n_video_frames': 164488,
        'assets': ('video', 'atd_meta', 'atd_raw', 'homography'),
    },
}
SUFFIXES = {
    'video': '.mp4',
    'atd_meta': '_atd.xml',
    'atd_raw': '_atd.txt',
    'homography': '_homography.csv',
    'smart_tagging': '_smart_tagging.xml',
}
# Inclusive original tactical-video boundaries; broadcast has its own timeline.
HALF_VIDEO_BLOCKS = [(1, 11185, 90651), (2, 110808, 190197)]


def asset_paths(game=GAME, data_dir=None, source=DEFAULT_SOURCE):
    """Return the expected asset paths for one camera; honor MTAH_DATA_DIR."""
    if game not in GAMES:
        raise KeyError(f'Unknown match: {game}')
    entry = SOURCES[source]
    folder = Path(data_dir or DATA_DIR) / source
    return {name: str(folder / (entry['stem'] + SUFFIXES[name])) for name in entry['assets']}


def source_frames(source=DEFAULT_SOURCE, game=GAME):
    if game not in GAMES:
        raise KeyError(f'Unknown match: {game}')
    return SOURCES[source]['n_video_frames']


def half_video_blocks(game=GAME):
    """Return (half, first frame, last frame) for the graded tactical halves."""
    if game not in GAMES:
        raise KeyError(f'Unknown match: {game}')
    return list(HALF_VIDEO_BLOCKS)
