import os
import subprocess
import sys
from setuptools import setup, find_packages
from setuptools.command.install import install

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
ExecStart=/usr/bin/python3 -m uvicorn loadmeters_api.api:app --host 0.0.0.0 --port 8081
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

class PostInstallCommand(install):
    def run(self):
        install.run(self)
        setup_service()

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
            'loadmeters=loadmeters_api.api:main',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="Load monitoring system for local network",
    python_requires=">=3.7",
    cmdclass={
        'install': PostInstallCommand,
    },
)

# 直接実行された場合の処理は不要 