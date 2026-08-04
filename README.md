# quillholic-skills

`quillholic-skills` is a collection of independent AI-agent skills for literary writing, translation, editing, and publication preparation.

The project is designed to keep authors and translators focused on ideas, voice, and story instead of repeatedly searching dictionaries and thesauruses, debating commas and colons, revisiting grammar books, or hunting for typos. It provides structured, reviewable workflows that help AI agents streamline the path from manuscript development through translation, editing, and querying—without taking creative authority away from the author.

## Install as a ChatGPT and Codex plugin

The five skills are also packaged as the skills-only
`quillholic-literary-suite` plugin. Add this GitHub repository as a
marketplace:

```text
codex plugin marketplace add cli1980/quillholic-skills --ref main
```

Then open the Plugins Directory in ChatGPT Work or Codex, select the
`Quillholic` marketplace, and install `quillholic-literary-suite`. Start a
new conversation after installation.
## Getting started

No installation is required. You can ask an AI agent to use a skill by name, or point it to the project:

```text
https://github.com/cli1980/quillholic-skills
```

Choose the working style that matches your AI environment.

### Chat-based use

This option is for browser-based AI chat services.

1. Create a project in the chat service.
2. Link or upload your manuscript to that project.
3. Ask the agent to use `quillholic-skills` from GitHub and describe what you want to do. If the agent does not recognize the project, give it the repository link.

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


## The idea behind the project

Fear alone is not a good reason for authors, translators, editors, or publishing professionals to resist AI. AI agents do not replace the author's idea, experience, taste, or judgment; they provide skills and perform structured work under direction.

The creative advantage still belongs to the person with an exceptional idea and the ability to recognize what serves it. Authors who combine that vision with skillful use of AI can spend less time on mechanical friction and more time making consequential creative decisions. This project is built on the belief that such collaboration will become a normal part of literary work—and that writers who learn to direct it thoughtfully will stand out.

## License

See [LICENSE](LICENSE).
