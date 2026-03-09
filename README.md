# LoadMeters

ローカルネットワーク向けの負荷監視システムです。

## 必要環境

- Python 3.7 以上
- systemd を使用する Linux（Ubuntu 15.04 以降、CentOS 7 以降など）

## インストール

**サービスとして動かす場合**は、systemd が使うのは **システムの `/usr/bin/python3`** なので、**root でインストール**してください。そうしないとサービス起動時に `ModuleNotFoundError: No module named 'loadmeters_api'` で落ちます。

```bash
# サービスで使う場合（推奨）
sudo pip3 install -e .
# または
sudo python3 -m pip install -e .

# 手元でだけ動かす場合
pip install -e .
```

## サービスとして稼働させる方法

API を systemd サービスとして常時稼働させる手順です。**root 権限が必要です。** 上記のとおり、先に **sudo pip3 install -e .** でインストールしておいてください。

### 方法 A: setup コマンドで一括設定（推奨）

パッケージをインストールしたあと、次のコマンドでサービス登録・起動まで行います。

```bash
sudo python3 setup.py setup
```

このコマンドで以下が行われます。

1. `/etc/systemd/system/loadmeters.service` にサービスファイルを作成
2. データ用ディレクトリ `/var/lib/loadmeters` を作成
3. `systemctl daemon-reload`
4. サービスを有効化（`systemctl enable loadmeters`）
5. サービスを起動（`systemctl start loadmeters`）

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
   sudo /usr/bin/python3 -m uvicorn loadmeters_api.api:app --host 0.0.0.0 --port 8081
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
