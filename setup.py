import os
import subprocess
from setuptools import setup, find_packages
from setuptools.command.install import install

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
ExecStart=/usr/bin/python3 -m loadmeters_api.api
WorkingDirectory=/var/lib/loadmeters
Environment=PORT=8081

[Install]
WantedBy=multi-user.target
"""
        
        try:
            # サービスファイルを書き込み
            service_path = "/etc/systemd/system/loadmeters.service"
            with open(service_path, "w") as f:
                f.write(service_content)
            print(f"Created service file at {service_path}")
            
            # データディレクトリの作成
            os.makedirs("/var/lib/loadmeters", exist_ok=True)
            print("Created data directory at /var/lib/loadmeters")
            
            # systemdの再読み込みとサービスの有効化
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            print("Reloaded systemd")
            subprocess.run(["systemctl", "enable", "loadmeters"], check=True)
            print("Enabled loadmeters service")
            subprocess.run(["systemctl", "start", "loadmeters"], check=True)
            print("Started loadmeters service")
        except Exception as e:
            print(f"Error during service setup: {e}")
            raise

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
            'loadmeters=loadmeters_api.api:main',
        ],
    },
    cmdclass={
        'install': PostInstallCommand,
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="Load monitoring system for local network",
    python_requires=">=3.7",
)

# アンインストール時の処理
import atexit
atexit.register(uninstall_service) 