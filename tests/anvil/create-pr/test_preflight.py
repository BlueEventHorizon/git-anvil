"""preflight.py の単体テスト（anvil:create-pr Phase 1〜3）。

git は一時リポジトリを実際に作って確かめる。gh の確認（有無・認証）だけを差し替える。次を固定する。

- ベースブランチの決定（引数 > develop > main > master、ローカルに無ければ origin）
- 保護ブランチ上での実行の検出
- コミット 0 件・detached HEAD での失敗
- コミット一覧（件名と本文）と変更ファイル統計の収集
- PR テンプレートと CI 設定の検出
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

_SCRIPT = Path(__file__).resolve().parents[3] / "anvil" / "skills" / "create-pr" / "scripts" / "preflight.py"

_spec = importlib.util.spec_from_file_location("anvil_create_pr_preflight", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class RepoTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, True)
        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "t@example.invalid")
        _git(self.root, "config", "user.name", "t")
        _git(self.root, "remote", "add", "origin", "https://github.com/octo/app.git")
        self._commit("base.txt", "init")
        self.body_file = str(self.root / ".temp" / "anvil" / "create-pr" / "pr_body_s1.md")
        patcher = mock.patch.object(mod.gh_checks, "check_gh")
        patcher.start()
        self.addCleanup(patcher.stop)
        cwd = Path.cwd()
        self.addCleanup(lambda: __import__("os").chdir(cwd))
        __import__("os").chdir(self.root)

    def _commit(self, name, message):
        (self.root / name).write_text(message + "\n", encoding="utf-8")
        _git(self.root, "add", name)
        _git(self.root, "commit", "-q", "-m", message)

    def _feature(self):
        _git(self.root, "checkout", "-q", "-b", "feature/x")
        self._commit("a.txt", "feat: add a\n\nbody line")


class BaseTest(RepoTestCase):
    def test_defaults_to_main_and_collects_commits(self):
        self._feature()
        result = mod.preflight(None, self.body_file)
        self.assertEqual(result["branch"], "feature/x")
        self.assertFalse(result["is_protected_branch"])
        self.assertEqual((result["base"], result["base_ref"]), ("main", "main"))
        self.assertEqual(len(result["commits"]), 1)
        self.assertEqual(result["commits"][0]["subject"], "feat: add a")
        self.assertEqual(result["commits"][0]["body"], "body line")
        self.assertIn("a.txt", result["diffstat"])
        self.assertIsNone(result["template"])
        self.assertFalse(result["has_ci"])
        self.assertTrue(Path(self.body_file).parent.is_dir())

    def test_develop_is_preferred(self):
        _git(self.root, "branch", "develop")
        self._feature()
        self.assertEqual(mod.preflight(None, self.body_file)["base"], "develop")

    def test_argument_wins(self):
        _git(self.root, "branch", "develop")
        self._feature()
        self.assertEqual(mod.preflight("main", self.body_file)["base"], "main")

    def test_origin_only_base_uses_remote_ref(self):
        self._feature()
        _git(self.root, "update-ref", "refs/remotes/origin/develop", "main")
        result = mod.preflight("develop", self.body_file)
        self.assertEqual((result["base"], result["base_ref"]), ("develop", "origin/develop"))

    def test_unknown_base_argument(self):
        self._feature()
        with self.assertRaisesRegex(mod.PreflightError, "nope"):
            mod.preflight("nope", self.body_file)


class FailureTest(RepoTestCase):
    def test_no_commits(self):
        _git(self.root, "checkout", "-q", "-b", "feature/empty")
        with self.assertRaisesRegex(mod.PreflightError, "コミットがありません"):
            mod.preflight(None, self.body_file)

    def test_detached_head(self):
        _git(self.root, "checkout", "-q", "--detach")
        with self.assertRaisesRegex(mod.PreflightError, "detached HEAD"):
            mod.preflight(None, self.body_file)

    def test_protected_branch_is_flagged(self):
        _git(self.root, "checkout", "-q", "-b", "develop")
        self._commit("b.txt", "fix: b")
        result = mod.preflight("main", self.body_file)
        self.assertTrue(result["is_protected_branch"])


class RepoFilesTest(RepoTestCase):
    def test_template_and_ci_are_detected(self):
        (self.root / ".github" / "workflows").mkdir(parents=True)
        (self.root / ".github" / "workflows" / "ci.yaml").write_text("on: push\n", encoding="utf-8")
        (self.root / ".github" / "PULL_REQUEST_TEMPLATE.md").write_text("## 概要\n", encoding="utf-8")
        self._feature()
        result = mod.preflight(None, self.body_file)
        self.assertEqual(result["template"], str(self.root / ".github" / "PULL_REQUEST_TEMPLATE.md"))
        self.assertTrue(result["has_ci"])

    def test_workflows_dir_without_yaml_is_not_ci(self):
        (self.root / ".github" / "workflows").mkdir(parents=True)
        (self.root / ".github" / "workflows" / "README.md").write_text("x\n", encoding="utf-8")
        self._feature()
        self.assertFalse(mod.preflight(None, self.body_file)["has_ci"])


class CliTest(unittest.TestCase):
    def test_error_is_json_on_stdout(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--body-file", str(Path(tmp) / "x.md")],
            capture_output=True, text=True, cwd=tmp,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(len(json.loads(proc.stdout)["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
