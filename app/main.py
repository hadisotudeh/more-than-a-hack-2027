"""Side-by-side match video and source-aligned tracking dashboard."""

from __future__ import annotations

import csv
import base64
from pathlib import Path
import sys

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pitch_component import render_tracking_pitch, serialize_frames  # noqa: E402
from app.possession_timeline import render_possession_timeline
from app.coverage import CameraMapping  # noqa: E402
from app.media_server import start_local_media_server  # noqa: E402
from app.sync import (  # noqa: E402
    format_clock,
    read_smart_tags,
    first_half_kickoff_window,
    source_kickoff_seconds,
    video_frame_at,
)
from app.possession import MODEL_OPTIONS, prediction_version, load_model_labels, possession_intervals
from app.tracking import TrackingSource  # noqa: E402
from app.video_component import render_match_video  # noqa: E402
from games import asset_paths, source_frames, half_video_blocks, GAME  # noqa: E402
from model.paths import PUBLIC_GT_PATH, BASELINES_DIR  # noqa: E402


SOURCE_OPTIONS = {
    "Tactical": "tactical",
    "Broadcast": "broadcast",
}
SMART_TAGGING_PATH = Path(asset_paths(source="tactical")["smart_tagging"])
PUBLIC_POSSESSION_PATH = PUBLIC_GT_PATH

# These offsets map time zero in each cropped MP4 back to its original source timeline. FFmpeg's
# MP4 edit list keeps any preceding decoding keyframe at a negative timestamp, so the native player
# presents the requested crop point itself as 00:00 without losing stream-copy quality.
CROPPED_VIDEO_OFFSETS = {
    "tactical": 443.88,
    "broadcast": 286.0,
}


def cropped_video_path(source: str) -> Path:
    original = Path(asset_paths(source=source)["video"])
    return original.with_name(f"{original.stem}_cropped{original.suffix}")


st.set_page_config(
    page_title="Who Has the Ball Possession?",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.html("""
<style>
  header.stAppHeader, .stAppToolbar, [data-testid="stHeader"],
  [data-testid="stToolbar"], [data-testid="stDecoration"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
  }
</style>
""")

st.markdown(
    """
    <style>
      html { font-size: 17px; }
      .stApp { background: #ffffff; color: #17202a; }
      [data-testid="stHeader"], [data-testid="stAppHeader"],
      [data-testid="stToolbar"], [data-testid="stDecoration"] {
        display: none !important;
      }
      .block-container { max-width: none; padding: .75rem 1.25rem 2.5rem; }
      h1, h2, h3, p, label, .stCaption { color: #17202a; }
      .hero-kicker { color: #667085; font-size: 1.2rem; font-weight: 800; letter-spacing: .16em; text-align: center; }
      .organizer-row { display: flex; align-items: center; justify-content: center; gap: 16px; }
      .organizer-row .hero-kicker { flex: 0 1 auto; text-align: left; }
      .organizer-row .organizer-logos { flex: 0 1 360px; min-width: 0; margin-left: 0; }
      .organizer-logos { display: flex; justify-content: flex-end;
                         align-items: center; gap: 8px; padding: 0;
                         width: min(100%, 360px); margin-left: auto; background: #ffffff;
                         border-radius: 6px; box-sizing: border-box; }
      .organizer-logos > img { display: block; width: 110px; height: 56px; object-fit: contain; min-width: 0; }
      .organizer-logos > img:last-child { width: 100px; height: 40px; flex: 0 0 100px; }
      .organizer-bih { position: relative; overflow: hidden; width: 135px;
                       aspect-ratio: 1632 / 336; flex-shrink: 1; }
      .organizer-bih img { position: absolute; display: block; width: 118%; max-width: none;
                           height: auto; left: -9%; top: -43%; }
      .match-header { display: grid; grid-template-columns: auto auto auto; align-items: center;
                      justify-content: center; gap: clamp(.45rem, 1vw, .9rem); width: 100%; margin: .45rem 0 .5rem; }
      .match-teams { display: flex; align-items: baseline; gap: clamp(.45rem, 1vw, .9rem); }
      .team-crest { width: clamp(52px, 5vw, 78px); height: clamp(52px, 5vw, 78px); object-fit: contain; }
      .hero-title { margin: 0; color: #111827 !important; font-size: clamp(1.55rem, 2.6vw, 2.8rem);
                    font-weight: 800; line-height: 1; letter-spacing: -.04em; white-space: nowrap; }
      .match-date { width: 100%; margin: 0; color: #667085; font-size: 1rem;
                    font-weight: 600; text-align: center; }
      .versus { line-height: 1; color: #98a2b3; font-size: clamp(1.3rem, 2.1vw, 2rem); font-weight: 800; letter-spacing: 0; }
      .hero-copy { max-width: 760px; margin-top: 0; color: #667085; font-size: 1.16rem; line-height: 1.6; }
      .source-note-wrap { display: flex; justify-content: flex-end; width: 100%; }
      .source-note { position: relative; width: 100%; max-width: 100%; margin-top: 0; color: #475467;
                     font-size: 1.05rem; line-height: 1.55; }
      .source-heading { position: absolute; bottom: calc(100% + .35rem); left: 0; color: #17202a; font-size: 1.08rem; }
      [data-testid="stRadio"] > div { gap: .35rem; }
      [data-testid="stRadio"] label { padding: .35rem .7rem; border: 1px solid #d0d5dd;
                                      border-radius: 999px; background: #ffffff; font-size: 1rem; }
      .st-key-camera-controls [data-testid="stRadio"] label,
      .st-key-possession-controls [data-testid="stRadio"] label {
        padding: 0; border: none; border-radius: 0; background: transparent;
      }
      .st-key-camera-controls [data-testid="stRadio"] label,
      .st-key-camera-controls [data-testid="stRadio"] label p,
      .st-key-possession-controls [data-testid="stRadio"] label,
      .st-key-possession-controls [data-testid="stRadio"] label p {
        font-size: 1.2rem; line-height: 1.5;
      }
      .st-key-camera-controls [data-testid="stWidgetLabel"] p,
      .st-key-possession-controls [data-testid="stWidgetLabel"] p {
        color: #17202a; font-size: 1.2rem; line-height: 1.5; font-weight: 700;
      }
      .st-key-camera-controls [data-testid="stRadio"] {
        display: flex; flex-direction: row; align-items: center;
        justify-content: center; width: 100%;
        flex-wrap: wrap; column-gap: 1rem; row-gap: .25rem;
      }
      .st-key-camera-controls [data-testid="stWidgetLabel"],
      .st-key-camera-controls [data-testid="stRadioGroup"] {
        width: auto !important; flex: 0 0 auto !important;
        margin: 0;
      }
      .st-key-camera-controls [data-testid="stElementContainer"] {
        width: 100%;
      }
      .st-key-camera-controls [role="radiogroup"] {
        margin-top: 0; justify-content: center;
      }
      .block-container > [data-testid="stVerticalBlock"] {
        gap: .25rem;
      }
      .camera-view-heading { margin: 0; }
      .stCaption { font-size: .96rem; line-height: 1.5; }
      .st-key-model-details p,
      .st-key-evaluation-table [data-testid="stTable"] th,
      .st-key-evaluation-table [data-testid="stTable"] td {
        font-size: 1.05rem;
      }
      @media (max-width: 640px) {
        .block-container { padding-top: 2.5rem; }
        .match-header { gap: .4rem; }
        .team-crest { width: 44px; height: 44px; }
        .hero-title { font-size: 1.3rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def tracking_source(source: str) -> TrackingSource:
    paths = asset_paths(source=source)
    return TrackingSource(paths["atd_meta"], paths["atd_raw"])


@st.cache_resource(show_spinner=False)
def camera_mapping(source: str) -> CameraMapping:
    return CameraMapping(asset_paths(source=source)["homography"])


@st.cache_data(show_spinner=False)
def tactical_kickoff_window() -> tuple[float, float]:
    event = first_half_kickoff_window(SMART_TAGGING_PATH)
    return event.start_seconds, event.end_seconds


@st.cache_data(show_spinner=False)
def tactical_smart_tags():
    return read_smart_tags(SMART_TAGGING_PATH)


def tracking_window(source, start, stop, stride):
    return tracking_source(source).iter_frames(start, stop, stride=stride)


@st.cache_data(show_spinner=False)
def model_possession(model_name: str, version):
    labels = load_model_labels(model_name)
    return labels, possession_intervals(labels)


@st.cache_data(show_spinner=False)
def public_model_scores(model_name: str, version):
    from evaluation import possession_metrics as pm
    labels, _ = model_possession(model_name, version)
    return pm.evaluate(pm.label_codes(pm.read_label_csv(PUBLIC_POSSESSION_PATH)),
                       pm.label_codes(labels))


@st.cache_data(show_spinner=False)
def baseline_comparison_rows():
    """Score the shipped hackathon baselines on the same public window as our model."""
    from evaluation import possession_metrics as pm
    truth = pm.label_codes(pm.read_label_csv(PUBLIC_POSSESSION_PATH))
    rows = []
    for name, label in (
        ("baseline_smooth125", "baseline_smooth125 (±5 s)"),
        ("baseline_smooth50", "baseline_smooth50 (±2 s)"),
        ("baseline_smooth25", "baseline_smooth25 (±1 s)"),
        ("baseline_raw", "baseline_raw (no smoothing)"),
    ):
        scores = pm.evaluate(truth, pm.label_codes(pm.read_label_csv(
            BASELINES_DIR / f"{name}.csv")))
        rows.append({
            "Model": label, "spellF1": scores["spell_f1_mean"],
            "macroF1": scores["macro_f1"], "Possessions": scores["n_pred_spells"],
            "Mean duration (s)": scores["mean_spell_duration_s"],
        })
    return rows


@st.cache_data(show_spinner=False)
def tactical_possession_intervals() -> list[dict[str, int | str]]:
    """Compress the public frame labels into intervals for the browser animation."""

    intervals: list[dict[str, int | str]] = []
    active_label: str | None = None
    active_start = 0
    previous_frame = -1
    with PUBLIC_POSSESSION_PATH.open(newline="", encoding="utf-8") as possession_file:
        for row in csv.DictReader(possession_file):
            frame = int(row["frame"])
            label = row["label"].strip().upper()
            if label == "X":
                if active_label is not None:
                    intervals.append({"start": active_start, "end": previous_frame, "label": active_label})
                    active_label = None
                previous_frame = frame
                continue
            if label != active_label:
                if active_label is not None:
                    intervals.append({"start": active_start, "end": previous_frame, "label": active_label})
                active_label = label
                active_start = frame
            previous_frame = frame
    if active_label is not None:
        intervals.append({"start": active_start, "end": previous_frame, "label": active_label})
    return intervals


@st.cache_resource(show_spinner=False)
def local_media_server():
    videos = {
        source: cropped_video_path(source)
        for source in SOURCE_OPTIONS.values()
    }
    providers = {}
    for source in SOURCE_OPTIONS.values():
        reader = tracking_source(source)
        mapping = camera_mapping(source)
        def window(start, reader=reader, mapping=mapping, source=source):
            if start >= reader.frame_count:
                raise ValueError('frame outside recording')
            stop = min(reader.frame_count, start + int(reader.fps * 60) + 1)
            return {
                'frames': serialize_frames(tracking_window(source, start, stop, 5)),
                'coverageStartFrame': start,
                'coverageMatrices': mapping.window(start, stop),
            }
        providers[source] = window
    return start_local_media_server(videos, tracking=providers)

identity_col, organizers_col = st.columns(2, gap="small", vertical_alignment="top")
with organizers_col:
    metrica_logo = base64.b64encode((ROOT / "app/assets/metrica-transparent.png").read_bytes()).decode("ascii")
    st.markdown(
        '''
        <div class="organizer-row">
        <div class="hero-kicker">More Than a Hack 2027</div>
        <div class="organizer-logos" aria-label="Event organizers">
        <img src="https://logos-world.net/wp-content/uploads/2024/10/Mobile-World-Capital-Barcelona-Logo-New.png" alt="Mobile World Capital Barcelona">
        <span class="organizer-bih"><img src="https://study-eu.s3.eu-west-1.amazonaws.com/uploads/university/bar-a-innovation-hub-logo.png" alt="Barça Innovation Hub"></span>
        <img src="data:image/png;base64,METRICA_LOGO" alt="Metrica Sports">
        </div>
        </div>'''.replace("METRICA_LOGO", metrica_logo),
        unsafe_allow_html=True,
    )
with identity_col:    
    st.markdown(
        '''
        <div class="match-header">
          <img class="team-crest" src="https://upload.wikimedia.org/wikipedia/en/4/47/FC_Barcelona_%28crest%29.svg" alt="FC Barcelona crest">
          <div class="match-teams">
            <div class="hero-title">Barcelona</div>
            <span class="versus">VS</span>
            <div class="hero-title">Athletic Club</div>
          </div>
          <img class="team-crest" src="https://upload.wikimedia.org/wikipedia/en/9/98/Club_Athletic_Bilbao_logo.svg" alt="Athletic Club crest">
        </div>
        ''',
        unsafe_allow_html=True,
    )

date_col, camera_col = st.columns(2, gap="small", vertical_alignment="center")
with date_col:
    st.markdown('<div class="match-date">August 24, 2024</div>', unsafe_allow_html=True)
with camera_col:
    with st.container(key="camera-controls"):
        selected_label = st.radio(
            "**Camera View:**",
            list(SOURCE_OPTIONS),
            horizontal=True,
        )

source = SOURCE_OPTIONS[selected_label]
kickoff_offset = source_kickoff_seconds(source, SMART_TAGGING_PATH)
video_time_offset = CROPPED_VIDEO_OFFSETS[source]
fps = tracking_source(source).fps

clip_duration = 60  # Initial buffer; subsequent windows load while playback continues.
video_start = 0.0
source_start = video_start + video_time_offset
source_end = min(source_frames(source) / fps, source_start + clip_duration)
start_frame = video_frame_at(source_start, fps)
stop_frame = min(source_frames(source), video_frame_at(source_end, fps) + 1)
sample_stride = max(1, round(fps / 5))
sync_id = f"{source}-{start_frame}-{stop_frame}"

if source == "tactical":
    tag_start, tag_end = tactical_kickoff_window()
    anchor_copy = f"Smart Tag kickoff window {format_clock(tag_start)}–{format_clock(tag_end)}"
else:
    anchor_copy = f"Broadcast kickoff anchor {format_clock(kickoff_offset)}"

try:
    model_versions = {name: prediction_version(name) for name in MODEL_OPTIONS}
except FileNotFoundError:
    st.error("Submission CSV is missing. Run python -m model.submission from the repository root.")
    st.stop()

model_name = next(iter(MODEL_OPTIONS))
display_intervals = (model_possession(model_name, model_versions[model_name])[1]
                     if source == "tactical" else None)

with st.spinner("Reading the selected tracking window…"):
    frames = list(
        tracking_window(
            source,
            start_frame,
            stop_frame,
            stride=sample_stride,
        )
    )

video_col, pitch_col = st.columns(2, gap="small")
with video_col:
    video_path = cropped_video_path(source)
    if not video_path.is_file():
        st.error(f"Video not found: {video_path}")
    else:
        render_match_video(
            url=local_media_server().url_for(source),
            label=f"{selected_label} recording of Barcelona versus Athletic Club",
            start_time=video_start,
            sync_id=sync_id,
            key=f"video-{sync_id}",
        )

    scores = public_model_scores(model_name, model_versions[model_name])
    st.markdown(f"### Public 5-min evaluation: {scores['n_gt_spells']} possessions")
    if source == "tactical":
        render_possession_timeline(
            intervals=display_intervals, ground_truth=tactical_possession_intervals(),
            fps=fps, sync_id=sync_id, video_time_offset=video_time_offset,
            start_time=video_start,
        )
    comparison_rows = []
    import pandas as pd
    for model_name in MODEL_OPTIONS:
        scores = public_model_scores(model_name, model_versions[model_name])
        comparison_rows.append({
            "Model": model_name, "spellF1": scores["spell_f1_mean"],
            "macroF1": scores["macro_f1"], "Possessions": scores["n_pred_spells"],
            "Mean duration (s)": scores["mean_spell_duration_s"],
        })
    comparison_rows.extend(baseline_comparison_rows())
    comparison_table = pd.DataFrame(comparison_rows).rename(columns={"Possessions": "\\# Possessions"})
    styled_comparison = comparison_table.style.apply(
        lambda row: ["font-weight: bold" if row["Model"] in MODEL_OPTIONS else ""] * len(row),
        axis=1,
    ).format({
        "Model": lambda name: f"[{name}](https://github.com/hadisotudeh/more-than-a-hack-2027/blob/main/README.md)"
        if name in MODEL_OPTIONS else name,
        "spellF1": "{:.2f}", "macroF1": "{:.2f}", "Mean duration (s)": "{:.2f}",
    })
    styled_comparison = styled_comparison.set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    with st.container(key="evaluation-table"):
        st.table(styled_comparison.hide(axis="index"))
    with st.container(key="model-details"):
        st.caption("For details about our possession model, please refer to the [README](https://github.com/hadisotudeh/more-than-a-hack-2027/blob/main/README.md).")

with pitch_col:
    render_tracking_pitch(
        frames=frames,
        camera_label=selected_label,
        fps=fps,
        kickoff_offset=kickoff_offset,
        start_time=video_start,
        video_time_offset=video_time_offset,
        sync_id=sync_id,
        key=f"tracking-{sync_id}",
        tracking_url=local_media_server().tracking_url_for(source),
        total_frames=source_frames(source),
        half_intervals=[{"half": half, "start": start, "end": end}
                        for half, start, end in half_video_blocks(GAME)]
        if source == "tactical" else None,
        coverage_start_frame=start_frame,
        coverage_matrices=camera_mapping(source).window(start_frame, stop_frame),
        smart_tags=tactical_smart_tags() if source == "tactical" else None,
        possession_intervals=display_intervals,
    )
