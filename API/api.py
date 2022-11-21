#/usr/bin/env python3
import os.path
import os
import re
import time
from fastapi import Depends, FastAPI
import uvicorn
import json
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

with open("spec.json") as f:
    spec = json.load(f)

ascii = re.compile("([a-z]+)([0-9]+)")


def df():
    result = {}
    with os.popen("df","r") as pipe:
        for line in pipe:
            columns = line.split()
            fs = columns[0]
            if "/r" in fs or "/u" in fs:
                host, path = fs.split(":")
                total = int(columns[1])
                used  = int(columns[2])
                result[path] = {
                    "capacity": total,
                    "filled"  : used
                }
    return result


def ostype(hostname):
    with os.popen(f"ssh {hostname}.local 'fgrep PRETTY_NAME /etc/os-release'") as pipe:
        result = pipe.readline().split("=")
        if len(result) > 1:
            return result[1].strip().strip('"')
    with os.popen(f"ssh {hostname}.local 'cat /etc/system-release'") as pipe:
        s = pipe.readline().strip()
        if len(s):
            return s
    assert False


def get_spec(hostname):
    try:
        with os.popen(f"ssh {hostname}.local fgrep -i bogomips /proc/cpuinfo") as pipe:
            lines = pipe.readlines()
            print(lines)
            bogomips = [float(x.split(":")[1].strip()) for x in lines]
            cores = len(bogomips)
            mips = sum(bogomips) / cores
            return {
                "cores": cores,
                "mips":  mips,
                "ostype": ostype(hostname),
            }
    except:
        return

def ruptime():
    output = {}
    with os.popen("ruptime -a","r") as pipe:
        for line in pipe:
            columns = line.split()
            if len(columns) == 9:
                server = columns[0]
                if server not in spec:
                    s = get_spec(server)
                    if s is not None:
                        spec[server] = s
                        with open("spec.json", "w") as f:
                            json.dump(spec, f, indent=4, sort_keys=True)
                else:
                    output[server] = spec[server]
                if server in output:
                    load = columns[-3]
                    load = load[0:len(load)-1]
                    load = float(load)
                    output[server]["load"] = load
    return json.dumps(output)


app = FastAPI()
api = FastAPI(openapi_prefix="/v1")
app.mount("/v1", api)
app.mount("/", StaticFiles(directory="../loadmeters/public", html=True), name="static")


origins = [
    "*",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/ruptime")
async def load_average() -> str:
    return ruptime()


@api.get("/df")
async def disk_usage() -> str:
    return df()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8088)) )