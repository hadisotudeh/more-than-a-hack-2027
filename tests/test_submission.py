"""Submission export uses the official contract and never publishes invalid output."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from games import GAME,GAMES
from evaluation import possession_metrics as pm
from model.submission import export_labels,SUBMISSION_PATH
from app.possession import load_model_labels,prediction_path


class SubmissionTests(unittest.TestCase):
    def test_roundtrip_and_match_policy(self):
        labels=np.full(GAMES[GAME]['n_video_frames'],'H')
        with tempfile.TemporaryDirectory() as folder:
            path=export_labels(labels,Path(folder)/'ready.csv')
            saved=pm.read_label_csv(path)
            self.assertIsNone(pm.validate_submission(saved,len(labels)))
            self.assertEqual(saved.columns.tolist(),['frame','label'])
            self.assertTrue((saved.label.iloc[110808:113742]=='D').all())
            self.assertEqual(saved.label.iloc[113742],'H')
            self.assertTrue((labels=='H').all())

    def test_bad_input_preserves_existing_submission(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ready.csv';path.write_text('existing valid artifact')
            for labels in [np.array(['H']),np.full(GAMES[GAME]['n_video_frames'],'INVALID')]:
                with self.assertRaises(ValueError):export_labels(labels,path)
                self.assertEqual(path.read_text(),'existing valid artifact')

    def test_invalid_written_bytes_are_not_published(self):
        def bad_writer(path,labels):Path(path).write_text('frame,label\n1,H\n')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ready.csv';path.write_text('previous')
            with patch('model.submission.write_submission',side_effect=bad_writer):
                with self.assertRaises(ValueError):export_labels(np.full(GAMES[GAME]['n_video_frames'],'H'),path)
            self.assertEqual(path.read_text(),'previous')
            self.assertEqual(list(Path(folder).glob('.submission-*')),[])

    def test_app_reads_upload_file_without_label_changes(self):
        self.assertEqual(prediction_path('Our model'),SUBMISSION_PATH)
        np.testing.assert_array_equal(load_model_labels('Our model'),pm.read_label_csv(SUBMISSION_PATH).label.to_numpy())


if __name__=='__main__':unittest.main()
