"""Cached mplsoccer pitch markings for the browser's animated canvas."""

import base64
from functools import lru_cache
from io import BytesIO

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from mplsoccer import Pitch


@lru_cache(maxsize=1)
def pitch_art() -> dict:
    length, width, margin = 105.3, 68.0, 1.0
    figure = Figure(figsize=((length + 2 * margin) / 10, (width + 2 * margin) / 10), dpi=160)
    FigureCanvasAgg(figure)
    axes = figure.add_axes((0, 0, 1, 1))
    pitch = Pitch(pitch_type='custom', pitch_length=length, pitch_width=width,
                  pitch_color='white', line_color='#626960', linewidth=1.2,
                  stripe=False, goal_type='line', axis=False)
    pitch.draw(ax=axes)
    axes.set_xlim(-margin, length + margin)
    # ATD coordinates increase down the screen; preserve that convention.
    axes.set_ylim(width + margin, -margin)
    output = BytesIO()
    figure.savefig(output, format='png', transparent=True, pad_inches=0)
    return {
        'image': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode('ascii'),
        'length': length, 'width': width, 'margin': margin,
    }
