#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "DiskReporter インストール"
make install
echo "curl http://localhost:8087/v1/info"
