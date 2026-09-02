#!/usr/bin/env bash
set -euo pipefail

APP_NAME="loadmeters"
APP_ROOT="/opt/${APP_NAME}"
SRC_DIR="${APP_ROOT}/src"
VENV_DIR="${APP_ROOT}/venv"
DATA_DIR="/var/lib/${APP_NAME}"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "このスクリプトは root で実行してください（例: sudo bash install.sh）。" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 が見つかりません。python3 をインストールしてください。" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync が見つかりません。sudo apt install rsync などでインストールしてください。" >&2
  exit 1
fi

echo "LoadMeters を /opt 配下にインストールします。"
echo "ソースディレクトリ: ${PWD}"
echo "アプリケーションルート: ${APP_ROOT}"
echo

mkdir -p "${SRC_DIR}" "${VENV_DIR}" "${DATA_DIR}"

echo "ソースコードを ${SRC_DIR} に同期しています..."
rsync -a --delete --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' ./ "${SRC_DIR}/"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "仮想環境を作成しています: ${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"
fi

echo "Svelte UI をビルドしています..."
if command -v npm >/dev/null 2>&1 && [[ -f "${SRC_DIR}/loadmeters/package.json" ]]; then
  (cd "${SRC_DIR}/loadmeters" && npm install && npm run build)
fi
mkdir -p "${SRC_DIR}/loadmeters_api/public" "${DATA_DIR}/public"
if [[ -f "${SRC_DIR}/loadmeters/public/index.html" ]]; then
  rsync -a "${SRC_DIR}/loadmeters/public/" "${SRC_DIR}/loadmeters_api/public/"
  rsync -a "${SRC_DIR}/loadmeters/public/" "${DATA_DIR}/public/"
fi

echo "仮想環境にパッケージをインストールしています..."
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install "${SRC_DIR}"

echo "systemd サービスファイルを作成しています: ${SERVICE_FILE}"
cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Load Meters Monitoring Service
After=network.target

[Service]
Type=simple
User=root
Restart=always
RestartSec=1
WorkingDirectory=${DATA_DIR}
Environment=PORT=8080
ExecStart=${VENV_DIR}/bin/python -m loadmeters_api.api

[Install]
WantedBy=multi-user.target
EOF

echo "systemd を再読み込みし、サービスを有効化・起動します..."
systemctl daemon-reload
systemctl enable "${APP_NAME}"
systemctl restart "${APP_NAME}"

echo
echo "インストールが完了しました。サービスの状態:"
systemctl status "${APP_NAME}" --no-pager -l || true
echo
echo "ログの確認: sudo journalctl -u ${APP_NAME} -f"

