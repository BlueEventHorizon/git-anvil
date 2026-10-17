# git-anvil

[![License MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A marketplace that ships **anvil**, a Claude Code plugin for GitHub operations: auto-generated commit messages, draft pull requests, and interactive issue creation.

**Marketplace version: 0.1.0**

[Japanese README (README.md)](README.md)

## Plugins

| Plugin    | Version | Description                                                                          |
| --------- | ------- | ------------------------------------------------------------------------------------ |
| **anvil** | 0.1.0   | GitHub operations toolkit. Create PRs, manage issues, and automate GitHub workflows. |

## Skills

> [Detailed Guide](docs/readme/guide_anvil.md) — Usage and examples

| Skill                                                       | Description                                                                                         | Trigger          |
| ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ---------------- |
| [**commit**](docs/readme/guide_anvil.md#commit)             | Generate commit message from changes, commit & push                                                 | `"commit"`       |
| [**create-pr**](docs/readme/guide_anvil.md#create-pr)       | Create a GitHub draft PR with auto-generated title/body                                             | `"create-pr"`    |
| [**create-issue**](docs/readme/guide_anvil.md#create-issue) | Pick Bug Report or Feature Request, collect the required sections interactively, and file the Issue | `"create issue"` |

## Installation

### Option A: Marketplace (persistent)

Inside a Claude Code session:

```
/plugin marketplace add BlueEventHorizon/git-anvil
/plugin install anvil@git-anvil
/reload-plugins
```

On Claude Code v2.1.275+, `/plugin install anvil --marketplace BlueEventHorizon/git-anvil` does the same in one command (Claude Code asks to confirm before adding the marketplace).

`/plugin install` installs to **user scope** by default, making the plugin available in every project. To choose a scope, open the **Discover** tab in `/plugin` and press Enter on the plugin, or pass `--scope` from your terminal:

```bash
claude plugin install anvil@git-anvil --scope user     # all your projects (default)
claude plugin install anvil@git-anvil --scope project  # everyone on this repo
claude plugin install anvil@git-anvil --scope local    # only you, only this repo
```

| Scope              | Applies to                     | Stored in                     | Shared via git  |
| ------------------ | ------------------------------ | ----------------------------- | --------------- |
| **user** (default) | yourself, across all projects  | `~/.claude/settings.json`     | no              |
| **project**        | all collaborators on this repo | `.claude/settings.json`       | enablement only |
| **local**          | yourself, in this repo only    | `.claude/settings.local.json` | no              |

> **Project scope note**: the committed `.claude/settings.json` shares only the enablement, not the plugin itself. Each collaborator still runs `claude plugin install anvil@git-anvil --scope project` once on their own machine.

To disable the plugin in a specific project, run `/plugin disable anvil@git-anvil`. To re-enable it, run `claude plugin enable anvil@git-anvil` from your terminal.

### Option B: Local directory (per session)

```bash
git clone https://github.com/BlueEventHorizon/git-anvil.git
claude --plugin-dir ./git-anvil/anvil
```

> **Note**: `--plugin-dir` is session-only. You must specify it every time you start Claude Code.

### Update

From your terminal (use the scope you installed with):

```bash
claude plugin update anvil@git-anvil --scope user
```

## Git Information Cache (.git_information.yaml)

On first run, `/anvil:create-pr` detects your GitHub repo from `git remote` and offers to save the settings to `.git_information.yaml` for future use.

## Requirements

- [Claude Code](https://claude.ai/code) CLI
- Python 3.14 or later (for the bundled Python scripts; 3.13 and earlier are not supported)
- [gh CLI](https://cli.github.com/) (authenticated)

## License

[MIT](LICENSE)
