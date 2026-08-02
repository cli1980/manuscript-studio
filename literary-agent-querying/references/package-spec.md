# Query Package Specification

Write the complete output tree only beneath an environment-provided Codex task-artifact or Outputs destination, whose path or identifier must not be invented. Query outputs are never Git-managed. Do not write into a Git repository, manuscript project, editorial repository, or editorial-process folder. Explicitly designated manuscript and supporting inputs are read-only evidence, never part of the generated package unless a submission requirement and the user specifically request a manuscript artifact.

## Artifact layout

```text
query-package/
|-- static/
|   |-- package-manifest.md
|   |-- intake-summary.md
|   |-- master-query-letter.md
|   |-- author-bio.md
|   |-- book-positioning.md
|   |-- agent-shortlist.md
|   |-- submission-checklist.md
|   `-- series-overview.md                 # when applicable
`-- on-demand/
    `-- tailored-<agent-slug>.zip           # only when explicitly requested
        `-- tailored/
            `-- <agent-slug>/
                |-- query-letter.md
                |-- synopsis.md                       # only when required or explicitly requested
                `-- submission-instructions.md        # required for every named-agent package
```

Do not copy the full manuscript into the package unless the user asks and the submission requirements require a separate manuscript artifact.

## Package manifest

Record:

- book title and source identity;
- manuscript path or attachment identity without relocating it;
- manuscript version, modification time, checksum, or Git SHA when available;
- artifact workspace identity;
- package creation and revision date;
- prerequisite refresh decision, decision date, fields reused, and fields refreshed;
- confirmed target market;
- artifact list;
- evidence basis: manuscript, author-confirmed, or inferred;
- manuscript-derived positioning status: confirmed, provisional, or disputed;
- unresolved placeholders or open items;
- readiness: `ready`, `ready-with-open-items`, or `not-ready`;
- validation summary.

The validation summary must report the number of material atomic claims audited, manuscript-mapped, separately author-confirmed, and unresolved. Any unsupported or overstated material claim forces `not-ready`. A required agent-specific synopsis that is missing, noncompliant, or unsupported also forces `not-ready`.

## Intake summary

Preserve the author-approved facts, positioning, series classification, relevant history, and open items. Record whether author-profile material accompanied the manuscript, which factors were approved for agent matching, and any disclosure boundary. This is package state, not text intended for agents.

Include a manuscript fact ledger for every pitch-critical proposition. Each entry must contain:

- proposed package wording or atomic claim;
- claim type: `fact`, `character-belief`, `inference`, or `ambiguous`;
- direct manuscript location, using chapter plus page, line, paragraph, or another stable locator available in the source;
- confidence and credible alternative interpretation when relevant;
- author confirmation when consequential inference or intentional ambiguity requires resolution;
- permitted wording and any qualification or attribution that must be preserved.

The ledger must reconcile chronology, entity identity, aliases, ships, locations, artifacts, institutions, programs, object provenance, causal relationships, motives, knowledge states, revelation timing, final choice, and ending. Narrative adjacency is not evidence of causation. A character statement is not automatically objective truth. Existing pitches, generated summaries, prior package prose, and editorial-process outputs are not manuscript evidence.

## Master query letter

Keep the letter concise, normally around one page. Use a professional salutation placeholder only in the master version. Include:

- a story-forward pitch centered on protagonist, conflict, choice, and stakes;
- title, category, genre, word count, and series status;
- useful comparable works and what the combination signals;
- a concise relevant biography;
- a professional closing.

Let the confirmed positioning determine what the letter foregrounds. The pitch should express the dominant story engine, address the intended readership, use only the worldbuilding needed to understand the conflict, and carry a restrained tonal correspondence with the novel's prose essence. Do not turn a quiet interior novel into an action pitch or an accessible commercial novel into an abstract literary statement.

The order may vary with the book. Avoid rhetorical questions, praise of the manuscript, invented market claims, theme lists, exhaustive worldbuilding, and synopsis-like coverage.

Use visible tokens such as `[AGENT NAME]` only in a file explicitly labeled draft or master. A tailored submission-ready letter must contain no unresolved token.

## Synopsis

Create a synopsis only inside an explicitly requested named-agent package when the target agent's verified guidelines require one or the author explicitly requests one. Follow the agent's specified length and format; when neither supplies a specification, default to a clear 1-2-page single-spaced synopsis. Include:

- protagonist and initial situation;
- inciting disruption;
- major causal turns and escalating choices;
- central relationship or subplot only when it changes the main plot;
- climax;
- ending and material resolution.

Use present tense and identify major characters clearly. Preserve the manuscript's actual causality. Do not conceal twists or end on a teaser.

Generate the synopsis from the approved manuscript fact ledger and confirmed positioning, then audit every material atomic claim against the ledger and manuscript. Do not require separate author approval: the ledger is the approved source of truth. If drafting reveals an unsupported claim, consequential inference, or unresolved ambiguity, correct the ledger and obtain any confirmation required for that underlying entry before regenerating and revalidating the synopsis.

## Author biography

Create:

- a short query-letter version, normally 40-100 words;
- an optional expanded version when useful.

Prioritize relevant credits, expertise, connection to the material, and previous books. For a debut author without credentials, use a dignified concise biography. Do not manufacture authority or require personal identity disclosure.

## Book positioning

Record:

- title;
- category and genre with manuscript evidence;
- word count;
- logline;
- short pitch;
- target and crossover readership with manuscript evidence;
- prose essence with manuscript evidence;
- dominant story type or narrative engine with manuscript evidence;
- tone with manuscript evidence;
- themes;
- differentiating promise;
- comparable works with a specific function and limitation for each;
- series classification;
- potential positioning risks or open decisions;
- confidence, credible alternatives, and query implications for each consequential classification.

Treat word-count conventions and market trends as guidance, not proof of quality. Browse current reliable sources when a recommendation depends on changing market conditions.

## Agent shortlist

Create an evidence-backed query order derived from the book-positioning profile. Include:

- research date, target market, and search scope;
- priority criteria, any author-supplied constraints, and whether author information was available at intake and used;
- `Priority 1`, `Priority 2`, and `Priority 3` tiers, with agents ordered within each tier;
- agent name, agency, territory, open status, represented categories, and relevant exclusions;
- the documented interests, clients, titles, interviews, or deal evidence that support the fit;
- a concise fit rationale tied to the novel's positioning and, only when available at intake, relevant author-approved matching factors;
- limitations, uncertainties, agency concurrency rules, and prior-submission conflicts;
- official source URLs, supplementary source URLs when used, and access dates;
- a separate watchlist for closed, uncertain, or currently ineligible agents;
- explicitly requested tailored-letter targets, when any; do not treat shortlist selection or priority ordering as a tailoring request.

Use current official agent or agency pages as the controlling source for eligibility and submission status. Do not rely on search-result snippets or third-party directories as final verification. Do not treat priority order as a prediction of representation, and do not hide weak evidence behind a numerical score.

When author-profile material accompanied the manuscript, it may refine candidate selection, tier placement, ordering, and personalization within the approved disclosure boundary. When it did not, omit author-side factors and do not infer or penalize missing credentials, platform, identity, previous books, or connections. Author information never overrides a hard category, eligibility, territory, or submission conflict.

## Series overview

Create only when applicable. Include:

- honest series classification;
- Book One's resolved movement;
- threads intentionally left open;
- one paragraph per later planned volume;
- overall series escalation and final destination;
- drafting status of later books.

Keep the master query focused on Book One. Do not attach the series overview to submissions unless requested.

## Submission checklist and named-agent instructions

The master checklist covers:

- manuscript completion and formatting;
- query, biography, and sample readiness, plus whether a synopsis must be generated for each target agent;
- title, genre, word-count, and series consistency;
- publication and submission-history disclosure;
- file naming and contact details;
- tracking fields for agent, agency, date, channel, materials, status, and response;
- a transfer of the active priority order from `agent-shortlist.md`;
- a reminder that sending requires separate explicit authorization.

For every explicitly requested named-agent package, create `tailored/<agent-slug>/submission-instructions.md`. It must be a standalone operating guide, not a research summary or generic checklist. The author should be able to use it without reopening the agency pages or asking what to do next.

Begin with `Submit here`, then record:

- author-supplied agent, agency, or submission-guidelines URL, when available;
- official source URL;
- date accessed;
- open status;
- fit and exclusions;
- exact form or email requirements;
- required synopsis length, format, and paste-or-attachment rule, or confirmation that no synopsis is requested;
- page or chapter quantity;
- attachment or paste rules;
- agency concurrency rule;
- response policy;
- personalization evidence;
- unresolved conflicts.

Follow with `Prepare these materials`, `Submission steps`, `Final check`, and `After submitting`. Use numbered steps containing one action each. Include filenames and formats for every upload, exact text-source mapping for every pasted item, and where applicable the requested sample-page or chapter boundary. Do not make the author infer whether an artifact should be pasted, attached, uploaded, or omitted.

For a website or online form, include:

- the direct form URL, not only the agency homepage;
- any account, login, browser, or file-size prerequisite stated by the official source;
- a field-by-field table with the visible field label, required or optional status, length or format limit, and the exact package file, section, or author-supplied value to enter;
- the upload order and accepted file types;
- the exact final review and submit actions.

For email, include:

- the verified recipient address;
- the exact or recommended subject line;
- the body assembly order, including where the salutation, query letter, synopsis, sample, and closing belong;
- every attachment filename, format, and naming convention;
- which materials must be pasted and which attached;
- the exact final review and send actions.

For both channels, include:

- agency concurrency, simultaneous-submission, referral, and prior-submission constraints that affect this submission;
- the stated response window or no-response policy;
- the tracking entry the author should record after sending;
- a reminder that the package has not been submitted and sending requires a separate explicit action.

Use a current official agent or agency page or form as the controlling source. An official submission email received from the agent or agency may control when the author supplies it; record the sender, recipient, date, subject, and relevant instructions. If sources conflict or the direct route cannot be verified, describe the conflict or missing item precisely, mark the guide and package `not-ready`, and do not invent a resolution.

## Tailored variants

Create `query-package/on-demand/tailored-<agent-slug>.zip` only after the author explicitly requests a tailored query letter and identifies that agent. Write the archive to the environment-provided task-artifact or Outputs destination so it is downloadable. Do not create, extract, stage, commit, or otherwise version a tailored folder or archive in any Git repository, and do not change the static package manifest solely to record it. If no downloadable artifact destination is available, state that the ZIP could not be persisted; do not redirect it into a repository or project folder.

Always include `tailored/<agent-slug>/submission-instructions.md`. Validate that its direct route and numbered actions match the current official evidence and every file actually present in the ZIP. Do not mark a named-agent package ready when the guide is absent, generic, stale, internally inconsistent, or unable to tell the author exactly how to submit.

Use the approved static query results as the sole source for the tailored letter's story-side content. Derive the pitch, metadata, comparable-title language, biography, and positioning from `static/master-query-letter.md`, `static/book-positioning.md`, `static/author-bio.md`, `static/intake-summary.md`, and confirmed static package state. Do not return to the manuscript to invent a different pitch for the agent, and never use editorial-process outputs.

Acquire current information about the identified agent and agency, using official sources as controlling evidence. Tailor only the salutation, genuine personalization, emphasis or ordering, formatting, and submission details that this agent evidence justifies. Preserve the static package's factual pitch, metadata, comparisons, biography claims, and positioning. If the agent requires a synopsis, generate it inside the tailored package from the approved fact ledger and match the verified requirements. If any static fact or positioning needs correction, revise and reconfirm the affected static state first, then regenerate the tailored materials from it.

Never claim that an agent requested the work, met the author, represents a comparison title, or expressed a preference unless a current reliable source supports it.

Treat every existing on-demand ZIP as invalid after a material correction to the static package from which it was derived. Regenerate the ZIP only upon the author's explicit request after the corrected static package passes the atomic-claim audit. A revised agent-specific synopsis must pass a new claim audit but requires no separate author approval.
