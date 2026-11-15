# Formattor

Approved home of the standalone formatter/generator: one installable tool
exposing a Python API and CLI over the same core.

**Current status:** design and gap documentation is consolidated here. The
executable package, CLI and production integration are not implemented yet;
there is no installation command to run at this stage.

## Architecture

- Proposal intake validates bound sources, trusted selections and design values.
- The implementation-independent format engine prepares, produces, verifies and
  seals candidates.
- Format implementations own native construction/composition. DOCX is default;
  InDesign is potential future support.
- Workflow/Studio consume the public tool interface and retain human gates and
  publication authority. Skills author proposals, not generated documents.

The planned installable source layout is `src/formattor/` with a project
`pyproject.toml`; those files are not created by this documentation relocation.

## Design Documents

| Document | Purpose |
| --- | --- |
| [High-level design and decisions](docs/interior-design-and-production.md) | Canonical requirements, ownership, approvals and open decisions |
| [Package architecture](docs/formattor-package-design.md) | Intake/engine/implementation contracts and dependencies |
| [Placement comparison](docs/formattor-placement-evaluation.md) | Inside-workflow versus standalone evaluation and approved location |
| [Current proposal-to-DOCX gaps](docs/proposal-to-docx-gap-analysis.md) | Field-level gaps, contract risks and construction-probe evidence |
| [Historical formatter gap analysis](docs/deterministic-docx-gap-analysis.md) | Earlier baseline; retired routes are not available implementations |
| [Author-brief mapping](docs/interior-design-skill-brief-mapping.md) | Source brief and interior-design refinements |
| [Semantic-role hand-off](docs/semantic-role-handoff.md) | Shared preparation/editing/translation role contract |

The last two documents are shared design dependencies. Their location here does
not transfer semantic annotation ownership from preparation/editing/translation
to the formatter.

Implementation progress stays in the repository [roadmap](../../roadmap.md),
not a second delivery tracker.
