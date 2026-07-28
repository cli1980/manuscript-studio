# quillholic-skills

`quillholic-skills` is a collection of independent AI-agent skills for literary writing, translation, editing, and publication preparation.

The project is designed to keep authors and translators focused on ideas, voice, and story instead of repeatedly searching dictionaries and thesauruses, debating commas and colons, revisiting grammar books, or hunting for typos. It provides structured, reviewable workflows that help AI agents streamline the path from manuscript development through translation, editing, and querying—without taking creative authority away from the author.

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
3. Ask the agent to use `literary-editing`, `literary-translation`, or `literary-agent-querying`. If the agent does not already recognize the skill, give it the repository link and ask it to follow the relevant `SKILL.md`.

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

Reads and positions a novel, researches and prioritizes suitable literary agents, conducts a focused author interview, and prepares query letters, synopses, biographies, submission checklists, and agent-specific materials. Agent recommendations are verified against current requirements, and author information is considered only when it is available and approved for matching.

## The idea behind the project

Fear alone is not a good reason for authors, translators, editors, or publishing professionals to resist AI. AI agents do not replace the author's idea, experience, taste, or judgment; they provide skills and perform structured work under direction.

The creative advantage still belongs to the person with an exceptional idea and the ability to recognize what serves it. Authors who combine that vision with skillful use of AI can spend less time on mechanical friction and more time making consequential creative decisions. This project is built on the belief that such collaboration will become a normal part of literary work—and that writers who learn to direct it thoughtfully will stand out.

## License

See [LICENSE](LICENSE).
