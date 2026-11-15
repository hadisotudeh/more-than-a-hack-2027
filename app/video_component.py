"""Range-streamed HTML5 video component for the dashboard."""

from __future__ import annotations

import streamlit as st


VIDEO_HTML = """
<div class="touchline-video-heading">VIDEO</div>
<section class="touchline-video-shell">
  <video class="touchline-match-video" controls muted preload="metadata" playsinline></video>
  <div class="touchline-video-status" aria-live="polite">Loading video metadata…</div>
</section>
"""


VIDEO_CSS = """
.touchline-video-heading {
  display: block; margin: 0; padding: 0 0 10px;
  color: #667085; font: 800 15.3px/22px var(--st-font, ui-sans-serif, system-ui, sans-serif);
  letter-spacing: .13em;
}
:host { font-size: 17px; }
.touchline-video-shell {
  position: relative; width: 100%; aspect-ratio: 16 / 9; display: grid; place-items: center;
  box-sizing: border-box;
  overflow: hidden; border: 1px solid #e4e7ec; border-radius: 18px;
  background: #050706; box-shadow: 0 12px 32px rgba(16,24,40,.08);
}
.touchline-match-video {
  position: absolute; inset: 0; display: block; width: 100%; height: 100%; object-fit: contain; background: #050706;
}
.touchline-video-status {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  padding: 8px 12px; border-radius: 999px; color: #dce7e0; background: rgba(4,12,8,.78);
  font: 600 .96rem var(--st-font, ui-sans-serif, system-ui, sans-serif); pointer-events: none;
}
.touchline-video-status[hidden] { display: none; }
"""


VIDEO_JS = r"""
export default function(component) {
  const { parentElement, data } = component;
  const video = parentElement.querySelector('.touchline-match-video');
  const status = parentElement.querySelector('.touchline-video-status');

  const seekToStart = () => {
    if (!Number.isFinite(video.duration)) return;
    video.currentTime = Math.min(data.startTime, video.duration);
    status.hidden = true;
  };
  const showError = () => {
    status.textContent = 'Unable to load the local video stream';
    status.hidden = false;
  };
  const seekWithKeyboard = event => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    if (!Number.isFinite(video.duration)) return;
    event.preventDefault();
    event.stopPropagation();
    const delta = event.key === 'ArrowRight' ? 5 : -5;
    video.currentTime = Math.max(0, Math.min(video.duration, video.currentTime + delta));
  };

  video.dataset.matchVideo = data.syncId;
  video.tabIndex = 0;
  video.title = 'Click or Tab to focus. Left / Right arrow: seek backward / forward 5 seconds.';
  video.setAttribute('aria-keyshortcuts', 'ArrowLeft ArrowRight');
  video.setAttribute('aria-label', data.label);
  video.addEventListener('keydown', seekWithKeyboard, true);
  video.addEventListener('loadedmetadata', seekToStart);
  video.addEventListener('error', showError);
  video.defaultMuted = true;
  video.muted = true;
  video.src = data.url;
  video.load();
  if (video.readyState >= 1) seekToStart();

  return () => {
    video.removeEventListener('keydown', seekWithKeyboard, true);
    video.removeEventListener('loadedmetadata', seekToStart);
    video.removeEventListener('error', showError);
    video.pause();
    video.removeAttribute('data-match-video');
    video.removeAttribute('src');
    video.load();
  };
}
"""


# Style isolation is disabled intentionally so the adjacent tracking component can locate the
# video element and read ``currentTime``. Component JavaScript remains trusted local source.
match_video = st.components.v2.component(
    "touchline_match_video",
    html=VIDEO_HTML,
    css=VIDEO_CSS,
    js=VIDEO_JS,
    isolate_styles=False,
)


def render_match_video(
    *,
    url: str,
    label: str,
    start_time: float,
    sync_id: str,
    key: str,
) -> None:
    """Mount full-match playback with unrestricted native seeking."""

    match_video(
        data={
            "url": url,
            "label": label,
            "startTime": start_time,
            "syncId": sync_id,
        },
        key=key,
        width="stretch",
        height="content",
    )
