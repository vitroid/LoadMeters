from __future__ import print_function

import os
import subprocess

from diskreporter.raid import _to_text


def df_volume(path, label):
    try:
        st = os.statvfs(path)
        fr = st.f_frsize
        total = fr * st.f_blocks
        free = fr * st.f_bavail
        used = total - fr * st.f_bfree
        return {
            "label": label,
            "path": path,
            "total": int(total),
            "used": int(used),
            "free": int(free),
            "users": {},
            "error": None,
        }
    except OSError as e:
        return {
            "label": label,
            "path": path,
            "total": 0,
            "used": 0,
            "free": 0,
            "users": {},
            "error": str(e),
        }


def _du_bytes(path):
    try:
        p = subprocess.Popen(
            ["du", "-s", "--block-size=1", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, _err = p.communicate()
        if p.returncode != 0 or not out:
            return None
        text = _to_text(out)
        return int(text.split()[0])
    except (OSError, ValueError):
        return None


def user_usage(path):
    users = {}
    try:
        names = sorted(os.listdir(path))
    except OSError:
        return users
    for name in names:
        if name.startswith("."):
            continue
        pth = os.path.join(path, name)
        try:
            if not os.path.isdir(pth) or os.path.islink(pth):
                continue
        except OSError:
            continue
        size = _du_bytes(pth)
        if size is not None:
            users[name] = size
    return users


def collect_volumes(spec, prev_users=None):
    if prev_users is None:
        prev_users = {}
    out = []
    for item in spec or []:
        path = item.get("path")
        if not path:
            continue
        label = item.get("label") or os.path.basename(path.rstrip("/")) or path
        vol = df_volume(path, label)
        if path in prev_users:
            vol["users"] = prev_users[path]
        out.append(vol)
    return out


def collect_users(spec):
    users_by_path = {}
    for item in spec or []:
        if not item.get("users"):
            continue
        path = item.get("path")
        if not path:
            continue
        users_by_path[path] = user_usage(path)
    return users_by_path
