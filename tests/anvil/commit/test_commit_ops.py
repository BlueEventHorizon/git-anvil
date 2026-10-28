"""commit_ops.py の単体テスト（anvil:commit）。

一時リポジトリと、origin 役の bare リポジトリを実際に作って確かめる。次を固定する。

- `prepare` が状態の 5 項目・ステージ済みの差分・ブランチ判定を返し、メッセージの置き場を作ること
- 保護ブランチの判定（develop → main → master の最初に存在するもの。detached HEAD）
- `stage` の `--tracked` / `--path`
- `commit` がメッセージファイルで commit し、成功時だけファイルを消すこと
- `push` が追跡設定の有無で `-u` を付け分けること
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

_SCRIPT = Path(__file__).resolve().parents[3] / "anvil" / "skills" / "commit" / "scripts" / "commit_ops.py"

_spec = importlib.util.spec_from_file_location("anvil_commit_ops", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


class RepoTestCase(unittest.TestCase):
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
        self._write("a.txt", "a\n")
        _git(self.work, "add", "a.txt")
        _git(self.work, "commit", "-q", "-m", "init")
        self.message_file = str(self.work / ".temp" / "anvil" / "commit" / "commit_msg_s1.txt")
        cwd = Path.cwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.work)

    def _write(self, name, text):
        (self.work / name).write_text(text, encoding="utf-8")


class PrepareTest(RepoTestCase):
    def test_reports_state_diff_and_branch(self):
        self._write("a.txt", "a2\n")
        _git(self.work, "add", "a.txt")
        self._write("new.txt", "n\n")
        result = mod.prepare(self.message_file)
        self.assertEqual(result["staged_paths"], ["a.txt"])
        self.assertEqual(result["untracked_paths"], ["new.txt"])
        self.assertIn("+a2", result["staged_diff"])
        self.assertEqual(result["branch"], "main")
        self.assertEqual(result["protected_branch"], "main")
        self.assertTrue(result["is_protected"])
        self.assertTrue(Path(self.message_file).parent.is_dir())

    def test_develop_is_the_protected_branch_when_it_exists(self):
        _git(self.work, "branch", "develop")
        result = mod.prepare(self.message_file)
        self.assertEqual(result["protected_branch"], "develop")
        self.assertFalse(result["is_protected"])

    def test_detached_head(self):
        _git(self.work, "checkout", "-q", "--detach")
        result = mod.prepare(self.message_file)
        self.assertIsNone(result["branch"])
        self.assertFalse(result["is_protected"])


class StageTest(RepoTestCase):
    def test_tracked_and_paths(self):
        self._write("a.txt", "a2\n")
        self._write("new.txt", "n\n")
        self._write("skip.txt", "s\n")
        result = mod.stage(True, ["new.txt"])
        self.assertEqual(result["staged_paths"], ["a.txt", "new.txt"])
        self.assertEqual(result["untracked_paths"], ["skip.txt"])

    def test_nothing_to_stage(self):
        with self.assertRaises(mod.OpsError):
            mod.stage(False, [])


class CommitTest(RepoTestCase):
    def test_commit_uses_file_and_deletes_it(self):
        self._write("a.txt", "a2\n")
        _git(self.work, "add", "a.txt")
        Path(self.message_file).parent.mkdir(parents=True)
        Path(self.message_file).write_text("fix: a の値を直す\n\n本文 `x` $HOME\n", encoding="utf-8")
        result = mod.commit(self.message_file)
        self.assertEqual(result["summary"], "fix: a の値を直す")
        self.assertEqual(_git(self.work, "log", "-1", "--format=%b").strip(), "本文 `x` $HOME")
        self.assertFalse(Path(self.message_file).exists())

    def test_failure_keeps_message_file(self):
        Path(self.message_file).parent.mkdir(parents=True)
        Path(self.message_file).write_text("chore: nothing\n", encoding="utf-8")
        with self.assertRaises(mod.OpsError):
            mod.commit(self.message_file)
        self.assertTrue(Path(self.message_file).exists())


class BranchAndPushTest(RepoTestCase):
    def test_new_branch_then_push_sets_upstream_once(self):
        mod.new_branch("feature/x")
        self.assertEqual(_git(self.work, "branch", "--show-current").strip(), "feature/x")
        self.assertEqual(mod.push("feature/x"), {"action": "push_set_upstream"})
        self._write("a.txt", "a3\n")
        _git(self.work, "commit", "-qam", "b")
        self.assertEqual(mod.push("feature/x"), {"action": "push"})
        self.assertEqual(
            _git(self.remote, "rev-parse", "refs/heads/feature/x").strip(),
            _git(self.work, "rev-parse", "HEAD").strip(),
        )


class CliTest(unittest.TestCase):
    def test_subcommand_is_required(self):
        proc = subprocess.run([sys.executable, str(_SCRIPT)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)

    def test_error_is_json_on_stdout(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "commit", "--message-file", str(Path(tmp) / "none.txt")],
            capture_output=True, text=True, cwd=tmp,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(len(json.loads(proc.stdout)["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
