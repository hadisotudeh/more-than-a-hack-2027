# Match assets

From the repository root, run:

```bash
pipenv sync
pipenv run python tools/setup_data.py
```

Setup places hackathon files and playback videos in `tactical/` and `broadcast/`.
These assets stay out of Git. Set `MTAH_DATA_DIR` to use a different match-data folder.
SkillCorner training data is downloaded separately under `data/skillcorner/`.

See the root [setup instructions](../README.md#run) for access requirements and the
local-bundle fallback. Competition terms are in the
[hackathon repository](https://github.com/hadisotudeh/more-than-a-hack-2027).
