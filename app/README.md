# Who Has the Ball Possession? · dashboard

## Run

After [data setup and training](../README.md#run), launch from the repository root:

```bash
pipenv run streamlit run app/main.py
```

Run the app and browser on the same computer. The app serves video through a local
HTTP endpoint and reads the validated `model/our_model.csv` without fitting a model.

## Views

- **Video and tracking:** playback and seeking keep the selected camera's animation synchronized.
- **Possession:** the tactical view displays our model's labels, a public-ground-truth timeline,
  and baseline scores. Broadcast uses its own tracking and has no tactical possession labels.
- **Camera coverage:** shading shows the visible pitch area using each frame's homography.
  Invalid mappings hide the shading.
- **Smart Tags:** automatic tactical annotations active at the current time; they are not model inputs.

## Alignment

Both recordings have independent timelines. Each tracking row aligns with its own video:
`video_frame = frame_id - 1`. Playback uses kickoff-trimmed copies created by the setup script,
then maps time back to the original recording for tracking, tags, and possession labels.

Tracking loads in one-minute windows at 5 Hz and is interpolated for display; homographies
retain their native frame rate. Player numbers identify tracking slots, not shirt numbers.
See [model details](../model/README.md) for training and label assumptions.
