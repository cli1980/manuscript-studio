# Agent instructions

These instructions apply to the entire repository. Follow any additional
instructions in nested `AGENTS.md` files for the files you change.

## Roadmap and progress

Read [roadmap.md](roadmap.md) before starting project work. Keep progress accurate
and understandable to both agents and humans. Do not invent priorities,
milestones, completed checks, or human approvals.

## Required before every push

Before every push of local commits to any remote:

1. Review all local commits that will be included in the push.
2. Update `roadmap.md` to reflect those changes and their current status. Update
   affected milestones and add a dated progress entry describing the changes,
   validation performed, remaining blockers or human review, and next step.
   If no milestone is affected, explicitly say so and describe the change.
3. Commit the roadmap update with the relevant work or in a separate commit
   included in the same push. An uncommitted roadmap edit does not satisfy this
   requirement.
4. Verify that the committed roadmap accurately describes the final changes
   being pushed. If the scope changes after the update, revise and commit it
   before pushing.

Do not push until this requirement is satisfied. This applies to every push,
including fixes, documentation changes, and maintenance work. These instructions
do not themselves authorize a push.
