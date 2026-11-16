# Claude Code リファレンス（SKILL / プラグイン / Agent）

SKILL と Agent を組み合わせてプラグインを組むときに依拠する、Claude Code の仕組みの事実と、この文書群が定める語彙を集める。特定のプロジェクトに依らない。個別の SKILL の作り方（frontmatter・description・引数・ファイル構成・命名、`allowed-tools` / `disallowed-tools` の効く範囲、Agent の起動方式の判定と完了の待ち方）は、meta プラグインの `author-skill` に従う。規約は [Claude Code 作成ガイド][authoring-guide] が持つ。

## 出典の記し方

- Claude Code の挙動には `出典:` 行を付ける（調査日 / 版 / 出典）。この文書群が定める語彙には付けない
- 出典は「公式」（URL と原文の引用。claude-code-guide Agent の WebFetch 経由で、逐語一致は保証されない）、「観測」、「公式 Issue」のいずれか
- 記録の無い調査日は「不明（初出 commit の日付）」、確かめられない事項は「確認できず」と書く
- 事実が変わったら書き換え、旧い記述を残さない

## 1. 起動経路 5 種と短縮名称

分類と短縮名称は、この文書群が定める語彙。各経路の挙動は Claude Code の挙動。

| 短縮名称            | 起動                                                                      | 手順書                              | 親 context | 出力               |
| ------------------- | ------------------------------------------------------------------------- | ----------------------------------- | ---------- | ------------------ |
| **継承型 SKILL**    | Skill ツール（`context:` 未指定）                                         | SKILL.md（親が直接 Read）           | 継承       | 親 context に展開  |
| **fork 型 SKILL**   | Skill ツール（`context: fork`）                                           | SKILL.md（隔離 context が Read）    | 遮断       | return 値のみ      |
| **汎用 Agent**      | Agent ツール（組み込み Agent。`general-purpose` / `Explore` / `Plan` 等） | 呼び出し元の prompt                 | 遮断       | 完了通知 + 出力    |
| **カスタム Agent**  | Agent ツール（`<plugin>:<name>`）                                         | `agents/<name>.md` の system prompt | 遮断       | 完了通知 + 出力    |
| **Bash subprocess** | Bash で外部プロセス起動                                                   | なし                                | 遮断       | exit code + stdout |

- 出典（fork 型）: 2026-09-26 / 2.1.283 / 公式 [Skills](https://code.claude.com/docs/en/skills)「Subagent doesn't see conversation history. Runs in background by default」
- 出典（それ以外）: 不明（初出 commit の日付: 2026-07-27） / 不明 / 確認できず

### `context: fork` の不具合

fork 型 SKILL を採用しない（または避ける）根拠。Anthropic の対応は issue の扱い（修正済み / 直さない / 未対応）。

| 公式 Issue | 内容                                                                               | Anthropic の対応                                           |
| ---------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| #18394     | `context: fork` が効かず、既存 context でそのまま実行される                        | 重複として閉じた。同じ症状の #16803 は v2.1.101 で修正済み |
| #34164     | fork 型 SKILL を別 SKILL から起動すると `$ARGUMENTS` が置換されない                | 直さない（not planned）                                    |
| #60720     | fork 型 SKILL の出力が Desktop の UI に届かない                                    | 直さない（not planned）                                    |
| #55592     | fork 型 SKILL が無限再帰する                                                       | 修正済み（v2.1.145）                                       |
| #34328     | fork 型 SKILL を起動しても subagent が立たない                                     | 直さない（not planned）                                    |
| #19751     | fork 型 SKILL の中で AskUserQuestion が機能しない                                  | 重複として閉じた。個別の対応は無い                         |
| #17283     | Skill ツール経由の起動で `context: fork` / `agent:` が無視される                   | 対応済み                                                   |
| #17351     | 入れ子の SKILL が、呼び出し元ではなく main context に戻る                          | 未対応（OPEN）                                             |
| #68233     | 再帰ガードが誤爆し、正当な fork の起動を止める（Agent ツールの `fork` 種別も対象） | 直さない（not planned）                                    |

- 出典: 2026-10-25 / 不明 / 公式 Issue anthropics/claude-code（`gh issue view` で状態を取得）。修正された版は meta の `author-skill` の記録（検証日 2026-09-28）による

## 2. `subagent_type` の値域

- 指定できるのは組み込み Agent 名（`general-purpose` / `Explore` / `Plan` / `claude` / `statusline-setup` / `claude-code-guide`）と、定義済みのカスタム Agent 名だけ
- プラグインの Agent は `<plugin>:<name>` の名前空間を持つ
- SKILL 名・slash 表記（`/<plugin>:<skill>`）・ファイルパスは無効

- 出典: 2026-09-26 / 2.1.283 / 公式 [Subagents](https://code.claude.com/docs/en/sub-agents)「four built-in subagents … Other Helper Agents: `claude`, `statusline-setup`, `claude-code-guide`」、[Plugins reference](https://code.claude.com/docs/en/plugins-reference)「an agent `reviewer` in plugin `deploy-tools` appears as `deploy-tools:reviewer`」

## 3. Agent の起動に関する観測

起動方式（foreground / background）の判定は、meta の `author-skill`（`frontmatter_spec.md`）が持つ。ここには、そこに無い観測だけを置く。

- 対話セッションの Agent ツールには `run_in_background` 引数が無く、常に background で動き、結果は後のターンに完了通知で届いた。出典: 2026-09-26 / 2.1.283 / 観測
- background で動いた subagent には AskUserQuestion が無かった。`tools:` に AskUserQuestion を列挙したカスタム Agent でも、`tools:` を省いた `general-purpose` でも同じだった。原因は確認できず。出典: 2026-09-28 / 2.1.283 / 観測
- `ScheduleWakeup` は `/loop` 動的モードの起動予約ツールであり、background 作業の完了はハーネスが通知する。出典: 2026-09-26 / 2.1.283 / 観測（ツール説明「Schedule when to resume work in /loop dynamic mode」）

[authoring-guide]: plugin_claude_code_authoring_guide.md
