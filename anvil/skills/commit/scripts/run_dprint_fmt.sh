#!/usr/bin/env bash
# commit 前に dprint fmt を実行する共有スクリプト。
# dprint.jsonc/dprint.json が存在し dprint コマンドが利用可能な場合のみ実行する。

set -euo pipefail

if [ -f dprint.jsonc ] || [ -f dprint.json ]; then
  if command -v dprint >/dev/null 2>&1; then
    dprint fmt
  else
    echo "warning: dprint 設定ファイルがあるが dprint コマンドが見つかりません。format スキップ" >&2
  fi
fi
