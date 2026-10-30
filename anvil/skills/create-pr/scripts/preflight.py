#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PR を作成する前の環境確認と、PR 本文の材料の収集をまとめて行う CLI。

`/anvil:create-pr` の Phase 1〜3 が使う。

## なぜ script にするか

確認（gh の有無・認証・git リポジトリか・現在ブランチ・ベースブランチ・コミットの有無）と材料の収集
（コミット一覧・変更ファイル統計・PR テンプレート・CI 設定の有無）は決定論的である。AI が手順ごとに
コマンドを組み立てると、コマンドの形が毎回変わり、許可ルールで事前承認できない。

## ベースブランチの決定

`--base` があればそれ。無ければ `develop` → `main` → `master` の順で、ローカルか `origin` に存在する
最初のものを採る。ローカルに無く `origin` にだけあるときは `origin/<base>` と比較する。

## 出力

成功時（終了コード 0）は標準出力に単一 JSON。

```json
{
  "branch": "feature/foo",
  "is_protected_branch": false,
  "base": "main",
  "base_ref": "main",
  "commits": [{"sha": "...", "subject": "...", "body": "..."}],
  "diffstat": " a.py | 2 +-\\n 1 file changed, ...",
  "template": "/repo/.github/PULL_REQUEST_TEMPLATE.md",
  "has_ci": true,
  "body_file": "/repo/.temp/anvil/create-pr/pr_body_<session>.md"
}
```

- `is_protected_branch`: 現在ブランチが `develop` / `main` / `master` のいずれか
- `template`: PR テンプレートの絶対パス。無ければ `null`
- `has_ci`: `.github/workflows/` に `*.yml` / `*.yaml` があるか。workflow が定義されているかまでしか
  分からない（トリガー条件が合わなければチェックは登録されない）
- `body_file`: 引数で受けたパスそのもの。親ディレクトリは作成済みである

失敗時（終了コード 1）は標準出力に `{"errors": [...]}`。最初に失敗した確認で止まる。

## 終了コード

| code | 意味                              |
| ---- | --------------------------------- |
| 0    | 確認が完了し、PR を作成できる     |
| 1    | 確認に失敗した（理由は `errors`） |
| 2    | 引数を受理できない（`argparse`）  |

## 依存

Python 標準ライブラリのみ。
"""

from __future__ import annotations

import argparse
import json
import shutil  # noqa: F401  テストが shutil.which を差し替えるために参照する
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parents[2] / "scripts"))

import gh_checks  # noqa: E402  プラグイン直下 scripts/ の共有部品

PreflightError = gh_checks.CheckError

BASE_CANDIDATES = ("develop", "main", "master")
PROTECTED_BRANCHES = frozenset(BASE_CANDIDATES)

_FIELD = "\x1f"
_RECORD = "\x1e"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def _ok(args: list[str]) -> bool:
    return _run(args).returncode == 0


def _stdout(args: list[str], what: str) -> str:
    proc = _run(args)
    if proc.returncode != 0:
        raise PreflightError(f"{what}を取得できません: {proc.stderr.strip()}")
    return proc.stdout


def current_branch() -> str:
    branch = _stdout(["git", "branch", "--show-current"], "現在ブランチ").strip()
    if not branch:
        raise PreflightError(
            "detached HEAD です。PR を作成するブランチへ切り替えてから再実行してください"
        )
    return branch


def _ref_for(name: str) -> str | None:
    """ブランチ名に対応する比較用の ref を返す。ローカルを優先し、無ければ origin を見る。"""
    if _ok(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{name}"]):
        return name
    if _ok(["git", "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{name}"]):
        return f"origin/{name}"
    return None


def resolve_base(base_arg: str | None) -> tuple[str, str]:
    """(ベースブランチ名, 比較用の ref) を返す。"""
    candidates = (base_arg,) if base_arg else BASE_CANDIDATES
    for name in candidates:
        ref = _ref_for(name)
        if ref:
            return name, ref
    if base_arg:
        raise PreflightError(
            f"ベースブランチ {base_arg} がローカルにも origin にもありません"
        )
    raise PreflightError(
        "ベースブランチを決められません（develop / main / master のいずれも無い）。引数で指定してください"
    )


def collect_commits(base_ref: str) -> list[dict]:
    out = _stdout(
        [
            "git",
            "log",
            f"{base_ref}..HEAD",
            f"--format=%H{_FIELD}%s{_FIELD}%b{_RECORD}",
        ],
        "コミット一覧",
    )
    commits = []
    for record in out.split(_RECORD):
        record = record.strip("\n")
        if not record:
            continue
        sha, subject, body = (record.split(_FIELD) + ["", ""])[:3]
        commits.append({"sha": sha, "subject": subject, "body": body.strip()})
    return commits


def preflight(base_arg: str | None, body_file: str) -> dict:
    gh_checks.check_gh(_run)
    gh_checks.check_git_repo(_run)
    branch = current_branch()
    base, base_ref = resolve_base(base_arg)
    commits = collect_commits(base_ref)
    if not commits:
        raise PreflightError(
            f"{base} からのコミットがありません。変更をコミットしてから再試行してください"
        )
    diffstat = _stdout(
        ["git", "diff", f"{base_ref}...HEAD", "--stat"], "変更ファイル統計"
    )
    root = Path(
        _stdout(["git", "rev-parse", "--show-toplevel"], "リポジトリルート").strip()
    )
    template = root / ".github" / "PULL_REQUEST_TEMPLATE.md"
    workflows = root / ".github" / "workflows"
    has_ci = workflows.is_dir() and (
        any(workflows.glob("*.yml")) or any(workflows.glob("*.yaml"))
    )
    Path(body_file).parent.mkdir(parents=True, exist_ok=True)
    return {
        "branch": branch,
        "is_protected_branch": branch in PROTECTED_BRANCHES,
        "base": base,
        "base_ref": base_ref,
        "commits": commits,
        "diffstat": diffstat.rstrip("\n"),
        "template": str(template) if template.is_file() else None,
        "has_ci": bool(has_ci),
        "body_file": body_file,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="PR 作成前の確認と本文の材料の収集を行い JSON で出力する"
    )
    parser.add_argument(
        "--base", help="ベースブランチ。省略時は develop > main > master"
    )
    parser.add_argument(
        "--body-file",
        required=True,
        help="本文ファイルのパス（親ディレクトリを作成する）",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        result = preflight(args.base, args.body_file)
    except PreflightError as e:
        print(json.dumps({"errors": [str(e)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
