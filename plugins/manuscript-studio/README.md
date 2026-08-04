# Manuscript Studio

An installable skills-only plugin for ChatGPT Work and Codex.

## Included skills

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

## Use

Invoke the plugin or a bundled skill explicitly, or ask directly for literary
editing, literary translation, agent research, a query package, manuscript
formatting, or an interactive approval review.
