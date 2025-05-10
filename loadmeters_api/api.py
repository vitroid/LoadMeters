#/usr/bin/env python3
import json
import os
import os.path
import socket
import subprocess
import sys

import requests
import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_utilities import repeat_every
from logging import getLogger, basicConfig, INFO, DEBUG
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
# Svelte? UIもこいつがserveする。
app.mount("/", StaticFiles(directory="/var/lib/loadmeters/public", html=True), name="static")


import http3

client = http3.AsyncClient()

async def call_api(url: str, **kwarg)->str:

    r = await client.get(url, **kwarg)
    return r.text

from requests.exceptions import Timeout, ConnectionError

@app.on_event("startup")
@repeat_every(seconds=5)  # 5 seconds  調子が悪くなったら、これをコメントアウトし、exceptでキャッチできていないエラーをさぐる
async def update_history() -> None:
# def update_history() -> None:
    logger = getLogger("uvicorn.app")
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
    logger.debug(servers)
    for i, server in enumerate(servers):
        logger.debug(f"{i}. {server}")
    logger.debug("----")

    for server, info in servers.items():
        logger.debug(server)
        headers = {"Accept": "application/json"}
        shortname = server.replace(".local.", "")
        port = info["port"]
        url = f'http://{server}:{port}/v1/info'
        try:
            logger.info(f"Try {url}")
            r = requests.get(f'http://{server}:{port}/v1/info', headers=headers) #, timeout=2)
            # r = await call_api(f'http://{server}:{port}/v1/info', headers=headers)
            logger.debug(f"Status code {r.status_code}")
            data = r.json()
            logger.info(f"  Obtained from {server}")
            if shortname not in stat:
                stat[shortname] = dict()
            stat[shortname] = stat[shortname] | data
            stat[shortname]["address"] = info["addresses"]
            stat[shortname]["history"] = stat[shortname].get("history", [])
            stat[shortname]["history"].append(data["load"])
        # except Timeout:
        #     logger.info(f"Failed to get info from {server}.")
        #     stat[shortname]["history"].append(-1)
        except ConnectionError:
            logger.info(f"  Failed to get info from {server}.")
            if shortname in stat:
                stat[shortname]["history"] = stat[shortname].get("history", [])
                stat[shortname]["history"].append(-1)
        finally:
            pass
        if shortname in stat and "history" in stat[shortname] and len(stat[shortname]["history"]) > 60:
            stat[shortname]["history"] = stat[shortname]["history"][-60:]
    logger.info("dump.")
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


def setup_service():
    print("Setting up service...")
    try:
        # systemdサービスファイルの作成
        service_content = """[Unit]
Description=Load Meters Monitoring Service
After=network.target

[Service]
Type=simple
User=root
Restart=always
RestartSec=1
ExecStart=/usr/bin/python3 -m loadmeters_api.api
WorkingDirectory=/var/lib/loadmeters
Environment=PORT=8081

[Install]
WantedBy=multi-user.target
"""
        
        # サービスファイルを書き込み
        service_path = "/etc/systemd/system/loadmeters.service"
        print(f"Writing service file to {service_path}")
        with open(service_path, "w") as f:
            f.write(service_content)
        print(f"Created service file at {service_path}")
        
        # データディレクトリの作成
        data_dir = "/var/lib/loadmeters"
        print(f"Creating data directory at {data_dir}")
        os.makedirs(data_dir, exist_ok=True)
        print("Created data directory")
        
        # systemdの再読み込みとサービスの有効化
        print("Reloading systemd...")
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        print("Systemd reloaded")
        
        print("Enabling loadmeters service...")
        subprocess.run(["systemctl", "enable", "loadmeters"], check=True)
        print("Service enabled")
        
        print("Starting loadmeters service...")
        subprocess.run(["systemctl", "start", "loadmeters"], check=True)
        print("Service started")
        
        print("Service setup completed successfully")
    except Exception as e:
        print(f"Error during service setup: {e}", file=sys.stderr)
        print(f"Error type: {type(e)}", file=sys.stderr)
        print(f"Error details: {str(e)}", file=sys.stderr)
        raise

def main():
    basicConfig(level=INFO)
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_service()
        return
    zeroconf = Zeroconf()
    listener = MyListener()
    browser = ServiceBrowser(zeroconf, "_loadreporter._tcp.local.", listener)
    uvicorn.run("api:app", host="0.0.0.0", reload=False, port=int(os.environ.get("PORT", "8081")))

if __name__ == "__main__":
    main()
