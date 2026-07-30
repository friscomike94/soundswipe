#!/usr/bin/env python3
"""SoundSwipe Ableton local bridge.

Serves the existing SoundSwipe UI and streams Ableton Core Library preview OGG
files without copying or uploading them. Ratings still sync from the browser to
Supabase through the existing SoundSwipe client.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import secrets
import socket
import subprocess
import sys
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
DEFAULT_CORE_ROOT = Path(
    "/Applications/Ableton Live 12 Trial.app/Contents/App-Resources/Core Library"
)
CATALOG_PATH = APP_ROOT / "data" / "ableton_core_library_catalog.json"
TOKEN_PATH = APP_ROOT.parent / ".soundswipe_ableton_bridge_token"


def load_or_create_token() -> str:
    if TOKEN_PATH.exists():
        token = TOKEN_PATH.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = secrets.token_urlsafe(18)
    TOKEN_PATH.write_text(token, encoding="utf-8")
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except OSError:
        pass
    return token


def local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def local_hostname() -> str:
    try:
        name = subprocess.check_output(
            ["/usr/sbin/scutil", "--get", "LocalHostName"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if name:
            return f"{name}.local"
    except (OSError, subprocess.SubprocessError):
        pass
    return local_ip()


def primary_role(item: dict) -> str:
    groups = item.get("tag_groups") or {}
    for group_name in ("Sounds", "Drums"):
        values = groups.get(group_name) or []
        if values:
            return str(values[0]).split("|")[0]
    category = item.get("category") or item.get("library_section") or "Other"
    return str(category)


def load_catalog(core_root: Path) -> tuple[list[dict], dict[str, dict]]:
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    items = []
    item_map: dict[str, dict] = {}
    preview_root = core_root / "Ableton Folder Info" / "Previews"
    for item in raw.get("items", []):
        preset_rel = str(item.get("preset_relative_path") or "")
        preview_rel = str(item.get("preview_relative_path") or "")
        if not preset_rel or not preview_rel:
            continue
        entry = {
            "id": str(item.get("id") or f"ableton:{preset_rel}"),
            "name": str(item.get("preset_name") or Path(preset_rel).stem),
            "role": primary_role(item),
            "engine": str(item.get("engine") or ""),
            "category": str(item.get("category") or ""),
            "content_type": str(item.get("content_type") or ""),
            "library_section": str(item.get("library_section") or ""),
            "factory_tags": list(item.get("factory_tags") or []),
            "feature_dimensions": int(item.get("feature_dimensions") or 0),
            "preset_relative_path": preset_rel,
            "preview_relative_path": preview_rel,
            "preview_path": preview_root / preview_rel,
        }
        items.append(entry)
        item_map[entry["id"]] = entry
    return items, item_map


class BridgeHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, *, token: str, core_root: Path):
        super().__init__(address, handler)
        self.token = token
        self.core_root = core_root
        self.items, self.item_map = load_catalog(core_root)
        self.source_items = [
            x for x in self.items if x["library_section"] in ("Devices", "Racks")
        ]
        self.gesture_items = [
            x for x in self.items if x["library_section"] in ("Grooves", "MIDI Clips")
        ]


class BridgeHandler(SimpleHTTPRequestHandler):
    server_version = "SoundSwipeAbletonBridge/0.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_ROOT), **kwargs)

    @property
    def bridge(self) -> BridgeHTTPServer:
        return self.server  # type: ignore[return-value]

    def end_headers(self) -> None:
        if getattr(self, "_set_pair_cookie", False):
            self.send_header(
                "Set-Cookie",
                f"ss_ableton_bridge={self.bridge.token}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Strict",
            )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _query(self) -> dict[str, list[str]]:
        return urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)

    def _authorized(self) -> bool:
        provided = (self._query().get("t") or [""])[0]
        if provided and secrets.compare_digest(provided, self.bridge.token):
            return True
        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        paired = cookies.get("ss_ableton_bridge")
        return bool(paired and secrets.compare_digest(paired.value, self.bridge.token))

    def _json(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _require_token(self) -> bool:
        if self._authorized():
            return True
        self._json({"ok": False, "error": "bridge_token_required"}, 403)
        return False

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Allow", "GET, HEAD, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/ableton/health":
            if not self._require_token():
                return
            missing = sum(1 for x in self.bridge.items if not x["preview_path"].is_file())
            self._json(
                {
                    "ok": missing == 0,
                    "bridge_version": "0.1",
                    "total": len(self.bridge.items),
                    "source_total": len(self.bridge.source_items),
                    "gesture_total": len(self.bridge.gesture_items),
                    "missing_previews": missing,
                    "sound_analyzer_vectors": sum(
                        1 for x in self.bridge.items if x["feature_dimensions"] == 64
                    ),
                }
            )
            return
        if parsed.path == "/ableton/catalog":
            if not self._require_token():
                return
            lane = (self._query().get("lane") or ["source"])[0]
            source = (
                self.bridge.gesture_items if lane == "gesture" else self.bridge.source_items
            )
            payload = []
            for x in source:
                payload.append(
                    {
                        "id": x["id"],
                        "name": x["name"],
                        "role": x["role"],
                        "engine": x["engine"],
                        "category": x["category"],
                        "content_type": x["content_type"],
                        "library_section": x["library_section"],
                        "factory_tags": x["factory_tags"],
                        "feature_dimensions": x["feature_dimensions"],
                        "preview_url": "/ableton/preview?id="
                        + urllib.parse.quote(x["id"], safe=""),
                    }
                )
            self._json({"lane": lane, "count": len(payload), "items": payload})
            return
        if parsed.path == "/ableton/preview":
            if not self._require_token():
                return
            item_id = (self._query().get("id") or [""])[0]
            item = self.bridge.item_map.get(item_id)
            if not item:
                self.send_error(HTTPStatus.NOT_FOUND, "Unknown Ableton item")
                return
            self._serve_audio(item["preview_path"])
            return
        allowed_static = {"/", "/index.html", "/manifest.json", "/manifest.webmanifest", "/sw.js"}
        if parsed.path not in allowed_static:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        if parsed.path in ("/", "/index.html"):
            self._set_pair_cookie = True
        super().do_GET()

    def _serve_audio(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Preview not found")
            return
        size = path.stat().st_size
        start, end = 0, size - 1
        range_header = self.headers.get("Range", "")
        partial = False
        if range_header.startswith("bytes="):
            try:
                raw_start, raw_end = range_header[6:].split("-", 1)
                if raw_start:
                    start = max(0, int(raw_start))
                if raw_end:
                    end = min(size - 1, int(raw_end))
                partial = True
            except (ValueError, TypeError):
                start, end, partial = 0, size - 1, False
        length = max(0, end - start + 1)
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "audio/ogg")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as handle:
            handle.seek(start)
            remaining = length
            while remaining > 0:
                chunk = handle.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def log_message(self, fmt: str, *args) -> None:
        sys.stdout.write("[bridge] " + (fmt % args) + "\n")
        sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="SoundSwipe Ableton local bridge")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8877, type=int)
    parser.add_argument("--core-root", type=Path, default=DEFAULT_CORE_ROOT)
    parser.add_argument("--no-open", action="store_true", help="Do not open the Mac browser")
    args = parser.parse_args()

    if not CATALOG_PATH.is_file():
        raise SystemExit(f"Catalog not found: {CATALOG_PATH}")
    if not args.core_root.is_dir():
        raise SystemExit(f"Ableton Core Library not found: {args.core_root}")

    token = load_or_create_token()
    server = BridgeHTTPServer(
        (args.host, args.port), BridgeHandler, token=token, core_root=args.core_root
    )
    host = local_hostname()
    url = f"http://{host}:{args.port}/"
    print("\nSoundSwipe Ableton Bridge is ready")
    print(f"Phone URL: {url}")
    print(f"Items: {len(server.items)} total / {len(server.source_items)} source / {len(server.gesture_items)} gesture")
    print("Keep this terminal and Mac awake while rating.\n")
    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping bridge.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
