# Roadmap-to-UX migration map

Version 0.1 extracts UX detail from the roadmap at baseline `87b7737`.
No UI or engine behavior changes in this migration.

| Former roadmap content | Canonical UX destination | What remains in the roadmap |
| --- | --- | --- |
| Cross-cutting Works intake and GUI immutability/metadata rules | [Principles](principles.md), [UXD-001](decisions/UXD-001-interaction-contracts.md) | Domain invariants and short design links |
| M3 action semantics, review/acceptance presentation, original download, implied closure | [UF-03](flows/UF-03-retrieve-artifacts.md), [UF-12](flows/UF-12-resolve-gate.md), [UF-13](flows/UF-13-finalize.md), [UF-16](flows/UF-16-pause-resume.md), [UF-17](flows/UF-17-recover.md), [UF-18](flows/UF-18-stop.md), UXD-001 | Milestone outcome, scope summary, acceptance gates, closure and verification evidence |
| M3 whole-book translation review interaction | [UF-07](flows/UF-07-translate.md), [chapter viewer](screens/chapter-viewer.md) | Required domain validation and live-vs-deterministic evidence |
| M4 pass selection/acceptance loop and implied editorial closure | [UF-08](flows/UF-08-edit.md), UXD-001 | Engine/template scope, remaining work, and historical implementation evidence |
| UX enhancement review, frontend structure, phases, title/brief/sample decisions, passage size, formatted-work hand-off | [Studio interface design record](designs/studio-interface.md) and individual current flows | High-level outcome, dependencies, implementation scope, and design link |
| Deterministic formatting's native settings and page-review interaction | [Formatting target](designs/deterministic-formatting.md) | Planned backend work, reproducibility/QA constraints, and acceptance criteria |

Dates, historical owner approvals, and qualifications are preserved in design
records. Words such as "planned" or "uncommitted" in dated historical records
describe that record's time; the [current flow inventory](README.md#flow-inventory)
is mapped separately to this branch. This prevents old future designs from being
presented as implemented features.

Delivery evidence stays in the roadmap rather than being duplicated as UX
validation. Existing workflow architecture and literary-skill documents remain
authoritative for their own domains. Plugin listing/privacy work, remote access
controls, evaluation-judge requirements, and runtime adapter architecture are
not moved wholesale into a studio interaction specification.
