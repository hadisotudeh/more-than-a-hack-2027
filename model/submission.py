"""Export and validate the upload-ready possession CSV."""
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd
from evaluation import possession_metrics as pm
from games import GAME, GAMES, half_video_blocks
from .match_policy import apply_known_dead_ball, pre_kickoff_blocks
from .config import ACTIVE_EXPERIMENT

from .paths import SUBMISSION_PATH, ARTIFACTS_DIR, TRAINING_REPORT_PATH, PUBLIC_GT_PATH


def write_submission(path, labels):
    """Write the hackathon's frame,label CSV, with zero-based frame numbers."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        handle.write('frame,label\n')
        handle.writelines(f'{frame},{label}\n' for frame, label in enumerate(labels))
    return str(path)


def export_labels(labels, destination=SUBMISSION_PATH):
    """Validate input, apply the match policy, then validate the exact bytes before publication.

    The atomic replacement keeps a failed export from replacing the app's last valid CSV.
    Validation is the same function used by evaluation/validate_submission.py.
    """
    destination = Path(destination)
    frame = pd.DataFrame({'frame': np.arange(len(labels)), 'label': labels})
    error = pm.validate_submission(frame, GAMES[GAME]['n_video_frames'])
    if error:
        raise ValueError(f'Submission: {error}')
    normalized = frame.label.astype(str).str.strip().str.upper().to_numpy()
    normalized = apply_known_dead_ball(normalized)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix='.submission-', suffix='.csv', dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        write_submission(str(temporary), normalized)
        saved = pm.read_label_csv(temporary)
        error = pm.validate_submission(saved, GAMES[GAME]['n_video_frames'])
        if error:
            raise ValueError(f'Exported submission: {error}')
        if saved.columns.tolist() != ['frame', 'label']:
            raise ValueError('Exported submission must contain exactly frame,label')
        np.testing.assert_array_equal(saved.label.to_numpy(), normalized)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def export_active():
    """Decode saved probabilities, export the single CSV, and record validation."""
    from .core.decode import decode
    training = json.loads(TRAINING_REPORT_PATH.read_text())
    with np.load(ARTIFACTS_DIR / 'barca_probabilities.npz') as probabilities:
        labels = decode(probabilities['p_dead'], probabilities['p_home_given_alive'],
                        [(a, b + 1) for _, a, b in half_video_blocks(GAME)],
                        GAMES[GAME]['n_video_frames'], training['decoder_parameters'])
    path = export_labels(labels)
    saved = pm.read_label_csv(path)
    gt = pm.read_label_csv(PUBLIC_GT_PATH)
    scores = pm.evaluate(pm.label_codes(gt), pm.label_codes(saved))
    training.setdefault('results', {})['barca'] = scores
    training['barca_postprocessing'] = {
        'known_dead_ball_blocks': pre_kickoff_blocks(),
        'policy_sha256': hashlib.sha256(Path(__file__).with_name('match_policy.py').read_bytes()).hexdigest(),
        'prediction_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    TRAINING_REPORT_PATH.write_text(json.dumps(training, indent=2) + '\n')
    report = {'file': path.name, 'experiment': ACTIVE_EXPERIMENT, 'rows': len(saved),
              'first_frame': int(saved.frame.iloc[0]), 'last_frame': int(saved.frame.iloc[-1]),
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'label_counts': {str(k): int(v) for k,v in saved.label.value_counts().items()},
              'public_spell_f1': scores['spell_f1_mean'], 'public_macro_f1': scores['macro_f1'],
              'format_valid': True, 'writer': 'model.submission.write_submission',
              'validator': 'evaluation.possession_metrics.validate_submission'}
    path.with_suffix('.validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return path


if __name__ == '__main__':
    export_active()
