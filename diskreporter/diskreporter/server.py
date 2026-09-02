#!/usr/bin/env python
"""stdlib-only HTTP server. Python 2.6+ / 3.x. No pip packages.

ThreadingMixIn + HTTP/1.0 close. A single-thread BaseHTTPServer treats
HTTP/1.1 keep-alive as persistent and blocks all other clients (false
unreachable alarms in LoadMeters).
"""
from __future__ import print_function

import json
import logging
import os
import socket
import sys
import threading
import time

try:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    from SocketServer import ThreadingMixIn
except ImportError:
    from socketserver import ThreadingMixIn

from diskreporter import __version__
from diskreporter.config import load_config
from diskreporter.raid import collect_raid
from diskreporter.volumes import collect_users, collect_volumes

__api_version__ = 1

_cache_lock = threading.Lock()
_cache = {
    "hostname": socket.gethostname().split(".")[0],
    "raid": {"backend": "none", "ok": True, "status": "pending", "arrays": []},
    "volumes": [],
    "updated": 0,
    "users_updated": 0,
    "version": __version__,
    "api": __api_version__,
}
_config = {}
_log = logging.getLogger("diskreporter")


def _users_map_from_volumes(volumes):
    out = {}
    for v in volumes or []:
        if v.get("path"):
            out[v["path"]] = v.get("users") or {}
    return out


def refresh_fast():
    raid = collect_raid(_config.get("raid"))
    with _cache_lock:
        prev = _users_map_from_volumes(_cache.get("volumes") or [])
    volumes = collect_volumes(_config.get("volumes") or [], prev)
    with _cache_lock:
        _cache["raid"] = raid
        _cache["volumes"] = volumes
        _cache["updated"] = time.time()
        _cache["hostname"] = socket.gethostname().split(".")[0]
    _log.info(
        "disk refresh raid=%s ok=%s volumes=%s",
        raid.get("backend"),
        raid.get("ok"),
        len(volumes),
    )


def refresh_users():
    users = collect_users(_config.get("volumes") or [])
    with _cache_lock:
        for vol in _cache.get("volumes") or []:
            if vol.get("path") in users:
                vol["users"] = users[vol["path"]]
        _cache["users_updated"] = time.time()
        _cache["updated"] = time.time()
    _log.info("user usage refresh paths=%s", len(users))


def _loop(fn, seconds, minimum):
    interval = max(minimum, float(seconds or minimum))
    while True:
        try:
            fn()
        except Exception as e:
            _log.error("%s: %s", fn.__name__, e)
        time.sleep(interval)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    timeout = 10

    def setup(self):
        BaseHTTPRequestHandler.setup(self)
        self.close_connection = 1

    def handle(self):
        self.close_connection = 1
        self.handle_one_request()

    def log_message(self, fmt, *args):
        _log.info("%s - " + fmt, self.address_string(), *args)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/v1/info", "/info"):
            with _cache_lock:
                payload = dict(_cache)
            body = json.dumps(payload)
            if sys.version_info[0] >= 3 and not isinstance(body, bytes):
                body = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    global _config
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _config = load_config()
    host = os.environ.get("HOST") or "0.0.0.0"
    port = int(os.environ.get("PORT") or _config.get("port") or 8087)
    _log.info(
        "diskreporter config=%s raid=%s volumes=%s python=%s",
        _config.get("_config_path"),
        _config.get("raid"),
        len(_config.get("volumes") or []),
        sys.version.split()[0],
    )
    refresh_fast()
    t_fast = threading.Thread(
        target=_loop,
        args=(refresh_fast, _config.get("raid_scan_seconds"), 30),
    )
    t_users = threading.Thread(
        target=_loop,
        args=(refresh_users, _config.get("user_scan_seconds"), 60),
    )
    t_fast.daemon = True
    t_users.daemon = True
    t_fast.start()
    t_users.start()
    httpd = ThreadingHTTPServer((host, port), Handler)
    _log.info("listening on http://%s:%s/v1/info", host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
