"""Train the active possession model and evaluate Barcelona's public window."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pickle
import platform
import time
import zipfile

import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

from . import datasets
from .paths import SKILLCORNER_DIR, MANIFEST_PATH, ARTIFACTS_DIR, TRAINING_REPORT_PATH, PUBLIC_GT_PATH
from .config import ACTIVE_EXPERIMENT, ACTIVE_EXCLUDE, ACTIVE_DEAD_EXCLUDE, ACTIVE_POSSESSION_EXCLUDE, GB_PARAMS, DECODER
from .core.classifiers import Stage1
from .match_policy import pre_kickoff_blocks

ROOT = Path(__file__).resolve().parent


def source_hash():
    digest = hashlib.sha256()
    for p in sorted(ROOT.glob('*.py')) + sorted((ROOT/'core').glob('*.py')):
        digest.update(p.name.encode())
        digest.update(p.read_bytes())
    manifest = MANIFEST_PATH
    if manifest.exists():
        digest.update(manifest.read_bytes())
    # Include local tactical inputs and scoring definition in cache provenance.
    from games import asset_paths
    paths = asset_paths(source='tactical')
    for p in [Path(paths['atd_meta']), Path(paths['atd_raw']),
              ROOT.parent/'games.py', ROOT.parent/'evaluation/possession_metrics.py',
              PUBLIC_GT_PATH]:
        with p.open('rb') as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
    return digest.hexdigest()


def unit(name, fingerprint):
    cache = ROOT/'cache'/fingerprint[:16]/f'{name}.pkl'
    if cache.exists():
        with cache.open('rb') as f:
            return pickle.load(f)
    print(f'Preparing {name}', flush=True)
    if name.startswith('skillcorner_'):
        match, labels, extra = datasets.load_skillcorner(int(name.split('_')[-1]))
    else:
        match, labels, extra = datasets.load_barca()
    result = (datasets.extract(match), labels, match.halves, datasets.audit_match(match, labels, extra))
    cache.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache.with_suffix(f'.{os.getpid()}.tmp')
    with temporary.open('wb') as f:
        pickle.dump(result, f, protocol=5)
    temporary.replace(cache)
    return result


def training_split():
    """Use all 20 SkillCorner matches for training; Barcelona is evaluation only."""
    matches = json.loads((SKILLCORNER_DIR/'matches.json').read_text())
    assert len(matches) == 20
    return [f'skillcorner_{m["id"]}' for m in sorted(matches, key=lambda m: m['id'])], ['barca']


def execute(threads=6):
    experiment = ACTIVE_EXPERIMENT
    started = time.time()
    fingerprint = source_hash()
    train_names, evaluation_names = training_split()
    artifacts = ARTIFACTS_DIR
    artifacts.mkdir(parents=True, exist_ok=True)
    # Freeze source before fitting so later edits cannot obscure what ran.
    with zipfile.ZipFile(artifacts/'source_snapshot.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(ROOT.glob('*.py')) + sorted((ROOT/'core').glob('*.py')):
            archive.write(p, str(p.relative_to(ROOT)))
        archive.write(MANIFEST_PATH, 'data_manifest.json')
    audit = []

    def training_items():
        for name in train_names:
            feats, labels, _, metadata = unit(name, fingerprint)
            audit.append(metadata)
            print(f'Training input {name}: {metadata["graded_frames"]} graded frames', flush=True)
            yield feats, labels

    model = Stage1(exclude=ACTIVE_EXCLUDE,
                   dead_exclude=ACTIVE_DEAD_EXCLUDE,
                   possession_exclude=ACTIVE_POSSESSION_EXCLUDE)
    with threadpool_limits(limits=threads):
        model.fit(training_items())
        trained_at = time.time()
        print(f'{experiment}: fit complete in {trained_at-started:.1f}s', flush=True)
        with (artifacts/'model.pkl').open('wb') as f:
            pickle.dump(model, f, protocol=5)
        test_audit = {}
        for target in evaluation_names:
            feats, labels, halves, metadata = unit(target, fingerprint)
            pd_, ph = model.predict(feats)
            test_audit[target] = metadata
            np.savez_compressed(artifacts/f'{target}_probabilities.npz', p_dead=pd_, p_home_given_alive=ph)
    report = dict(experiment=experiment, train_matches=train_names, evaluation_matches=evaluation_names,
                  source_sha256=fingerprint, model_sha256=hashlib.sha256((artifacts/'model.pkl').read_bytes()).hexdigest(),
                  synthetic_augmentation=False, model_parameters=GB_PARAMS, decoder_parameters=DECODER,
                  deduplicate_dead=model.deduplicate_dead, exclude=model.exclude,
                  dead_exclude=model.dead_exclude, possession_exclude=model.possession_exclude,
                  input_counts={"dead": model.dead.n_features_in_, "possession": model.poss.n_features_in_},
                  barca_postprocessing={'known_dead_ball_blocks': pre_kickoff_blocks()},
                  versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__, sklearn=sklearn.__version__),
                  training_seconds=trained_at-started, total_seconds=time.time()-started,
                  feature_names=dict(team=model.names[0], shared=model.names[1]),
                  training_audit=audit, evaluation_audit=test_audit, results={})
    TRAINING_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRAINING_REPORT_PATH.write_text(json.dumps(report, indent=2)+'\n')
    from .submission import export_active
    export_active()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--threads', type=int, default=6)
    args = parser.parse_args()
    execute(args.threads)
