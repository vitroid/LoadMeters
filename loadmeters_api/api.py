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
    def __init__(self, loop=None):
        self._update_lock = asyncio.Lock()
        self._pending_updates = {}
        self._update_task = None
        self._loop = loop

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
            getLogger("uvicorn.app").warning("Event loop not available, skipping server update")

    async def _flush_updates(self):
        """ペンディング中の更新をファイルに書き込み"""
        await asyncio.sleep(1.0)  # 1秒待ってバッチ処理
        
        if not self._pending_updates:
            return
            
        try:
            # 現在のデータを読み込み
            data = await read_json_file_async("servers.json")
            
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
            await write_json_file_async("servers.json", data)
            
            # ペンディング更新をクリア
            n = len(self._pending_updates)
            self._pending_updates.clear()
            getLogger("uvicorn.app").info(f"Updated servers.json with {n} servers")
            
        except Exception as e:
            getLogger("uvicorn.app").error(f"Error updating servers.json: {e}")

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
            getLogger("uvicorn.app").debug(f"Zeroconf update_service: {name} get_service_info=None, will retry")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        # サービス削除時の処理（必要に応じて実装）
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """mDNS でサービス発見時に呼ばれる。get_service_info は解決直後は None になりうるため遅延再取得する"""
        log = getLogger("uvicorn.app")
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    global zeroconf_instance, listener_instance, browser_instance
    
    # 起動時の処理
    getLogger("uvicorn.app").info("Setting up Zeroconf service discovery...")
    
    # データディレクトリの確認
    data_dir = "/var/lib/loadmeters"
    os.makedirs(data_dir, exist_ok=True)
    os.chdir(data_dir)
    
    # Zeroconfの設定（interfaces=All で全IFを監視し、同一ホストの loadreporter も検出しやすくする）
    try:
        zeroconf_instance = Zeroconf(interfaces=InterfacesType.All) if InterfacesType else Zeroconf()
    except Exception:
        zeroconf_instance = Zeroconf()
    listener_instance = MyListener()
    
    # イベントループを設定
    loop = asyncio.get_running_loop()
    listener_instance.set_loop(loop)
    
    browser_instance = ServiceBrowser(zeroconf_instance, "_loadreporter._tcp.local.", listener_instance)
    getLogger("uvicorn.app").info("Zeroconf service discovery started")
    
    # 定期的なupdate_history実行を開始
    async def periodic_update():
        while True:
            try:
                await update_history()
                await asyncio.sleep(5)  # 5秒間隔
            except Exception as e:
                getLogger("uvicorn.app").error(f"Error in periodic update: {e}")
                await asyncio.sleep(5)
    
    update_task = asyncio.create_task(periodic_update())
    getLogger("uvicorn.app").info("Periodic update task started")
    
    yield
    
    # 終了時の処理
    getLogger("uvicorn.app").info("Shutting down services...")
    update_task.cancel()
    try:
        await update_task
    except asyncio.CancelledError:
        pass
    
    if browser_instance:
        browser_instance.cancel()
    if zeroconf_instance:
        zeroconf_instance.close()
    
    # HTTPクライアントのクリーンアップ
    await http_client.aclose()
    getLogger("uvicorn.app").info("All services shut down")

app = FastAPI(lifespan=lifespan)
api = FastAPI(root_path=f"/v{__api_version__}")
app.mount(f"/v{__api_version__}", api)

# Svelte? UIもこいつがserveする。
static_dir = "/var/lib/loadmeters/public"
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    getLogger("uvicorn.app").warning(f"Static directory {static_dir} does not exist")


# グローバル非同期HTTPクライアント
http_client = httpx.AsyncClient(timeout=5.0)

async def call_api(url: str, **kwargs) -> str:
    """非同期HTTPリクエスト"""
    r = await http_client.get(url, **kwargs)
    return r.text

# 非同期ファイル操作関数
async def read_json_file_async(filename: str) -> dict:
    """非同期でJSONファイルを読み込み"""
    try:
        async with aiofiles.open(filename, 'r') as f:
            content = await f.read()
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

async def write_json_file_async(filename: str, data: dict) -> None:
    """非同期でJSONファイルに書き込み"""
    async with aiofiles.open(filename, 'w') as f:
        await f.write(json.dumps(data, indent=4))

from httpx import RequestError, TimeoutException

# HTTPクライアントのクリーンアップはlifespanで処理

async def fetch_server_info(server: str, info: dict, logger) -> tuple[str, dict]:
    """個別サーバーから情報を非同期で取得"""
    import time
    start_time = time.time()
    
    headers = {"Accept": "application/json"}
    shortname = server.replace(".local.", "")
    port = info["port"]
    url = f'http://{server}:{port}/v1/info'
    
    try:
        logger.debug(f"Fetching {url}")
        response = await http_client.get(url, headers=headers)
        elapsed = time.time() - start_time
        logger.debug(f"Status {response.status_code} from {server} ({elapsed:.3f}s)")
        
        data = response.json()
        logger.info(f"✓ {server} ({elapsed:.3f}s)")
        
        return shortname, {
            "success": True,
            "data": data,
            "addresses": info["addresses"]
        }
    except (RequestError, TimeoutException) as e:
        elapsed = time.time() - start_time
        logger.warning(f"✗ {server} failed ({elapsed:.3f}s): {e}")
        return shortname, {
            "success": False,
            "addresses": info["addresses"]
        }

# update_history関数は後でlifespanから呼び出される
async def update_history() -> None:
    import time
    cycle_start = time.time()
    logger = getLogger("uvicorn.app")
    
    # 非同期でファイル読み込み
    io_start = time.time()
    servers = await read_json_file_async("servers.json")
    stat = await read_json_file_async("stat.json")
    io_time = time.time() - io_start
    
    logger.info(f"📊 Update cycle: {len(servers)} servers, file I/O: {io_time:.3f}s")
    logger.debug(f"Current servers: {list(servers.keys())}")

    # 全サーバーに対して並列でHTTPリクエストを実行
    if servers:
        fetch_start = time.time()
        tasks = [fetch_server_info(server, info, logger) for server, info in servers.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        fetch_time = time.time() - fetch_start
        
        # 結果を処理
        successful_fetches = 0
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in fetch_server_info: {result}")
                continue
                
            shortname, server_result = result
            
            if shortname not in stat:
                stat[shortname] = dict()
            
            if server_result["success"]:
                successful_fetches += 1
                data = server_result["data"]
                stat[shortname] = stat[shortname] | data
                stat[shortname]["address"] = server_result["addresses"]
                stat[shortname]["history"] = stat[shortname].get("history", [])
                stat[shortname]["history"].append(data["load"])
            else:
                stat[shortname]["history"] = stat[shortname].get("history", [])
                stat[shortname]["history"].append(-1)
            
            # 履歴を60件に制限
            if "history" in stat[shortname] and len(stat[shortname]["history"]) > 60:
                stat[shortname]["history"] = stat[shortname]["history"][-60:]
        
        logger.info(f"📡 Parallel fetch: {successful_fetches}/{len(servers)} success ({fetch_time:.3f}s)")
    
    # 非同期でファイル書き込み
    write_start = time.time()
    await write_json_file_async("stat.json", stat)
    write_time = time.time() - write_start
    
    total_time = time.time() - cycle_start
    logger.info(f"💾 Cycle complete: {total_time:.3f}s total (I/O: {io_time:.3f}s + {write_time:.3f}s)")


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
    """統計情報を非同期で取得"""
    return await read_json_file_async("stat.json")


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

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8081"))
    getLogger().info("Starting loadmeters API at http://%s:%s", host, port)
    # アプリケーションオブジェクトを直接渡すことで、モジュール名に依存しない起動にする
    uvicorn.run(app, host=host, reload=False, port=port)

if __name__ == "__main__":
    main()
