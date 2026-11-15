"""Native tracking adapters; labels never enter feature construction."""
from dataclasses import replace
import json

import numpy as np
import pandas as pd

from .core.io import Match, load_epts
from .core import features
from .paths import SKILLCORNER_DIR, PUBLIC_GT_PATH



def skillcorner_labels(phases, halves, n_frames, home_id, away_id):
    """Weak H/A labels from phases; their complement inside halves is assumed D.

    Phase ends are exclusive (successive phases share a boundary). No labels
    are inferred from coordinate missingness. Null tracking possession is not
    itself interpreted as dead ball.
    """
    labels = np.full(n_frames, 'X', dtype='<U1')
    for start, stop in halves:
        labels[start:stop] = 'D'
    for phase in phases.itertuples(index=False):
        start, stop = int(phase.frame_start), int(phase.frame_end)
        if phase.team_in_possession_id not in (home_id, away_id):
            raise ValueError('Unknown phase possession team')
        if start < 0 or start >= stop:
            raise ValueError(f'Invalid phase bounds {start}:{stop}')
        # Some provider phases overrun the first-half end, even into the
        # second-half video block. Clip to the phase's declared period only.
        if hasattr(phase, 'period'):
            period = int(phase.period)
            if not 1 <= period <= len(halves):
                raise ValueError('Unknown phase period')
            a, b = halves[period - 1]
            if not a <= start < b:
                raise ValueError('Phase starts outside its declared half')
            stop = min(stop, b)
        elif not any(a <= start < stop <= b for a, b in halves):
            raise ValueError('Phase outside half')
        lab = 'H' if phase.team_in_possession_id == home_id else 'A'
        existing = labels[start:stop]
        if np.any((existing != 'D') & (existing != lab)):
            raise ValueError('Contradictory overlapping phase labels')
        labels[start:stop] = lab
    return labels


def load_skillcorner(mid):
    folder = SKILLCORNER_DIR/str(mid)
    meta = json.loads((folder/f'{mid}_match.json').read_text())
    phases = pd.read_csv(folder/f'{mid}_phases_of_play.csv')
    players = meta['players']
    ids = {p['id']: i for i, p in enumerate(players)}
    home, away = meta['home_team']['id'], meta['away_team']['id']
    assert all(p['team_id'] in (home, away) for p in players)
    team = np.array([0 if p['team_id'] == home else 1 for p in players], dtype=np.int8)
    halves = [(int(p['start_frame']), int(p['end_frame']) + 1)
              for p in meta['match_periods'] if p['period'] in (1, 2)]
    n = max(b for _, b in halves)
    length, width = float(meta['pitch_length']), float(meta['pitch_width'])
    x, y = [np.full((n, len(players)), np.nan, dtype=np.float32) for _ in range(2)]
    bx, by = [np.full(n, np.nan, dtype=np.float32) for _ in range(2)]
    tracking_labels = np.full(n, 'X', dtype='<U1')
    detected = np.zeros(n, dtype=bool)
    periods = np.zeros(n, dtype=np.int8)
    with (folder/f'{mid}_tracking_extrapolated.jsonl').open() as handle:
        for line in handle:
            row = json.loads(line)
            i = row['frame']
            if i >= n or row['period'] not in (1, 2):
                continue
            periods[i] = row['period']
            b = row.get('ball_data') or {}
            if b.get('x') is not None and b.get('y') is not None:
                bx[i], by[i] = b['x'] + length/2, b['y'] + width/2
            detected[i] = b.get('is_detected') is True
            tracking_labels[i] = {'home team': 'H', 'away team': 'A'}.get(
                (row.get('possession') or {}).get('group'), 'X')
            for p in row['player_data']:
                j = ids[p['player_id']]
                if p.get('x') is not None and p.get('y') is not None:
                    x[i, j], y[i, j] = p['x'] + length/2, p['y'] + width/2
    declared_halves = halves
    halves = []
    for h, (a, b) in enumerate(declared_halves, 1):
        observed = np.flatnonzero(periods == h)
        if not len(observed) or observed[0] != a or observed[-1] not in (b-1, b-2):
            raise ValueError(f'Period/metadata mismatch for {mid}')
        stop = int(observed[-1]) + 1
        if not np.all(periods[a:stop] == h):
            raise ValueError(f'Missing interior period rows for {mid}')
        halves.append((a, stop))
    labels = skillcorner_labels(phases, halves, n, home, away)
    match = Match(x=x, y=y, speed=np.full_like(x, np.nan), team=team,
                  ball_x=bx, ball_y=by, pitch=(length, width), fps=10,
                  halves=halves, name=f'skillcorner_{mid}')
    both = np.isin(labels, ['H', 'A']) & np.isin(tracking_labels, ['H', 'A'])
    audit = {'label_source': 'phases_of_play; complement within halves assumed D',
             'metadata_endpoint_frames_absent_from_tracking': sum(b-d for (_, b), (_, d) in zip(declared_halves, halves)),
             'phase_rows_clipped_at_period_end': sum(int(r.frame_end) > halves[int(r.period)-1][1] for r in phases.itertuples()),
             'tracking_possession_comparable_frames': int(both.sum()),
             'tracking_possession_team_disagreements': int(np.sum(labels[both] != tracking_labels[both])),
             'phase_dead_but_tracking_team_frames': int(np.sum((labels == 'D') & np.isin(tracking_labels, ['H', 'A']))),
             'ball_detected_frames': int(detected.sum())}
    return match, labels, audit


def load_barca():
    from games import GAME, GAMES, asset_paths, half_video_blocks
    paths = asset_paths(source='tactical')
    match = load_epts(paths['atd_meta'], paths['atd_raw'], pitch=GAMES[GAME]['pitch'],
                      n_frames=GAMES[GAME]['n_video_frames'], name='barca_tactical')
    match.halves = [(a, b + 1) for _, a, b in half_video_blocks(GAME)]
    # Public labels are read only for evaluation, not features or training.
    gt = pd.read_csv(PUBLIC_GT_PATH)
    labels = np.full(match.n_frames, 'X', dtype='<U1')
    frames = gt.frame.to_numpy(dtype=int)
    assert len(np.unique(frames)) == len(frames) and frames.min() >= 0 and frames.max() < match.n_frames
    labels[frames] = gt.label.to_numpy()
    assert np.sum(labels != 'X') == 7500
    return match, labels, {'label_source': 'public Barcelona 5-minute human ground truth',
                           'source': 'tactical only'}


def extract(match):
    """Compute each half independently: windows never cross halftime.

    Raw arrays remain unchanged. Reference feature-only spike cleaning and
    <=0.4-second interpolation are retained; no synthetic training data.
    """
    output = None
    for a, b in match.halves:
        half = replace(match, x=match.x[a:b], y=match.y[a:b], speed=match.speed[a:b],
                       ball_x=match.ball_x[a:b], ball_y=match.ball_y[a:b], halves=[(0, b-a)])
        computed = features.compute(half)
        if output is None:
            output = {'team': {k: {name: np.full(match.n_frames, np.nan, dtype=np.float32)
                                  for name in computed['team'][k]} for k in (0, 1)},
                      'shared': {name: np.full(match.n_frames, np.nan, dtype=np.float32)
                                 for name in computed['shared']}, 'fps': match.fps}
        for k in (0, 1):
            for name, values in computed['team'][k].items():
                output['team'][k][name][a:b] = values
        for name, values in computed['shared'].items():
            output['shared'][name][a:b] = values
    return output


def audit_match(match, labels, extra):
    graded = labels != 'X'
    ball = np.isfinite(match.ball_x) & np.isfinite(match.ball_y)
    return dict(name=match.name, fps=match.fps, frames=match.n_frames, halves=match.halves,
                graded_frames=int(graded.sum()), ball_available_frames=int((ball & graded).sum()),
                label_counts={k: int(np.sum(labels == k)) for k in 'HADX'},
                ball_availability_by_label={k: {'frames': int(np.sum(labels == k)),
                    'available': int(np.sum(ball & (labels == k)))} for k in 'HAD'}, **extra)
