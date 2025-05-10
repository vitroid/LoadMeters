import os
import subprocess
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info

class PostInstallCommand(install):
    def run(self):
        install.run(self)
        
        # systemdサービスファイルの作成
        service_content = """[Unit]
Description=Load Meters Monitoring Service
After=network.target

[Service]
Type=simple
User=root
Restart=always
RestartSec=1
ExecStart=/usr/local/bin/loadmeters
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

class PostDevelopCommand(develop):
    def run(self):
        develop.run(self)
        self._setup_service()

class PostEggInfoCommand(egg_info):
    def run(self):
        egg_info.run(self)
        self._setup_service()

    def _setup_service(self):
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

def uninstall_service():
    try:
        subprocess.run(["systemctl", "stop", "loadmeters"])
        subprocess.run(["systemctl", "disable", "loadmeters"])
        os.remove("/etc/systemd/system/loadmeters.service")
        subprocess.run(["systemctl", "daemon-reload"])
    except:
        pass

setup(
    name="loadmeters",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "requests",
        "http3",
        "zeroconf",
        "fastapi-utilities",
    ],
    entry_points={
        'console_scripts': [
            'loadmeters=API.api:main',
        ],
    },
    cmdclass={
        'install': PostInstallCommand,
        'develop': PostDevelopCommand,
        'egg_info': PostEggInfoCommand,
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="Load monitoring system for local network",
    python_requires=">=3.7",
)

# アンインストール時の処理
import atexit
atexit.register(uninstall_service) 