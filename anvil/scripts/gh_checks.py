# -*- coding: utf-8 -*-
"""複数の skill の script が共有する、gh CLI と git リポジトリの事前確認。

`skills/create-issue/scripts/preflight.py` と `skills/create-pr/scripts/preflight.py` が import する。
単独では実行しない。

確認に失敗したら `CheckError` を投げる。メッセージは利用者へそのまま示せる文にする。

## 依存

Python 標準ライブラリのみ。
"""

from __future__ import annotations

import shutil
import subprocess


class CheckError(Exception):
    """事前確認に失敗した。メッセージは利用者へそのまま示す。"""


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def check_gh(runner=run) -> None:
    """gh CLI が入っていて、認証済みであることを確かめる。"""
    if shutil.which("gh") is None:
        raise CheckError("gh CLI が必要です。インストール: https://cli.github.com/")
    if runner(["gh", "auth", "status"]).returncode != 0:
        raise CheckError("gh CLI が認証されていません。実行してください: gh auth login")


def check_git_repo(runner=run) -> str:
    """git リポジトリであることを確かめ、origin の URL を返す。"""
    if runner(["git", "rev-parse", "--is-inside-work-tree"]).returncode != 0:
        raise CheckError("git リポジトリではありません。対象のリポジトリへ移動してから再実行してください")
    proc = runner(["git", "remote", "get-url", "origin"])
    if proc.returncode != 0:
        raise CheckError("リモート origin が設定されていません。実行してください: git remote add origin <url>")
    return proc.stdout
