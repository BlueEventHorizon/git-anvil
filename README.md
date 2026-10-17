# git-anvil

[![License MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

GitHub 操作のための Claude Code プラグイン **anvil** を配布するマーケットプレイス。コミットメッセージの自動生成、PR のドラフト作成、Issue の起票を対話で行う。

**マーケットプレイスバージョン: 0.1.0**

[English README (README_en.md)](README_en.md)

## プラグイン一覧

| プラグイン | バージョン | 説明                                                                          |
| ---------- | ---------- | ----------------------------------------------------------------------------- |
| **anvil**  | 0.1.0      | GitHub 操作ツールキット。PR 作成、Issue 管理、GitHub ワークフロー自動化に対応 |

## スキル一覧

> [詳細ガイド](docs/readme/guide_anvil_ja.md) — 使い方、使用例

| スキル                                                         | 説明                                                                                              | トリガー         |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------- |
| [**commit**](docs/readme/guide_anvil_ja.md#commit)             | 変更内容からコミットメッセージを自動生成し commit & push                                          | `"コミットして"` |
| [**create-pr**](docs/readme/guide_anvil_ja.md#create-pr)       | GitHub PR をドラフト作成。コミット差分からタイトル/本文を自動生成                                 | `"PR を作成"`    |
| [**create-issue**](docs/readme/guide_anvil_ja.md#create-issue) | Bug Report / Feature Request を選び、種別ごとの必須セクションを対話で収集して GitHub Issue を起票 | `"issue を作成"` |

## インストール

### 方法 A: マーケットプレイス経由（永続）

Claude Code セッション内で:

```
/plugin marketplace add BlueEventHorizon/git-anvil
/plugin install anvil@git-anvil
/reload-plugins
```

Claude Code v2.1.275 以降では、`/plugin install anvil --marketplace BlueEventHorizon/git-anvil` の 1 コマンドでも同じことができる（マーケットプレイスを追加する前に確認を求められる）。

`/plugin install` は既定で **user スコープ**にインストールし、自分の全プロジェクトで使えるようになる。スコープを選ぶには `/plugin` の **Discover** タブでプラグインを選んで Enter を押すか、ターミナルから `--scope` を指定する:

```bash
claude plugin install anvil@git-anvil --scope user     # 自分の全プロジェクトで使う（既定）
claude plugin install anvil@git-anvil --scope project  # このリポのチーム全員で使う
claude plugin install anvil@git-anvil --scope local    # このリポで自分だけ使う
```

| スコープ         | 対象範囲                 | 設定保存先                    | git で共有されるもの |
| ---------------- | ------------------------ | ----------------------------- | -------------------- |
| **user**（既定） | 自分・全プロジェクト     | `~/.claude/settings.json`     | なし                 |
| **project**      | このリポジトリの全員     | `.claude/settings.json`       | 有効化の設定のみ     |
| **local**        | 自分・このリポジトリのみ | `.claude/settings.local.json` | なし                 |

> **project スコープの注意**: git に commit した `.claude/settings.json` で共有されるのは有効化の設定だけで、プラグイン本体は配られない。共同作業者もそれぞれ自分のマシンで `claude plugin install anvil@git-anvil --scope project` を 1 回実行する必要がある。

> **注意**: 同じプラグインをすでにインストール済みの場合、別スコープで再インストールはできない。スコープを変更するには先にアンインストールしてから再インストールする。

特定のプロジェクトで無効化したい場合は `/plugin disable anvil@git-anvil` を実行する。再有効化はターミナルから `claude plugin enable anvil@git-anvil`。

### 方法 B: ローカルディレクトリ（セッション限定）

```bash
git clone https://github.com/BlueEventHorizon/git-anvil.git
claude --plugin-dir ./git-anvil/plugins/anvil
```

> **注意**: `--plugin-dir` はセッション限定。Claude Code を起動するたびに指定が必要。

### 更新

ターミナルから（スコープはインストール時に選択したものを指定）:

```bash
claude plugin update anvil@git-anvil --scope user
```

## Git 情報キャッシュ (.git_information.yaml)

`/anvil:create-pr` の初回実行時に `git remote` から GitHub リポジトリを検出し、`.git_information.yaml` への設定保存を提案する。

## 動作要件

- [Claude Code](https://claude.ai/code) CLI
- Python 3.14 以上（Python スクリプト実行用。Python 3.13 以下はサポート対象外）
- [gh CLI](https://cli.github.com/)（認証済み）

## ライセンス

[MIT](LICENSE)
