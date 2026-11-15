from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
import tempfile
import unittest
from urllib.request import Request, urlopen

from app.media_server import _parse_range, start_local_media_server


class RangeParsingTests(unittest.TestCase):
    def test_full_file_and_common_ranges(self) -> None:
        self.assertEqual(_parse_range(None, 100), (0, 99, False))
        self.assertEqual(_parse_range("bytes=10-19", 100), (10, 19, True))
        self.assertEqual(_parse_range("bytes=95-", 100), (95, 99, True))
        self.assertEqual(_parse_range("bytes=-4", 100), (96, 99, True))

    def test_rejects_invalid_or_multiple_ranges(self) -> None:
        for value in ("items=0-1", "bytes=100-", "bytes=5-2", "bytes=0-1,3-4"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _parse_range(value, 100)


class MediaServerTests(unittest.TestCase):
    def test_streams_only_the_requested_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "sample.mp4"
            video.write_bytes(b"0123456789")
            try:
                endpoint = start_local_media_server({"sample": video})
            except PermissionError as exc:
                self.skipTest(f"loopback sockets are disabled in this environment: {exc}")
            try:
                request = Request(endpoint.url_for("sample"), headers={"Range": "bytes=2-5"})
                with urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, HTTPStatus.PARTIAL_CONTENT)
                    self.assertEqual(response.headers["Accept-Ranges"], "bytes")
                    self.assertEqual(response.headers["Content-Range"], "bytes 2-5/10")
                    self.assertEqual(response.read(), b"2345")
            finally:
                endpoint.close()


if __name__ == "__main__":
    unittest.main()
