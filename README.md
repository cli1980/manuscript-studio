# Manuscript Studio

**Manuscript Studio** is a collection of independent AI-agent skills for literary writing, translation, editing, and publication preparation.

The project is designed to keep authors and translators focused on ideas, voice, and story instead of repeatedly searching dictionaries and thesauruses, debating commas and colons, revisiting grammar books, or hunting for typos. It provides structured, reviewable workflows that help AI agents streamline the path from manuscript development through translation, editing, and querying—without taking creative authority away from the author.

## Install as a ChatGPT and Codex plugin

The six skills live in one canonical directory, `plugins/manuscript-studio/skills/`.
The skills-only `manuscript-studio` plugin uses these files directly; the standalone
installer copies from the same source. Add this GitHub repository as a marketplace:

```text
codex plugin marketplace add cli1980/manuscript-studio --ref main
```

Then open the Plugins Directory on a supported ChatGPT desktop or Codex surface,
select the `Manuscript Studio` marketplace, and install `manuscript-studio`.
Start a new conversation after installation. Local/Git marketplace availability
varies by product and workspace; adding this marketplace does not by itself
publish the plugin to the public directory or install it in ChatGPT web.

Existing installations do not automatically migrate because the marketplace
and plugin IDs changed. Uninstall `quillholic-literary-suite`, add the renamed
marketplace if necessary, and install `manuscript-studio`.

## Install standalone skills for Codex

Clone or download this repository and use Python 3.10 or newer. No third-party
Python packages, administrator privileges, or symlinks are required. From the
repository root, list the skills and preview installation:

```text
python scripts/install_skills.py --list
python scripts/install_skills.py --dry-run
```

Install all six skills into `~/.agents/skills/`:

```text
python scripts/install_skills.py
```

Or install selected skills:

```text
python scripts/install_skills.py literary-editing literary-agent-querying
```

Editing, translation, querying, and formatting also install the shared
`prepare-manuscript` and `review-approval-sheet` skills to preserve sibling references. Complete skill
folders are copied, including references, scripts, tests, agent metadata, and
assets; Python bytecode and cache directories are excluded.

Use `--dest` for another skill directory, such as a manuscript project's
`.agents/skills/` folder outside this source repository:

```text
python scripts/install_skills.py --dest "C:/Manuscripts/My Novel/.agents/skills" literary-editing
```

On Windows, `py -3` can replace `python`. The installer also works from another
working directory when invoked by its full path. Codex should discover the
installed skills automatically; restart it if they do not appear. Choose either
standalone installation or the plugin for the same skills in a given environment
to avoid duplicate skill entries. This script does not install into ChatGPT web.

### Updates and existing installations

After updating your repository checkout, preview and explicitly authorize an update:

```text
python scripts/install_skills.py --update --dry-run
python scripts/install_skills.py --update
```

Use the same `--dest` and skill selection as the original installation when applicable.
The installer performs no downloads and does not update Git or agent configuration.

- Reinstalling identical, managed skills is a no-op.
- Updates require `--update` and a valid `.manuscript-studio-install.json` receipt
  inside each installed skill. Hashes detect edited, added, or deleted files.
- Unmanaged or locally modified installations are never overwritten, even with
  `--update`. Preserve any local work and move the conflicting skill directory
  outside the discovery directory before reinstalling.
- Each clean update retains the previous directory in
  `<destination-parent>/.manuscript-studio-backups/`, outside the skills discovery
  directory. The installer prints its exact location and does not prune backups.
- Sources and destinations containing symlinks or Windows reparse points are
  rejected. Installing into or over this source repository is also rejected.
- The full selection is preflighted before installation. Replacements are staged
  and recover the old directory if publishing fails, but a multi-skill install is
  not one transaction. If interrupted, inspect the installed skills and retained
  backups before retrying. Remove a stale `.manuscript-studio-install.lock` from
  the destination only after confirming no installer is running.

## Getting started

For automatic skill discovery, use a supported installation method above. For
manual instruction-based use, point the agent to a skill's `SKILL.md` under
`plugins/manuscript-studio/skills/` and make its referenced resources available.
Reading a GitHub page alone does not install a skill or provide a script runtime.

Choose the working style that matches your AI environment.

### Chat-based use

This option is for browser-based AI chat services.

1. Create a project in the chat service.
2. Link or upload your manuscript to that project.
3. Select an installed **Manuscript Studio** skill when your product supports it. Otherwise upload the relevant skill instructions and supporting resources, or ask the agent to read them from this repository. Confirm that the required files and execution tools are available before starting a script-backed workflow.

The agent will use project files and chat output artifacts as its workspace. Because a web chat may not have Git or direct filesystem access, some version-control features will be unavailable. In that case, the agent will not modify the manuscript source directly: it will return the revised source for you to review and apply manually.

### App-based use

This option is for desktop apps with local file access, such as the ChatGPT app, Codex app, or Claude app.

Create or select two separate local folders:

```text
Manuscripts/   Your authoritative manuscript source
Workspace/     Editorial notes, analyses, decision tables, and other working files
```

Give the app access to both folders, then ask the agent to use a skill by name or point it to the repository. Keeping source and workspace separate protects the manuscript and lets every skill follow the same workflow.

Git is optional but recommended. When Git is available, the agent can maintain the manuscript and workspace as separate repositories and commit approved changes. Without Git, the same folder structure still works, but the agent should return an updated manuscript for you to apply manually rather than changing the source.

## Included skills

### `prepare-manuscript`

Discovers manuscripts only within a designated source location, verifies the
requested scope, and produces a neutral, versioned package of chapter-based UTF-8
Markdown. A shared `work.json` records work metadata, preparation readiness, and
separate downstream status summaries; revision manifests bind chapter order,
source locators, extraction quality, and file hashes. Editing and translation
delegate preparation to this skill. Formatting and querying can consume the same
contract while retaining their own source and approval rules.

The machine-readable schemas and validator are included in the skill. Install
its `requirements.txt` to run `scripts/validate_preparation.py <work-root>/work.json`;
use `--check-sources` to verify accessible local originals as well.

### `literary-editing`

Runs manuscript assessment, developmental editing, line editing, copyediting, specialist review, proofreading, and final QA. It keeps the manuscript source separate from the editorial workspace, presents proposed changes for approval, and applies only decisions the author accepts.

### `literary-translation`

Translates literary works chapter by chapter using source analysis, a living glossary, systematic passage division, alternative drafts, and source-grounded review. Its goal is natural literary English that preserves the source's meaning, voice, rhythm, and reader experience.

### `literary-agent-querying`

Reads and positions a novel, builds a synopsis-complete story ledger, researches and prioritizes suitable literary agents, and prepares reusable query materials. Existing approved artifacts are reused by default. Only an explicit request to build a package for a specific agent creates an on-demand ZIP, including a synopsis only when that agent's verified guidelines request one.

### `format-manuscript`

Inspects a project draft, recommends and confirms a reusable genre- and purpose-appropriate formatting specification, then orchestrates production of a polished manuscript edition without changing the prose. Its current primary path produces visually verified Word manuscripts with semantic styles and an accurate table of contents while keeping the specification reusable for future PDF and EPUB adapters.

### `review-approval-sheet`

Provides a shared interactive review interface for stable-ID approval sheets. It validates revision-bound state, presents compact navigation and item-specific decisions, parses explicit submissions, and preserves each literary skill's own authoritative records, domain rules, and separate action gates.

## Workflow prototype

The [workflow CLI](workflow/README.md) provides an initial orchestration implementation:
verified preparation, translation with source-grounded review and human gates,
explicit artifact acceptance, and Markdown export. It persists run state and review
receipts in SQLite and uses a Codex App Server adapter. General line editing is not
part of the default translation flow.

This prototype is separate from the distributed skills plugin. See its README for
setup, tests, recovery, and current limits, and the
[architecture](workflow/docs/architecture.md) for the planned web application.

## Development and verification

Edit skill content only under `plugins/manuscript-studio/skills/`. The plugin and
standalone installer use that same directory; do not recreate top-level skill
copies. When introducing a sibling-skill dependency, update the installer's
`DEPENDENCIES` mapping and its tests.

Run the existing dependency-free Python regression suites from the repository root:

```text
python -B scripts/test_install_skills.py
python -B plugins/manuscript-studio/skills/literary-agent-querying/scripts/test_sample_boundary.py
python -B plugins/manuscript-studio/skills/literary-agent-querying/scripts/test_validate_on_demand.py
python -B plugins/manuscript-studio/skills/review-approval-sheet/scripts/test_approval_review.py
```

The preparation schema validator uses `jsonschema`. In your Python environment:

```text
python -m pip install -r plugins/manuscript-studio/skills/prepare-manuscript/requirements.txt
python -B plugins/manuscript-studio/skills/prepare-manuscript/scripts/test_validate_preparation.py
```

Installer tests use temporary destinations, not your personal skill directory.
Real symlink tests skip when the OS does not permit link creation; simulated link
and Windows reparse-point checks still run. To also check the rendered approval
interface's JavaScript syntax, set `NODE_BINARY` to an available Node.js executable
before running the approval-review suite.

Agent workflow evaluations live in [`evals/`](evals/README.md), outside the
distributed skill directories. The [ground-truth review server](evals/server/README.md)
provides a judge-only translation review interface for scores, comments, and
issue annotations, with temporary shared-key access. Passages, translations,
and case metadata are read-only. Cases, shared fixtures, rubrics, and ignored
run results remain separate from distributed skills. The
[blind translation-judge runner](evals/README.md#run-the-translation-judge) can
export human-labeled training examples, compare blind model predictions with
human judgments, or judge new translated outputs without human references.
Fine-tuning job execution and automatic dataset splitting are not implemented.

Server edits are staged in a temporary workspace. Use **Submit changes** to
publish judgment records to the original evaluation files; unsubmitted edits are discarded
when the server restarts.

## The idea behind the project

Fear alone is not a good reason for authors, translators, editors, or publishing professionals to resist AI. AI agents do not replace the author's idea, experience, taste, or judgment; they provide skills and perform structured work under direction.

The creative advantage still belongs to the person with an exceptional idea and the ability to recognize what serves it. Authors who combine that vision with skillful use of AI can spend less time on mechanical friction and more time making consequential creative decisions. This project is built on the belief that such collaboration will become a normal part of literary work—and that writers who learn to direct it thoughtfully will stand out.

## License

See [LICENSE](LICENSE).
