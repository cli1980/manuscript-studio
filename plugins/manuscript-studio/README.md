# Manuscript Studio

An installable skills-only plugin for ChatGPT Work and Codex.

## Included skills

- Prepare Manuscript
- Literary Editing
- Literary Translation
- Literary Agent Querying
- Interior Design
- Review Approval Sheet

The plugin does not include an MCP server or its own service connection.
Skills use files and host tools made available by the active product surface;
query research may use that host's browser/search tools.

See [runtime support and fallback examples](RUNTIME-SUPPORT.md), the
[privacy policy](PRIVACY.md), and [support contact](SUPPORT.md) before use.
Interior design returns a structured proposal; it does not generate documents.
It needs verified preparation but no Documents skill or office renderer.
Invoke it standalone or as a reusable component; no workflow run is required.
Interactive approval sheets require the particular Codex inline visualization
surface; other hosts use validated, revision-bound text decisions.

All manuscript workflows reuse the
[shared metadata contract](skills/prepare-manuscript/references/manuscript-metadata.md).
Preparation extracts explicit metadata and infers missing descriptive fields from
the text with evidence and confidence. Values remain editable; subsequent
enrichment preserves supplied values and user corrections.

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
interior design, or an interactive literary approval review.
