"""Public-window possession comparison synchronized to tactical video."""
import streamlit as st

TIMELINE_HTML = r"""
  <section id="possession-timeline" class="possession-timeline" aria-label="Five-minute possession comparison" hidden>
    <div class="timeline-legend"><span><i class="dot barca"></i>Barcelona</span><span><i class="dot bilbao"></i>Athletic Club</span><span><i class="dot dead"></i>Dead ball</span></div>
    <div class="timeline-row"><span>Ground truth</span><div class="timeline-track" id="truth-track"></div></div>
    <div class="timeline-row"><span>Our model</span><div class="timeline-track" id="model-track"></div></div>
    <div class="timeline-row"><span></span><div class="timeline-axis"><span>0:00</span><span>1:00</span><span>2:00</span><span>3:00</span><span>4:00</span><span>5:00</span></div></div>
  </section>
"""

TIMELINE_CSS = r"""
 :host { display: block; font-size: 17px; color: #17202a; font-family: var(--st-font, ui-sans-serif, system-ui, sans-serif); }
* { box-sizing: border-box; }
.dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
.dot.barca { background: #8C0A59; }
.dot.bilbao { background: #fff; border: 1px solid #111; }
.possession-timeline { order: 2; padding: 0 12px; font-size: .85rem; }
.possession-timeline[hidden] { display: none; }
.timeline-legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 0 0 8px; }
.timeline-legend span { display: inline-flex; align-items: center; gap: 5px; }
.dot.dead { background: #98a2b3; }
.timeline-row { display: grid; grid-template-columns: 90px minmax(0, 1fr); align-items: center; gap: 8px; margin: 8px 0; }
.timeline-row:last-child { margin-bottom: 0; }
.timeline-track { position: relative; height: 28px; border: 1px solid #667085; overflow: hidden; background: #eaecf0; }
.timeline-segment { position: absolute; top: 0; bottom: 0; }
.timeline-cursor { position: absolute; top: 0; bottom: 0; width: 2px; background: #f79009; box-shadow: 0 0 0 1px #17202a; }
.timeline-axis { display: flex; justify-content: space-between; font-variant-numeric: tabular-nums; color: #667085; }
"""

TIMELINE_JS = r"""
export default function(component) {
  const { parentElement, data } = component;
  const possessionIntervals = data.possessionIntervals;
  const timeline = parentElement.querySelector('#possession-timeline');
  const truth = data.groundTruthIntervals || [];
  const cursors = [];
  let timelineStart = 0, timelineEnd = 0;
  if (truth.length && possessionIntervals?.length) {
    timeline.hidden = false;
    timelineStart = Math.min(...truth.map(item => item.start));
    timelineEnd = Math.max(...truth.map(item => item.end)) + 1;
    const duration = timelineEnd - timelineStart;
    const colors = {H: '#8C0A59', A: '#ffffff', D: '#98a2b3', X: '#eaecf0'};
    const names = {H: 'Barcelona', A: 'Athletic Club', D: 'Dead ball', X: 'Unavailable'};
    [['#truth-track', truth], ['#model-track', possessionIntervals]].forEach(([id, intervals]) => {
      const track = parentElement.querySelector(id);
      intervals.forEach(item => {
        const start = Math.max(timelineStart, item.start), end = Math.min(timelineEnd, item.end + 1);
        if (end <= start) return;
        const segment = document.createElement('span');
        segment.className = 'timeline-segment';
        segment.style.left = `${100 * (start - timelineStart) / duration}%`;
        segment.style.width = `${100 * (end - start) / duration}%`;
        segment.style.background = colors[item.label];
        segment.title = `${names[item.label]} · ${((start - timelineStart) / data.fps).toFixed(2)}–${((end - timelineStart) / data.fps).toFixed(2)} s`;
        track.append(segment);
      });
      const cursor = document.createElement('span');
      cursor.className = 'timeline-cursor';
      track.append(cursor);
      cursors.push(cursor);
    });
  }
  const updateTimeline = frame => cursors.forEach(cursor => {
    cursor.hidden = frame < timelineStart || frame >= timelineEnd;
    cursor.style.left = `${100 * (frame - timelineStart) / (timelineEnd - timelineStart)}%`;
  });

  const selector = `video[data-match-video="${CSS.escape(data.syncId)}"]`;
  let animationId;
  const tick = () => {
    const video = document.querySelector(selector);
    const time = video && video.readyState >= 1 ? video.currentTime : data.startTime;
    updateTimeline(Math.floor((time + data.videoTimeOffset) * data.fps));
    animationId = requestAnimationFrame(tick);
  };
  tick();
  return () => cancelAnimationFrame(animationId);
}
"""

possession_timeline = st.components.v2.component(
    "touchline_possession_timeline", html=TIMELINE_HTML, css=TIMELINE_CSS, js=TIMELINE_JS,
)


def render_possession_timeline(*, intervals, ground_truth, fps, sync_id, video_time_offset, start_time):
    possession_timeline(
        data={"possessionIntervals": intervals, "groundTruthIntervals": ground_truth,
              "fps": fps, "syncId": sync_id, "videoTimeOffset": video_time_offset,
              "startTime": start_time},
        key=f"possession-timeline-{sync_id}", width="stretch", height="content",
    )
