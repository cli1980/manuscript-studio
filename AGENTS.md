# Agent instructions

These instructions apply to the entire repository. Follow any additional
instructions in nested `AGENTS.md` files for the files you change.

## Roadmap and progress

Read [roadmap.md](roadmap.md) before starting project work. Keep progress accurate
and understandable to both agents and humans. Do not invent priorities,
milestones, completed checks, or human approvals.

## Milestone branches

For all milestone development after M3, create and switch to a dedicated feature
branch before making implementation changes. If that milestone already has a
feature branch, continue on it. Do not develop milestones directly on `main`;
keep unrelated milestone work on separate branches. Use descriptive names such
as `feature/m4-literary-edit` or `feature/remote-multi-user`.

## Interior design and formatting

Before changing interior-design skills, formatting inputs, production, or workflow
integration, read the
[high-level design](tools/formattor/docs/interior-design-and-production.md), including
its requirement traceability and open-decision register.

`tools/formattor` is a pinned submodule from `cli1980/book-formatter`. If its
documents are absent, run
`git submodule update --init --recursive tools/formattor` first. Edit tool-owned
files in that repository and update the parent's gitlink; do not recreate a
second tracked copy in this repository.

Keep owner-confirmed requirements separate from draft recommendations. Preserve
stable requirement/decision IDs; record subsequent direction and its effects in
the design. Do not silently resolve open product decisions or claim implementation
without linked evidence. Keep milestone scope/progress in `roadmap.md` and link
to the design instead of creating another delivery tracker.

## Compatibility

Until the product's first formal release, do not preserve backward compatibility
when doing so would complicate schemas; prefer the cleaner schema.

## Line endings

Use LF line endings for every text file in the repository, including new files,
regardless of the platform or the `core.autocrlf` setting. The root
`.gitattributes` enforces LF on commit and checkout. Do not add CRLF files;
the only exceptions are files marked `-text` by a nested `.gitattributes`
(verbatim evaluation evidence), whose bytes must be preserved unchanged.
Check with `git ls-files --eol`.
