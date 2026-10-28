"""push_branch.py の単体テスト（anvil:create-pr Phase 4.1）。

一時リポジトリと、origin 役の bare リポジトリを実際に作って確かめる。次を固定する。

- リモートに無ければ `-u` 付きで push する
- リモートがローカル HEAD と一致すれば push しない
- 一致しなければ push する
- push の失敗を `errors` で返す
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[3] / "anvil" / "skills" / "create-pr" / "scripts" / "push_branch.py"

_spec = importlib.util.spec_from_file_location("anvil_create_pr_push_branch", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


class PushTest(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.remote = tmp / "remote.git"
        self.work = tmp / "work"
        _git(tmp, "init", "-q", "--bare", str(self.remote))
        _git(tmp, "init", "-q", "-b", "main", str(self.work))
        _git(self.work, "config", "user.email", "t@example.invalid")
        _git(self.work, "config", "user.name", "t")
        _git(self.work, "remote", "add", "origin", str(self.remote))
        self._commit("a")
        _git(self.work, "checkout", "-q", "-b", "feature/x")
        cwd = Path.cwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.work)

    def _commit(self, name):
        (self.work / name).write_text(name, encoding="utf-8")
        _git(self.work, "add", name)
        _git(self.work, "commit", "-q", "-m", name)

    def _remote_head(self):
        return _git(self.remote, "rev-parse", "refs/heads/feature/x").strip()

    def test_new_branch_is_pushed_with_upstream(self):
        self.assertEqual(mod.push("feature/x"), {"action": "pushed_new"})
        self.assertEqual(self._remote_head(), _git(self.work, "rev-parse", "HEAD").strip())
        self.assertEqual(_git(self.work, "config", "branch.feature/x.remote").strip(), "origin")

    def test_up_to_date_does_not_push(self):
        mod.push("feature/x")
        self.assertEqual(mod.push("feature/x"), {"action": "up_to_date"})

    def test_stale_remote_is_pushed(self):
        mod.push("feature/x")
        self._commit("b")
        self.assertEqual(mod.push("feature/x"), {"action": "pushed"})
        self.assertEqual(self._remote_head(), _git(self.work, "rev-parse", "HEAD").strip())

    def test_push_failure_is_reported(self):
        mod.push("feature/x")
        # リモート側を先に進め、ローカルの push を non-fast-forward で拒否させる
        other = self.work.parent / "other"
        _git(self.work.parent, "clone", "-q", "-b", "feature/x", str(self.remote), str(other))
        _git(other, "config", "user.email", "t@example.invalid")
        _git(other, "config", "user.name", "t")
        (other / "c").write_text("c", encoding="utf-8")
        _git(other, "add", "c")
        _git(other, "commit", "-q", "-m", "c")
        _git(other, "push", "-q", "origin", "feature/x")
        self._commit("d")
        with self.assertRaisesRegex(mod.PushError, "git push"):
            mod.push("feature/x")


class CliTest(unittest.TestCase):
    def test_branch_is_required(self):
        proc = subprocess.run([sys.executable, str(_SCRIPT)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)

    def test_error_is_json_on_stdout(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--branch", "x"], capture_output=True, text=True, cwd=tmp
        )
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(len(json.loads(proc.stdout)["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
