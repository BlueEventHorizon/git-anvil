# anvil Detailed Guide

GitHub operations toolkit. Auto-generate commit messages, create draft PRs, and file issues.

## Skill Details

### commit

```
/anvil:commit [message]
```

| Argument  | Description                                            |
| --------- | ------------------------------------------------------ |
| `message` | Commit message (omit for auto-generation from changes) |

### create-pr

```
/anvil:create-pr [base-branch]
```

| Argument      | Description                                                         |
| ------------- | ------------------------------------------------------------------- |
| `base-branch` | Base branch (omit to auto-detect in order: develop > main > master) |

### create-issue

```
/anvil:create-issue [--repo <owner>/<repo>] [issue-title]
```

| Argument      | Description                                                               |
| ------------- | ------------------------------------------------------------------------- |
| `--repo`      | Target repository (`[HOST/]OWNER/REPO`; omit to use the current `origin`) |
| `issue-title` | Hint for the Issue title (omit to settle it in dialog)                    |

Pick the Issue kind (Bug Report / Feature Request), answer the required sections for that kind interactively, then the Issue is filed.

When `--repo` points to a repository other than the current `origin`, the skill asks for confirmation before collecting the Issue content. The preview before filing always shows the target repository.

## Requirements

- [gh CLI](https://cli.github.com/) (authenticated)
