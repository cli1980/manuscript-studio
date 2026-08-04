# Domain Adapters

Map domain records into the shared schema without transferring domain authority to the interface.

## Literary-agent querying

- Bind the sheet to ledger revision, manuscript checksum, and review revision.
- Use one atomic story proposition per item.
- Show evidence, permitted wording, qualification, prohibited overstatement, prior response, and reopened reason.
- Define `approve` as resolve, `qualify` as resolve with a required note, `correct` as reopen with a required note, and `keep ambiguous` as resolve.
- Let querying propagate corrections, invalidate dependents, rebuild compression profiles, and require final closure.

## Literary editing

- Bind the sheet to job ID, workspace review identity, source import identity, and proposal ledger.
- Show location, current text, proposed text or operation, rationale, effect, dependencies, and paragraph-boundary evidence when applicable.
- Define `accept`, `reject`, and `defer` as resolve; `accept with modification` as resolve with exact wording; and `revise proposal` as reopen with a note.
- Let editing quick-check decisions, update the decision table, and require a separate apply instruction before manuscript changes.

## Literary translation

Use the shared interface for passage maps, chapter sanity diffs, and multiple independent Step 3.2 choices. Keep dependent, discussion-heavy, or genuinely single issues in the normal one-at-a-time dialogue.

### Passage map

- Use one item per proposed passage boundary or passage unit.
- Show source anchors and structural reason.
- Define `approve` as resolve and `move boundary`, `merge`, or `split` as reopen with a note.
- Let translation regenerate the complete map after any boundary change.

### Step 3.2 issue ledger

- Use one item per fixed issue only when batch review is requested.
- Show exact original, current translation, source effect, alternatives, and recommendation.
- Let translation define option commands, apply settled choices to the checkpoint, and update glossary or voice state.

### Chapter sanity review

- Use one item per proposed edit.
- Show location, current wording, proposed wording, and reason.
- Define `accept`, `reject`, and `defer` as resolve; `accept with modification` requires exact wording.
- Preserve the translation workflow's complete-diff approval semantics.

## Manuscript formatting

- Bind the sheet to manuscript identity, format-specification revision, edition profile, and intended output format.
- Use one `FM###` item per consequential design group, not one item per numeric token.
- Show the recommendation, manuscript or convention evidence, meaningful alternatives, and downstream effects.
- Define `approve` as resolve, `modify` as resolve with exact instructions, and `revise recommendation` as reopen with a note.
- Put the edition classification and intended-use confirmation inside an `FM` item when it is not already confirmed.
- On review-continuation requests, render the newest saved revision instead of switching to serial chat prompts; after a disposition, increment the revision and render only remaining or reopened items.
- Let formatting update the authoritative specification, invalidate dependent outputs, and require separate final closure before generation.

## Other domains

Use stable IDs, atomic summaries, labeled details, explicit commands, and revision bindings. Define whether each decision resolves the item or reopens domain work. Never use the shared layer to invent application authority.
