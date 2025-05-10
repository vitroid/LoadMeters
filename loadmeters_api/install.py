import os
import subprocess
from poetry.plugins import ApplicationPlugin
from poetry.console import Application

class InstallPlugin(ApplicationPlugin):
    def activate(self, application: Application):
        application.event_handlers.append(self._post_install)

    def _post_install(self, event, *args, **kwargs):
        if event.name != "post_install":
            return

        # systemdサービスファイルの作成
        service_content = """[Unit]
Description=Load Meters Monitoring Service
After=network.target

[Service]
Type=simple
User=root
Restart=always
RestartSec=1
Environment=POETRY_HOME=/opt/poetry
Environment=PATH=/opt/poetry/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/poetry/bin/poetry run loadmeters
WorkingDirectory=/var/lib/loadmeters
Environment=PORT=8081

[Install]
WantedBy=multi-user.target
"""
        
        # サービスファイルを書き込み
        service_path = "/etc/systemd/system/loadmeters.service"
        with open(service_path, "w") as f:
            f.write(service_content)
        
        # データディレクトリの作成
        os.makedirs("/var/lib/loadmeters", exist_ok=True)
        
        # systemdの再読み込みとサービスの有効化
        subprocess.run(["systemctl", "daemon-reload"])
        subprocess.run(["systemctl", "enable", "loadmeters"])
        subprocess.run(["systemctl", "start", "loadmeters"]) 