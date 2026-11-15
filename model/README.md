# Possession model

Two scikit-learn `HistGradientBoostingClassifier` models estimate dead-ball probability
and the possessing team during live play. A Viterbi decoder turns frame probabilities
into possession intervals. Training uses 20 SkillCorner matches; Barcelona public labels
are used for evaluation only. Future observations make inference offline.

See the root [pipeline and feature table](../README.md#pipeline),
[exact feature inventory](FEATURES.md), and [evaluation results](RESULTS.md).

## Train and export

From the repository root, with Python 3.14 and FFmpeg installed:

```bash
pipenv sync
pipenv run python tools/setup_data.py
pipenv run python -m model.run --threads 6
```

Training saves the active model under `model/artifacts/`, evaluates the
public window, and exports the validated `model/our_model.csv` used by the app.
Training provenance and held-out results are in `model/reports/`.
SkillCorner data and checksums live in `data/skillcorner/`. Downloaded data, feature caches,
fitted weights, and generated CSVs are ignored by Git.

To regenerate the submission from saved probabilities without retraining:

```bash
pipenv run python -m model.submission
pipenv run python evaluation/validate_submission.py model/our_model.csv
```

The submission contains exactly `frame,label`, 199,319 rows indexed 0–199318, and
`H/A/D/X` labels. Invalid exports preserve the previous CSV. The validation receipt
records the checksum, label counts, and public scores. The app reads these exact labels.

## Training and limitations

Both classifiers use 600 rounds, learning rate 0.05, at most 31 leaves, minimum leaf size
400, L2 regularization 1, seed 0, and no early stopping. Training samples every second
10 Hz frame. Both teams are treated symmetrically. Features reset at each half;
implausible ball jumps are removed and gaps up to 0.4 seconds are interpolated.
Longer gaps remain missing. No synthetic augmentation is used.

SkillCorner possession phases supply home/away labels. Remaining frames within each
half are assumed dead ball, so incomplete annotations can introduce label errors.
The held-out matches and Barcelona public window were repeatedly inspected; their
scores are not blind-test performance.

Graded second-half setup frames 110,808–113,741 are forced to dead ball after decoding;
frame 113,742 remains predicted. This leaves the first-half public scores unchanged.

See [source and data provenance](PROVENANCE.md) and the
[hackathon repository](https://github.com/hadisotudeh/more-than-a-hack-2027)
for competition rules and submission requirements.
