#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Issue を起票する前の環境確認と起票先の解決をまとめて行う CLI。

`/anvil:create-issue` の Phase 0 が使う。

## なぜ script にするか

確認の手順（gh の有無・認証・git リポジトリか・起票先の解決・起票先の存在・ラベルの有無）は
決定論的である。AI が手順ごとにコマンドを組み立てると、コマンドの形が毎回変わり、許可ルールで
事前承認できない。1 本の script にまとめれば、SKILL の `allowed-tools` でこの script の呼び出しだけを
事前承認でき、起動後は確認なしで進む。

## 起票先の解決

`resolve_target_repo.py` の規則に従う（`--repo` があればそれ、無ければ `origin`）。

## 出力

成功時（終了コード 0）は標準出力に単一 JSON。

```json
{
  "target": "github.com/octo/app",
  "source": "argument",
  "origin_repo": "github.com/octo/main",
  "is_external": true,
  "missing_labels": ["enhancement"],
  "body_file": "/path/to/project/.temp/anvil/create-issue/issue_body_<session>.md"
}
```

- `missing_labels`: 起票先に存在しない種別ラベル（`bug` / `enhancement` のうち）
- `body_file`: 引数で受けたパスそのもの。親ディレクトリは作成済みである

失敗時（終了コード 1）は標準出力に `{"errors": [...]}`。最初に失敗した確認で止まる。

## 終了コード

| code | 意味                             |
| ---- | -------------------------------- |
| 0    | 確認が完了し、起票できる         |
| 1    | 確認に失敗した（理由は `errors`）|
| 2    | 引数を受理できない（`argparse`） |

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
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parents[2] / "scripts"))

import gh_checks  # noqa: E402  プラグイン直下 scripts/ の共有部品
import resolve_target_repo  # noqa: E402

KIND_LABELS = ("bug", "enhancement")


PreflightError = gh_checks.CheckError


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def check_target(target: str) -> None:
    proc = _run(["gh", "repo", "view", target, "--json", "nameWithOwner,hasIssuesEnabled"])
    if proc.returncode != 0:
        raise PreflightError(f"起票先 {target} を参照できません（存在しない・権限が無い）: {proc.stderr.strip()}")
    if not json.loads(proc.stdout).get("hasIssuesEnabled", False):
        raise PreflightError(f"起票先 {target} は Issue が無効です")


def missing_labels(target: str) -> list[str]:
    proc = _run(["gh", "label", "list", "--repo", target, "--json", "name", "--limit", "1000"])
    if proc.returncode != 0:
        raise PreflightError(f"起票先 {target} のラベルを取得できません: {proc.stderr.strip()}")
    names = {item["name"] for item in json.loads(proc.stdout)}
    return [label for label in KIND_LABELS if label not in names]


def preflight(repo_arg: str | None, body_file: str) -> dict:
    gh_checks.check_gh(_run)
    origin_url = gh_checks.check_git_repo(_run)
    try:
        resolved = resolve_target_repo.resolve(origin_url, repo_arg)
    except resolve_target_repo.ResolveError as e:
        raise PreflightError(str(e)) from e
    check_target(resolved["target"])
    resolved["missing_labels"] = missing_labels(resolved["target"])
    Path(body_file).parent.mkdir(parents=True, exist_ok=True)
    resolved["body_file"] = body_file
    return resolved


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Issue 起票前の確認と起票先の解決を行い JSON で出力する")
    parser.add_argument("--repo", help="起票先（[HOST/]OWNER/REPO）。省略時は origin")
    parser.add_argument("--body-file", required=True, help="本文ファイルのパス（親ディレクトリを作成する）")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        result = preflight(args.repo, args.body_file)
    except PreflightError as e:
        print(json.dumps({"errors": [str(e)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
