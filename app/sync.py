"""Kickoff anchors and frame/time conversion for the dashboard.

Tracking for each source is already aligned one-to-one with that source's video.  The offsets in
this module only choose a useful kickoff-relative starting point for the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
import math


TACTICAL_SOURCE = "tactical"
BROADCAST_SOURCE = "broadcast"
BROADCAST_KICKOFF_SECONDS = 4 * 60 + 46


def read_smart_tags(path: str | Path) -> list[dict]:
    """Read automatic tag intervals in absolute tactical-video seconds."""
    events = []
    for instance in ET.parse(path).iter("instance"):
        start = float(instance.findtext("start", "nan"))
        end = float(instance.findtext("end", "nan"))
        code = (instance.findtext("code") or "").strip()
        if not code or not math.isfinite(start) or not math.isfinite(end) or end <= start:
            continue
        labels = [
            {"group": (label.findtext("group") or "").strip(),
             "text": (label.findtext("text") or "").strip()}
            for label in instance.findall("label")
        ]
        events.append({"start": start, "end": end, "code": code, "labels": labels})
    return sorted(events, key=lambda event: event["start"])


@dataclass(frozen=True, slots=True)
class KickoffWindow:
    """A Smart Tag interval around a kickoff on the tactical video timeline."""

    start_seconds: float
    end_seconds: float
    half: str

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


def first_half_kickoff_window(smart_tagging_path: str | Path) -> KickoffWindow:
    """Return the first-half ``Kick Off (Start)`` Smart Tag interval.

    Smart Tagging marks a window around the restart rather than the exact ball-strike frame.  The
    dashboard intentionally starts at the beginning of that window so the user sees the setup and
    the kickoff.
    """

    path = Path(smart_tagging_path)
    if not path.is_file():
        raise FileNotFoundError(f"Smart Tagging file not found: {path}")

    matches: list[KickoffWindow] = []
    for instance in ET.parse(path).iter("instance"):
        code = (instance.findtext("code") or "").strip().casefold()
        tags = {
            (label.findtext("group") or "").strip():
            (label.findtext("text") or "").strip()
            for label in instance.findall("label")
        }
        event_type = tags.get("Type", "").casefold()
        half = tags.get("Half", "")
        if code != "set pieces" or event_type != "kick off (start)":
            continue
        if half and half.casefold() != "1st half":
            continue

        start = float(instance.findtext("start", "nan"))
        end = float(instance.findtext("end", "nan"))
        if start >= 0 and end > start:
            matches.append(KickoffWindow(start, end, half or "1st Half"))

    if not matches:
        raise ValueError(f"{path}: no first-half Kick Off (Start) Smart Tag found")
    return min(matches, key=lambda event: event.start_seconds)


def source_kickoff_seconds(source: str, smart_tagging_path: str | Path) -> float:
    """Return the requested source-specific kickoff-relative UI anchor."""

    if source == TACTICAL_SOURCE:
        return first_half_kickoff_window(smart_tagging_path).start_seconds
    if source == BROADCAST_SOURCE:
        return float(BROADCAST_KICKOFF_SECONDS)
    raise ValueError(f"Unknown source: {source!r}")


def video_frame_at(seconds: float, fps: float) -> int:
    """Convert source-video seconds to a zero-based frame without overshooting."""

    if seconds < 0:
        raise ValueError("seconds must be non-negative")
    if fps <= 0:
        raise ValueError("fps must be positive")
    return int(seconds * fps)


def format_clock(seconds: float) -> str:
    """Format a non-negative duration as ``MM:SS.ss``."""

    seconds = max(0.0, seconds)
    minutes, remainder = divmod(seconds, 60.0)
    return f"{int(minutes):02d}:{remainder:05.2f}"

