"""Repository paths shared by training, submission export, and the app."""
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent
SKILLCORNER_DIR = PROJECT_ROOT / 'data' / 'skillcorner'
MANIFEST_PATH = SKILLCORNER_DIR / 'manifest.json'
ARTIFACTS_DIR = MODEL_DIR / 'artifacts'
REPORTS_DIR = MODEL_DIR / 'reports'
TRAINING_REPORT_PATH = REPORTS_DIR / 'training.json'
SUBMISSION_PATH = MODEL_DIR / 'our_model.csv'
PUBLIC_GT_PATH = PROJECT_ROOT / 'evaluation' / 'ground_truth' / 'BAR-ATH_possession_gt_public.csv'
BASELINES_DIR = PROJECT_ROOT / 'evaluation' / 'baselines'
