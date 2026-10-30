#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""現在ブランチを origin へ push し、リモートをローカル HEAD に一致させる CLI。

`/anvil:create-pr` の Phase 4.1 が使う。

## なぜ script にするか

「リモートに同名ブランチがあるか」「あればローカル HEAD と一致するか」で push の要否と形が決まる。
この分岐は決定論的であり、AI が出力を読み比べると取り違える。

remote-tracking ref はローカルのキャッシュで、fetch しなければ古い可能性がある。そのため
`git ls-remote` でリモートを直接問い合わせる。

## 出力

成功時（終了コード 0）は標準出力に `{"action": "..."}`。

| `action`     | 意味                                                  |
| ------------ | ----------------------------------------------------- |
| `pushed_new` | リモートに無かったので `git push -u origin` した      |
| `pushed`     | リモートがローカル HEAD と異なったので push した      |
| `up_to_date` | リモートがローカル HEAD と一致しており、push していない |

失敗時（終了コード 1）は標準出力に `{"errors": [...]}`。

## 終了コード

| code | 意味                                |
| ---- | ----------------------------------- |
| 0    | リモートがローカル HEAD と一致した  |
| 1    | 一致させられなかった（理由は `errors`） |
| 2    | 引数を受理できない（`argparse`）    |

## 依存

Python 標準ライブラリのみ。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


class PushError(Exception):
    """push できなかった。メッセージは利用者へそのまま示す。"""


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def _stdout(args: list[str]) -> str:
    proc = _run(args)
    if proc.returncode != 0:
        raise PushError(f"{' '.join(args)} が失敗しました: {proc.stderr.strip()}")
    return proc.stdout


def remote_sha(branch: str) -> str | None:
    out = _stdout(["git", "ls-remote", "--heads", "origin", branch]).strip()
    if not out:
        return None
    return out.splitlines()[0].split()[0]


def push(branch: str) -> dict:
    remote = remote_sha(branch)
    if remote is None:
        _stdout(["git", "push", "-u", "origin", branch])
        return {"action": "pushed_new"}
    head = _stdout(["git", "rev-parse", "HEAD"]).strip()
    if remote == head:
        return {"action": "up_to_date"}
    _stdout(["git", "push", "origin", branch])
    return {"action": "pushed"}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="現在ブランチを origin へ push する")
    parser.add_argument(
        "--branch", required=True, help="push するブランチ（現在ブランチ）"
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        result = push(args.branch)
    except PushError as e:
        print(json.dumps({"errors": [str(e)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
