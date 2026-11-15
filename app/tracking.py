"""Small, dependency-free reader for Metrica FIFA/EPTS tracking exports.

The challenge tracking files are large (roughly 140--195 MB), so the dashboard should not load
them into a dataframe on every Streamlit rerun.  ``TrackingSource`` scans the raw file once to
build a compact in-memory byte-offset index, then seeks directly to only the frames needed by the
animation.

All public frame arguments are zero-based video-frame indices.  Metrica's raw EPTS records are
one-based, and the conversion is handled internally.
"""

from __future__ import annotations

from array import array
from bisect import bisect_right
from dataclasses import dataclass
import math
from pathlib import Path
from threading import Lock
from typing import Iterator, Sequence
import xml.etree.ElementTree as ET


HOME = "H"
AWAY = "A"
UNKNOWN_TEAM = "?"


@dataclass(frozen=True, slots=True)
class TrackInfo:
    """Metadata for one EPTS player/track channel."""

    track_id: str
    team: str
    number: str
    name: str


@dataclass(frozen=True, slots=True)
class TrackedPoint:
    """One visible player/track at a frame, in normalized pitch coordinates."""

    track_id: str
    team: str
    number: str
    name: str
    x: float
    y: float
    speed: float | None


@dataclass(frozen=True, slots=True)
class BallPoint:
    """The tracked ball at a frame, in normalized pitch coordinates."""

    x: float
    y: float
    speed: float | None


@dataclass(frozen=True, slots=True)
class TrackingFrame:
    """A single decoded EPTS frame."""

    video_frame: int
    source_frame_id: int
    time_seconds: float
    players: tuple[TrackedPoint, ...]
    ball: BallPoint | None


@dataclass(frozen=True, slots=True)
class _PlayerGroup:
    track_id: str
    channels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _FormatBlock:
    start_frame: int
    end_frame: int
    players: tuple[_PlayerGroup, ...]
    ball_channels: tuple[str, ...]


class TrackingSource:
    """Lazy random-access reader for a Metrica metadata/raw tracking pair.

    Parameters
    ----------
    metadata_path:
        FIFA/EPTS metadata XML.
    raw_path:
        Colon/semicolon-delimited Metrica raw tracking file.

    Notes
    -----
    The byte-offset index uses eight bytes per frame (about 1.6 MB for the tactical feed) and is
    kept in memory only.  The raw tracking data itself is never retained in memory.
    """

    def __init__(self, metadata_path: str | Path, raw_path: str | Path) -> None:
        self.metadata_path = Path(metadata_path)
        self.raw_path = Path(raw_path)
        if not self.metadata_path.is_file():
            raise FileNotFoundError(f"Tracking metadata not found: {self.metadata_path}")
        if not self.raw_path.is_file():
            raise FileNotFoundError(f"Raw tracking data not found: {self.raw_path}")

        root = ET.parse(self.metadata_path).getroot()
        self.fps = _read_float_text(root, "FrameRate")
        self.pitch_length, self.pitch_width = _read_pitch(root)

        teams = list(root.findall(".//Teams/Team"))
        if len(teams) < 2:
            raise ValueError(f"{self.metadata_path}: expected at least two teams")
        self.team_names = {
            HOME: teams[0].findtext("Name") or "Home",
            AWAY: teams[1].findtext("Name") or "Away",
        }
        team_codes = {teams[0].get("id"): HOME, teams[1].get("id"): AWAY}

        self.tracks: dict[str, TrackInfo] = {}
        for player in root.findall(".//Players/Player"):
            track_id = player.get("id")
            if not track_id:
                continue
            number = player.findtext("ShirtNumber") or track_id
            name = player.findtext("Name") or f"Track {number}"
            self.tracks[track_id] = TrackInfo(
                track_id=track_id,
                team=team_codes.get(player.get("teamId"), UNKNOWN_TEAM),
                number=number,
                name=name,
            )

        channel_map: dict[str, tuple[str, str]] = {}
        for channel in root.findall(".//PlayerChannels/PlayerChannel"):
            channel_id = channel.get("id")
            player_id = channel.get("playerId")
            value_name = channel.get("channelId")
            if channel_id and player_id and value_name:
                channel_map[channel_id] = (player_id, value_name)

        self._formats = _read_formats(root, channel_map)
        if not self._formats:
            raise ValueError(f"{self.metadata_path}: no EPTS DataFormatSpecification found")
        self._format_starts = [block.start_frame for block in self._formats]

        self._offsets: array[int] | None = None
        self._index_lock = Lock()

    @property
    def frame_count(self) -> int:
        """Number of raw/video frames, building the compact seek index on first access."""

        self.build_index()
        assert self._offsets is not None
        return len(self._offsets)

    def build_index(self) -> int:
        """Build the raw-file byte-offset index once and return its frame count."""

        if self._offsets is not None:
            return len(self._offsets)
        with self._index_lock:
            if self._offsets is not None:
                return len(self._offsets)

            offsets: array[int] = array("Q")
            expected_frame_id = 1
            with self.raw_path.open("rb") as handle:
                while True:
                    offset = handle.tell()
                    line = handle.readline()
                    if not line:
                        break
                    colon = line.find(b":")
                    if colon <= 0:
                        raise ValueError(
                            f"{self.raw_path}: malformed record at byte offset {offset}"
                        )
                    try:
                        frame_id = int(line[:colon])
                    except ValueError as exc:
                        raise ValueError(
                            f"{self.raw_path}: invalid frame id at byte offset {offset}"
                        ) from exc
                    if frame_id != expected_frame_id:
                        raise ValueError(
                            f"{self.raw_path}: expected frame id {expected_frame_id}, "
                            f"found {frame_id}"
                        )
                    offsets.append(offset)
                    expected_frame_id += 1

            self._offsets = offsets
            return len(offsets)

    def read_frame(self, video_frame: int) -> TrackingFrame:
        """Read one zero-based video frame without loading the full tracking file."""

        self.build_index()
        assert self._offsets is not None
        if video_frame < 0 or video_frame >= len(self._offsets):
            raise IndexError(
                f"video frame {video_frame} outside 0..{len(self._offsets) - 1}"
            )
        with self.raw_path.open("rb") as handle:
            handle.seek(self._offsets[video_frame])
            return self._decode_line(handle.readline())

    def iter_frames(
        self,
        start_video_frame: int,
        stop_video_frame: int,
        *,
        stride: int = 1,
    ) -> Iterator[TrackingFrame]:
        """Yield ``[start, stop)`` video frames at ``stride`` using one file handle."""

        self.build_index()
        assert self._offsets is not None
        if stride < 1:
            raise ValueError("stride must be at least 1")
        start = max(0, start_video_frame)
        stop = min(stop_video_frame, len(self._offsets))
        if stop < start:
            raise ValueError("stop_video_frame must not be before start_video_frame")

        with self.raw_path.open("rb") as handle:
            for video_frame in range(start, stop, stride):
                handle.seek(self._offsets[video_frame])
                yield self._decode_line(handle.readline())

    def read_window(
        self,
        start_video_frame: int,
        *,
        frame_count: int,
        stride: int = 1,
    ) -> list[TrackingFrame]:
        """Return a bounded animation window as decoded frame objects."""

        if frame_count < 0:
            raise ValueError("frame_count must be non-negative")
        stop = start_video_frame + frame_count
        return list(self.iter_frames(start_video_frame, stop, stride=stride))

    def _decode_line(self, raw_line: bytes) -> TrackingFrame:
        try:
            text = raw_line.decode("ascii").strip()
        except UnicodeDecodeError as exc:
            raise ValueError(f"{self.raw_path}: tracking record is not ASCII") from exc
        parts = text.split(":")
        if len(parts) != 3:
            raise ValueError(f"{self.raw_path}: expected three colon-delimited fields")

        source_frame_id = int(parts[0])
        block = self._format_for(source_frame_id)
        player_values = parts[1].split(";") if parts[1] else []
        if len(player_values) != len(block.players):
            raise ValueError(
                f"{self.raw_path}: frame {source_frame_id} has {len(player_values)} player "
                f"groups; metadata specifies {len(block.players)}"
            )

        visible_players: list[TrackedPoint] = []
        for group, encoded in zip(block.players, player_values):
            values = _channel_values(encoded, group.channels)
            x, y = values.get("x"), values.get("y")
            if x is None or y is None:
                continue
            info = self.tracks.get(
                group.track_id,
                TrackInfo(group.track_id, UNKNOWN_TEAM, group.track_id, group.track_id),
            )
            visible_players.append(
                TrackedPoint(
                    track_id=info.track_id,
                    team=info.team,
                    number=info.number,
                    name=info.name,
                    x=x,
                    y=y,
                    speed=_first_present(values, "s", "speed"),
                )
            )

        ball_values = _channel_values(parts[2], block.ball_channels)
        ball_x, ball_y = ball_values.get("x"), ball_values.get("y")
        ball = None
        if ball_x is not None and ball_y is not None:
            ball = BallPoint(
                x=ball_x,
                y=ball_y,
                speed=_first_present(ball_values, "s", "speed"),
            )

        video_frame = source_frame_id - 1
        return TrackingFrame(
            video_frame=video_frame,
            source_frame_id=source_frame_id,
            time_seconds=video_frame / self.fps,
            players=tuple(visible_players),
            ball=ball,
        )

    def _format_for(self, source_frame_id: int) -> _FormatBlock:
        index = bisect_right(self._format_starts, source_frame_id) - 1
        if index < 0:
            raise ValueError(
                f"{self.metadata_path}: no format block for frame {source_frame_id}"
            )
        block = self._formats[index]
        if source_frame_id > block.end_frame:
            raise ValueError(
                f"{self.metadata_path}: no format block for frame {source_frame_id}"
            )
        return block


def _read_float_text(root: ET.Element, tag: str) -> float:
    text = root.findtext(f".//{tag}")
    if text is None:
        raise ValueError(f"missing {tag} in tracking metadata")
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"invalid {tag} in tracking metadata: {text!r}")
    return value


def _read_pitch(root: ET.Element) -> tuple[float, float]:
    field = root.find(".//FieldSize")
    if field is None:
        raise ValueError("missing FieldSize in tracking metadata")
    length_text, width_text = field.findtext("Width"), field.findtext("Height")
    if length_text is None or width_text is None:
        raise ValueError("incomplete FieldSize in tracking metadata")
    return float(length_text), float(width_text)


def _read_formats(
    root: ET.Element,
    channel_map: dict[str, tuple[str, str]],
) -> tuple[_FormatBlock, ...]:
    blocks: list[_FormatBlock] = []
    for spec in root.findall(".//DataFormatSpecifications/DataFormatSpecification"):
        start = int(spec.get("startFrame", "0"))
        end = int(spec.get("endFrame", "-1"))
        player_container = next(
            (
                register
                for register in spec.findall("./SplitRegister")
                if register.find(".//PlayerChannelRef") is not None
            ),
            None,
        )
        ball_container = next(
            (
                register
                for register in spec.findall("./SplitRegister")
                if register.find(".//BallChannelRef") is not None
            ),
            None,
        )
        if player_container is None or ball_container is None:
            continue

        players: list[_PlayerGroup] = []
        for player_register in player_container.findall("./SplitRegister"):
            refs = player_register.findall("./PlayerChannelRef")
            mapped = [channel_map.get(ref.get("playerChannelId", "")) for ref in refs]
            mapped = [item for item in mapped if item is not None]
            if not mapped:
                continue
            track_ids = {track_id for track_id, _ in mapped}
            if len(track_ids) != 1:
                raise ValueError("one EPTS player register references multiple players")
            players.append(
                _PlayerGroup(
                    track_id=mapped[0][0],
                    channels=tuple(value_name for _, value_name in mapped),
                )
            )

        ball_channels = tuple(
            ref.get("channelId", "")
            for ref in ball_container.findall("./BallChannelRef")
            if ref.get("channelId")
        )
        if start > 0 and end >= start and players and ball_channels:
            blocks.append(
                _FormatBlock(
                    start_frame=start,
                    end_frame=end,
                    players=tuple(players),
                    ball_channels=ball_channels,
                )
            )

    blocks.sort(key=lambda block: block.start_frame)
    return tuple(blocks)


def _channel_values(encoded: str, channels: Sequence[str]) -> dict[str, float | None]:
    fields = encoded.split(",") if encoded else []
    values: dict[str, float | None] = {}
    for channel, field in zip(channels, fields):
        try:
            value = float(field)
        except (TypeError, ValueError):
            value = math.nan
        values[channel] = value if math.isfinite(value) else None
    for channel in channels[len(fields) :]:
        values[channel] = None
    return values


def _first_present(
    values: dict[str, float | None],
    *channels: str,
) -> float | None:
    for channel in channels:
        value = values.get(channel)
        if value is not None:
            return value
    return None

