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

| Argument      | Description                                                                              |
| ------------- | ---------------------------------------------------------------------------------------- |
| `base-branch` | Base branch (omit to auto-detect from `.git_information.yaml` > develop > main > master) |

### create-issue

```
/anvil:create-issue [issue-title]
```

| Argument      | Description                                            |
| ------------- | ------------------------------------------------------ |
| `issue-title` | Hint for the Issue title (omit to settle it in dialog) |

Pick the Issue kind (Bug Report / Feature Request), answer the required sections for that kind interactively, then the Issue is filed.

## Requirements

- [gh CLI](https://cli.github.com/) (authenticated)
