# Manuscript Studio

**Manuscript Studio** is a collection of independent AI-agent skills for literary writing, translation, editing, and publication preparation.

The project is designed to keep authors and translators focused on ideas, voice, and story instead of repeatedly searching dictionaries and thesauruses, debating commas and colons, revisiting grammar books, or hunting for typos. It provides structured, reviewable workflows that help AI agents streamline the path from manuscript development through translation, editing, and querying—without taking creative authority away from the author.

## Formatter Tool Submodule

[Book Formatter](https://github.com/cli1980/book-formatter) is an independent
repository, checked out here as the pinned `tools/formattor` submodule.
Its [design and gap-analysis index](https://github.com/cli1980/book-formatter/blob/237be7d034b57f7a77fd0b7e9cd0ecb03a27d05c/README.md)
is authoritative for the formatter. The current content is documentation;
executable API/CLI packaging and generator integration remain pending.

For an existing checkout:

```text
git submodule update --init --recursive tools/formattor
```

For a new checkout, use `git clone --recurse-submodules`. Submodule update uses
the parent repository's pinned commit, not automatically the latest `main`.
Skills-only plugin installation does not require the formatter checkout.

## Install as a ChatGPT and Codex plugin

The seven skills live in one canonical directory, `plugins/manuscript-studio/skills/`.
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

Before use, read the plugin's [privacy policy](plugins/manuscript-studio/PRIVACY.md),
[support contact](plugins/manuscript-studio/SUPPORT.md), and
[runtime support and fallback examples](plugins/manuscript-studio/RUNTIME-SUPPORT.md).
The separately installed standalone formatter supplies the bounded DOCX-only
workflow POC; it does not require Word or a renderer. PDF/rendering is deferred.
Interactive reviews depend on the host's inline visualization support, with
revision-bound text fallback when it is unavailable.

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

Install all seven skills into `~/.agents/skills/`:

```text
python scripts/install_skills.py
```

Or install selected skills:

```text
python scripts/install_skills.py literary-editing literary-agent-querying
```

Editing, translation and analysis install shared preparation and review skills.
Querying installs `manuscript-analysis` and its transitive dependencies;
interior design installs preparation. These dependencies preserve sibling references. Complete skill
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

Shared metadata now includes title/subtitle, credited contributors and roles,
original and manuscript languages, type/form, genres, audience, keywords,
description, edition, series, and revision-scoped extent. Preparation infers missing
descriptive values from textual evidence and records confidence and provenance;
supplied values and user edits take precedence. All fields remain editable.
See the [shared metadata contract](plugins/manuscript-studio/skills/prepare-manuscript/references/manuscript-metadata.md)
for the structure, proposal format, and editing commands.

The machine-readable schemas and validator are included in the skill. Install
its `requirements.txt` to run `scripts/validate_preparation.py <work-root>/work.json`;
use `--check-sources` to verify accessible local originals as well.
New work records use schema version 2; version-1 records remain readable.
`scripts/prepare_metadata.py migrate <work-root>/work.json` migrates a legacy
record, and `enrich` computes missing extent and applies evidence-bound proposals
from the preparation agent. Neither operation edits manuscript text.

### `manuscript-analysis`

Reads verified preparation and produces chapter summaries, a full neutral
synopsis, a reading profile and an evidence-bound story ledger. Owns characters,
relationships, causal events, plot threads, chronology, knowledge/revelations,
object provenance, resolutions and atomic story-claim review. Querying consumes
the approved ledger instead of maintaining a second one.

The initial skill reuses the existing Markdown ledger and review contracts under
`manuscript-analysis/revisions/<analysis-id>/`; its JSON review state uses the
shared approval interface. It does not yet add a machine-readable story-graph
validator, automatic novel analysis or Studio/CLI workflow stages.

### `literary-editing`

Runs manuscript assessment, developmental editing, line editing, copyediting, specialist review, proofreading, and final QA. It keeps the manuscript source separate from the editorial workspace, presents proposed changes for approval, and applies only decisions the author accepts.

Contributor context is in the [design rationale](docs/literary-editing-rationale.md);
planned skill-execution checks are in the
[editing evaluation scenarios](evals/cases/literary-editing/README.md).
The skill and its references remain the authoritative operating instructions.

### `literary-translation`

Translates literary works chapter by chapter using source analysis, a living glossary, systematic passage division, alternative drafts, and source-grounded review. Its goal is natural literary English that preserves the source's meaning, voice, rhythm, and reader experience.

### `literary-agent-querying`

Consumes the source-bound, item-by-item approved ledger from `manuscript-analysis`,
develops market positioning, researches and prioritizes literary agents, and
prepares queries, bios, comparisons and submission materials. Its static manifest
pins the external analysis rather than copying the ledger/review. Only an
explicit named-agent complete-package request authorizes an on-demand ZIP,
including a submission synopsis only when verified guidelines request one.
The neutral analysis synopsis is not a query artifact or submission authority.

### `interior-design`

Reads verified preparation, metadata, agent reading and author preferences to
produce a proposed interior-design form: typography, leading, geometry, paragraph
rhythm, semantic text roles and navigation. It runs standalone without a workflow
run or orchestration UI, or can be called as a reusable component. The
[output schema](plugins/manuscript-studio/skills/interior-design/schemas/interior-design-proposal.schema.json)
and [synthetic example](plugins/manuscript-studio/skills/interior-design/references/proposal.example.json)
are machine-readable. This replaces the former `format-manuscript` skill; it
does not generate documents, approve designs or attest production QA. Native
intake and production are separate from the skill; the workflow consumes the
standalone formatter for the bounded editable-DOCX POC.

### `review-approval-sheet`

Provides a shared interactive review interface for stable-ID approval sheets. It validates revision-bound state, presents compact navigation and item-specific decisions, parses explicit submissions, and preserves each literary skill's own authoritative records, domain rules, and separate action gates.

## Workflow prototype

The [workflow CLI](workflow/README.md) provides an initial orchestration implementation:
verified preparation, a human metadata review gate, translation with
source-grounded review and human gates,
explicit artifact acceptance, and Markdown export. It persists run state and review
receipts in SQLite and uses a Codex App Server adapter. General line editing is not
part of the default translation flow.
Literary editing starts its final formatting phase after manuscript approval,
with interior design and an editable specification-review form. The old separate
formatter route and format skill are removed. Exact-plan authorization, checked
DOCX construction, candidate download and final editable-document acceptance are
integrated into that phase. PDF/rendered-page review and translation composition
remain pending; no print certification is claimed.

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
python -B scripts/test_plugin_listing.py
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

## License

Copyright (c) 2026 Crossborder Art & Media LLC. The repository uses two licenses
(see [LICENSE](LICENSE)):

- **Skills** (`plugins/manuscript-studio/`) and **evaluations** (`evals/`): MIT,
  free for any use, including commercial use.
- **Workflow engine** (`workflow/`) and **Manuscript Studio** (`studio/`):
  [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0),
  source-available for personal, research, educational, and other noncommercial
  use. Commercial use requires a separate license negotiated with Crossborder
  Art & Media LLC. Versions of `workflow/` published before this change remain
  under MIT.
- **Fixtures** (`fixtures/`): the terms recorded with each fixture.
