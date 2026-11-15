"""Verify that training, prediction refresh, and the app select the promoted model."""
import json
import pickle
import unittest
from pathlib import Path
import numpy as np
from app.possession import MODEL_OPTIONS, prediction_path, prediction_version, load_model_labels
from model.config import ACTIVE_EXPERIMENT, ACTIVE_EXCLUDE, ACTIVE_DEAD_EXCLUDE, ACTIVE_POSSESSION_EXCLUDE
from model.run import training_split
from model.paths import ARTIFACTS_DIR, TRAINING_REPORT_PATH, PUBLIC_GT_PATH
from evaluation import possession_metrics as pm
from model.core.decode import decode
from model.match_policy import apply_known_dead_ball
from games import GAME, half_video_blocks

ROOT=Path(__file__).resolve().parents[1]


class ActiveModelTests(unittest.TestCase):
    def test_active_paths_and_training_split(self):
        self.assertEqual(MODEL_OPTIONS, {'Our model': ACTIVE_EXPERIMENT})
        path=prediction_path('Our model')
        self.assertEqual(path,ROOT/'model/our_model.csv')
        self.assertEqual(prediction_version('Our model')[0],str(path))
        train,evaluation=training_split()
        self.assertEqual(len(train),20)
        self.assertEqual(evaluation,['barca'])

    def test_promoted_checkpoint_and_app_predictions(self):
        with (ARTIFACTS_DIR/'model.pkl').open('rb') as f:model=pickle.load(f)
        self.assertTrue(model.deduplicate_dead)
        self.assertEqual(model.exclude, ACTIVE_EXCLUDE)
        self.assertEqual(model.dead_exclude, ACTIVE_DEAD_EXCLUDE)
        self.assertEqual(model.possession_exclude, ACTIVE_POSSESSION_EXCLUDE)
        self.assertEqual(model.dead.n_features_in_,121)
        self.assertEqual(model.poss.n_features_in_,108)
        for name in ['own_cx_m1.0','opp_cx_m1.0','own_cx_m3.0','opp_cx_m3.0']:
            self.assertNotIn(name,model.names[0])
        self.assertEqual(model.dead.n_iter_,600)
        self.assertEqual(model.poss.n_iter_,600)
        labels=load_model_labels('Our model')
        report=json.loads(TRAINING_REPORT_PATH.read_text())
        with np.load(ARTIFACTS_DIR/'barca_probabilities.npz') as probabilities:
            expected=apply_known_dead_ball(decode(
                probabilities['p_dead'],probabilities['p_home_given_alive'],
                [(a,b+1) for _,a,b in half_video_blocks(GAME)],len(labels),report['decoder_parameters']))
        np.testing.assert_array_equal(labels,expected)
        scores=pm.evaluate(pm.label_codes(pm.read_label_csv(PUBLIC_GT_PATH)),pm.label_codes(labels))
        reported=json.loads(TRAINING_REPORT_PATH.read_text())['results']['barca']
        self.assertAlmostEqual(scores['spell_f1_mean'],reported['spell_f1_mean'])
        self.assertAlmostEqual(scores['macro_f1'],reported['macro_f1'])


if __name__=='__main__': unittest.main()
