#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本文ファイルから GitHub Issue を作成する CLI。

`/anvil:create-issue` の Phase 4.3 が使う。本文ファイルは AI が `Write` ツールで書いたものを受け取る。

## なぜ script にするか

`gh issue create` の呼び出しと、成功時の本文ファイルの削除は決定論的である。script にすれば、SKILL の
`allowed-tools` でこの script の呼び出しだけを事前承認できる。

## 本文ファイルの扱い

- 成功: 本文ファイルを削除する
- 失敗: 本文ファイルを残す（再試行でそのまま使う）

## 出力

成功時（終了コード 0）は標準出力に `{"url": "...", "number": N}`。
失敗時（終了コード 1）は標準出力に `{"errors": [...]}`。

## 終了コード

| code | 意味                             |
| ---- | -------------------------------- |
| 0    | Issue を作成した                 |
| 1    | 作成できなかった（理由は `errors`）|
| 2    | 引数を受理できない（`argparse`） |

## 依存

Python 標準ライブラリのみ。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_ISSUE_URL = re.compile(r"https?://\S+/issues/(\d+)")


class CreateError(Exception):
    """作成できなかった。メッセージは利用者へそのまま示す。"""


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def create(repo: str, title: str, body_file: str, label: str | None) -> dict:
    path = Path(body_file)
    if not path.is_file():
        raise CreateError(f"本文ファイルがありません: {body_file}")
    args = [
        "gh",
        "issue",
        "create",
        "--repo",
        repo,
        "--title",
        title,
        "--body-file",
        str(path),
    ]
    if label:
        args += ["--label", label]
    proc = _run(args)
    if proc.returncode != 0:
        raise CreateError(f"gh issue create が失敗しました: {proc.stderr.strip()}")
    m = _ISSUE_URL.search(proc.stdout)
    if not m:
        raise CreateError(
            f"gh issue create の出力から Issue の URL を読み取れません: {proc.stdout.strip()}"
        )
    path.unlink()
    return {"url": m.group(0), "number": int(m.group(1))}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="本文ファイルから GitHub Issue を作成する"
    )
    parser.add_argument("--repo", required=True, help="起票先（[HOST/]OWNER/REPO）")
    parser.add_argument("--title", required=True, help="Issue タイトル")
    parser.add_argument("--body-file", required=True, help="本文ファイルのパス")
    parser.add_argument("--label", help="付けるラベル（省略時はラベルなし）")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        result = create(args.repo, args.title, args.body_file, args.label)
    except CreateError as e:
        print(json.dumps({"errors": [str(e)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
