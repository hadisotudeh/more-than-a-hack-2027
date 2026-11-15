"""Fetch pinned external datasets, keeping tracking files unchanged."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time
import urllib.request

from .paths import SKILLCORNER_DIR, MANIFEST_PATH
SC_REV = "4340d274572876239c154c90bc507a9b3250a656"


def fetch(url, target, expected=None):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if expected is None or hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            return target
    for attempt in range(4):
        try:
            digest = hashlib.sha256()
            with urllib.request.urlopen(url, timeout=180) as source, target.with_suffix(target.suffix + '.part').open('wb') as out:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
                    out.write(chunk)
            if expected and digest.hexdigest() != expected:
                raise ValueError(f'Checksum mismatch: {url}')
            target.with_suffix(target.suffix + '.part').replace(target)
            return target
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def skillcorner_one(match):
    mid = match['id']
    folder = SKILLCORNER_DIR / str(mid)
    base = f'https://raw.githubusercontent.com/SkillCorner/opendata/{SC_REV}/data/matches/{mid}'
    for suffix in ('match.json', 'phases_of_play.csv'):
        fetch(f'{base}/{mid}_{suffix}', folder / f'{mid}_{suffix}')
    name = f'{mid}_tracking_extrapolated.jsonl'
    pointer = fetch(f'{base}/{name}', folder / 'tracking.lfs').read_text()
    digest = pointer.split('oid sha256:')[1].split()[0]
    fetch(f'https://media.githubusercontent.com/media/SkillCorner/opendata/{SC_REV}/data/matches/{mid}/{name}?download=1', folder / name, digest)
    print(f'Downloaded SkillCorner {mid}', flush=True)


def main():
    index = fetch(f'https://raw.githubusercontent.com/SkillCorner/opendata/{SC_REV}/data/matches.json', SKILLCORNER_DIR/'matches.json')
    jobs = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for m in json.loads(index.read_text()):
            jobs.append(pool.submit(skillcorner_one, m))
        for future in as_completed(jobs):
            future.result()
    manifest = {'skillcorner_revision': SC_REV, 'files': {}}
    for path in sorted(SKILLCORNER_DIR.rglob('*')):
        if path.is_file() and path.name != 'manifest.json':
            manifest['files'][str(path.relative_to(SKILLCORNER_DIR.parent))] = hashlib.sha256(path.read_bytes()).hexdigest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print('All datasets ready.', flush=True)


if __name__ == '__main__':
    main()
