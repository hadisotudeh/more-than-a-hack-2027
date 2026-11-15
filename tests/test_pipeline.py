"""Alignment, native-data preservation, temporal boundaries, and split checks."""
import unittest
from dataclasses import replace
import numpy as np
import pandas as pd

from model.datasets import skillcorner_labels, load_barca, load_skillcorner, extract
from model.core.io import Match
from model.core.classifiers import spell_weights


class PipelineTests(unittest.TestCase):
    def test_barca_pre_kickoff_exact_boundaries(self):
        from model.match_policy import apply_known_dead_ball, pre_kickoff_blocks
        self.assertEqual(pre_kickoff_blocks(), [(110808, 113742)])
        labels = np.full(199319, 'H', dtype='<U1')
        corrected = apply_known_dead_ball(labels)
        self.assertTrue(np.all(corrected[110808:113742] == 'D'))
        self.assertEqual(int(np.sum(corrected == 'D')), 2934)
        self.assertEqual(corrected[110807], 'H')
        self.assertEqual(corrected[113742], 'H')
        self.assertEqual(corrected[11185], 'H')
        self.assertTrue(np.all(labels == 'H'))

    def test_skillcorner_training_keeps_barcelona_held_out(self):
        from model.run import training_split
        training, evaluation = training_split()
        self.assertEqual(len(set(training)), 20)
        self.assertEqual(evaluation, ['barca'])

    def test_phase_boundaries_and_dead_complement(self):
        phases = pd.DataFrame([dict(frame_start=2, frame_end=5, team_in_possession_id=10),
                               dict(frame_start=5, frame_end=7, team_in_possession_id=20)])
        labels = skillcorner_labels(phases, [(1, 9)], 10, 10, 20)
        self.assertEqual(''.join(labels), 'XDHHHAADDX')

    def test_overlapping_team_labels_rejected(self):
        phases = pd.DataFrame([dict(frame_start=2, frame_end=6, team_in_possession_id=10),
                               dict(frame_start=5, frame_end=7, team_in_possession_id=20)])
        with self.assertRaises(ValueError):
            skillcorner_labels(phases, [(1, 9)], 10, 10, 20)

    def test_phase_overrun_does_not_label_next_half(self):
        phases = pd.DataFrame([dict(frame_start=3, frame_end=9,
                                   team_in_possession_id=10, period=1)])
        labels = skillcorner_labels(phases, [(1,5),(6,10)], 11, 10, 20)
        self.assertEqual(''.join(labels), 'XDDHHXDDDDX')

    def test_native_arrays_unchanged_and_no_cross_half_context(self):
        n = 300
        x = np.tile([20., 30., 70., 80.], (n, 1)).astype(np.float32)
        ball = np.full(n, 21., dtype=np.float32)
        ball[40:80] = np.nan
        m = Match(x=x, y=np.full_like(x, 34.), speed=np.full_like(x, np.nan),
                  team=np.array([0, 0, 1, 1]), ball_x=ball,
                  ball_y=np.where(np.isfinite(ball), 34., np.nan), pitch=(105.,68.),
                  fps=10, halves=[(0,150), (150,300)])
        before = m.ball_x.copy()
        f = extract(m)
        np.testing.assert_array_equal(m.ball_x, before)
        self.assertTrue(np.all(f['shared']['ball_known'][40:80] == 0))
        altered = m.ball_x.copy(); altered[150:] = 80.
        g = extract(replace(m, ball_x=altered))
        for name in f['shared']:
            np.testing.assert_array_equal(f['shared'][name][:150], g['shared'][name][:150])

    def test_possession_weight_seconds(self):
        for fps in (10,25):
            labels = np.array(['H']*(8*fps)+['A']*(4*fps)+['D']*fps)
            w = spell_weights(labels, 8*fps)
            self.assertTrue(np.all(w[:8*fps] == 1))
            self.assertTrue(np.all(w[8*fps:12*fps] == 2))

    def test_external_and_public_alignment(self):
        match, labels, _ = load_barca()
        scored = np.flatnonzero(labels != 'X')
        self.assertEqual((scored[0],scored[-1],len(scored)), (11185,18684,7500))
        self.assertEqual(match.halves[1][0], 110808)
        match, labels, _ = load_skillcorner(2017461)
        self.assertEqual(int(np.sum(labels != 'X')), 58452)
        self.assertEqual(int(np.sum(np.isfinite(match.ball_x))), 40404)


if __name__ == '__main__':
    unittest.main()
