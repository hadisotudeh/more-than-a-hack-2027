"""Streamlit component that renders tracking in sync with the native video player."""

from __future__ import annotations

from typing import Any, Iterable

import streamlit as st

from app.tracking import TrackingFrame
from app.pitch_art import pitch_art


PITCH_HTML = """
<div class="touchline-tracking-heading">TRACKING</div>
<section class="tracking-shell" aria-label="Tracking animation">
  <header class="tracking-header">
    <div>
      <strong id="camera-label">Camera</strong>
      <span id="half-label" class="half-label">Half unavailable</span>
    </div>
    <div class="clock-stack">
      <span id="match-clock">00:00.00</span>
      <small id="frame-label">Frame —</small>
    </div>
  </header>
  <div id="possession-indicator" class="possession-indicator" hidden></div>
  <div class="pitch-wrap">
    <canvas id="tracking-canvas" role="img" aria-label="Horizontal football pitch with tracked players"></canvas>
    <div id="tracking-empty" class="tracking-empty" hidden>No tracking observations at this frame</div>
  </div>
  <footer class="tracking-footer">
    <div class="tracking-legend">
    <span><i class="dot barca"></i>Barcelona</span>
    <span><i class="dot bilbao"></i>Athletic Club</span>
    <span><i class="dot ball"></i>Ball</span>
    <span><i class="dot coverage"></i><span id="coverage-label">Camera coverage</span></span>
    </div>
    <div id="smart-tags-footer" hidden>
      <div class="eyebrow">ACTIVE SMART TAGS</div>
      <div id="smart-tags-list" aria-live="polite" aria-atomic="true"></div>
    </div>
  </footer>
</section>
"""


PITCH_CSS = """
.touchline-tracking-heading {
  display: block; margin: 0; padding: 0 0 10px;
  color: #667085; font: 800 15.3px/22px var(--st-font, ui-sans-serif, system-ui, sans-serif);
  letter-spacing: .13em;
}
:host { display: block; width: 100%; font-size: 17px; }
* { box-sizing: border-box; }
.tracking-shell {
  width: 100%; padding: 0;
  display: flex; flex-direction: column; gap: 8px;
  color: #17202a; border: none; border-radius: 0;
  background: transparent;
  box-shadow: none; overflow: hidden;
  font-family: var(--st-font, ui-sans-serif, system-ui, sans-serif);
}
.tracking-header, .tracking-footer { display: flex; align-items: center; justify-content: space-between; }
.tracking-header { order: 3; padding: 2px 12px 0; }
.tracking-footer { order: 4; padding: 0 12px 10px; }
.tracking-header strong { display: block; margin-top: 2px; font-size: 1.18rem; letter-spacing: -.01em; }
.half-label { display: inline-block; margin-top: 5px; color: #475467; font-size: .96rem; }
.eyebrow { color: #667085; font-size: .88rem; font-weight: 800; letter-spacing: .15em; }
.clock-stack { text-align: right; font-variant-numeric: tabular-nums; }
#match-clock { display: block; font-size: 1.35rem; font-weight: 800; color: #000000; }
#frame-label { color: #667085; font-size: .9rem; }
.pitch-wrap { order: 0; position: relative; flex: none; width: 100%; aspect-ratio: 16 / 9; background: white; border-radius: 18px; overflow: hidden; }
#tracking-canvas { position: absolute; inset: 0; display: block; width: 100%; height: 100%; min-height: 0; }
.possession-indicator {
  order: 1; align-self: center; min-width: 190px; margin: 2px 12px 0; padding: 7px 12px;
  border: 1px solid rgba(16,24,40,.14); border-radius: 999px;
  background: rgba(255,255,255,.94); box-shadow: 0 4px 14px rgba(16,24,40,.12);
  color: #344054; font-size: .96rem; font-weight: 800; text-align: center; backdrop-filter: blur(6px);
}
.possession-indicator[hidden] { display: none; }
.possession-indicator.home { background: rgba(140,10,89,.94); color: #fff; border-color: #8c0a59; }
.possession-indicator.away { background: rgba(255,255,255,.96); color: #111; border-color: #344054; }
.possession-indicator.dead { background: rgba(52,64,84,.94); color: #fff; border-color: #344054; }
.tracking-empty {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  padding: 8px 12px; border-radius: 999px; background: rgba(4, 12, 8, .72);
  color: #dce7e0; font-size: .96rem; backdrop-filter: blur(5px);
}
.tracking-footer { flex-direction: column; align-items: stretch; gap: 10px; flex-shrink: 0; color: #475467; font-size: .95rem; }
.tracking-legend { display: flex; flex-wrap: wrap; gap: 10px 17px; }
.dot.coverage { background: #F7F8F3; border: 1px solid #000; }
#smart-tags-footer { border-top: 1px solid #e4e7ec; padding-top: 10px; }
#smart-tags-footer[hidden] { display: none; }
#smart-tags-list {
  display: flex; flex-wrap: wrap; align-content: flex-start; align-items: flex-start;
  gap: 6px; margin-top: 6px; height: 240px; min-height: 80px; overflow-y: auto;
}
.smart-tag { padding: 5px 9px; border-radius: 8px; background: #fff4e8; border: 1px solid #f6c98b; color: #7a4512; line-height: 1.4; }
.no-smart-tags { color: #667085; }
.tracking-footer span { display: inline-flex; align-items: center; gap: 6px; }
.dot { width: 12px; height: 12px; flex-shrink: 0; border-radius: 50%; display: inline-block; }
.dot.barca { background: #8C0A59; border: 1px solid #fff; }
.dot.bilbao { background: #fff; border: 1px solid #111; }
.dot.ball { background: #000000; }
"""


PITCH_JS = r"""
export default function(component) {
  const { parentElement, data } = component;
  const canvas = parentElement.querySelector('#tracking-canvas');
  const ctx = canvas.getContext('2d');
  const art = data.pitchArt;
  const pitchImage = new Image();
  pitchImage.src = art.image;
  const empty = parentElement.querySelector('#tracking-empty');
  const matchClock = parentElement.querySelector('#match-clock');
  const frameLabel = parentElement.querySelector('#frame-label');
  const cameraLabel = parentElement.querySelector('#camera-label');
  cameraLabel.textContent = data.cameraLabel;
  const halfLabel = parentElement.querySelector('#half-label');
  const possessionIndicator = parentElement.querySelector('#possession-indicator');
  const possessionIntervals = data.possessionIntervals;
  possessionIndicator.hidden = possessionIntervals === null || possessionIntervals === undefined;
  const updatePossession = frame => {
    if (possessionIndicator.hidden) return;
    const interval = possessionIntervals.find(item => item.start <= frame && frame <= item.end);
    const labels = {
      H: ['Barcelona in possession', 'home'],
      A: ['Athletic Club in possession', 'away'],
      D: ['Dead ball', 'dead'],
      X: ['Possession unknown', 'unknown'],
    };
    const [text, state] = interval ? labels[interval.label] : ['Public possession unavailable', 'unknown'];
    possessionIndicator.textContent = text;
    possessionIndicator.className = `possession-indicator ${state}`;
  };
  halfLabel.title = data.halfIntervals?.length
    ? 'Based on published tactical-video half boundaries'
    : 'The tracking XML does not provide usable half boundaries for this camera';
  const halfAtFrame = frame => {
    const intervals = data.halfIntervals || [];
    if (!intervals.length) return 'Half unavailable';
    const active = intervals.find(interval => interval.start <= frame && frame <= interval.end);
    if (active) return active.half === 1 ? '1st half' : '2nd half';
    if (frame < intervals[0].start) return 'Before kickoff';
    if (frame > intervals[intervals.length - 1].end) return 'After full time';
    return 'Halftime';
  };
  const tagsFooter = parentElement.querySelector('#smart-tags-footer');
  const tagsList = parentElement.querySelector('#smart-tags-list');
  tagsFooter.hidden = data.smartTags === null || data.smartTags === undefined;
  const trackingShell = parentElement.querySelector('.tracking-shell');
  let lastTagsLayout = -Infinity;
  const alignTagsWithEvaluation = () => {
    if (tagsFooter.hidden || performance.now() - lastTagsLayout < 200) return;
    lastTagsLayout = performance.now();
    const details = document.querySelector('.st-key-model-details');
    const reference = details?.querySelector('p') || details;
    if (!reference) return;
    const left = reference.getBoundingClientRect();
    const shell = trackingShell.getBoundingClientRect();
    const list = tagsList.getBoundingClientRect();
    // Only align side-by-side columns; use a compact box on stacked mobile layouts.
    const sideBySide = left.right <= shell.left + 20;
    const bottomPadding = shell.bottom - list.bottom;
    const height = sideBySide ? Math.max(80, Math.round(left.bottom - list.top - bottomPadding)) : 240;
    const value = `${height}px`;
    if (tagsList.style.height !== value) tagsList.style.height = value;
  };
  const tags = data.smartTags || [];
  let activeTagKey = null;
  const updateTags = (time) => {
    if (tagsFooter.hidden) return;
    const active = tags.map((event, index) => ({event, index}))
      .filter(({event}) => event.start <= time && time < event.end);
    const key = active.map(({index}) => index).join(',');
    if (key === activeTagKey) return;
    activeTagKey = key;
    tagsList.replaceChildren();
    if (!active.length) {
      const note = document.createElement('span');
      note.className = 'no-smart-tags';
      note.textContent = 'No active Smart Tags';
      tagsList.append(note);
    }
    active.forEach(({event}) => {
      const badge = document.createElement('span');
      badge.className = 'smart-tag';
      const labels = event.labels.filter(label => label.text && label.text !== 'N/A' && label.group !== 'Half');
      badge.textContent = [event.code, ...labels.map(label => `${label.group}: ${label.text}`)].join(' · ');
      badge.title = `${event.start.toFixed(2)}–${event.end.toFixed(2)} s (tactical video)`;
      tagsList.append(badge);
    });
  };

  let frames = data.frames || [];
  let times = frames.map((frame) => frame.t);
  let coverageStart = data.coverageStartFrame;
  let matrices = data.coverageMatrices || [];
  const windows = new Map();
  const pending = new Map();
  const retryAfter = new Map();
  let disposed = false;
  let activeWindow = null;
  const windowFrames = Math.round(data.fps * 60);
  const requestWindow = (start) => {
    if (!data.trackingUrl || start >= data.totalFrames || windows.has(start) || pending.has(start)
        || Date.now() < (retryAfter.get(start) || 0)) return;
    const controller = new AbortController();
    pending.set(start, controller);
    fetch(`${data.trackingUrl}?frame=${start}`, {signal: controller.signal})
      .then(response => { if (!response.ok) throw Error('Tracking request failed'); return response.json(); })
      .then(payload => {
        if (disposed) return;
        windows.set(start, payload);
        while (windows.size > 3) windows.delete(windows.keys().next().value);
        retryAfter.delete(start);
      })
      .catch(error => { if (error.name !== 'AbortError') retryAfter.set(start, Date.now() + 2000); })
      .finally(() => pending.delete(start));
  };
  const followVideo = sourceTime => {
    const frame = Math.max(0, Math.min(data.totalFrames - 1, Math.floor(sourceTime * data.fps)));
    const start = Math.floor(frame / windowFrames) * windowFrames;
    requestWindow(start);
    if (frame >= start + windowFrames - data.fps * 10) requestWindow(start + windowFrames);
    if (activeWindow !== start && windows.has(start)) {
      const payload = windows.get(start);
      frames = payload.frames;
      times = frames.map(frame => frame.t);
      coverageStart = payload.coverageStartFrame;
      matrices = payload.coverageMatrices;
      activeWindow = start;
    }
  };
  const videoSelector = `video[data-match-video="${CSS.escape(data.syncId)}"]`;
  let video = null;
  let animationId = null;

  const clock = (seconds) => {
    const safe = Math.round(Math.max(0, seconds) * 100) / 100;
    const minutes = Math.floor(safe / 60);
    const remainder = safe - minutes * 60;
    return `${String(minutes).padStart(2, '0')}:${remainder.toFixed(2).padStart(5, '0')}`;
  };

  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.max(1, window.devicePixelRatio || 1);
    const width = Math.max(1, Math.round(rect.width * ratio));
    const height = Math.max(1, Math.round(rect.height * ratio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
  };

  const artworkBox = () => {
    const scale = Math.min(canvas.width / (art.length + 2 * art.margin),
      canvas.height / (art.width + 2 * art.margin));
    const width = (art.length + 2 * art.margin) * scale;
    const height = (art.width + 2 * art.margin) * scale;
    return { x: (canvas.width - width) / 2, y: (canvas.height - height) / 2, width, height, scale };
  };
  const pitchBox = () => {
    const box = artworkBox();
    return { x: box.x + art.margin * box.scale, y: box.y + art.margin * box.scale,
      width: art.length * box.scale, height: art.width * box.scale };
  };

  // Clip the pitch against the image bounds in homogeneous coordinates. Unlike
  // inverse-projecting four image corners, this also handles a visible horizon.
  const coveragePolygons = (matrix, width, height) => {
    if (!matrix || !width || !height) return [];
    const u = matrix.slice(0, 3), v = matrix.slice(3, 6), w = matrix.slice(6, 9);
    const planes = [w, u, w.map((n, i) => width * n - u[i]),
      v, w.map((n, i) => height * n - v[i])];
    return [1, -1].map(sign => {
      let polygon = [[0, 0], [1, 0], [1, 1], [0, 1]];
      planes.forEach((plane, planeIndex) => {
        const value = p => sign * (plane[0] * p[0] + plane[1] * p[1] + plane[2])
          - (planeIndex === 0 ? 1e-9 : 0);
        const output = [];
        polygon.forEach((end, index) => {
          const start = polygon[(index + polygon.length - 1) % polygon.length];
          const a = value(start), b = value(end);
          if ((a >= 0) !== (b >= 0)) {
            const t = a / (a - b);
            output.push([start[0] + t * (end[0] - start[0]), start[1] + t * (end[1] - start[1])]);
          }
          if (b >= 0) output.push(end);
        });
        polygon = output;
      });
      return polygon;
    }).filter(polygon => polygon.length >= 3);
  };

  const drawPitch = (box, coverage) => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    // Fill only: camera coverage has no outline. Players and pitch lines stay above it.
    ctx.fillStyle = '#F7F8F3';
    coverage.forEach(polygon => {
      ctx.beginPath();
      polygon.forEach(([x, y], index) => {
        const px = box.x + x * box.width, py = box.y + y * box.height;
        if (index === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      });
      ctx.closePath();
      ctx.fill();
    });
    if (pitchImage.complete && pitchImage.naturalWidth) {
      const artwork = artworkBox();
      ctx.drawImage(pitchImage, artwork.x, artwork.y, artwork.width, artwork.height);
    }
  };

  const position = (x, y, box) => ({ px: box.x + x * box.width, py: box.y + y * box.height });

  const nearestFrames = (time) => {
    if (!frames.length || time < times[0] - .3 || time > times[times.length - 1] + .3) return null;
    let low = 0, high = times.length - 1;
    while (low < high) {
      const mid = Math.floor((low + high) / 2);
      if (times[mid] < time) low = mid + 1; else high = mid;
    }
    const right = low;
    const left = Math.max(0, right - 1);
    const span = Math.max(.0001, times[right] - times[left]);
    const alpha = right === left ? 0 : Math.max(0, Math.min(1, (time - times[left]) / span));
    return { a: frames[left], b: frames[right], alpha };
  };

  const interpolatePlayers = ({ a, b, alpha }) => {
    const previous = new Map((a.players || []).map((player) => [String(player.id), player]));
    const next = new Map((b.players || []).map((player) => [String(player.id), player]));
    const ids = new Set([...previous.keys(), ...next.keys()]);
    return [...ids].flatMap((id) => {
      const player = previous.get(id);
      const target = next.get(id);
      if (player && target && target.team === player.team) {
        return [{ ...player, x: player.x + (target.x - player.x) * alpha, y: player.y + (target.y - player.y) * alpha }];
      }
      const nearest = alpha < .5 ? player : target;
      return nearest ? [nearest] : [];
    });
  };

  const interpolateBall = ({ a, b, alpha }) => {
    if (!a.ball || !b.ball) return alpha < .5 ? (a.ball || null) : (b.ball || null);
    return [a.ball[0] + (b.ball[0] - a.ball[0]) * alpha, a.ball[1] + (b.ball[1] - a.ball[1]) * alpha];
  };

  const drawPlayer = (player, box) => {
    const { px, py } = position(player.x, player.y, box);
    const radius = Math.max(8, Math.min(box.width, box.height) * .025);
    ctx.beginPath(); ctx.arc(px, py, radius, 0, Math.PI * 2);
    ctx.fillStyle = player.team === 'H' ? '#8C0A59' : '#ffffff'; ctx.fill();
    ctx.strokeStyle = player.team === 'H' ? '#f5effa' : '#171717'; ctx.lineWidth = Math.max(1.2, radius * .12); ctx.stroke();
    ctx.fillStyle = player.team === 'H' ? '#ffffff' : '#111111';
    ctx.font = `800 ${Math.max(9, radius * .92)}px ui-sans-serif, system-ui, sans-serif`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(String(player.number), px, py + .3);
  };

  const draw = () => {
    resize();
    const box = pitchBox();
    if (!video || !video.isConnected || !video.matches(videoSelector)) bindVideo();
    const time = video && video.readyState >= 1 ? video.currentTime : data.startTime;
    const sourceTime = time + data.videoTimeOffset;
    const videoFrame = Math.max(0, Math.floor(sourceTime * data.fps));
    followVideo(sourceTime);
    const index = videoFrame - coverageStart;
    const matrix = matrices[index];
    const available = Boolean(matrix && video?.videoWidth && video?.videoHeight);
    const coverage = available ? coveragePolygons(matrix, video.videoWidth, video.videoHeight) : [];
    drawPitch(box, coverage);
    parentElement.querySelector('#coverage-label').textContent = available
      ? 'Camera coverage' : 'Camera mapping unavailable';
    updateTags(sourceTime);
    alignTagsWithEvaluation();
    updatePossession(videoFrame);
    const pair = nearestFrames(sourceTime);
    matchClock.textContent = clock(sourceTime - data.kickoffOffset);
    frameLabel.textContent = `Video frame ${videoFrame}`;
    halfLabel.textContent = halfAtFrame(videoFrame);
    if (pair) {
      const players = interpolatePlayers(pair);
      const ball = interpolateBall(pair);
      empty.hidden = Boolean(players.length || ball);
      players.forEach((player) => drawPlayer(player, box));
      if (ball) {
        const { px, py } = position(ball[0], ball[1], box);
        const radius = Math.max(5, Math.min(box.width, box.height) * .012);
        ctx.beginPath(); ctx.arc(px, py, radius, 0, Math.PI * 2);
        ctx.fillStyle = '#000000'; ctx.fill();
      }
    } else {
      empty.hidden = false;
    }
    empty.textContent = pair ? 'No tracking observations at this frame'
      : (retryAfter.size ? 'Unable to load tracking — retrying…' : 'Loading tracking…');
    animationId = requestAnimationFrame(draw);
  };

  const bindVideo = () => {
    video = document.querySelector(videoSelector);
    return Boolean(video);
  };

  bindVideo();
  const domObserver = new MutationObserver(() => { if (!video || !document.contains(video)) bindVideo(); });
  domObserver.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['data-match-video'],
  });
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(canvas);
  draw();

  return () => {
    disposed = true;
    pending.forEach(controller => controller.abort());
    if (animationId !== null) cancelAnimationFrame(animationId);
    domObserver.disconnect();
    resizeObserver.disconnect();
  };
}
"""


tracking_pitch = st.components.v2.component(
    "touchline_tracking_pitch",
    html=PITCH_HTML,
    css=PITCH_CSS,
    js=PITCH_JS,
)


def serialize_frames(frames: Iterable[TrackingFrame]) -> list[dict[str, Any]]:
    """Convert decoded frames into compact, JSON-safe component records."""

    records: list[dict[str, Any]] = []
    for frame in frames:
        players = [
            {
                "id": player.track_id,
                "team": player.team,
                "number": player.number,
                "x": round(player.x, 6),
                "y": round(player.y, 6),
            }
            for player in frame.players
            if player.team in {"H", "A"}
        ]
        ball = None if frame.ball is None else [round(frame.ball.x, 6), round(frame.ball.y, 6)]
        records.append(
            {
                "f": frame.video_frame,
                "t": round(frame.time_seconds, 4),
                "players": players,
                "ball": ball,
            }
        )
    return records


def render_tracking_pitch(
    *,
    frames: Iterable[TrackingFrame],
    camera_label: str,
    fps: float,
    kickoff_offset: float,
    start_time: float,
    video_time_offset: float,
    sync_id: str,
    key: str,
    smart_tags: list[dict[str, Any]] | None = None,
    possession_intervals: list[dict[str, Any]] | None = None,
    coverage_start_frame: int = 0,
    coverage_matrices: list[list[float] | None] | None = None,
    tracking_url: str | None = None,
    total_frames: int = 0,
    half_intervals: list[dict[str, int]] | None = None,
) -> None:
    """Mount the synchronized pitch component."""

    tracking_pitch(
        data={
            "frames": serialize_frames(frames),
            "pitchArt": pitch_art(),
            "cameraLabel": camera_label,
            "fps": fps,
            "kickoffOffset": kickoff_offset,
            "startTime": start_time,
            "videoTimeOffset": video_time_offset,
            "syncId": sync_id,
            "smartTags": smart_tags,
            "possessionIntervals": possession_intervals,
            "coverageStartFrame": coverage_start_frame,
            "coverageMatrices": coverage_matrices,
            "trackingUrl": tracking_url,
            "totalFrames": total_frames,
            "halfIntervals": half_intervals,
        },
        key=key,
        width="stretch",
        height="content",
    )

