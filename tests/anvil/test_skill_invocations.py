"""anvil の SKILL.md が script を呼ぶ書き方の検査。

次を固定する。

- `${CLAUDE_SKILL_DIR}` で始まるパスは、パス全体を `"` で囲む。置換後のパスに空白があると
  （`My Projects` 等）、囲まなければ複数の引数に分かれて実行に失敗する
- `allowed-tools` の Bash ルールは、本文と同じ `"${CLAUDE_SKILL_DIR}/scripts/` で始める。Bash ルールは
  コマンドの文字列そのものと照合されるため、引用符の有無が食い違うと事前承認が効かない
"""

import re
import unittest
from pathlib import Path

_SKILLS = Path(__file__).resolve().parents[2] / "anvil" / "skills"
_PLACEHOLDER = "${CLAUDE_SKILL_DIR}"


def _skill_files():
    return sorted(_SKILLS.glob("*/SKILL.md"))


def _split(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    return frontmatter, body


class SkillInvocationTest(unittest.TestCase):
    def test_skills_exist(self):
        self.assertTrue(_skill_files())

    def test_placeholder_paths_are_quoted_in_body(self):
        for path in _skill_files():
            _, body = _split(path)
            for i, line in enumerate(body.splitlines(), 1):
                for m in re.finditer(re.escape(_PLACEHOLDER), line):
                    with self.subTest(skill=path.parent.name, line=line.strip()):
                        self.assertEqual(line[m.start() - 1 : m.start()], '"')

    def test_allowed_tools_rules_match_quoted_form(self):
        for path in _skill_files():
            frontmatter, _ = _split(path)
            rules = re.findall(r"Bash\(([^)]*)\)", frontmatter)
            for rule in rules:
                if _PLACEHOLDER not in rule:
                    continue
                with self.subTest(skill=path.parent.name, rule=rule):
                    self.assertIn(f'"{_PLACEHOLDER}/scripts/', rule)


if __name__ == "__main__":
    unittest.main()
