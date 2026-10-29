#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Issue の起票先リポジトリを解決する read-only CLI。

`/anvil:create-issue` の Phase 0 が、起票先と、それがカレントリポジトリ（`origin`）と
異なるかを判定するために使う。

## なぜ script にするか

起票先を誤ると、無関係なリポジトリに Issue が公開される。取り消しても通知・検索結果に残る。
`origin` の URL は ssh（`git@host:owner/repo.git`）・https・`ssh://` の各形式を取り、
AI に読ませると末尾の `.git` やホストの扱いで取り違える。比較は機械判定でなければ守れない。

## 解決の規則

- `--repo` が指定されれば、それを起票先とする（`source: "argument"`）
- 指定が無ければ `origin` を起票先とする（`source: "origin"`）

起票先の値をファイルに保存して読み直すことはしない。保存した値はファイルごと別プロジェクトへ
複製されうるため、複製先から元のリポジトリへ起票させる経路になる。

## 出力

成功時は終了コード 0、標準出力に単一 JSON。

```json
{
  "target": "github.com/octo/app",
  "source": "argument",
  "origin_repo": "github.com/octo/main",
  "is_external": true
}
```

`target` / `origin_repo` は `gh --repo` にそのまま渡せる `HOST/OWNER/REPO` 形式である。
ホストは `github.com` でも省かない。`gh` はホストの無い `OWNER/REPO` を既定ホスト（`GH_HOST` 等）で
解釈するため、省くと、ここで解決したホストとは別のホストのリポジトリが対象になりうる。
`--repo` にホストが無いときは `github.com` とする。

`is_external` は起票先が `origin` と異なるか。ホスト・owner・repo を大文字小文字を区別せずに
比較する（GitHub の名前は大文字小文字を区別しない）。

`--repo` の形式が不正、`origin` が無い、`origin` の URL を解釈できない場合は、標準出力に
`{"errors": [...]}` を出して終了コード 1 で終わる。

`preflight.py` が `resolve()` を import して使う。単独の CLI としても動く。

## 依存

Python 標準ライブラリのみ。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

_DEFAULT_HOST = "github.com"

# GitHub の owner は英数字とハイフン、repo は英数字と `.` `_` `-`。
_OWNER = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_REPO = r"[A-Za-z0-9._-]+"
_REPO_ARG = re.compile(rf"(?:(?P<host>[A-Za-z0-9.-]+)/)?(?P<owner>{_OWNER})/(?P<repo>{_REPO})")

# `scheme://[user@]host[:port]/path`
_URL_FORM = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://(?:[^@/]+@)?(?P<host>[^/:]+)(?::\d+)?/(?P<path>.+)$")
# `[user@]host:path`（scp 形式）
_SCP_FORM = re.compile(r"^(?:[^@/]+@)?(?P<host>[^/:]+):(?P<path>[^/].*)$")


class ResolveError(Exception):
    """起票先を解決できない。"""


def _repo_name_ok(repo: str) -> bool:
    return repo not in (".", "..")


def parse_repo_arg(value: str) -> tuple[str, str, str]:
    """`--repo` の値を (host, owner, repo) に分解する。URL や `.git` 付きは受け付けない。"""
    m = _REPO_ARG.fullmatch(value)
    if not m or not _repo_name_ok(m.group("repo")):
        raise ResolveError(f"--repo の形式が不正です（[HOST/]OWNER/REPO で指定してください）: {value}")
    return (m.group("host") or _DEFAULT_HOST, m.group("owner"), m.group("repo"))


def parse_remote_url(url: str) -> tuple[str, str, str]:
    """`origin` の URL を (host, owner, repo) に分解する。"""
    url = url.strip()
    m = _URL_FORM.match(url) or _SCP_FORM.match(url)
    if not m:
        raise ResolveError(f"origin の URL を解釈できません: {url}")
    path = m.group("path").rstrip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    parts = path.split("/")
    if (
        len(parts) != 2
        or not re.fullmatch(_OWNER, parts[0])
        or not re.fullmatch(_REPO, parts[1])
        or not _repo_name_ok(parts[1])
    ):
        raise ResolveError(f"origin の URL から OWNER/REPO を取り出せません: {url}")
    return (m.group("host"), parts[0], parts[1])


def _format(host: str, owner: str, repo: str) -> str:
    return f"{host}/{owner}/{repo}"


def _key(host: str, owner: str, repo: str) -> tuple[str, str, str]:
    return (host.lower(), owner.lower(), repo.lower())


def resolve(origin_url: str, repo_arg: str | None) -> dict:
    origin = parse_remote_url(origin_url)
    if repo_arg is None:
        target, source = origin, "origin"
    else:
        target, source = parse_repo_arg(repo_arg), "argument"
    return {
        "target": _format(*target),
        "source": source,
        "origin_repo": _format(*origin),
        "is_external": _key(*target) != _key(*origin),
    }


def _origin_url() -> str:
    proc = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise ResolveError(f"origin を取得できません: {proc.stderr.strip()}")
    return proc.stdout


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Issue の起票先リポジトリを解決し JSON で出力する（read-only）")
    parser.add_argument("--repo", help="起票先（[HOST/]OWNER/REPO）。省略時は origin")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        result = resolve(_origin_url(), args.repo)
    except ResolveError as e:
        print(json.dumps({"errors": [str(e)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
