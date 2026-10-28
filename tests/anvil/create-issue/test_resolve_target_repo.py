"""resolve_target_repo.py の単体テスト（anvil:create-issue Phase 0）。

起票先の誤りは無関係なリポジトリへの公開になる。次を固定する。

- `origin` の URL 形式（scp / https / ssh://、`.git` の有無、末尾 `/`、ポート、user 部）
- `--repo` の形式検証（URL や `.git` 付きを受け付けない）
- `is_external` の判定（大文字小文字を区別しない。ホストの違いも別リポジトリとみなす）
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "anvil" / "skills" / "create-issue" / "scripts" / "resolve_target_repo.py"
)

_spec = importlib.util.spec_from_file_location("anvil_resolve_target_repo", _SCRIPT_PATH)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


class ParseRemoteUrlTest(unittest.TestCase):
    def test_accepted_forms(self):
        cases = {
            "git@github.com:octo/app.git": ("github.com", "octo", "app"),
            "git@github.com:octo/app": ("github.com", "octo", "app"),
            "https://github.com/octo/app.git": ("github.com", "octo", "app"),
            "https://github.com/octo/app": ("github.com", "octo", "app"),
            "https://github.com/octo/app/": ("github.com", "octo", "app"),
            "https://user@github.com/octo/app.git": ("github.com", "octo", "app"),
            "ssh://git@github.com/octo/app.git": ("github.com", "octo", "app"),
            "ssh://git@github.com:22/octo/app.git": ("github.com", "octo", "app"),
            "git@ghe.example.com:team/my.repo_1.git": ("ghe.example.com", "team", "my.repo_1"),
            "https://github.com/octo/app.git\n": ("github.com", "octo", "app"),
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(mod.parse_remote_url(url), expected)

    def test_rejected_forms(self):
        for url in [
            "",
            "/local/path/repo.git",
            "https://github.com/octo",
            "https://github.com/octo/app/extra",
            "git@github.com:octo/..",
        ]:
            with self.subTest(url=url):
                with self.assertRaises(mod.ResolveError):
                    mod.parse_remote_url(url)


class ParseRepoArgTest(unittest.TestCase):
    def test_accepted(self):
        self.assertEqual(mod.parse_repo_arg("octo/app"), ("github.com", "octo", "app"))
        self.assertEqual(
            mod.parse_repo_arg("ghe.example.com/team/app"), ("ghe.example.com", "team", "app")
        )

    def test_rejected(self):
        for value in [
            "app",
            "https://github.com/octo/app",
            "octo/app/extra/more",
            "-octo/app",
            "octo/..",
            "octo/app ",
            "octo/app\n",
            "",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(mod.ResolveError):
                    mod.parse_repo_arg(value)


class ResolveTest(unittest.TestCase):
    ORIGIN = "git@github.com:octo/app.git"

    def test_without_argument_targets_origin(self):
        self.assertEqual(
            mod.resolve(self.ORIGIN, None),
            {"target": "octo/app", "source": "origin", "origin_repo": "octo/app", "is_external": False},
        )

    def test_argument_matching_origin_is_not_external(self):
        result = mod.resolve(self.ORIGIN, "Octo/App")
        self.assertEqual(result["source"], "argument")
        self.assertFalse(result["is_external"])

    def test_argument_with_explicit_default_host_is_not_external(self):
        self.assertFalse(mod.resolve(self.ORIGIN, "github.com/octo/app")["is_external"])

    def test_different_repo_is_external(self):
        result = mod.resolve(self.ORIGIN, "octo/other")
        self.assertEqual(result["target"], "octo/other")
        self.assertTrue(result["is_external"])

    def test_different_host_is_external(self):
        """GHE の origin に対し OWNER/REPO だけを渡すと github.com が対象になる。別物として扱う。"""
        result = mod.resolve("git@ghe.example.com:octo/app.git", "octo/app")
        self.assertEqual(result["target"], "octo/app")
        self.assertEqual(result["origin_repo"], "ghe.example.com/octo/app")
        self.assertTrue(result["is_external"])


class CliTest(unittest.TestCase):
    def _git_repo(self, origin: str | None) -> str:
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        subprocess.run(["git", "init", "-q", tmp], check=True)
        if origin is not None:
            subprocess.run(["git", "-C", tmp, "remote", "add", "origin", origin], check=True)
        return tmp

    def _run(self, cwd: str, *args: str):
        return subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), *args], capture_output=True, text=True, cwd=cwd
        )

    def test_outputs_json(self):
        proc = self._run(self._git_repo("https://github.com/octo/app.git"), "--repo", "octo/other")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            json.loads(proc.stdout),
            {"target": "octo/other", "source": "argument", "origin_repo": "octo/app", "is_external": True},
        )

    def test_missing_origin_fails(self):
        proc = self._run(self._git_repo(None))
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(len(json.loads(proc.stdout)["errors"]), 1)

    def test_invalid_argument_fails(self):
        proc = self._run(self._git_repo("https://github.com/octo/app.git"), "--repo", "nope")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("--repo", json.loads(proc.stdout)["errors"][0])


if __name__ == "__main__":
    unittest.main()
