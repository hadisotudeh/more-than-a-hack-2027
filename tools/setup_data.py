"""Download training/match data and prepare app playback: pipenv run python tools/setup_data.py."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from games import asset_paths

DRIVE_URL = 'https://drive.google.com/drive/folders/18KTDrUQX4sZXFfWnRcz09-FTehburY_K'
OFFSETS = {'tactical': '443.88', 'broadcast': '286.00'}


def required_files(data_dir):
    return {Path(path).name: Path(path) for source in OFFSETS
            for path in asset_paths(data_dir=str(data_dir), source=source).values()}


def present(path):
    return path.is_file() and path.stat().st_size > 0


def install_stream(source, target):
    """Only complete files replace destinations; interrupted copies remain .part."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.part')
    with temporary.open('wb') as output:
        shutil.copyfileobj(source, output, length=1024 * 1024)
    if not present(temporary):
        raise ValueError(f'Empty asset: {target.name}')
    temporary.replace(target)
    print(f'Ready: {target}', flush=True)


def install_bundle(bundle, required):
    """Copy only expected filenames, never extract archive paths or links."""
    def wanted(name):
        target = required.get(Path(name).name)
        return target if target is not None and not present(target) else None

    if bundle.is_dir():
        for path in sorted(bundle.rglob('*')):
            if path.is_file() and (target := wanted(path.name)):
                with path.open('rb') as source:
                    install_stream(source, target)
        for path in sorted(bundle.rglob('*')):
            if path.is_file() and is_archive(path.name):
                install_bundle(path, required)
    elif zipfile.is_zipfile(bundle):
        with zipfile.ZipFile(bundle) as archive:
            for member in archive.infolist():
                if not member.is_dir() and (target := wanted(member.filename)):
                    with archive.open(member) as source:
                        install_stream(source, target)
    elif tarfile.is_tarfile(bundle):
        with tarfile.open(bundle) as archive:
            for member in archive:
                if member.isfile() and (target := wanted(member.name)):
                    with archive.extractfile(member) as source:
                        install_stream(source, target)
    else:
        raise ValueError(f'Expected a folder, ZIP, or TAR bundle: {bundle}')


def is_archive(name):
    return name.lower().endswith(('.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tar.xz'))


def download_match(data_dir, required, url):
    try:
        import gdown
    except ImportError as error:
        raise RuntimeError('Install the downloader: pipenv sync') from error
    staging = data_dir / '.downloads'
    staging.mkdir(parents=True, exist_ok=True)
    try:
        entries = gdown.download_folder(url=url, output=str(staging), skip_download=True, quiet=True)
        if not entries:
            raise RuntimeError('Google Drive returned no downloadable files.')
        for entry in entries:
            name = Path(entry.path).name
            target = required.get(name)
            if target is not None and not present(target):
                temporary = target.with_name(target.name + '.part')
                target.parent.mkdir(parents=True, exist_ok=True)
                if not gdown.download(id=entry.id, output=str(temporary), resume=True):
                    raise RuntimeError(f'Download failed: {name}')
                if not present(temporary):
                    raise RuntimeError(f'Empty download: {name}')
                temporary.replace(target)
            elif is_archive(name) and any(not present(p) for p in required.values()):
                # Use the Drive ID rather than an untrusted remote path.
                archive = staging / (entry.id + '-' + name)
                if not present(archive):
                    partial = archive.with_name(archive.name + '.part')
                    if not gdown.download(id=entry.id, output=str(partial), resume=True):
                        raise RuntimeError(f'Download failed: {name}')
                    partial.replace(archive)
                install_bundle(archive, required)
    except Exception as error:
        raise RuntimeError(
            f'Cannot download the competition bundle: {error}\n'
            'The Drive folder must allow your download; sign-in-only links cannot be fetched '
            'by gdown. Download the bundle in your browser, then rerun with --bundle PATH '
            '(a ZIP/TAR file or extracted folder).'
        ) from error


def prepare_videos(data_dir, ffmpeg):
    for source, offset in OFFSETS.items():
        original = Path(asset_paths(data_dir=str(data_dir), source=source)['video'])
        target = original.with_name(original.stem + '_cropped.mp4')
        if present(target):
            print(f'Already ready: {target}', flush=True)
            continue
        temporary = target.with_name(target.stem + '.part.mp4')
        subprocess.run([ffmpeg, '-nostdin', '-y', '-ss', offset, '-i', str(original),
                        '-map', '0', '-c', 'copy', '-movflags', '+faststart', str(temporary)], check=True)
        temporary.replace(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('MTAH_DATA_DIR') or ROOT / 'data'))
    parser.add_argument('--drive-url', default=DRIVE_URL)
    parser.add_argument('--bundle', type=Path, help='Use an already downloaded match bundle instead of Drive')
    args = parser.parse_args()
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        parser.exit(1, 'FFmpeg is required. Install it and rerun this command.\n')
    required = required_files(args.data_dir.resolve())
    try:
        if any(not present(path) for path in required.values()):
            if args.bundle:
                install_bundle(args.bundle.resolve(), required)
            else:
                download_match(args.data_dir.resolve(), required, args.drive_url)
        missing = [str(path) for path in required.values() if not present(path)]
        if missing:
            raise RuntimeError('Bundle is incomplete; missing:\n' + '\n'.join(missing))
        prepare_videos(args.data_dir.resolve(), ffmpeg)
        from model.download import main as download_training
        download_training()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Setup failed: {error}\n')
    print('Data and playback videos are ready. Next: pipenv run python -m model.run', flush=True)


if __name__ == '__main__':
    main()
