# Agent instructions

These instructions apply to the entire repository. Follow any additional
instructions in nested `AGENTS.md` files for the files you change.

## Roadmap and progress

Read [roadmap.md](roadmap.md) before starting project work. Keep progress accurate
and understandable to both agents and humans. Do not invent priorities,
milestones, completed checks, or human approvals.

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
