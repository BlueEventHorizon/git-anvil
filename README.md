# git-anvil

[![License MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A marketplace that ships **anvil**, a Claude Code plugin for GitHub operations: auto-generated commit messages, draft pull requests, and interactive issue creation.

**Marketplace version: 0.1.1**

English | [日本語](README.ja.md)

## Plugins

| Plugin    | Version | Description                                                                          |
| --------- | ------- | ------------------------------------------------------------------------------------ |
| **anvil** | 0.1.1   | GitHub operations toolkit. Create PRs, manage issues, and automate GitHub workflows. |

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

In a session, `/plugin install` opens the plugin's details in the `/plugin` panel, where you pick User / Project / Local (you can also open the **Discover** tab in `/plugin` and press Enter on the plugin). From your terminal, `claude plugin install` installs to **user scope** (available in every project) unless you pass `--scope`:

```bash
claude plugin install anvil@git-anvil --scope user     # all your projects (terminal default)
claude plugin install anvil@git-anvil --scope project  # everyone on this repo
claude plugin install anvil@git-anvil --scope local    # only you, only this repo
```

| Scope                       | Applies to                     | Stored in                     | Shared via git  |
| --------------------------- | ------------------------------ | ----------------------------- | --------------- |
| **user** (terminal default) | yourself, across all projects  | `~/.claude/settings.json`     | no              |
| **project**                 | all collaborators on this repo | `.claude/settings.json`       | enablement only |
| **local**                   | yourself, in this repo only    | `.claude/settings.local.json` | no              |

> **Project scope note**: the committed `.claude/settings.json` shares only the enablement, not the plugin itself. Each collaborator still runs `claude plugin install anvil@git-anvil --scope project` once on their own machine.

> **Note**: a plugin that is already installed cannot be reinstalled at a different scope. To change the scope, uninstall it first and then install it again.

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

## Requirements

- [Claude Code](https://claude.ai/code) CLI
- Python 3.14 or later (for the bundled Python scripts; 3.13 and earlier are not supported)
- [gh CLI](https://cli.github.com/) (authenticated)

## License

[MIT](LICENSE)
