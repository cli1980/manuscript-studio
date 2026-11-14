# Interaction principles and domain boundaries

These contracts are migrated from the roadmap and existing UI, not new approvals.
See [UXD-001](decisions/UXD-001-interaction-contracts.md) for dates and revisions.

1. **Organize around works and outcomes.** Intake creates a work, not a run.
   A work's source, metadata, accepted outputs, and lineage remain inspectable
   without entering a run. Starting a workflow selects an existing work.
2. **Protect manuscript authority.** Source and output are read-only in the GUI.
   Highlighting and comments are feedback, not manuscript edits. Workflow gates
   and the engine authorize changes; interface convenience never bypasses them.
3. **Separate metadata from prose.** Shared metadata is editable, versioned,
   and attributable. Locked fields and active-run restrictions remain enforced
   server-side. A metadata correction is not an edit to prepared chapter text.
4. **Put decisions after their evidence.** For chapter-based workflows, reading
   precedes the decision. Whole-book and pass decisions follow the content column.
   A generic frame may contain different bodies without changing domain rules.
5. **Distinguish feedback, approval, application, and finalization.** "Continue,"
   a discussion, or a request for revision is not blanket approval. Some advice
   sheets close implicitly; chapter approval, editorial application, consistency
   closure, pass acceptance, and final acceptance have their own contracts.
6. **Bind decisions to what was shown.** Stable item IDs, gate/sheet revisions,
   record revisions, and content bindings prevent stale or duplicate decisions.
   Feedback for a previous gate must not appear as input for the next one.
7. **Make state and next action legible.** Show stage/chapter progress, what needs
   the user, and actionable errors. A chapter count is not whole-book progress.
   Live refresh must not erase unsent work or imply a decision was accepted.
8. **Explain control scope.** Pause waits for the turn; stop cancels the run;
   retry and restart are not equivalent. Explain affected and retained work,
   and require the confirmations exposed by the engine.
9. **Make irreversible acceptance unmistakable.** A finalized run cannot be
   changed or restarted. A new run on the same work publishes a new version;
   the old accepted version remains immutable.
10. **Expose capability limits honestly.** Formatting requires its configured
    construction/rendering/QA path. A planned preview, download, role, filter,
    or model picker is not a current capability merely because it is designed.

The UX specification describes how users encounter domain rules. It does not
redefine engine authorization, persistence, authentication, or artifact contracts.
Those remain in the code, workflow design documents, and milestone scope.
