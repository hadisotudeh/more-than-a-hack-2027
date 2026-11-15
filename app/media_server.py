"""Loopback-only, byte-range media serving for the large match videos.

``st.video`` stores local files in Streamlit's in-memory media store.  The challenge recordings
are several gigabytes each, so the dashboard instead gives the browser an HTTP endpoint that
streams only the byte ranges requested by the native HTML5 video element.
"""

from __future__ import annotations

import atexit
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import json
import sys
from threading import Thread
from urllib.parse import quote, unquote, urlsplit, parse_qs


_COPY_CHUNK_BYTES = 1024 * 1024


class _QuietDisconnectHTTPServer(ThreadingHTTPServer):
    """Ignore browser disconnects while preserving tracebacks for real server errors."""

    def handle_error(self, request, client_address) -> None:
        error = sys.exc_info()[1]
        if isinstance(error, (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


@dataclass(frozen=True, slots=True)
class LocalMediaServer:
    """A running media endpoint restricted to an explicit set of local files."""

    host: str
    port: int
    token: str
    keys: frozenset[str]
    _server: ThreadingHTTPServer = field(repr=False, compare=False)
    _thread: Thread = field(repr=False, compare=False)

    def url_for(self, key: str) -> str:
        if key not in self.keys:
            raise KeyError(f"unknown media key {key!r}")
        return f"http://{self.host}:{self.port}/{self.token}/{quote(key, safe='')}.mp4"

    def close(self) -> None:
        """Stop the endpoint, primarily for tests and explicit teardown."""

        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)

    def tracking_url_for(self, key: str) -> str:
        return self.url_for(key).removesuffix('.mp4') + '.json'


def start_local_media_server(media: dict[str, str | Path], tracking=None) -> LocalMediaServer:
    """Start a daemon HTTP server that supports single-range MP4 requests.

    The server binds only to ``127.0.0.1`` and exposes only the files supplied in ``media`` behind
    a random per-process URL token.  It is intended for the local Streamlit workflow in this
    repository, not as a production media service.
    """

    if not media:
        raise ValueError("at least one media file is required")

    files: dict[str, Path] = {}
    for key, raw_path in media.items():
        if not key or "/" in key or "\\" in key:
            raise ValueError(f"invalid media key: {key!r}")
        path = Path(raw_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"video not found: {path}")
        files[key] = path

    token = secrets.token_urlsafe(24)

    class RangeRequestHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            self._serve(send_body=False)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            self._serve(send_body=True)

        def _serve(self, *, send_body: bool) -> None:
            request_path = urlsplit(self.path).path
            prefix = f"/{token}/"
            if request_path.startswith(prefix) and request_path.endswith('.json'):
                key = unquote(request_path[len(prefix):-5])
                provider = (tracking or {}).get(key)
                if provider is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    start = int(parse_qs(urlsplit(self.path).query).get('frame', ['0'])[0])
                    if start < 0:
                        raise ValueError('negative frame')
                    body = json.dumps(provider(start), allow_nan=False).encode()
                except (ValueError, IndexError):
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                if send_body:
                    try:
                        self.wfile.write(body)
                    except OSError:
                        pass
                return
            if not request_path.startswith(prefix) or not request_path.endswith(".mp4"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            key = unquote(request_path[len(prefix) : -len(".mp4")])
            path = files.get(key)
            if path is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            size = path.stat().st_size
            byte_range = self.headers.get("Range")
            try:
                start, end, partial = _parse_range(byte_range, size)
            except ValueError:
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            length = end - start + 1
            self.send_response(HTTPStatus.PARTIAL_CONTENT if partial else HTTPStatus.OK)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "private, max-age=3600")
            if partial:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()

            if not send_body:
                return

            try:
                with path.open("rb") as handle:
                    handle.seek(start)
                    remaining = length
                    while remaining:
                        chunk = handle.read(min(_COPY_CHUNK_BYTES, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except OSError:
                # Seeking causes browsers to cancel obsolete range requests; that is expected.
                return

        def log_message(self, format: str, *args: object) -> None:
            # Avoid one terminal log entry for every browser range request.
            return

    server = _QuietDisconnectHTTPServer(("127.0.0.1", 0), RangeRequestHandler)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, name="match-media-server", daemon=True)
    thread.start()

    host, port = server.server_address[:2]
    endpoint = LocalMediaServer(
        host=str(host),
        port=int(port),
        token=token,
        keys=frozenset(files),
        _server=server,
        _thread=thread,
    )
    atexit.register(endpoint.close)
    return endpoint


def _parse_range(value: str | None, size: int) -> tuple[int, int, bool]:
    """Parse a single RFC 7233 byte range into inclusive bounds."""

    if size <= 0:
        raise ValueError("empty media file")
    if value is None:
        return 0, size - 1, False
    if not value.startswith("bytes=") or "," in value:
        raise ValueError("only one byte range is supported")

    bounds = value[len("bytes=") :].strip()
    if "-" not in bounds:
        raise ValueError("malformed byte range")
    start_text, end_text = bounds.split("-", 1)

    if not start_text:
        suffix_length = int(end_text)
        if suffix_length <= 0:
            raise ValueError("invalid suffix byte range")
        start = max(0, size - suffix_length)
        end = size - 1
    else:
        start = int(start_text)
        if start < 0 or start >= size:
            raise ValueError("range starts outside media")
        end = size - 1 if not end_text else min(int(end_text), size - 1)
        if end < start:
            raise ValueError("range ends before it starts")

    return start, end, True
