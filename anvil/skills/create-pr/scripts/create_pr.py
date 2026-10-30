#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本文ファイルから draft PR を作成する CLI。

`/anvil:create-pr` の Phase 4.2 が使う。本文ファイルは AI が `Write` ツールで書いたものを受け取る。

## なぜ script にするか

`gh pr create` の呼び出しと、成功時の本文ファイルの削除は決定論的である。script にすれば、SKILL の
`allowed-tools` でこの script の呼び出しだけを事前承認できる。

## PR のリポジトリ

PR が作られたリポジトリは、`gh pr create` が出力する PR の URL から取り出して返す。`origin` から
推定しない。fork では `gh` が PR を upstream に作ることがあり、`origin` から推定すると、CI の状態を
別のリポジトリへ問い合わせてしまうためである。

## 本文ファイルの扱い

- 成功: 本文ファイルを削除する
- 失敗: 本文ファイルを残す（再試行でそのまま使う）

## 出力

成功時（終了コード 0）は標準出力に `{"url": "...", "number": N, "repo": "HOST/OWNER/REPO"}`。
`repo` は `gh --repo` にそのまま渡せる形で、ホストは `github.com` でも省かない（`gh` はホストの無い
`OWNER/REPO` を既定ホスト（`GH_HOST` 等）で解釈し、PR とは別のホストへ問い合わせうるため）。
失敗時（終了コード 1）は標準出力に `{"errors": [...]}`。

## 終了コード

| code | 意味                                |
| ---- | ----------------------------------- |
| 0    | PR を作成した                       |
| 1    | 作成できなかった（理由は `errors`） |
| 2    | 引数を受理できない（`argparse`）    |

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

_PR_URL = re.compile(
    r"https?://(?P<host>[^/\s]+)/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)/pull/(?P<number>\d+)"
)


class CreateError(Exception):
    """作成できなかった。メッセージは利用者へそのまま示す。"""


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def parse_pr_url(text: str) -> dict | None:
    m = _PR_URL.search(text)
    if not m:
        return None
    repo = f"{m.group('host')}/{m.group('owner')}/{m.group('repo')}"
    return {"url": m.group(0), "number": int(m.group("number")), "repo": repo}


def create(base: str, title: str, body_file: str) -> dict:
    path = Path(body_file)
    if not path.is_file():
        raise CreateError(f"本文ファイルがありません: {body_file}")
    proc = _run(
        [
            "gh",
            "pr",
            "create",
            "--draft",
            "--base",
            base,
            "--title",
            title,
            "--body-file",
            str(path),
        ]
    )
    if proc.returncode != 0:
        raise CreateError(f"gh pr create が失敗しました: {proc.stderr.strip()}")
    result = parse_pr_url(proc.stdout)
    if result is None:
        raise CreateError(
            f"gh pr create の出力から PR の URL を読み取れません: {proc.stdout.strip()}"
        )
    path.unlink()
    return result


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="本文ファイルから draft PR を作成する")
    parser.add_argument("--base", required=True, help="ベースブランチ")
    parser.add_argument("--title", required=True, help="PR タイトル")
    parser.add_argument("--body-file", required=True, help="本文ファイルのパス")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        result = create(args.base, args.title, args.body_file)
    except CreateError as e:
        print(json.dumps({"errors": [str(e)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
