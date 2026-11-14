# Agent instructions

These instructions apply to the entire repository. Follow any additional
instructions in nested `AGENTS.md` files for the files you change.

## Roadmap and progress

Read [roadmap.md](roadmap.md) before starting project work. Keep progress accurate
and understandable to both agents and humans. Do not invent priorities,
milestones, completed checks, or human approvals.

## UX specification

[docs/ux/README.md](docs/ux/README.md) is the versioned source of truth for
user flows, screen contracts, interaction rules, and UX decisions. Read the
relevant flow/screen documents before changing the studio UI, and update them
with behavior changes. Distinguish current behavior from proposed designs,
and source mapping from actual browser/test validation.

Keep milestone scope, delivery status, priorities, and implementation evidence
in `roadmap.md`; link to UX IDs instead of duplicating detailed designs there.

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
