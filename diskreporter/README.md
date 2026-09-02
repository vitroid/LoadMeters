# DiskReporter

NFS サーバ上で RAID 死活・容量・ユーザー占有を HTTP で返す、依存の少ないデーモンです。
LoadMeters が mDNS (`_diskreporter._tcp`) で発見し、`GET /v1/info` を低頻度で集めます。

Python **2.6 以降**（CentOS 6 の標準 Python を含む）と 3.x。pip パッケージは不要です（標準ライブラリのみ）。

## 報告する内容

`GET /v1/info`（例: `http://localhost:8087/v1/info`）

1. **RAID 死活** — 設定の `raid`（`arcconf` / `mdadm` / `none`）。`ok` が false なら異常。
2. **容量と使用量** — `volumes[].path` の `statvfs`（バイト）。
3. **ユーザー占有** — `users: true` のボリュームで、直下ディレクトリごとに `du`（低頻度）。

時系列は持ちません。応答はキャッシュです。

## 設定

`/etc/diskreporter.json`（例は `diskreporter.json.example`）

```json
{
  "port": 8087,
  "raid": "arcconf",
  "raid_scan_seconds": 300,
  "user_scan_seconds": 3600,
  "volumes": [
    { "path": "/export/home", "label": "home", "users": true }
  ]
}
```

- `arcconf`: `/usr/StorMan/arcconf getconfig 1 LD`（`ARCCONF` でパス変更可）
- `mdadm`: `/proc/mdstat`
- `none`: RAID なし（容量のみ）

## インストール

NFS サーバ上で:

```bash
git clone https://github.com/vitroid/diskreporter.git
cd diskreporter
sudo make install
```

- ソースは `/opt/diskreporter`
- 起動スクリプトは `python` を自動検出（2.6 でも可）
- systemd があれば unit、なければ SysV `init.d`（CentOS 6）
- Avahi があれば `_diskreporter._tcp` ポート 8087 を広告

手動起動:

```bash
export PYTHONPATH=/opt/diskreporter
python -m diskreporter.server
```

## API

- `GET /v1/info` — JSON スナップショット
