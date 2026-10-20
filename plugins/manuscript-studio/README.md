# Manuscript Studio

An installable skills-only plugin for ChatGPT Work and Codex.

## Included skills

- Prepare Manuscript
- Literary Editing
- Literary Translation
- Literary Agent Querying
- Format Manuscript
- Review Approval Sheet

The plugin does not include an MCP server or request access to external
services. Each skill operates on files, attachments, project workspaces, or
Codex artifacts made available by the active product surface.

## Install from GitHub

Add the repository marketplace:

```text
codex plugin marketplace add cli1980/manuscript-studio --ref main
```

Then install `manuscript-studio` from the Manuscript Studio marketplace in
the ChatGPT desktop Plugins Directory or the Codex CLI plugin browser. Start a
new conversation after installation so the bundled skills are available.

If you previously installed `quillholic-literary-suite`, uninstall that plugin
and install `manuscript-studio`; the new name is a new plugin identity.

## Standalone use and maintenance

The `skills/` directory is the canonical source for both plugin and standalone
use. Edit skills here; do not maintain another source copy at the repository root.
From a checkout's repository root, run `python scripts/install_skills.py --dry-run`
and then `python scripts/install_skills.py` to install standalone copies for local
Codex. See the [standalone installation and update instructions](../../README.md#install-standalone-skills-for-codex).
The installer copies the same resources that the plugin packages and does not
install into ChatGPT web. Local/Git marketplace support varies by surface and
workspace; it is separate from publishing to the public plugin directory.

## Use

Invoke the plugin or a bundled skill explicitly, or ask directly for manuscript preparation, literary
editing, literary translation, agent research, a query package, manuscript
formatting, or an interactive approval review.
