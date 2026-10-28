#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`/anvil:commit` の git 操作をまとめた CLI。

## なぜ script にするか

ステージの状態の検査・ステージ・ブランチの判定・commit・push は決定論的である。AI が手順ごとに
コマンドを組み立てると、コマンドの形が毎回変わり、許可ルールで事前承認できない。1 本の script の
サブコマンドにまとめれば、SKILL の `allowed-tools` でこの script の呼び出しだけを事前承認できる。

## サブコマンド

| サブコマンド | 行うこと                                                                        |
| ------------ | ------------------------------------------------------------------------------- |
| `prepare`    | 変更の状態・ステージ済みの差分・ブランチの判定を返し、メッセージの置き場を作る |
| `stage`      | `git add -u`（`--tracked`）と、指定パスの `git add`（`--path`）。状態を返す     |
| `new-branch` | `git checkout -b <name>`                                                        |
| `commit`     | メッセージファイルで `git commit -F`。成功したらメッセージファイルを削除する   |
| `push`       | 追跡設定があれば `git push`、無ければ `git push -u origin <branch>`             |

## 出力

成功時（終了コード 0）は標準出力に単一 JSON。失敗時（終了コード 1）は `{"errors": [...]}`。

`prepare` / `stage` の出力:

```json
{
  "tracked_paths": [], "staged_paths": [], "unstaged_paths": [],
  "untracked_paths": [], "stale_staged_paths": [],
  "staged_diff": "diff --git ...",
  "branch": "feature/x",
  "protected_branch": "main",
  "is_protected": false
}
```

- 状態の 5 項目は `inspect_stage_state.py` と同じ判定である
- `staged_diff`: `git diff --cached`（commit される内容）
- `branch`: 現在ブランチ。detached HEAD なら `null`
- `protected_branch`: `develop` → `main` → `master` の順で、ローカルか origin に最初に存在するもの。
  無ければ `null`
- `is_protected`: `branch` が `protected_branch` と一致するか

`commit` の出力は `{"sha": "...", "summary": "..."}`。`push` の出力は `{"action": "push" | "push_set_upstream"}`。

## 終了コード

| code | 意味                                |
| ---- | ----------------------------------- |
| 0    | 操作が完了した                      |
| 1    | 完了しなかった（理由は `errors`）   |
| 2    | 引数を受理できない（`argparse`）    |

## 依存

Python 標準ライブラリのみ。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import inspect_stage_state  # noqa: E402

PROTECTED_CANDIDATES = ("develop", "main", "master")


class OpsError(Exception):
    """操作が完了しなかった。メッセージは利用者へそのまま示す。"""


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def _stdout(args: list[str]) -> str:
    proc = _run(args)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise OpsError(f"{' '.join(args)} が失敗しました: {detail}")
    return proc.stdout


def _branch_exists(name: str) -> bool:
    for ref in (f"refs/heads/{name}", f"refs/remotes/origin/{name}"):
        if _run(["git", "show-ref", "--verify", "--quiet", ref]).returncode == 0:
            return True
    return False


def branch_info() -> dict:
    branch = _stdout(["git", "branch", "--show-current"]).strip() or None
    protected = next((name for name in PROTECTED_CANDIDATES if _branch_exists(name)), None)
    return {
        "branch": branch,
        "protected_branch": protected,
        "is_protected": branch is not None and branch == protected,
    }


def state() -> dict:
    result = inspect_stage_state.inspect(_stdout(["git", "status", "--porcelain", "-z"]))
    result["staged_diff"] = _stdout(["git", "diff", "--cached"])
    result.update(branch_info())
    return result


def prepare(message_file: str) -> dict:
    result = state()
    Path(message_file).parent.mkdir(parents=True, exist_ok=True)
    result["message_file"] = message_file
    return result


def stage(tracked: bool, paths: list[str]) -> dict:
    if not tracked and not paths:
        raise OpsError("ステージする対象がありません（--tracked か --path を指定してください）")
    if tracked:
        _stdout(["git", "add", "-u"])
    if paths:
        _stdout(["git", "add", "--", *paths])
    return state()


def new_branch(name: str) -> dict:
    _stdout(["git", "checkout", "-b", name])
    return {"branch": name}


def commit(message_file: str) -> dict:
    path = Path(message_file)
    if not path.is_file():
        raise OpsError(f"メッセージファイルがありません: {message_file}")
    _stdout(["git", "commit", "-F", str(path)])
    path.unlink()
    return {
        "sha": _stdout(["git", "rev-parse", "HEAD"]).strip(),
        "summary": _stdout(["git", "log", "-1", "--format=%s"]).strip(),
    }


def push(branch: str) -> dict:
    has_upstream = _run(["git", "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"]).returncode == 0
    if has_upstream:
        _stdout(["git", "push"])
        return {"action": "push"}
    _stdout(["git", "push", "-u", "origin", branch])
    return {"action": "push_set_upstream"}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="/anvil:commit の git 操作")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare", help="状態・差分・ブランチ判定を返し、メッセージの置き場を作る")
    p.add_argument("--message-file", required=True)
    p = sub.add_parser("stage", help="git add -u / git add -- <path>")
    p.add_argument("--tracked", action="store_true", help="追跡済みファイルを全てステージする（git add -u）")
    p.add_argument("--path", action="append", default=[], help="ステージする未追跡ファイル（複数可）")
    p = sub.add_parser("new-branch", help="git checkout -b")
    p.add_argument("--name", required=True)
    p = sub.add_parser("commit", help="git commit -F")
    p.add_argument("--message-file", required=True)
    p = sub.add_parser("push", help="git push")
    p.add_argument("--branch", required=True)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.message_file)
        elif args.command == "stage":
            result = stage(args.tracked, args.path)
        elif args.command == "new-branch":
            result = new_branch(args.name)
        elif args.command == "commit":
            result = commit(args.message_file)
        else:
            result = push(args.branch)
    except OpsError as e:
        print(json.dumps({"errors": [str(e)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
