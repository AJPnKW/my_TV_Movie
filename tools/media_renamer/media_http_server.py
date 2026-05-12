# FILE: tools/media_renamer/media_http_server.py
# VERSION: v0.6.8
# UPDATED: 2026-05-11
from __future__ import annotations

import argparse
import mimetypes
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote


class RangeRequestHandler(SimpleHTTPRequestHandler):
    server_version = "MediaCleanupHTTP/0.6.8"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        root = Path(self.server.root_path).resolve()  # type: ignore[attr-defined]
        clean = unquote(path.split("?", 1)[0].split("#", 1)[0]).lstrip("/")
        candidate = (root / clean).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return str(root)
        return str(candidate)

    def send_head(self):  # noqa: ANN001
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            index = path / "Media_Library.html"
            if index.exists():
                path = index
            else:
                return self.list_directory(str(path))
        if not path.exists():
            self.send_error(404, "File not found")
            return None
        size = path.stat().st_size
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        range_header = self.headers.get("Range", "")
        if range_header.startswith("bytes="):
            start_text, _, end_text = range_header[6:].partition("-")
            try:
                start = int(start_text or "0")
                end = int(end_text) if end_text else size - 1
                end = min(end, size - 1)
                if start > end:
                    raise ValueError
            except ValueError:
                self.send_error(416, "Invalid range")
                return None
            handle = open(path, "rb")
            handle.seek(start)
            self.send_response(206)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(end - start + 1))
            self.end_headers()
            self.range_remaining = end - start + 1
            return handle
        handle = open(path, "rb")
        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.send_header("Content-Length", str(size))
        self.end_headers()
        return handle

    def copyfile(self, source, outputfile) -> None:  # noqa: ANN001
        remaining = getattr(self, "range_remaining", None)
        if remaining is None:
            return super().copyfile(source, outputfile)
        chunk_size = 1024 * 1024
        while remaining > 0:
            chunk = source.read(min(chunk_size, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.exists():
        raise FileNotFoundError(root)
    httpd = ThreadingHTTPServer((args.host, args.port), RangeRequestHandler)
    httpd.root_path = str(root)  # type: ignore[attr-defined]
    print(f"Serving {root} at http://{args.host}:{args.port}/Media_Library.html", flush=True)
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
