from __future__ import print_function

import os
import re
import subprocess

ARCCONF_BIN = os.environ.get("ARCCONF") or "/usr/StorMan/arcconf"


def _to_text(data):
    if data is None:
        return ""
    if isinstance(data, type(u"")):
        return data
    try:
        return data.decode("utf-8", "replace")
    except Exception:
        return str(data)


def _run(cmd):
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = p.communicate()
    return _to_text(out) + _to_text(err)


def parse_arcconf(text):
    arrays = []
    current = None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = re.match(r"Logical device number\s+(\S+)", line, re.I)
        if m:
            if current:
                arrays.append(current)
            current = {
                "id": m.group(1),
                "name": "",
                "level": "",
                "state": "",
                "size": "",
            }
            continue
        if current is None:
            continue
        if "Logical device name" in line:
            current["name"] = line.split(":", 1)[-1].strip()
        elif re.search(r"RAID level", line, re.I):
            current["level"] = line.split(":", 1)[-1].strip()
        elif re.search(r"Status of logical device", line, re.I):
            current["state"] = line.split(":", 1)[-1].strip()
        elif re.match(r"\s+Size\s*:", line):
            current["size"] = line.split(":", 1)[-1].strip()
    if current:
        arrays.append(current)

    bad = []
    for arr in arrays:
        state = (arr.get("state") or "").lower()
        if state != "optimal":
            bad.append(arr.get("state") or "unknown")
    if not arrays:
        return {
            "backend": "arcconf",
            "ok": False,
            "status": "no logical devices",
            "arrays": arrays,
            "detail": (text[-2000:] if text else "empty arcconf output"),
        }
    ok = len(bad) == 0
    status = "Optimal" if ok else ", ".join(bad)
    return {
        "backend": "arcconf",
        "ok": ok,
        "status": status,
        "arrays": arrays,
        "detail": "" if ok else text[-2000:],
    }


def collect_arcconf():
    if not os.path.isfile(ARCCONF_BIN) and not os.environ.get("ARCCONF"):
        return {
            "backend": "arcconf",
            "ok": False,
            "status": "arcconf not found",
            "arrays": [],
            "detail": ARCCONF_BIN,
        }
    try:
        text = _run([ARCCONF_BIN, "getconfig", "1", "LD"])
    except OSError as e:
        return {
            "backend": "arcconf",
            "ok": False,
            "status": "arcconf failed",
            "arrays": [],
            "detail": str(e),
        }
    return parse_arcconf(text)


def parse_mdstat(text):
    arrays = []
    ok = True
    statuses = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(md\d+)\s*:\s*(.*)$", line)
        if m:
            name, rest = m.group(1), m.group(2)
            if "active" in rest:
                state = "active"
            elif rest:
                state = rest.split()[0]
            else:
                state = "unknown"
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            degraded = bool(re.search(r"\[[U_]*_[U_]*\]", next_line))
            recovering = "recovery" in next_line.lower() or "resync" in next_line.lower()
            if "inactive" in rest.lower() or degraded or recovering:
                ok = False
                if recovering:
                    state = "rebuild"
                elif degraded:
                    state = "degraded"
            arrays.append({"id": name, "name": name, "level": "", "state": state, "size": ""})
            statuses.append(state)
        i += 1
    if not arrays:
        return {
            "backend": "mdadm",
            "ok": True,
            "status": "no md arrays",
            "arrays": [],
            "detail": "",
        }
    return {
        "backend": "mdadm",
        "ok": ok,
        "status": "Optimal" if ok else ", ".join(statuses),
        "arrays": arrays,
        "detail": "" if ok else text[-2000:],
    }


def collect_mdadm():
    path = "/proc/mdstat"
    try:
        fp = open(path, "r")
        try:
            text = fp.read()
        finally:
            fp.close()
    except OSError as e:
        return {
            "backend": "mdadm",
            "ok": False,
            "status": "mdstat unreadable",
            "arrays": [],
            "detail": str(e),
        }
    return parse_mdstat(text)


def collect_none():
    return {
        "backend": "none",
        "ok": True,
        "status": "n/a",
        "arrays": [],
        "detail": "",
    }


BACKENDS = {
    "arcconf": collect_arcconf,
    "mdadm": collect_mdadm,
    "none": collect_none,
}


def collect_raid(backend):
    name = (backend or "none").lower()
    fn = BACKENDS.get(name)
    if not fn:
        return {
            "backend": name,
            "ok": False,
            "status": "unknown backend " + name,
            "arrays": [],
            "detail": "",
        }
    return fn()
