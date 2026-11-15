"""Saved SkillCorner model predictions on the original tactical timeline."""
import pandas as pd
from evaluation import possession_metrics as pm
from games import GAME, GAMES
from model.paths import SUBMISSION_PATH
from model.config import ACTIVE_EXPERIMENT

MODEL_OPTIONS = {
    "Our model": ACTIVE_EXPERIMENT,
}


def prediction_path(name):
    if name not in MODEL_OPTIONS:
        raise ValueError(f"Unknown model: {name}")
    return SUBMISSION_PATH


def prediction_version(name):
    path = prediction_path(name)
    info = path.stat()
    return str(path), info.st_mtime_ns, info.st_size


def load_model_labels(name):
    path = prediction_path(name)
    frame = pd.read_csv(path)
    error = pm.validate_submission(frame, GAMES[GAME]["n_video_frames"])
    if error:
        raise ValueError(f"{name}: {error}")
    # Playback and scoring use the exact labels in the upload-ready file.
    return frame.label.to_numpy()


def possession_intervals(labels):
    intervals = []
    start = 0
    for stop in range(1, len(labels) + 1):
        if stop == len(labels) or labels[stop] != labels[start]:
            intervals.append({"start": start, "end": stop - 1, "label": str(labels[start])})
            start = stop
    return intervals
