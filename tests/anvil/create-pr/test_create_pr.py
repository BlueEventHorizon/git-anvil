"""create_pr.py の単体テスト（anvil:create-pr Phase 4.2）。

`gh` は呼ばず、`_run` を差し替えて固定する。次を確かめる。

- `gh pr create` へ渡す引数（draft・ベース・タイトル・本文ファイル）
- PR の URL から番号とリポジトリを取り出すこと（fork で upstream に作られた場合を含む）
- 成功時に本文ファイルを消し、失敗時に残すこと
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

_SCRIPT = Path(__file__).resolve().parents[3] / "anvil" / "skills" / "create-pr" / "scripts" / "create_pr.py"

_spec = importlib.util.spec_from_file_location("anvil_create_pr_create", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class ParseUrlTest(unittest.TestCase):
    def test_github_com(self):
        self.assertEqual(
            mod.parse_pr_url("https://github.com/upstream/app/pull/7\n"),
            {"url": "https://github.com/upstream/app/pull/7", "number": 7, "repo": "upstream/app"},
        )

    def test_enterprise_host_is_kept(self):
        self.assertEqual(mod.parse_pr_url("https://ghe.example.com/t/app/pull/3")["repo"], "ghe.example.com/t/app")

    def test_no_url(self):
        self.assertIsNone(mod.parse_pr_url("Warning: something"))


class CreateTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.body = Path(tmp) / "pr_body_s1.md"
        self.body.write_text("don't `x` $HOME\n", encoding="utf-8")

    def test_success_returns_pr_and_deletes_body(self):
        runner = mock.Mock(return_value=_proc(stdout="https://github.com/upstream/app/pull/7\n"))
        with mock.patch.object(mod, "_run", runner):
            result = mod.create("main", "[Feature] X", str(self.body))
        self.assertEqual(result["repo"], "upstream/app")
        self.assertEqual(result["number"], 7)
        self.assertFalse(self.body.exists())
        self.assertEqual(
            runner.call_args.args[0],
            ["gh", "pr", "create", "--draft", "--base", "main", "--title", "[Feature] X", "--body-file", str(self.body)],
        )

    def test_failure_keeps_body(self):
        runner = mock.Mock(return_value=_proc(returncode=1, stderr="a pull request already exists"))
        with mock.patch.object(mod, "_run", runner):
            with self.assertRaisesRegex(mod.CreateError, "already exists"):
                mod.create("main", "t", str(self.body))
        self.assertTrue(self.body.exists())

    def test_unparsable_output_keeps_body(self):
        with mock.patch.object(mod, "_run", mock.Mock(return_value=_proc(stdout="ok"))):
            with self.assertRaises(mod.CreateError):
                mod.create("main", "t", str(self.body))
        self.assertTrue(self.body.exists())


class CliTest(unittest.TestCase):
    def test_error_is_json_on_stdout(self):
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--base", "main", "--title", "t", "--body-file", "/nonexistent/x.md"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(len(json.loads(proc.stdout)["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
