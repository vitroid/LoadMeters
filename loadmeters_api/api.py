#/usr/bin/env python3
import json
import os
import os.path
import socket
import subprocess
import sys
import aiofiles
import asyncio
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_utilities import repeat_every
from logging import getLogger, basicConfig, INFO, DEBUG
__api_version__ = 1
DATA_DIR = os.environ.get("LOADMETERS_DATA", "/var/lib/loadmeters")

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
try:
    from zeroconf import InterfacesType
except ImportError:
    InterfacesType = None  # 古い zeroconf では未定義


def uint32_to_ip(t):
    """Zeroconf の addresses 要素（IPv4/IPv6混在の bytes）から IPv4 だけ文字列に変換"""
    try:
        if isinstance(t, (bytes, bytearray)) and len(t) == 4:
            return socket.inet_ntoa(t)
    except OSError:
        # IPv6 (16byte) など inet_ntoa で扱えないものは無視
        return None
    return None


class MyListener(ServiceListener):
    def __init__(self, loop=None, json_filename="servers.json"):
        self._update_lock = asyncio.Lock()
        self._pending_updates = {}
        self._update_task = None
        self._loop = loop
        self.json_filename = json_filename

    def set_loop(self, loop):
        """メインイベントループを設定"""
        self._loop = loop

    def _schedule_server_update(self, server: str, port: int, addresses: list):
        """サーバー情報の更新をスケジュール（頻繁な更新をバッファリング）"""
        self._pending_updates[server] = {
            "port": port,
            "addresses": addresses
        }
        
        # 既存のタスクをキャンセルして新しいタスクをスケジュール
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
        
        # メインイベントループが利用可能な場合のみタスクを作成
        if self._loop and self._loop.is_running():
            self._update_task = asyncio.run_coroutine_threadsafe(
                self._flush_updates(), self._loop
            )
        else:
            # イベントループが利用できない場合は同期的に処理
            getLogger("uvicorn.error").warning("Event loop not available, skipping server update")

    async def _flush_updates(self):
        """ペンディング中の更新をファイルに書き込み"""
        await asyncio.sleep(1.0)  # 1秒待ってバッチ処理
        
        if not self._pending_updates:
            return
            
        try:
            # 現在のデータを読み込み
            data = await read_json_file_async(self.json_filename)
            
            # ペンディング中の更新を適用
            for server, info in self._pending_updates.items():
                # Zeroconf からは IPv4/IPv6 が混ざった bytes の配列で渡されることがある。
                # inet_ntoa で扱える IPv4 (4byte) だけを取り出し、それ以外は無視する。
                addrs: list[str] = []
                for addr in info["addresses"]:
                    ip = uint32_to_ip(addr)
                    if ip:
                        addrs.append(ip)

                data[server] = {
                    "port": info["port"],
                    "addresses": addrs,
                }
            
            # ファイルに書き込み
            await write_json_file_async(self.json_filename, data)
            
            # ペンディング更新をクリア
            n = len(self._pending_updates)
            self._pending_updates.clear()
            getLogger("uvicorn.error").info(f"Updated {self.json_filename} with {n} servers")
            
        except Exception as e:
            getLogger("uvicorn.error").error(f"Error updating {self.json_filename}: {e}")

    def _on_service_resolved(self, zc: Zeroconf, type_: str, name: str, info) -> None:
        """解決済みサービス情報を反映（add_service/update_service から共通で使用）"""
        if not info or not info.addresses:
            return
        # info.server は "tc.local." のような FQDN、port と addresses は取得済み
        self._schedule_server_update(info.server, info.port, info.addresses)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            self._on_service_resolved(zc, type_, name, info)
        else:
            getLogger("uvicorn.error").debug(f"Zeroconf update_service: {name} get_service_info=None, will retry")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        # サービス削除時の処理（必要に応じて実装）
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """mDNS でサービス発見時に呼ばれる。get_service_info は解決直後は None になりうるため遅延再取得する"""
        log = getLogger("uvicorn.error")
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            log.info(f"Zeroconf: discovered {name} -> {info.server}:{info.port}")
            self._on_service_resolved(zc, type_, name, info)
            return
        # 同一ホストや解決の遅れで None になりうる → メインループで少し待ってから再取得
        if self._loop and self._loop.is_running():
            async def resolve_later():
                await asyncio.sleep(0.8)
                info2 = zc.get_service_info(type_, name)
                if info2 and info2.addresses:
                    log.info(f"Zeroconf: discovered (retry) {name} -> {info2.server}:{info2.port}")
                    self._on_service_resolved(zc, type_, name, info2)
                else:
                    log.warning(f"Zeroconf: {name} still unresolved after retry (get_service_info={info2})")
            asyncio.run_coroutine_threadsafe(resolve_later(), self._loop)
        else:
            log.warning(f"Zeroconf: add_service {name} but get_service_info=None and no event loop")


# グローバル変数でZeroconf関連オブジェクトを保持
zeroconf_instance = None
listener_instance = None
browser_instance = None
disk_listener_instance = None
disk_browser_instance = None
_supervisor_task = None
_disk_supervisor_task = None

app = FastAPI()
api = FastAPI(root_path=f"/v{__api_version__}")
app.mount(f"/v{__api_version__}", api)

def find_static_dir():
    """Svelte のビルド成果物 (index.html) があるディレクトリを探す。"""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.environ.get("LOADMETERS_STATIC", ""),
        "/var/lib/loadmeters/public",
        os.path.join(here, "public"),
        os.path.join(here, "..", "loadmeters", "public"),
    ]
    for path in candidates:
        if path and os.path.isfile(os.path.join(path, "index.html")):
            return os.path.abspath(path)
    return None


# Svelte UI も同じプロセスで配信する（デフォルトポート 8080）。
static_dir = find_static_dir()
if static_dir:
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    getLogger("uvicorn.error").info("Serving UI from %s", static_dir)
else:
    getLogger("uvicorn.error").warning("Static UI directory not found; / will 404")


# 各ホスト独立。接続タイムアウトは短く、死んだ相手が他を巻き込まないようにする。
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=1.5, read=3.0, write=3.0, pool=5.0),
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
)
# diskreporter は HTTP/1.0。keepalive すると相手が接続待ちで止まり、誤警告になる。
disk_http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=2.0, read=8.0, write=5.0, pool=5.0),
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=0),
    headers={"Accept": "application/json", "Connection": "close"},
)
POLL_INTERVAL = 5.0
DISK_POLL_INTERVAL = 300.0
_stat_lock = asyncio.Lock()
_disk_lock = asyncio.Lock()
_poll_tasks = {}
_disk_poll_tasks = {}

async def call_api(url: str, **kwargs) -> str:
    """非同期HTTPリクエスト"""
    r = await http_client.get(url, **kwargs)
    return r.text

# 非同期ファイル操作関数
def _data_path(filename: str) -> str:
    if os.path.isabs(filename):
        return filename
    return os.path.join(DATA_DIR, filename)


async def read_json_file_async(filename: str) -> dict:
    """非同期でJSONファイルを読み込み"""
    try:
        async with aiofiles.open(_data_path(filename), 'r') as f:
            content = await f.read()
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

async def write_json_file_async(filename: str, data: dict) -> None:
    """非同期でJSONファイルに書き込み"""
    async with aiofiles.open(_data_path(filename), 'w') as f:
        await f.write(json.dumps(data, indent=4))

from httpx import RequestError, TimeoutException

# HTTPクライアントのクリーンアップはlifespanで処理

def _ipv4_hosts(server: str, info: dict):
    """問い合わせ先。IPv4 だけ使う（.local の同期 DNS でイベントループを止めない）。"""
    hosts = []
    for addr in info.get("addresses") or []:
        if isinstance(addr, str) and addr.count(".") == 3 and addr not in hosts:
            hosts.append(addr)
    if not hosts:
        hosts.append(server.rstrip("."))
    return hosts


async def fetch_server_info(server: str, info: dict, logger) -> tuple:
    """1 台だけ問い合わせる。失敗しても他ホストのタスクには影響しない。"""
    import time
    start_time = time.time()
    headers = {"Accept": "application/json"}
    shortname = server.replace(".local.", "").rstrip(".")
    port = info["port"]
    last_error = None

    for host in _ipv4_hosts(server, info):
        url = f"http://{host}:{port}/v1/info"
        try:
            logger.debug("Fetching %s", url)
            response = await http_client.get(url, headers=headers)
            data = response.json()
            elapsed = time.time() - start_time
            logger.info("✓ %s via %s (%.3fs)", server, host, elapsed)
            return shortname, {
                "success": True,
                "data": data,
                "addresses": info.get("addresses") or [],
            }
        except (RequestError, TimeoutException) as e:
            last_error = e
            logger.debug("✗ %s via %s: %s", server, host, e)
            continue

    elapsed = time.time() - start_time
    logger.warning("✗ %s failed (%.3fs): %s", server, elapsed, last_error)
    return shortname, {
        "success": False,
        "addresses": info.get("addresses") or [],
    }


async def apply_one_result(shortname: str, server_result: dict) -> None:
    """1 台分の結果だけ stat.json にマージする。"""
    async with _stat_lock:
        stat = await read_json_file_async("stat.json")
        if shortname not in stat:
            stat[shortname] = {}
        if server_result["success"]:
            data = server_result["data"]
            stat[shortname] = stat[shortname] | data
            stat[shortname]["address"] = server_result["addresses"]
            stat[shortname]["history"] = stat[shortname].get("history", [])
            stat[shortname]["history"].append(data["load"])
        else:
            stat[shortname]["history"] = stat[shortname].get("history", [])
            stat[shortname]["history"].append(-1)
        if len(stat[shortname]["history"]) > 60:
            stat[shortname]["history"] = stat[shortname]["history"][-60:]
        await write_json_file_async("stat.json", stat)


async def poll_one_loop(server: str) -> None:
    """1 ホスト専用ループ。他ホストの遅延・失敗と独立。"""
    import time
    log = getLogger("uvicorn.error")
    while True:
        started = time.monotonic()
        try:
            servers = await read_json_file_async("servers.json")
            info = servers.get(server)
            if not info:
                return
            shortname, result = await fetch_server_info(server, info, log)
            await apply_one_result(shortname, result)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error("poll %s: %s", server, e)
        await asyncio.sleep(max(0.1, POLL_INTERVAL - (time.monotonic() - started)))


async def fetch_disk_info(server: str, info: dict, logger) -> tuple:
    """diskreporter の /v1/info。失敗しても他ホストには影響しない。"""
    import time
    start_time = time.time()
    headers = {"Accept": "application/json"}
    shortname = server.replace(".local.", "").rstrip(".")
    port = info["port"]
    last_error = None

    for host in _ipv4_hosts(server, info):
        url = f"http://{host}:{port}/v1/info"
        try:
            logger.debug("Fetching disk %s", url)
            response = await disk_http_client.get(url, headers=headers)
            data = response.json()
            elapsed = time.time() - start_time
            logger.info("✓ disk %s via %s (%.3fs)", server, host, elapsed)
            return shortname, {
                "success": True,
                "data": data,
                "addresses": info.get("addresses") or [],
            }
        except (RequestError, TimeoutException) as e:
            last_error = e
            logger.debug("✗ disk %s via %s: %s", server, host, e)
            continue

    elapsed = time.time() - start_time
    logger.warning("✗ disk %s failed (%.3fs): %s", server, elapsed, last_error)
    return shortname, {
        "success": False,
        "addresses": info.get("addresses") or [],
    }


async def apply_one_disk_result(shortname: str, server_result: dict) -> None:
    async with _disk_lock:
        disk = await read_json_file_async("disk.json")
        prev = disk.get(shortname) or {}
        if server_result["success"]:
            data = server_result["data"] or {}
            raid = data.get("raid") or {}
            disk[shortname] = {
                "reachable": True,
                "raid": raid,
                "volumes": data.get("volumes") or [],
                "updated": data.get("updated"),
                "hostname": data.get("hostname") or shortname,
                "address": server_result["addresses"],
            }
        else:
            raid = dict(prev.get("raid") or {})
            disk[shortname] = {
                "reachable": False,
                "raid": raid,
                "volumes": prev.get("volumes") or [],
                "updated": prev.get("updated"),
                "hostname": prev.get("hostname") or shortname,
                "address": server_result["addresses"],
            }
        await write_json_file_async("disk.json", disk)


async def poll_one_disk_loop(server: str) -> None:
    import time
    log = getLogger("uvicorn.error")
    while True:
        started = time.monotonic()
        try:
            servers = await read_json_file_async("disks.json")
            info = servers.get(server)
            if not info:
                return
            shortname, result = await fetch_disk_info(server, info, log)
            await apply_one_disk_result(shortname, result)
            if not result.get("success"):
                await asyncio.sleep(15.0)
                continue
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error("disk poll %s: %s", server, e)
        await asyncio.sleep(max(1.0, DISK_POLL_INTERVAL - (time.monotonic() - started)))


async def supervise_disk_polls() -> None:
    log = getLogger("uvicorn.error")
    while True:
        try:
            servers = await read_json_file_async("disks.json")
            for server in servers:
                task = _disk_poll_tasks.get(server)
                if task is None or task.done():
                    _disk_poll_tasks[server] = asyncio.create_task(poll_one_disk_loop(server))
                    log.info("Started disk poll task for %s", server)
            for server, task in list(_disk_poll_tasks.items()):
                if server not in servers:
                    task.cancel()
                    del _disk_poll_tasks[server]
                    log.info("Stopped disk poll task for %s", server)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error("supervise_disk_polls: %s", e)
        await asyncio.sleep(2.0)


async def supervise_polls() -> None:
    """servers.json に合わせて、ホストごとの独立タスクを増減する。"""
    log = getLogger("uvicorn.error")
    while True:
        try:
            servers = await read_json_file_async("servers.json")
            for server in servers:
                task = _poll_tasks.get(server)
                if task is None or task.done():
                    _poll_tasks[server] = asyncio.create_task(poll_one_loop(server))
                    log.info("Started poll task for %s", server)
            for server, task in list(_poll_tasks.items()):
                if server not in servers:
                    task.cancel()
                    del _poll_tasks[server]
                    log.info("Stopped poll task for %s", server)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error("supervise_polls: %s", e)
        await asyncio.sleep(2.0)


@app.on_event("startup")
async def on_startup():
    """FastAPI 0.85 は lifespan= を無視するので on_event で起動する。"""
    global zeroconf_instance, listener_instance, browser_instance, _supervisor_task
    global disk_listener_instance, disk_browser_instance, _disk_supervisor_task
    log = getLogger("uvicorn.error")
    log.info("Setting up data dir and independent poll tasks...")

    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        os.chdir(DATA_DIR)
    except OSError as e:
        log.warning("chdir %s failed: %s", DATA_DIR, e)

    data_writable = os.access(DATA_DIR, os.W_OK)
    log.info("DATA_DIR=%s writable=%s", DATA_DIR, data_writable)

    if not data_writable:
        log.warning("Data dir %s is not writable; serving UI/API only", DATA_DIR)
        return

    try:
        zeroconf_instance = Zeroconf(interfaces=InterfacesType.All) if InterfacesType else Zeroconf()
    except Exception:
        zeroconf_instance = Zeroconf()
    loop = asyncio.get_running_loop()
    listener_instance = MyListener(json_filename="servers.json")
    listener_instance.set_loop(loop)
    browser_instance = ServiceBrowser(zeroconf_instance, "_loadreporter._tcp.local.", listener_instance)
    disk_listener_instance = MyListener(json_filename="disks.json")
    disk_listener_instance.set_loop(loop)
    disk_browser_instance = ServiceBrowser(zeroconf_instance, "_diskreporter._tcp.local.", disk_listener_instance)
    log.info("Zeroconf service discovery started (loadreporter + diskreporter)")

    _supervisor_task = asyncio.create_task(supervise_polls())
    _disk_supervisor_task = asyncio.create_task(supervise_disk_polls())
    log.info("Independent per-server poll tasks started")


@app.on_event("shutdown")
async def on_shutdown():
    log = getLogger("uvicorn.error")
    log.info("Shutting down services...")
    for task in list(_poll_tasks.values()) + list(_disk_poll_tasks.values()):
        task.cancel()
    _poll_tasks.clear()
    _disk_poll_tasks.clear()
    if _supervisor_task is not None:
        _supervisor_task.cancel()
        try:
            await _supervisor_task
        except asyncio.CancelledError:
            pass
    if _disk_supervisor_task is not None:
        _disk_supervisor_task.cancel()
        try:
            await _disk_supervisor_task
        except asyncio.CancelledError:
            pass
    if disk_browser_instance:
        disk_browser_instance.cancel()
    if browser_instance:
        browser_instance.cancel()
    if zeroconf_instance:
        zeroconf_instance.close()
    await http_client.aclose()
    await disk_http_client.aclose()
    log.info("All services shut down")

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
    """統計情報を非同期で取得"""
    return await read_json_file_async("stat.json")


@api.get("/disk")
async def disk_status():
    """NFS/RAID の低頻度スナップショット。"""
    return await read_json_file_async("disk.json")


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
Environment=PORT=8080

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

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    getLogger().info("Starting loadmeters API at http://%s:%s", host, port)
    # アプリケーションオブジェクトを直接渡すことで、モジュール名に依存しない起動にする
    uvicorn.run(app, host=host, reload=False, port=port)

if __name__ == "__main__":
    main()
