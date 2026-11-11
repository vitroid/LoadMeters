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


PD_GOOD_STATES = ("online", "optimal", "hot spare", "ready", "raw", "global hot spare", "dedicated hot spare")
PD_ERROR_COUNTERS = (
    "Hardware Error Count",
    "Medium Error Count",
    "Parity Error Count",
    "Link Failure Count",
    "Aborted Command Count",
)


def _kv(line):
    if ":" not in line:
        return None, None
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def _celsius(value):
    m = re.match(r"\s*(-?\d+)\s*C", value or "")
    if m:
        return int(m.group(1))
    return None


def _int_or_none(value):
    m = re.match(r"\s*(\d+)", value or "")
    if m:
        return int(m.group(1))
    return None


def parse_arcconf_pd(text):
    blocks = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r"Device #(\d+)$", line)
        if m:
            current = {"_id": m.group(1)}
            blocks.append(current)
            continue
        if current is None:
            continue
        if line.startswith("Device is "):
            current["_kind"] = line[len("Device is "):]
            continue
        key, value = _kv(line)
        if key and key not in current:
            current[key] = value

    disks = []
    for b in blocks:
        kind = b.get("_kind") or ""
        if "enclosure" in kind.lower() or "State" not in b:
            continue
        location = b.get("Reported Location") or ""
        m = re.search(r"Slot\s*(\d+)", location)
        cd = re.search(r"Connector\s*(\d+),\s*Device\s*(\d+)", location)
        if m:
            slot = m.group(1)
        elif cd:
            slot = "%s:%s" % (cd.group(1), cd.group(2))
        else:
            slot = b["_id"]
        state = b.get("State") or "unknown"
        smart = (b.get("S.M.A.R.T.") or "").lower()
        smart_warnings = _int_or_none(b.get("S.M.A.R.T. warnings"))
        errors = {}
        for name in PD_ERROR_COUNTERS:
            n = _int_or_none(b.get(name))
            if n:
                errors[name.replace(" Count", "")] = n
        warn = []
        if smart == "yes":
            warn.append("S.M.A.R.T. failure predicted")
        if smart_warnings:
            warn.append("S.M.A.R.T. warnings %d" % smart_warnings)
        disks.append({
            "id": b["_id"],
            "slot": slot,
            "location": location,
            "kind": kind,
            "state": state,
            "ok": state.lower().startswith(PD_GOOD_STATES),
            "vendor": b.get("Vendor") or "",
            "model": b.get("Model") or "",
            "serial": b.get("Serial number") or "",
            "size": b.get("Total Size") or "",
            "temperature": _celsius(b.get("Temperature")),
            "smart_warnings": smart_warnings,
            "errors": errors,
            "warnings": warn,
        })
    return disks


def parse_arcconf_ad(text):
    info = {}
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or set(line) <= set("-"):
            continue
        key, value = _kv(line)
        if key is None:
            section = line
            continue
        if "battery" in section.lower() or "zmm" in section.lower() or "backup" in section.lower():
            if key in ("Status", "Overall Backup Unit Status") and "backup" not in info:
                info["backup"] = value
            continue
        if key not in info:
            info[key] = value
    if "Controller Status" not in info:
        return None
    temp_text = info.get("Temperature") or ""
    return {
        "model": info.get("Controller Model") or "",
        "status": info.get("Controller Status"),
        "ok": info.get("Controller Status", "").lower() == "optimal",
        "temperature": _celsius(temp_text),
        "temperature_abnormal": "abnormal" in temp_text.lower(),
        "defunct": _int_or_none(info.get("Defunct disk drive count")),
        "backup": info.get("backup") or "",
    }


def merge_arcconf_health(result, disks, controller):
    bad = []
    warnings = []
    for d in disks:
        if not d["ok"]:
            bad.append("slot %s %s" % (d["slot"], d["state"]))
        for w in d["warnings"]:
            warnings.append("slot %s: %s" % (d["slot"], w))
    if controller:
        if not controller["ok"]:
            bad.append("controller " + (controller["status"] or "unknown"))
        if controller["defunct"]:
            bad.append("defunct disks %d" % controller["defunct"])
        if controller["temperature_abnormal"]:
            warnings.append("controller temperature abnormal")
        if "fail" in controller["backup"].lower():
            warnings.append("cache backup " + controller["backup"])
    result["disks"] = disks
    result["controller"] = controller
    result["warnings"] = warnings
    if bad:
        if result["ok"]:
            result["status"] = ", ".join(bad)
        else:
            result["status"] = result["status"] + ", " + ", ".join(bad)
        result["ok"] = False
    return result


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
    result = parse_arcconf(text)
    try:
        disks = parse_arcconf_pd(_run([ARCCONF_BIN, "getconfig", "1", "PD"]))
    except OSError:
        disks = []
    try:
        controller = parse_arcconf_ad(_run([ARCCONF_BIN, "getconfig", "1", "AD"]))
    except OSError:
        controller = None
    return merge_arcconf_health(result, disks, controller)


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
