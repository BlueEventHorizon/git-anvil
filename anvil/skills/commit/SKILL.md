---
name: commit
description: |
  コミットメッセージを自動生成し、手間なく commit & push できる。
  トリガー: "コミットして", "commit して", "push して", "commit & push"
user-invocable: true
argument-hint: "[message]"
allowed-tools: Bash(python3 "${CLAUDE_SKILL_DIR}/scripts/*), Bash(bash "${CLAUDE_SKILL_DIR}/scripts/*), Write, AskUserQuestion
---

# /anvil:commit

変更内容を要約したコミットメッセージを生成し、GitHub へ commit & push する。

## コマンド構文

```
/anvil:commit [message]
```

| 引数    | 内容                                               |
| ------- | -------------------------------------------------- |
| message | コミットメッセージ（省略時は変更内容から自動生成） |

---

## Phase 0: フォーマット適用

commit 前に format 乱れを必ず解消する。format ずれたまま commit すると、後で誰かが fmt を走らせたときに無関係なファイルが diff に混入し、PR レビューや git blame が混乱する。

共有スクリプトで実行する（存在チェック + 実行、条件判定ロジックのインライン重複を避けるため）:

```bash
bash "${CLAUDE_SKILL_DIR}/scripts/run_dprint_fmt.sh"
```

`dprint fmt` が新たにファイルを書き換えた場合、今回の変更と無関係なファイルであっても revert せず、本 commit に含める。

`dprint` 以外の formatter (prettier / black / rustfmt 等) が project で使われている場合は、CLAUDE.md か README.md の指示に従って手動適用したうえで本 commit に含める。

---

## Phase 1: 変更の状態を調べる

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/commit_ops.py" prepare --message-file "${CLAUDE_PROJECT_DIR}/.temp/anvil/commit/commit_msg_${CLAUDE_SESSION_ID}.txt"
```

script は、変更の状態・ステージ済みの差分・現在ブランチと保護ブランチを返し、コミットメッセージの置き場を作る。`git status` 等を自分で実行して同じ判定をしない。

- **終了コード 0** → 出力 JSON を **現在の状態** として記録する（`tracked_paths` / `staged_paths` / `unstaged_paths` / `untracked_paths` / `stale_staged_paths` / `staged_diff` / `branch` / `is_protected` / `message_file`）。以降の `<message-file>` は `message_file` を指す
- **それ以外** → 出力 JSON の `errors` を提示してエラー終了する

`staged_paths` / `unstaged_paths` / `untracked_paths` が**すべて空** → エラー終了:

```
Error: コミットする変更がありません。
変更をファイルに保存してから再試行してください。
```

---

## Phase 2: ステージング確認

**原則: ステージ済みファイルのみをコミット対象とする。自動で `git add` しない。**

**ただし「ステージ済みがあるから」を理由に、確認せず Phase 3 へ進んではならない。**
先に Phase 1 の現在の状態で `stale_staged_paths`（index の内容が作業ツリーと食い違うパス）を確認する。

**分岐は網羅する**。どの条件にも当てはまらない状態を残すと、そこで AI が手順から外れて即興する。

| 状態                                                                                                  | 行き先                  |
| ----------------------------------------------------------------------------------------------------- | ----------------------- |
| `staged_paths` が**空でなく**、`unstaged_paths` `untracked_paths` `stale_staged_paths` が**すべて空** | そのまま Phase 3 へ進む |
| **上記以外すべて**                                                                                    | 2.2 の確認へ進む        |

2.2 へ進む状態は次のいずれかであり、**利用者へはどれに当たるかを示す**（選ぶべき選択肢が変わるため）。

- `stale_staged_paths` が空でない → **そのまま commit すると、作業ツリーの最新ではなく古い内容が入る**
  （ステージ後にさらに編集したファイルで起きる）。差分は commit した後にしか現れないため、気付くのは
  常に手遅れになる
- `staged_paths` と `unstaged_paths` が**ともに空でない**（混在）→ 同じ変更の一部が落ちる可能性がある
- `staged_paths` が空で `unstaged_paths` が空でない → **ステージされたものが無く、このままでは commit
  できない**。何をステージするかを決める必要がある
- `untracked_paths` だけが空でない → `git add -u` の対象外であり、個別に確認する必要がある

**ステージ対象は、いずれの場合も利用者に確認してから確定する。** AI が「必要と思われるファイル」を
自分の判断だけでステージしない。

#### 2.1 状態の読み方

**混在の判定は `staged_paths` と `unstaged_paths` で行う**。`git status` の出力を自分で読んで判定しない（quote 表記・rename の `->` 表記で取り違える。script 化はそれを避けるためにある）。`tracked_paths` は両者の合算であり、混在の判定には使えない。

**`stale_staged_paths` が空でない場合、そのパスを利用者へ明示する [MANDATORY]**。「ステージ済みだが、その後さらに編集されている」ことは `git status` の 2 文字表記（`MM` / `AM`）にしか現れず、見落とすと古い内容が commit される。ステージし直せば解消するため、2.2 の選択肢は現在の内容で `git add` し直す形にする。

#### 2.2 ステージ対象を確認する

`AskUserQuestion` で次を提示する。

- **追跡済みファイルを全てステージする**（既定）→ `python3 "${CLAUDE_SKILL_DIR}/scripts/commit_ops.py" stage --tracked` を実行し、Phase 3 へ進む
- **現在ステージされている内容のまま進む** → `git add` せず Phase 3 へ進む。**下記の条件では提示しない**
- **ステージせずに終了する** → 終了

2 番目の選択肢は Phase 2 冒頭の原則（ステージ済みのみをコミット対象とする）そのものである。意図的に一部だけステージした利用者に、これが無いと「無関係な変更まで巻き込む」か「中止する」しか残らない。

**次のいずれかでは 2 番目を提示してはならない**。提示すると、選んだ結果が利用者の意図と食い違う。

| 条件                            | 提示しない理由                                                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `stale_staged_paths` が空でない | 作業ツリーの最新ではなく古い内容が commit される——Phase 2 が防いでいる事故そのものである                                 |
| `staged_paths` が空             | ステージされたものが無く、そのまま進んでも commit する対象がゼロになる。**選べるが何も起きない選択肢は、選択肢ではない** |

`stale_staged_paths` が空でない場合は、1 番目の選択肢の説明に「ステージし直して最新の内容にする」ことを明記する（`git add -u` は現在の内容で index を更新するため、これで解消する）。

未追跡ファイル（`untracked_paths`）がある場合は AskUserQuestion を使用して個別にステージするか確認する（`git add -u` の対象外であるため上記の選択とは別に問う）。ステージするものは `python3 "${CLAUDE_SKILL_DIR}/scripts/commit_ops.py" stage --path <パス>`（複数なら `--path` を繰り返す。追跡済みも同時にステージするなら `--tracked` を併せて付ける）で 1 回にまとめて実行する。

`stage` の終了コードが 0 なら、出力 JSON で**現在の状態**を置き換える。それ以外なら `errors` を提示してエラー終了する。

---

## Phase 3: コミットメッセージ生成

Phase 2 でステージ対象が確定した後に生成する。commit されない変更を説明に含めないためである。

### 引数あり

指定されたメッセージをそのまま使用する。

### 引数なし

現在の状態の `staged_diff`（`git diff --cached`。commit される内容）を解析して要約を自動生成する。変更の性質に応じて以下のプレフィックスを使用:

| 変更の性質       | プレフィックス |
| ---------------- | -------------- |
| 新機能追加       | `feat:`        |
| バグ修正         | `fix:`         |
| リファクタリング | `refactor:`    |
| 文書変更         | `docs:`        |
| その他           | `chore:`       |

---

## Phase 3.5: 保護ブランチチェック [MANDATORY]

保護ブランチへの直接 commit を未然に防ぐ。

### 3.5.1 現在のブランチと保護ブランチ

現在の状態の `branch` / `is_protected` を使う。保護ブランチは `develop` / `main` / `master` のすべてである（`create-pr` と同じ。script が判定済み）。

### 3.5.2 `is_protected` が `true` の場合

`AskUserQuestion` で警告し、対応を確認する:

```
現在のブランチ (<current-branch>) は保護ブランチです。直接 commit せず feature ブランチを作成することを推奨します。

提案する feature ブランチ名: feature/<Phase 3 で生成したコミットメッセージから推定したスラッグ>
```

- **feature ブランチを作成して続行**（デフォルト）→ 提案したブランチ名を `AskUserQuestion` で承認・修正させた上で `python3 "${CLAUDE_SKILL_DIR}/scripts/commit_ops.py" new-branch --name <branch>` を実行し、Phase 4 へ進む（失敗したら `errors` を提示して確認する）
- **このまま保護ブランチに commit する（非推奨）** → 警告を出したまま Phase 4 へ進む
- **キャンセル** → 終了（commit しない）

ブランチ名の推定は AI が Phase 3 で生成したコミットメッセージ（`fix(anvil): ...` 等）の要約部分を英語スラッグ化して `feature/` を前置する（例: `fix(anvil): create-pr の CI 待機の打ち切り条件を明確化` → `feature/anvil-clarify-ci-wait-cutoff`）。

### 3.5.3 `is_protected` が `false` の場合

そのまま Phase 4 へ進む（確認不要）。

---

## Phase 4: コミット確認

以下の内容を表示した上で、AskUserQuestion を使用してコミットの承認を得る:

```
ブランチ: <current-branch>
メッセージ: <生成したコミットメッセージ>
対象ファイル: <ステージング済みファイル一覧>
```

- **コミットする** → 次を実行する:
  1. `Write` ツールで、コミットメッセージをそのまま `<message-file>` に書く（シェルで書き出さない）
  2. `python3 "${CLAUDE_SKILL_DIR}/scripts/commit_ops.py" commit --message-file "<message-file>"` を実行する。終了コード 0 なら script が `<message-file>` を削除している
- **キャンセル** → 終了（push は行わない）

コミット失敗（pre-commit hook によるエラー等。終了コード 0 以外）の場合は、AskUserQuestion を使用して `errors` を提示し対応を確認する。`<message-file>` は残っているので、再試行ではそのまま使う。

---

## Phase 5: プッシュ確認

コミット成功後、AskUserQuestion を使用してプッシュの承認を得る:

- **push しない（デフォルト）** → push せずに終了
- **push する** → `python3 "${CLAUDE_SKILL_DIR}/scripts/commit_ops.py" push --branch <current-branch>` を実行する（script が追跡設定の有無で `git push` と `git push -u origin` を使い分ける）

push 失敗（終了コード 0 以外）の場合は AskUserQuestion を使用して `errors` を提示し対応を確認する。

`branch` が `null`（detached HEAD）の場合は push の選択肢を出さず、push できない旨を伝えて終了する。

---

## Phase 6: PR 作成の案内

コミット成功後、push の選択に関わらず、コミットした変更が Issue の修正だと分かるとき（ブランチ名・コミットメッセージ・会話に Issue 番号があるとき）は、終了前に次の注意を表示する:

```
この変更は Issue #<N> の修正です。PR を作成し、本文に `Closes #<N>` を書いてください（/anvil:create-pr）。
PR を経由せずにマージすると、Issue が閉じないまま残ることがあります。
```

Issue 番号が分からないときは表示しない。PR の作成はこのスキルで行わない。

---

## エラーハンドリング

| エラー        | 対応                                                                   |
| ------------- | ---------------------------------------------------------------------- |
| 変更なし      | エラー終了・変更を促す                                                 |
| script が失敗 | `errors` を提示する（各 Phase の記述に従う）                           |
| detached HEAD | `branch` が `null` → ブランチ名なしで commit まで続行し、push はしない |
| コミット失敗  | AskUserQuestion でエラー内容を提示し対応を確認                         |
| push 失敗     | AskUserQuestion でエラー内容を提示し対応を確認                         |
