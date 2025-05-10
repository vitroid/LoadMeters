# Install

* Install npm https://www.digitalocean.com/community/tutorials/how-to-install-node-js-on-ubuntu-20-04

# LoadMetersサーバの起動方法
## ソースを展開する。
git clone --branch svelte https://github.com/vitroid/LoadMeters.git

## API (backend)
```shell
cd API
pipenv shell
python api.py
```
## UI server (frontend)
```shell
cd loadmeters
npm run dev
```

# Agent (loadreporter)のインストール
各クライアントで

```shell
su
cd /tmp
git clone https://github.com/vitroid/loadreporter.git
cd loadreporter
make install
```