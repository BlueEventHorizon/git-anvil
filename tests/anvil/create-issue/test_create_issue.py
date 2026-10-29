"""create_issue.py の単体テスト（anvil:create-issue Phase 4.3）。

`gh` は呼ばず、`_run` を差し替えて固定する。次を確かめる。

- `gh issue create` へ渡す引数（ラベルの有無）
- 成功時に本文ファイルを消し、失敗時に残すこと
- 出力から URL と番号を取り出すこと
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

_SCRIPT = Path(__file__).resolve().parents[3] / "anvil" / "skills" / "create-issue" / "scripts" / "create_issue.py"

_spec = importlib.util.spec_from_file_location("anvil_create_issue_create", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

URL = "https://github.com/octo/app/issues/42"


def _proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class CreateTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.body = Path(tmp) / "issue_body_s1.md"
        self.body.write_text("don't `x` $HOME\n", encoding="utf-8")

    def _create(self, proc, label="bug"):
        runner = mock.Mock(return_value=proc)
        with mock.patch.object(mod, "_run", runner):
            result = mod.create("octo/app", "[Bug] t", str(self.body), label)
        return result, runner.call_args.args[0]

    def test_success_returns_url_and_deletes_body(self):
        result, args = self._create(_proc(stdout=URL + "\n"))
        self.assertEqual(result, {"url": URL, "number": 42})
        self.assertFalse(self.body.exists())
        self.assertEqual(
            args,
            ["gh", "issue", "create", "--repo", "octo/app", "--title", "[Bug] t", "--body-file", str(self.body),
             "--label", "bug"],
        )

    def test_without_label(self):
        _, args = self._create(_proc(stdout=URL), label=None)
        self.assertNotIn("--label", args)

    def test_failure_keeps_body(self):
        runner = mock.Mock(return_value=_proc(returncode=1, stderr="HTTP 403"))
        with mock.patch.object(mod, "_run", runner):
            with self.assertRaisesRegex(mod.CreateError, "HTTP 403"):
                mod.create("octo/app", "t", str(self.body), None)
        self.assertTrue(self.body.exists())

    def test_unparsable_output_keeps_body(self):
        runner = mock.Mock(return_value=_proc(stdout="ok"))
        with mock.patch.object(mod, "_run", runner):
            with self.assertRaises(mod.CreateError):
                mod.create("octo/app", "t", str(self.body), None)
        self.assertTrue(self.body.exists())

    def test_missing_body_file(self):
        self.body.unlink()
        with self.assertRaisesRegex(mod.CreateError, "本文ファイルがありません"):
            mod.create("octo/app", "t", str(self.body), None)


class CliTest(unittest.TestCase):
    def test_error_is_json_on_stdout(self):
        """本文ファイルが無ければ gh を呼ぶ前に失敗し、errors を返す。"""
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--repo", "octo/app", "--title", "t", "--body-file", "/nonexistent/x.md"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(len(json.loads(proc.stdout)["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
