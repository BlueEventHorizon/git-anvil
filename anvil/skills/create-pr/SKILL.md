---
name: create-pr
description: |
  コミット差分からタイトル・本文を生成し、PR を素早く作成できる。
  トリガー: "PR を作成", "プルリクエスト作成", "create-pr", "PR 出して"
user-invocable: true
argument-hint: "[base-branch]"
allowed-tools: Bash(python3 "${CLAUDE_SKILL_DIR}/scripts/*), Bash(gh pr view *), Write, Read, AskUserQuestion
---

# /anvil:create-pr

現在のブランチのコミット差分を解析し、GitHub PR をドラフト作成する。

## コマンド構文

```
/anvil:create-pr [base-branch]
```

| 引数        | 内容                                                          |
| ----------- | ------------------------------------------------------------- |
| base-branch | ベースブランチ（省略時は develop > main > master の順で決定） |

---

## Phase 1: 確認と材料の収集

### 1.1 確認と収集

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/preflight.py" --body-file "${CLAUDE_PROJECT_DIR}/.temp/anvil/create-pr/pr_body_${CLAUDE_SESSION_ID}.md" [--base <引数で指定された値>]
```

script は、gh CLI の有無と認証・git リポジトリか・現在ブランチ・ベースブランチ（引数 > develop > main > master）・`<base>` からのコミットの有無を確かめ、PR 本文の材料（コミット一覧・変更ファイル統計・PR テンプレート・CI 設定の有無）を集め、本文ファイルの置き場を作る。コマンドを自分で組み立てて同じ確認・収集をしない。

- **終了コード 0** → 出力 JSON の `branch` / `is_protected_branch` / `base` / `commits` / `diffstat` / `template` / `has_ci` / `body_file` を記録する。以降の `<base>` は `base` を、`<current-branch>` は `branch` を、`<body-file>` は `body_file` を指す
- **それ以外** → 出力 JSON の `errors` をそのまま提示してエラー終了する（コミットが無い・detached HEAD を含む）

> **注意**: `git status` の状態（ステージングされた変更等）は PR 作成可否の判断に使用しない。

### 1.2 保護ブランチからの実行

`is_protected_branch` が `true`（現在ブランチが main / master / develop）の場合 → AskUserQuestion を使用して警告し確認する（続行 or 中止）

---

## Phase 2: PR 情報生成

Phase 1 の `commits`（件名と本文）と `diffstat` から生成する。

### 2.1 PR タイトルの生成

ブランチ名から変換:

| ブランチ名パターン | PR タイトル              |
| ------------------ | ------------------------ |
| `feature/xxx-yyy`  | `[Feature] Xxx yyy`      |
| `fix/xxx`          | `[Fix] Xxx`              |
| `chore/xxx`        | `[Chore] Xxx`            |
| `docs/xxx`         | `[Docs] Xxx`             |
| `refactor/xxx`     | `[Refactor] Xxx`         |
| その他             | ブランチ名をそのまま使用 |

コミット内容からタイトルを補正する（コミットメッセージが明確な場合はそちらを優先）。

### 2.2 PR 本文の生成

PR テンプレートの適用:

1. `template` が `null` でなければ、そのファイルを Read して骨格に使用し、コミット差分から内容を補完する
2. `null` の場合は下記デフォルト構造を使用:

```markdown
## 概要

{コミットメッセージ・差分から自動生成}

## 変更内容

{diffstat を整形}

## テスト

- [ ] 動作確認済み
```

### 2.3 Issue クローズキーワードの付与

コミットメッセージ（`commits`）や会話コンテキストから、この PR が解決する Issue 参照（`Fixes #N` / `Closes #N` / `Resolves #N` 等）を検出する。検出した Issue ごとに、参照先リポジトリに応じて PR 本文（概要セクション付近）に以下を追記する:

| 参照先 Issue       | 追記する記法                                                                                                                                                |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **同一リポジトリ** | `Closes #<N>`（GitHub の自動クローズキーワードとして機能する）                                                                                              |
| **別リポジトリ**   | `Closes https://github.com/<owner>/<repo>/issues/<N>`（フル URL。自動クローズキーワードは同一リポジトリ限定のため機能しないが、追跡用リンクとして明記する） |

該当 Issue が見つからない場合はこの節をスキップする（無理に追記しない）。

---

## Phase 3: リモートプッシュ & PR 作成

### 3.1 リモートへのプッシュ

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/push_branch.py" --branch <current-branch>
```

script は、origin に同名ブランチが無ければ `git push -u origin` し、あってもローカル HEAD と異なれば push する（remote-tracking ref はローカルキャッシュのため、`git ls-remote` でリモートを直接問い合わせる）。

- **終了コード 0** → 3.2 へ（出力 JSON の `action` は `pushed_new` / `pushed` / `up_to_date`）
- **それ以外** → 出力 JSON の `errors` を提示し、AskUserQuestion で対応を確認する（中止 or 別対応）

### 3.2 PR 作成

特殊文字（引用符・バッククォート・ドル記号等）が含まれても安全に渡すため、本文はファイルにして渡す。本文ファイルは `Write` ツールで書く。シェル（ヒアドキュメント・`echo` 等）で書き出さない。

1. `Write` ツールで、Phase 2 で生成した本文をそのまま `<body-file>` に書く
2. PR を作成する:
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/create_pr.py" --base <base> --title "<title>" --body-file "<body-file>"
   ```
   - **終了コード 0** → 出力 JSON の `url` / `number` / `repo` を記録する。`repo` は PR が実際に作られたリポジトリであり、Phase 5 の問い合わせ先に使う（fork では upstream になることがある）。script が `<body-file>` を削除している
   - **それ以外** → 出力 JSON の `errors` を表示して終了する。`<body-file>` は残っているので、再実行ではそのまま使える

**PR 本文に含めないもの**:

- `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
- `Co-Authored-By: Claude <noreply@anthropic.com>`

---

## Phase 4: 完了

PR URL を表示する。

```
PR を作成しました:
  <PR URL>
```

ブラウザで開くか確認（AskUserQuestion）:

```
ブラウザで PR を開きますか？
```

- **はい** → `gh pr view <number> --repo <repo> --web`
- **いいえ** → 終了

---

## Phase 5: CI 結果確認 [MANDATORY]

### 5.1 CI 設定の有無を確認

Phase 1 の `has_ci` を見る。

- **`false`**（`.github/workflows/` に `*.yml` / `*.yaml` が無い）→ 本 Phase をスキップして終了
- **`true`** → 5.2 へ

**ここで判定できるのは「workflow が定義されているか」までである**。定義されていても、その workflow の
トリガー条件（`on.pull_request.branches` 等）が今回の PR に合致しなければチェックは登録されない。
したがって存在を確認できたことを「CI が走るはず」の根拠にしない——5.2 が返す `status` が唯一の実態である。

### 5.2 CI の状態を問い合わせる

Phase 3.2 で作成した PR の `number` と `repo` に対し、状態を問い合わせる:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/inspect_ci_status.py" --pr <number> --repo <repo>
```

**`gh pr checks` を直接呼んで終了コードで分岐してはならない [MANDATORY]**。`gh` の終了コードは
「全件成功」「1 件以上失敗」「チェックが未登録」を 0 と 1 に畳み込む。push 直後は GitHub 側で
チェックが登録される前に問い合わせが届くため、**未登録は必ず通る状態**であり、終了コードで分岐すると
これを CI 失敗として報告する（実際に起きた誤報告である）。

stdout の単一 JSON から `status` を読み、下表に従う。**それ以外の判断をしない**（bucket の集計・
優先順位の適用は script が済ませている）:

| `status`       | 意味                                    | 行き先                       |
| -------------- | --------------------------------------- | ---------------------------- |
| `succeeded`    | 全チェックが成功（スキップを含む）      | 5.3 へ                       |
| `failed`       | 1 件以上が失敗                          | 5.4 へ                       |
| `cancelled`    | 失敗は無いが 1 件以上がキャンセルされた | 5.4 へ（失敗と区別して提示） |
| `pending`      | 実行中のチェックが残っている            | 5.2.1 へ                     |
| `not_reported` | チェックがまだ 1 件も登録されていない   | 5.2.1 へ                     |

`counts` / `checks` / `failed_checks` は 5.3・5.4 の報告に使う。件数を数え直さない。

script が非ゼロ終了した場合（`gh` 自体が失敗した・`gh` の出力を解釈できない・既知でない bucket が返った等）は、CI の
成否を判定できていない。**成功にも失敗にも畳まず**、エラー内容を提示して `AskUserQuestion` で対応を
確認する。

#### 5.2.1 完了まで待つ

**待機のループは本 SKILL が駆動する**（script は問い合わせた時点の状態だけを返し、完了待ちを
持たない）。`--delay 30` を付けて 5.2 のコマンドを繰り返し呼ぶ（script が 30 秒待ってから 1 回問い合わせる）。
`sleep` との複合コマンドにしない（事前承認の形から外れ、呼ぶたびに確認が出る）。

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/inspect_ci_status.py" --pr <number> --repo <repo> --delay 30
```

- `status` が `pending` / `not_reported` のまま → 継続。ただし **`--delay 30` 付きで 20 回呼んでも
  変わらなければ（約 600 秒）打ち切り**、その時点の `status` と `counts` を添えて報告する（CI 自体は GitHub 側で
  継続しているため、本 Phase の再実行で状態を取り直せる旨も伝える）
- それ以外の `status` になった → 上表に従って 5.3 / 5.4 へ進む

**呼ぶたびに 1 回、その時点の状態をテキストで利用者へ報告する。省略しない**（`status` と
`counts.total` を含める）。`not_reported` が続く場合は「チェックがまだ登録されていない」ことを明示する
——これを黙って待つと、CI が発火しない設定不備と登録待ちの区別が利用者に見えない。

### 5.3 CI 全件成功時

完了報告に CI 結果を追記する:

```
CI: ✅ すべてのチェックが成功しました（<counts.pass> 件成功 / <counts.skipping> 件スキップ）
```

`counts.skipping` が 0 の場合はスキップの記載を省く。

### 5.4 CI 失敗時 / キャンセル時

`failed_checks` の各要素（`name` / `bucket` / `link`）を提示したうえで `AskUserQuestion` で対応を確認する。
**`status` が `cancelled` の場合は「キャンセルされた」と提示する**（失敗と同じ文言にしない。キャンセルは
誰かが止めたことであってコードの欠陥ではないため、利用者の次の判断が変わる）。

```
CI が失敗しました（または: CI がキャンセルされました）:
<failed_checks の name / bucket / link>

対応を選択してください:
- 修正する: 失敗原因を調査し、修正してから再度 push する
- このまま報告して終了: 現状の PR URL と CI 失敗内容を報告して終了する
```

---

## エラーハンドリング

| エラー                                                                                      | 対応                                                                                                                        |
| ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `preflight.py` が失敗（gh・認証・リポジトリ・ベースブランチ・コミット 0 件・detached HEAD） | 出力 JSON の `errors` を提示してエラー終了                                                                                  |
| main/master/develop ブランチから実行                                                        | AskUserQuestion で警告し確認（続行 or 中止）                                                                                |
| `push_branch.py` が失敗                                                                     | `errors` を提示し、AskUserQuestion で対応を確認                                                                             |
| `create_pr.py` が失敗                                                                       | `errors` を表示して終了。本文ファイルは残る                                                                                 |
| CI 失敗（`status: failed`）                                                                 | `failed_checks` を提示し、AskUserQuestion で対応（修正する / このまま報告して終了）を確認                                   |
| CI キャンセル（`status: cancelled`）                                                        | 失敗と区別して「キャンセルされた」と提示し、同じ選択肢で対応を確認（Phase 5.4）                                             |
| CI が登録されないまま打ち切り                                                               | `status: not_reported` のまま 20 回（約 600 秒）経過。その事実と `counts` を報告し、本 Phase の再実行で取り直せる旨を伝える |
| CI 状態の検査自体が失敗                                                                     | `inspect_ci_status.py` が非ゼロ終了。**成功にも失敗にも畳まず**、エラー内容を提示して AskUserQuestion で対応を確認          |
