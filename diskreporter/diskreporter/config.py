from __future__ import print_function

import json
import os

DEFAULT_CONFIG = {
    "port": 8087,
    "raid": "none",
    "raid_scan_seconds": 300,
    "user_scan_seconds": 3600,
    "volumes": [],
}

CONFIG_CANDIDATES = [
    os.environ.get("DISKREPORTER_CONFIG") or "",
    "/etc/diskreporter.json",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "diskreporter.json"),
]


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    for path in CONFIG_CANDIDATES:
        if not path:
            continue
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            continue
        fp = open(path, "r")
        try:
            data = json.load(fp)
        finally:
            fp.close()
        if isinstance(data, dict):
            cfg.update(data)
        cfg["_config_path"] = path
        return cfg
    cfg["_config_path"] = None
    return cfg
