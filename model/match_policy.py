"""Known match boundaries applied after inference, without possession GT input."""
import numpy as np
from games import GAME, GAMES, half_video_blocks

# Observed kickoff frames on the original tactical-video timeline.
KICKOFF_VIDEO_FRAMES = {"1st Half": 11185, "2nd Half": 113742}


def pre_kickoff_blocks():
    # Keep observed kickoff instants separate from graded-half boundaries.
    blocks = []
    for half, start, end in half_video_blocks(GAME):
        kickoff = KICKOFF_VIDEO_FRAMES['1st Half' if half == 1 else '2nd Half']
        stop = min(end + 1, kickoff)
        if start < stop:
            blocks.append((start, stop))
    return blocks


def apply_known_dead_ball(labels):
    """Copy labels, forcing only graded pre-kickoff frames to D (half-open)."""
    result = np.asarray(labels, dtype='<U1').copy()
    if len(result) != GAMES[GAME]['n_video_frames']:
        raise ValueError('Expected the full Barcelona tactical frame timeline')
    for start, stop in pre_kickoff_blocks():
        result[start:stop] = 'D'
    return result
