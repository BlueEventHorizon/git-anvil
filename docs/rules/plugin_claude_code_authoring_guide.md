# Claude Code 作成ガイド（SKILL / カスタム Agent）

SKILL とカスタム Agent を組み合わせてプラグインを組むときの、特定のプロジェクトに依らない規約。個別の SKILL の作り方（frontmatter・description・引数・ファイル構成・命名）は、meta プラグインの `author-skill` に従う。依拠する仕組みの事実と、ここで使う語彙は [Claude Code リファレンス][reference] が持つ。プロジェクト固有の採否は、プロジェクトの方針文書が持つ。

## 名称

- 起動経路は、リファレンスの短縮名称（継承型 SKILL / fork 型 SKILL / 汎用 Agent / カスタム Agent / Bash subprocess）で書く。番号（`#3a` 等）だけで参照しない
- 「subagent」を単独で使わない。fork 型 SKILL / 汎用 Agent / カスタム Agent のどれかで書くか、具体名で書く
- `subagent_type` には組み込み Agent 名か定義済みのカスタム Agent 名だけを書く。prompt に slash 表記（`/<plugin>:<skill>`）を書かない

## 起動経路

- 隔離 context が要る処理はカスタム Agent（`agents/<name>.md`）にし、Agent ツールで `<plugin>:<name>` として起動する。fork 型 SKILL（`context: fork` / `agent`）は、リファレンスの「`context: fork` の不具合」のとおり、既定で避ける
- カスタム Agent にするのは、同じロールを複数の呼び出し元から別 context で使うとき、書き込みの境界を常時拘束したいとき、親 context が肥大するとき

### 起動経路の選び方

上から順に判定し、最初に当てはまるものを選ぶ。

1. 決定論的に完結する処理（コマンドライン引数と exit code / stdout で済む） → Bash subprocess
2. 手順を呼び出し元がその場で組み立てる、一回限りの委譲 → 汎用 Agent
3. 隔離 context が要る、事前に定義したロール → カスタム Agent
4. それ以外（手順が安定し、親 context を活かす） → 継承型 SKILL

### 継承型 SKILL

- `$ARGUMENTS` に親 context を貼らない。args は最小限のパラメータだけ。Issue 本文・進行中の手順・差分・ファイル全文・「その後〜して」という指示を貼らない（カスタム Agent に渡す prompt も同じ）

### カスタム Agent

- frontmatter に `name` / `description` / `tools` / `model` を書く
- 禁止事項（他 Agent の起動 / 親タスクの引き継ぎ / allowlist 外への書き込み）を否定形で書き、起動 prompt を親の指示として解釈しないことを書く
- 書き込む Agent には、対象の限定・無関係な refactor の禁止・修正後の構文検証を常時課す。編集可能ファイルの allowlist は、課すことを推奨する

### 多重防御

| 層            | 実現方法                                      | カスタム Agent | 継承型 SKILL   |
| ------------- | --------------------------------------------- | -------------- | -------------- |
| A. Agent 境界 | Agent ツールで起動し親 context を遮断         | 必須           | 該当なし       |
| B. Role 制約  | system prompt / SKILL.md に否定形で書く       | 必須           | 必須           |
| C. allowlist  | `tools:` / `allowed-tools:`                   | 必須           | 推奨           |
| D. 物理 deny  | `.claude/settings.json` の `permissions.deny` | プロジェクト側 | プロジェクト側 |

## 別スキルの呼び出し [MANDATORY]

- Claude への指示として書き、Skill ツールで起動させる
- 自身を Skill ツールで呼ばない・「`/<self-skill>` を実行します」と書かない（無限ループになる）。作業着手前に毎回呼ばれる SKILL や、多くの起点になる SKILL は、この禁止を冒頭に明記する（meta の `author-skill`「No Self-Invocation」）

## Agent の完了の待ち方 [MANDATORY]

- 完了を `ScheduleWakeup` で待たない。ターンを終えて完了通知を待つ（待ち方の書き方は、meta の `author-skill` が持つ）

[reference]: plugin_claude_code_reference.md
