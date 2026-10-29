"""preflight.py の単体テスト（anvil:create-issue Phase 0）。

外部コマンド（gh / git）は呼ばず、`_run` と `shutil.which` を差し替えて固定する。次を確かめる。

- 確認の順序と、最初に失敗した確認で止まること
- 起票先の解決（`--repo` の有無、`is_external`）
- 存在しない種別ラベルの列挙
- 本文ファイルの親ディレクトリを作ること
- CLI の出力形式（成功は結果の JSON、失敗は `errors` の配列）
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parents[3] / "anvil" / "skills" / "create-issue" / "scripts"

_spec = importlib.util.spec_from_file_location("anvil_create_issue_preflight", _SCRIPTS / "preflight.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

ORIGIN = "git@github.com:octo/app.git\n"


def _proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class FakeRunner:
    """コマンドの先頭語の組から結果を返す。呼ばれたコマンドを記録する。"""

    def __init__(self, overrides=None):
        self.results = {
            ("gh", "auth"): _proc(),
            ("git", "rev-parse"): _proc(stdout="true\n"),
            ("git", "remote"): _proc(stdout=ORIGIN),
            ("gh", "repo"): _proc(stdout=json.dumps({"nameWithOwner": "octo/app", "hasIssuesEnabled": True})),
            ("gh", "label"): _proc(stdout=json.dumps([{"name": "bug"}, {"name": "enhancement"}])),
        }
        self.results.update(overrides or {})
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        return self.results[(args[0], args[1])]


class PreflightTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.body_file = str(Path(self.tmp) / ".temp" / "anvil" / "create-issue" / "issue_body_s1.md")
        patcher = mock.patch.object(mod.shutil, "which", return_value="/usr/bin/gh")
        patcher.start()
        self.addCleanup(patcher.stop)

    def _preflight(self, runner, repo_arg=None):
        with mock.patch.object(mod, "_run", runner):
            return mod.preflight(repo_arg, self.body_file)

    def test_success_targets_origin_and_creates_body_dir(self):
        result = self._preflight(FakeRunner())
        self.assertEqual(result["target"], "github.com/octo/app")
        self.assertEqual(result["source"], "origin")
        self.assertFalse(result["is_external"])
        self.assertEqual(result["missing_labels"], [])
        self.assertEqual(result["body_file"], self.body_file)
        self.assertTrue(Path(self.body_file).parent.is_dir())
        self.assertFalse(Path(self.body_file).exists())

    def test_repo_argument_is_external_and_queried(self):
        runner = FakeRunner()
        result = self._preflight(runner, "octo/other")
        self.assertEqual(result["target"], "github.com/octo/other")
        self.assertTrue(result["is_external"])
        self.assertIn(["gh", "repo", "view", "github.com/octo/other", "--json", "nameWithOwner,hasIssuesEnabled"], runner.calls)

    def test_missing_labels_are_listed_in_fixed_order(self):
        runner = FakeRunner({("gh", "label"): _proc(stdout=json.dumps([{"name": "question"}]))})
        self.assertEqual(self._preflight(runner)["missing_labels"], ["bug", "enhancement"])

    def test_gh_not_installed(self):
        with mock.patch.object(mod.shutil, "which", return_value=None):
            with self.assertRaisesRegex(mod.PreflightError, "cli.github.com"):
                self._preflight(FakeRunner())

    def test_stops_at_first_failure(self):
        cases = {
            ("gh", "auth"): "gh auth login",
            ("git", "rev-parse"): "git リポジトリではありません",
            ("git", "remote"): "git remote add origin",
            ("gh", "repo"): "参照できません",
            ("gh", "label"): "ラベルを取得できません",
        }
        for key, message in cases.items():
            with self.subTest(key=key):
                runner = FakeRunner({key: _proc(returncode=1, stderr="boom")})
                with self.assertRaisesRegex(mod.PreflightError, message):
                    self._preflight(runner)
                self.assertEqual(runner.calls[-1][:2], list(key))

    def test_issues_disabled(self):
        runner = FakeRunner(
            {("gh", "repo"): _proc(stdout=json.dumps({"nameWithOwner": "octo/app", "hasIssuesEnabled": False}))}
        )
        with self.assertRaisesRegex(mod.PreflightError, "Issue が無効"):
            self._preflight(runner)

    def test_invalid_repo_argument(self):
        with self.assertRaisesRegex(mod.PreflightError, "--repo"):
            self._preflight(FakeRunner(), "nope")


class CliTest(unittest.TestCase):
    def test_error_is_json_on_stdout(self):
        """git リポジトリでない場所では（gh が無い・未認証の環境でも）確認に失敗し、errors を返す。"""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        proc = subprocess.run(
            [sys.executable, str(_SCRIPTS / "preflight.py"), "--body-file", str(Path(tmp) / "x.md")],
            capture_output=True, text=True, cwd=tmp,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(len(json.loads(proc.stdout)["errors"]), 1)

    def test_body_file_is_required(self):
        proc = subprocess.run(
            [sys.executable, str(_SCRIPTS / "preflight.py")], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
