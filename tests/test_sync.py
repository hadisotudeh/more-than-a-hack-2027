from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from app.sync import (
    BROADCAST_KICKOFF_SECONDS,
    first_half_kickoff_window,
    format_clock,
    source_kickoff_seconds,
    video_frame_at,
)


SMART_TAG_FIXTURE = """<?xml version="1.0"?>
<root>
  <instance>
    <start>10.5</start><end>15.5</end><code>SET PIECES</code>
    <label><group>Type</group><text>Kick Off (Start)</text></label>
    <label><group>Half</group><text>1st Half</text></label>
  </instance>
</root>
"""


class SyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "tags.xml"
        self.path.write_text(SMART_TAG_FIXTURE, encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_reads_first_half_kickoff_window(self) -> None:
        event = first_half_kickoff_window(self.path)
        self.assertEqual(event.start_seconds, 10.5)
        self.assertEqual(event.end_seconds, 15.5)
        self.assertEqual(event.duration_seconds, 5.0)

    def test_source_offsets(self) -> None:
        self.assertEqual(source_kickoff_seconds("tactical", self.path), 10.5)
        self.assertEqual(
            source_kickoff_seconds("broadcast", self.path),
            float(BROADCAST_KICKOFF_SECONDS),
        )

    def test_time_and_frame_helpers(self) -> None:
        self.assertEqual(video_frame_at(443.88, 25), 11097)
        self.assertEqual(format_clock(285), "04:45.00")


if __name__ == "__main__":
    unittest.main()

