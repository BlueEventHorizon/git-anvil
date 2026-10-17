# anvil 詳細ガイド

GitHub 操作ツールキット。コミットメッセージ自動生成、PR ドラフト作成、Issue 起票に対応。

## スキル詳細

### commit

```
/anvil:commit [message]
```

| 引数      | 説明                                               |
| --------- | -------------------------------------------------- |
| `message` | コミットメッセージ（省略時は変更内容から自動生成） |

### create-pr

```
/anvil:create-pr [base-branch]
```

| 引数          | 説明                                                                                    |
| ------------- | --------------------------------------------------------------------------------------- |
| `base-branch` | ベースブランチ（省略時は `.git_information.yaml` > develop > main > master の順で決定） |

### create-issue

```
/anvil:create-issue [issue-title]
```

| 引数          | 説明                                             |
| ------------- | ------------------------------------------------ |
| `issue-title` | Issue タイトルのヒント（省略時は対話で確定する） |

Issue 種別（Bug Report / Feature Request）を選び、種別ごとの必須セクションを対話で収集してから起票する。

## 動作要件

- [gh CLI](https://cli.github.com/)（認証済み）
