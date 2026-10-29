# ローカル開発・デバッグガイド

**作成日**: 2026-06-02
**目的**: プラグイン開発時のローカルデバッグ手順をまとめる
**適用範囲**: このリポジトリのコントリビューター

---

## 1. プラグインのローカルロード

### 1.1 `--plugin-dir` でロードする

```bash
claude --plugin-dir ./anvil
```

セッション起動後、すべての anvil スキルが `/` コマンドとして使用可能になる。`--plugin-dir` にはプラグインルート（`.claude-plugin/plugin.json` を持つディレクトリ）を渡す。マーケットプレイスのルート（リポジトリルート）を渡しても何もロードされない。

### 1.2 マーケットプレイス経由（配布経路の動作確認）

`--plugin-dir` は `marketplace.json` を読まないため、カタログの不備（`source` の誤り等）は検出できない。配布経路はローカルのマーケットプレイスとして登録して確かめる:

```bash
/plugin marketplace add ./
/plugin install anvil@git-anvil
/reload-plugins
```

公開版を確かめる場合は `/plugin marketplace add BlueEventHorizon/git-anvil` を使う。

### 1.3 manifest の検証

```bash
claude plugin validate . --strict          # マーケットプレイス
claude plugin validate ./anvil --strict    # プラグイン
```

---

## 2. スキル動作の確認手順

### 2.1 起動後の確認

```
/anvil:commit      # anvil スキルの動作確認（例）
```

### 2.2 SKILL.md を編集した場合

セッションを再起動する（`--plugin-dir` オプション付きで再実行）。編集内容はセッション内では即時反映されない。

```bash
claude --plugin-dir ./anvil
```

---

## 3. Python スクリプトの単体確認

SKILL.md から呼び出されるスクリプトは、Claude セッションを介さずに直接実行して動作確認できる。

```bash
# ステージ状態の検査（commit）
python3 anvil/skills/commit/scripts/inspect_stage_state.py

# commit の git 操作（commit。prepare 以外は実際にステージ・commit・push される）
python3 anvil/skills/commit/scripts/commit_ops.py prepare --message-file .temp/anvil/commit/commit_msg_test.txt
python3 anvil/skills/commit/scripts/commit_ops.py {stage|new-branch|commit|push} ...

# PR 作成前の確認と本文の材料の収集（create-pr）
python3 anvil/skills/create-pr/scripts/preflight.py --body-file .temp/anvil/create-pr/pr_body_test.md [--base <branch>]

# 現在ブランチの push（create-pr。実際に push される）
python3 anvil/skills/create-pr/scripts/push_branch.py --branch <branch>

# 本文ファイルから draft PR を作成（create-pr。実際に作成される）
python3 anvil/skills/create-pr/scripts/create_pr.py --base <branch> --title "<title>" --body-file <path>

# PR の CI 状態の検査（create-pr）
python3 anvil/skills/create-pr/scripts/inspect_ci_status.py --pr <PR番号> --repo <owner>/<repo> [--delay 30]

# Issue 起票前の確認と起票先の解決（create-issue）
python3 anvil/skills/create-issue/scripts/preflight.py --body-file .temp/anvil/create-issue/issue_body_test.md [--repo <owner>/<repo>]

# 本文ファイルから Issue を作成（create-issue。実際に起票される）
python3 anvil/skills/create-issue/scripts/create_issue.py --repo <owner>/<repo> --title "<title>" --body-file <path> [--label <label>]
```

`python3` が見つからない環境では `/opt/homebrew/bin/python3` を使う。

---

## 4. テスト実行

```bash
# 全テスト一括実行
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

テストの配置ルールは `CLAUDE.md` の「Testing」セクションを参照。

---

## 5. フォーマット

```bash
dprint fmt      # JSON / TOML / Markdown / YAML に適用
dprint check    # 差分チェックのみ（CI 向け）
```

設定ファイル: `dprint.jsonc`

---

## 6. デバッグのポイント

### 6.1 スキルが認識されない

- `--plugin-dir` のパスが正しいか確認（`./anvil` のようにプラグインルートを指定）
- `anvil/.claude-plugin/plugin.json` が壊れていないか確認（`claude plugin validate ./anvil --strict`）
- `anvil/skills/{skill}/SKILL.md` の frontmatter `name` がディレクトリ名と一致し、`user-invocable: true` であるか確認

### 6.2 スクリプトが期待した動作をしない

コード読解による推論で 2〜3 回修正しても解決しない場合は `print()` / 変数ダンプで実際の状態を観測する。観測後にログを除去すること（`CLAUDE.md` Debugging セクションも参照）。

---

## 7. 参考

- `CLAUDE.md` — リポジトリ全体の規約・構成説明
