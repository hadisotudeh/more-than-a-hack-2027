"""Checks for match-bundle installation without network access or real videos."""
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tools import setup_data


class BundleTests(unittest.TestCase):
    def test_nested_zip_installs_only_expected_names_and_preserves_existing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            required = setup_data.required_files(root / 'data')
            existing = next(iter(required.values()))
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b'existing')
            bundle = root / 'bundle.zip'
            with zipfile.ZipFile(bundle, 'w') as archive:
                for name in required:
                    archive.writestr('bundle/nested/' + name, b'asset')
                archive.writestr('../../unexpected.txt', b'not extracted')
            setup_data.install_bundle(bundle, required)
            self.assertTrue(all(setup_data.present(p) for p in required.values()))
            self.assertEqual(existing.read_bytes(), b'existing')
            self.assertFalse((root / 'unexpected.txt').exists())

    def test_tar_ignores_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'data' / 'asset.txt'
            bundle = root / 'bundle.tar.gz'
            with tarfile.open(bundle, 'w:gz') as archive:
                link = tarfile.TarInfo('asset.txt')
                link.type = tarfile.SYMTYPE
                link.linkname = '/etc/passwd'
                archive.addfile(link)
                info = tarfile.TarInfo('nested/asset.txt')
                info.size = 4
                archive.addfile(info, io.BytesIO(b'data'))
            setup_data.install_bundle(bundle, {'asset.txt': target})
            self.assertEqual(target.read_bytes(), b'data')
            self.assertFalse(target.is_symlink())

    def test_interrupted_copy_does_not_publish_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'asset.txt'
            with patch.object(setup_data.shutil, 'copyfileobj', side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):
                    setup_data.install_stream(io.BytesIO(b'data'), target)
            self.assertFalse(target.exists())

    def test_existing_assets_skip_drive_and_video_processing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in setup_data.required_files(root).values():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'asset')
            for source in setup_data.OFFSETS:
                path = root / source / f'BAR-ATH_{source}_cropped.mp4'
                path.write_bytes(b'video')
            with (patch('sys.argv', ['setup_data.py', '--data-dir', str(root)]),
                  patch.object(setup_data.shutil, 'which', return_value='/usr/bin/ffmpeg'),
                  patch.object(setup_data, 'download_match') as drive,
                  patch.object(setup_data.subprocess, 'run') as ffmpeg,
                  patch('model.download.main') as training):
                setup_data.main()
                drive.assert_not_called()
                ffmpeg.assert_not_called()
                training.assert_called_once()


if __name__ == '__main__':
    unittest.main()
