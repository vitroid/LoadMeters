# LoadMeters

ローカルネットワーク向けの負荷監視システムです。

## 必要環境

- Python 3.7 以上
- systemd を使用する Linux（Ubuntu 15.04 以降、CentOS 7 以降など）

## インストール（推奨: /opt venv + systemd 自動設定）

最も簡単な方法は、リポジトリルートで `install.sh` を実行し、/opt 配下に専用の仮想環境と systemd サービスを自動でセットアップする方法です。

```bash
git clone https://github.com/vitroid/LoadMeters.git
cd LoadMeters
sudo bash install.sh
```

このスクリプトは、以下を自動で行います。

1. ソースを `/opt/loadmeters/src` にコピー
2. `/opt/loadmeters/venv` に仮想環境を作成し、その中に LoadMeters と依存パッケージをインストール
3. データ用ディレクトリ `/var/lib/loadmeters` を作成
4. `/etc/systemd/system/loadmeters.service` を作成（`ExecStart=/opt/loadmeters/venv/bin/python -m loadmeters_api.api`）
5. `systemctl daemon-reload` / `enable` / `restart` を実行してサービスを起動

**重要:** Python パッケージはすべて `/opt/loadmeters/venv` の中にインストールされるため、壊れたシステム Python や他のアプリには影響しません。

## インストール（pip + `loadmeters setup`）

専用 venv を作らず、システム Python に直接入れて済ませたい場合は、次の 2 コマンドでパッケージのインストールから systemd の設定・起動まで行えます。

```bash
sudo pip install git+https://github.com/vitroid/LoadMeters.git
sudo loadmeters setup
```

`loadmeters setup` は以下を自動で行います。

1. データ用ディレクトリ `/var/lib/loadmeters` を作成
2. `/etc/systemd/system/loadmeters.service` を作成（`ExecStart=/usr/bin/python3 -m loadmeters_api.api`）
3. `systemctl daemon-reload` / `enable` / `start` を実行してサービスを起動

`loadmeters` コマンドが PATH にない場合は、次でも同じです。

```bash
sudo python3 -m loadmeters_api.api setup
```

**注意:** サービスは `/usr/bin/python3` で動くため、`pip install` も **root（`sudo`）で実行**し、同じ Python にパッケージが入るようにしてください。ユーザー環境だけに入れた場合、サービス起動時に `ModuleNotFoundError` になることがあります（[トラブルシューティング](#トラブルシューティング起動しないとき) 参照）。

## サービスとして稼働させる方法

`install.sh` または `loadmeters setup` を実行すると、自動的に systemd サービスとして常駐するように設定されます。通常は追加の作業は不要です。

以下は、手動で設定する場合の参考情報です。

### 方法 A: 既存の venv を使って systemd を手動設定する

すでに `/opt/loadmeters/venv` と `/opt/loadmeters/src` が作成されている場合、次の内容でサービスファイルを作成できます。

```bash
sudo tee /etc/systemd/system/loadmeters.service >/dev/null <<'EOF'
[Unit]
Description=Load Meters Monitoring Service
After=network.target

[Service]
Type=simple
User=root
Restart=always
RestartSec=1
WorkingDirectory=/var/lib/loadmeters
Environment=PORT=8081
ExecStart=/opt/loadmeters/venv/bin/python -m loadmeters_api.api

[Install]
WantedBy=multi-user.target
EOF

sudo mkdir -p /var/lib/loadmeters
sudo systemctl daemon-reload
sudo systemctl enable loadmeters
sudo systemctl start loadmeters
```

### 方法 B: 手動で systemd を設定する

1. **サービスファイルを配置する**

   ```bash
   sudo cp loadmeters.service /etc/systemd/system/
   ```

2. **データ用ディレクトリを作成する**

   ```bash
   sudo mkdir -p /var/lib/loadmeters
   ```

3. **systemd を再読み込みし、サービスを有効化・起動する**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable loadmeters
   sudo systemctl start loadmeters
   ```

**注意:** 方法 B を使う場合も、**先に** リポジトリルートで `sudo pip3 install -e .` を実行し、`loadmeters_api` がシステムの Python から import できる状態にしておいてください。

---

## トラブルシューティング（起動しないとき）

1. **エラー内容を確認する**

   ```bash
   sudo journalctl -u loadmeters -n 80 --no-pager
   ```

   Python のトレースバックが出ていれば、そのメッセージに従って対応してください。

2. **よくある原因: `ModuleNotFoundError: No module named 'loadmeters_api'`**

   サービスは root で `/usr/bin/python3` を実行するため、**その Python にパッケージが入っていない**と起動しません。リポジトリルートで次を実行してから再度起動してください。

   ```bash
   sudo pip3 install -e .
   sudo systemctl restart loadmeters
   ```

3. **手動で同じコマンドを実行して試す**

   ```bash
   cd /var/lib/loadmeters
   sudo /opt/loadmeters/venv/bin/python -m loadmeters_api.api
   ```

   同じエラーがターミナルに表示されるので、原因の切り分けに使えます。

---

## サービスの操作

| 操作     | コマンド |
|----------|----------|
| 起動     | `sudo systemctl start loadmeters`   |
| 停止     | `sudo systemctl stop loadmeters`    |
| 再起動   | `sudo systemctl restart loadmeters` |
| 状態確認 | `sudo systemctl status loadmeters`  |
| ログ確認 | `sudo journalctl -u loadmeters -f`   |

## 設定

- **ポート**: デフォルトは **8081**。サービス単位では `Environment=PORT=8081` で指定されています。変更する場合は `/etc/systemd/system/loadmeters.service` の `Environment=PORT=...` を編集したあと、`sudo systemctl daemon-reload` と `sudo systemctl restart loadmeters` を実行してください。
- **データディレクトリ**: `/var/lib/loadmeters`（サービスファイルの `WorkingDirectory`）。ここに stat 用の JSON などが配置される想定です。

## 動作確認

サービス起動後、API は次の URL で利用できます。

- 例: `http://<サーバのIP>:8081/stat`

ブラウザや `curl` でアクセスして応答を確認してください。
