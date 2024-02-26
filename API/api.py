#/usr/bin/env python3
import json
import os
import os.path
import socket

import requests
import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_utils.tasks import repeat_every

__api_version__ = 1

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf


def uint32_to_ip(t):
    # t = struct.pack("!I", ipn)
    return socket.inet_ntoa(t)


class MyListener(ServiceListener):

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(name)
        print(f"Service {name} updated")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} removed")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        # 賢明な方法ではないが、ほかにthread間でデータを渡すうまい方法を知らない。
        try:
            with open("servers.json") as f:
                data = json.load(f)
        except:
            data = {}
        # with open("debug.txt", "w") as f:
        #     print([uint32_to_ip(a) for a in info.addresses], file=f)
        data[info.server] = {
            "port": info.port,
            "addresses": [uint32_to_ip(a) for a in info.addresses]
        }
        with open("servers.json", "w") as f:
            json.dump(data, f, indent=4)
        print(f"Service {name} added, service info: {info}")


app = FastAPI()
api = FastAPI(root_path=f"/v{__api_version__}")
app.mount(f"/v{__api_version__}", api)
app.mount("/", StaticFiles(directory="../loadmeters/public", html=True), name="static")



@app.on_event("startup")
@repeat_every(seconds=15)  # 15 seconds
def update_history() -> None:
    fn = "servers.json"
    try:
        with open(fn) as f:
            servers = json.load(f)
    except:
        servers = {}
    fn = "stat.json"
    try:
        with open(fn) as f:
            stat = json.load(f)
    except:
        stat = dict()
    for server, info in servers.items():
        headers = {"Accept": "application/json"}
        shortname = server.replace(".local.", "")
        try:
            port = info["port"]
            r = requests.get(f'http://{server}:{port}/v1/info', headers=headers)
            data = r.json()
            if shortname not in stat:
                stat[shortname] = dict()
            stat[shortname] = stat[shortname] | data
            stat[shortname]["address"] = info["addresses"]
            stat[shortname]["history"] = stat[shortname].get("history", [])
            stat[shortname]["history"].append(data["load"])
        except:
            stat[shortname]["history"].append(-1)
        if len(stat[shortname]["history"]) > 60:
            stat[shortname]["history"] = stat[shortname]["history"][-60:]
    with open(fn, "w") as f:
        json.dump(stat, f, indent=4)


# update_history()

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


@api.get("/stat")
async def load_average():
    try:
        with open("stat.json") as f:
            return json.load(f)
    except:
        return {}


if __name__ == "__main__":
    zeroconf = Zeroconf()
    listener = MyListener()
    browser = ServiceBrowser(zeroconf, "_loadreporter._tcp.local.", listener)
    uvicorn.run("api:app", host="0.0.0.0", reload=True, port=int(os.environ.get("PORT", 8088)) )
