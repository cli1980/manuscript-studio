# Query Package Specification

When a writable project root exists, create and write the complete output tree beneath `<project-root>/query-package/`. Do not inspect Git or use Git status to decide whether output may be created, and do not stage or commit query outputs unless the user separately asks. When no writable project root exists, including web chat, create the same logical output tree as Codex artifacts. Never write query outputs inside an editorial-process subfolder. Explicitly designated manuscript and supporting inputs are read-only evidence, never part of the generated package unless a submission requirement and the user specifically request a manuscript artifact.

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
    `-- agent-package-<agent-slug>.zip      # only after an authorized named-agent complete-package request
        `-- agent-package/
            `-- <agent-slug>/
                |-- package-manifest.md                # required for every on-demand ZIP
                |-- query-letter.md
                |-- synopsis.md                        # only when the agent requests one
                `-- submission-instructions.md         # required for every on-demand ZIP
```

Do not copy the full manuscript into the package unless the user asks and the submission requirements require a separate manuscript artifact.

The story ledger and its review records live in the separate manuscript-analysis
revision, not this tree. The static manifest pins their identities and hashes
under [the analysis handoff](manuscript-analysis-handoff.md). Do not create local
copies or treat a neutral analysis synopsis as an authorized query synopsis.

## Terminal on-demand deliverables

Treat every on-demand ZIP as a complete, one-time terminal product, not reusable project state. Never inspect, extract, quote, summarize, copy, or revise a prior on-demand output while building static state or another on-demand package. An explicit audit of a named prior package may read it only for that audit; its contents remain forbidden as evidence or rebuild input.

For every named-agent build, rebuild, or regeneration, create an empty staging directory outside `query-package/on-demand/`, reproduce every applicable artifact from approved static state, designated manuscript material required for the submission, and current verified agent evidence, validate the new ZIP, then atomically replace the unversioned destination. Never edit an existing ZIP in place. Keep only complete `agent-package-<agent-slug>.zip` files in `query-package/on-demand/`; loose files and staging directories are invalid.

## Package manifest

Record:

- book title and source identity;
- manuscript path or attachment identity without relocating it;
- manuscript version, modification time, or checksum when available, without inspecting Git;
- shared work locator and prepared revision when supplied, plus metadata record revision and consumed shared metadata fields/values; changes to mutable workflow status alone do not invalidate manuscript evidence;
- structured story-ledger identity, revision, approval status, synopsis readiness, bound manuscript identity, human-review artifact identity, gate status, approval-unit counts, and final closure date;
- external analysis manifest locator/checksum, contract/revision, ledger and review locators/checksums, whole-work coverage and evidence-audit results;
- project-root or Codex artifact identity;
- package creation and revision date;
- static-artifact reuse decision, decision date, full-flow trigger when any, fields reused, and fields refreshed; never treat on-demand output as reusable;
- confirmed target market;
- artifact list;
- evidence basis: manuscript, author-confirmed, or inferred;
- manuscript-derived positioning status: confirmed, provisional, or disputed;
- unresolved placeholders or open items;
- readiness: `ready`, `ready-with-open-items`, or `not-ready`;
- validation summary.

The validation summary must report the number of material atomic claims audited, manuscript-mapped, separately author-confirmed, and unresolved. Any unsupported or overstated material claim forces `not-ready`. A required agent-specific synopsis that is missing, noncompliant, or unsupported also forces `not-ready`.

## Intake summary

Preserve the author-approved project facts, positioning, series classification, relevant history, disclosure boundary, and open items. This is package state, not text intended for agents. Keep the structured story ledger in the separate static artifact below.

## Structured story ledger

Consume the pinned ledger from [manuscript-analysis](../../manuscript-analysis/SKILL.md)
under [the handoff contract](manuscript-analysis-handoff.md). That skill owns
construction, source auditing, item-level review, corrections and separate final
closure. Querying requires ledger `approved`, human gate `passed`, appropriate
synopsis readiness, complete unchanged source coverage and matching hashes.
Otherwise keep the static package `not-ready`. Corrections return to analysis,
invalidate affected query state/products, and require a newly verified binding;
querying must not repair or approve a local ledger fork.

## Master query letter

Keep the letter concise, normally around one page. Use a professional salutation placeholder only in the master version. Include:

- a story-forward pitch centered on protagonist, conflict, choice, and stakes;
- title, category, genre, word count, and series status;
- useful comparable works and what the combination signals;
- a concise relevant biography;
- a professional closing.

Let the confirmed positioning determine what the letter foregrounds. The pitch should express the dominant story engine, address the intended readership, use only the worldbuilding needed to understand the conflict, and carry a restrained tonal correspondence with the novel's prose essence. Do not turn a quiet interior novel into an action pitch or an accessible commercial novel into an abstract literary statement.

The order may vary with the book. Avoid rhetorical questions, praise of the manuscript, invented market claims, theme lists, exhaustive worldbuilding, and synopsis-like coverage.

Treat the opening as a compact query pitch rather than a miniature synopsis. Unless official instructions require another structure, use one short paragraph, normally two to four sentences, to establish the protagonist, destabilizing problem, and immediate pressure or stakes. Apply the same gate to the entire story-pitch block. When no synopsis is requested, normally keep that block to one or two short paragraphs containing only the turns needed to frame the central opposition, consequential choice, and stakes; omit resolution history, climax mechanics, and chains of discoveries. If the block could stand alone as a condensed synopsis, compress or reframe it. Put credible personalization before the pitch or in the transition to metadata rather than after a multi-paragraph plot summary. `No synopsis requested` suppresses the separate synopsis artifact and any synopsis substitute embedded in the letter; it does not suppress a short description or query pitch that the guidelines request.

Use visible tokens such as `[AGENT NAME]` only in a file explicitly labeled draft or master. An agent-specific submission-ready letter must contain no unresolved token.

## Synopsis

Do not create a query-package/static synopsis or a submission synopsis before the author explicitly asks to build, rebuild, or regenerate the complete package for a named agent. A separate neutral synopsis may exist in manuscript-analysis, but is not submission prose or a substitute for the approved ledger. Inside an authorized package, create a synopsis only when verified guidelines request one. Follow the specified length, weighting and format; absent those details, default to a clear 1-2-page single-spaced synopsis. Include:

- protagonist and initial situation;
- inciting disruption;
- major causal turns and escalating choices;
- central relationship or subplot only when it changes the main plot;
- climax;
- ending and material resolution.

Use present tense and identify major characters clearly. Preserve the manuscript's actual causality. Do not conceal twists or end on a teaser.

Generate fresh from the pinned approved analysis ledger, then audit every
material atomic claim against ledger IDs and recorded locators. Do not inspect
or reuse prior submission synopses, on-demand packages or the neutral analysis
synopsis as drafting authority. Do not reopen unchanged source or require
separate synopsis approval. If drafting reveals a gap, stop and return it to
manuscript-analysis for authorized repair, dependent invalidation and renewed
item review/final closure before repinning and regenerating.

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
- authorized `build a package for <agent>` requests, when any; do not treat shortlist selection, priority ordering, a query-letter request, a synopsis request, or tailoring discussion as on-demand authorization.

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

## Submission checklist and on-demand instructions

The master checklist covers:

- manuscript completion and formatting;
- query, biography, and sample readiness, plus whether a synopsis must be generated for each target agent;
- title, genre, word-count, and series consistency;
- publication and submission-history disclosure;
- file naming and contact details;
- tracking fields for agent, agency, date, channel, materials, status, and response;
- a transfer of the active priority order from `agent-shortlist.md`;
- a reminder that sending requires separate explicit authorization.

For every authorized `build a package for <agent>` request, create `agent-package/<agent-slug>/package-manifest.md` and `agent-package/<agent-slug>/submission-instructions.md`. Always put a `Sample material` record in the manifest, including `not-requested` when applicable. The instructions must be a standalone operating guide that demonstrates exactly where and how to append, paste, upload, or attach the sample. The author should be able to use them without reopening the agency pages or asking what to do next.

Begin with `Submit here`, then record:

- author-supplied agent, agency, or submission-guidelines URL, when available;
- official source URL;
- date accessed;
- open status;
- fit and exclusions;
- exact form or email requirements;
- whether a synopsis is requested and, if so, its required length, weighting, format, and paste-or-attachment rule, or confirmation that no synopsis is requested;
- sample-page or chapter quantity, source-manuscript identity and version, exact start and end locators, and status: `prepared`, `author-supplied`, `not-requested`, or `missing`;
- sample delivery mode, required filename and format when applicable, and exact form field, upload slot, attachment step, or email-body insertion point;
- agency concurrency rule;
- response policy;
- personalization evidence;
- unresolved conflicts.

Follow with `Prepare these materials`, `Submission steps`, `Final check`, and `After submitting`. Use numbered steps containing one action each. Include filenames and formats for every upload, exact text-source mapping for every pasted item, and the requested sample-page or chapter boundary. Demonstrate the precise placement of the sample: name the web field or upload slot, or identify where it is appended in the email body relative to the query letter, synopsis, and closing. Do not make the author infer whether an artifact should be appended, pasted, attached, uploaded, or omitted.

For page-count samples, render the designated source in the submission format and treat the requested page count as a hard maximum. Use `scripts/sample_boundary.py` to align extracted text to the physical cutoff. If the cutoff intersects a paragraph, roll back to the preceding complete paragraph; never extend past the page limit and never retain a partial sentence or paragraph. Include the generated `sample-boundary.json` in the ZIP, and state the requested pages, physical cutoff, rollback decision, effective end locator, and passing validation in both the manifest and instructions.

For a website or online form, include:

- the direct form URL, not only the agency homepage;
- any account, login, browser, or file-size prerequisite stated by the official source;
- a field-by-field table with the visible field label, required or optional status, length or format limit, and the exact package file, section, author-supplied value, or sample-material range to enter;
- the upload order and accepted file types;
- the exact final review and submit actions.

For email, include:

- the verified recipient address;
- the exact or recommended subject line;
- the body assembly order, including the exact point where the sample is appended relative to the salutation, query letter, synopsis, and closing;
- every attachment filename, format, and naming convention;
- which materials must be pasted and which attached;
- the exact final review and send actions.

For both channels, include:

- agency concurrency, simultaneous-submission, referral, and prior-submission constraints that affect this submission;
- the stated response window or no-response policy;
- the tracking entry the author should record after sending;
- a reminder that the package has not been submitted and sending requires a separate explicit action.

Use a current official agent or agency page or form as the controlling source. An official submission email received from the agent or agency may control when the author supplies it; record the sender, recipient, date, subject, and relevant instructions. If sources conflict or the direct route cannot be verified, describe the conflict or missing item precisely, mark the guide and package `not-ready`, and do not invent a resolution.

## On-demand package manifest

Create `agent-package/<agent-slug>/package-manifest.md` inside every on-demand ZIP. Record:

- the author request to build, rebuild, or regenerate the complete package, the target agent, and agency;
- package creation and revision date;
- manuscript source identity and checksum or version;
- static package identity, static manifest checksum or revision, and approval date;
- structured story-ledger revision, approval status, synopsis readiness, bound manuscript identity, synchronized human-review Markdown and JSON identities, gate status, approval-unit counts, and final closure date;
- reused static artifacts and any targeted static correction made before packaging;
- `Build mode: fresh-reproduction` and `Prior on-demand source: none`;
- official agent-research sources and access dates;
- whether the agent requests a synopsis and its verified length, weighting, format, and delivery method;
- a `Sample material` record containing the verified requirement or `not-requested`, page or chapter quantity, source-manuscript identity and version, exact start and end locators, preserved sequence, delivery mode, filename and format when applicable, exact destination or insertion point, and status; for a page-count sample, also record the physical cutoff, any rollback, the effective complete-paragraph end, and the `sample-boundary.json` result;
- every file included in the ZIP;
- unresolved items and conflicts;
- readiness: `ready`, `ready-with-open-items`, or `not-ready`;
- validation results, including atomic-claim audit counts for the query letter and synopsis when present.

Do not update the static manifest solely to record an on-demand ZIP. The on-demand manifest provides the provenance link. A missing, stale, unapproved, not-ready, or mismatched story ledger, human-review artifact, open or invalidated human gate, missing final closure, static identity, manuscript identity, required artifact, required sample, sample boundary, page-limit validation, complete-paragraph ending, or sample-placement instruction forces `not-ready`. A required sample may be `author-supplied` only when its source identity, availability, boundary, and format have been verified.

## On-demand agent packages

Create `query-package/on-demand/agent-package-<agent-slug>.zip` only after the author explicitly asks to build, rebuild, or regenerate the complete package for a named agent. This is the sole on-demand request type. Reuse approved static state, but exclude the entire on-demand tree and all prior on-demand artifacts from context. Reverify current agent evidence and reproduce the whole package in empty staging outside `query-package/on-demand/`; never incrementally revise, extract, copy from, or edit a prior package. Validate the new ZIP before atomically replacing the destination. In a writable project workspace, write the downloadable archive beneath `<project-root>/query-package/on-demand/`, creating the folder when needed. Do not inspect or gate on Git, and do not stage or commit the archive unless the user separately asks. When no writable project root exists, create the ZIP as a Codex artifact. If neither destination is available, state that the complete ZIP could not be persisted and stop; never emit the package or its component files into conversation context. Never create or extract the package inside an editorial-process subfolder.

Always include `agent-package/<agent-slug>/package-manifest.md`, `agent-package/<agent-slug>/query-letter.md`, `agent-package/<agent-slug>/claim-audit.md`, and `agent-package/<agent-slug>/submission-instructions.md`, plus every synopsis, sample, boundary report, form answer, email body, attachment, or assembly artifact required by the verified submission. Validate that the manifest binds the ZIP to the approved static package and manuscript source and contains the mandatory `Sample material` record. For every page-count sample, require `sample-boundary.json` and reject a sample that exceeds the rendered page limit or ends with a partial sentence or paragraph. Validate that the instructions' direct route, sample placement, and numbered actions match the current official evidence and every file or author-supplied item actually available. Do not mark an on-demand package ready when either file is absent, generic, stale, internally inconsistent, missing the sample record, or unable to establish provenance and tell the author exactly how to submit.

Derive agent-specific query story claims only from the external approved
manuscript-analysis ledger pinned in the static manifest. Use approved static
positioning, metadata, comparisons and biography for other content; the master
query is a coverage baseline, not a prose template. Do not return to the
manuscript to invent a different pitch, and never use editorial-process outputs.

Acquire current information about the identified agent and agency, using official sources as controlling evidence. Change only the salutation, genuine personalization, emphasis or ordering, formatting, and submission details that this agent evidence justifies. Preserve the static package's factual pitch, metadata, comparisons, biography claims, and positioning. If the agent's verified guidelines request a synopsis, generate it inside the on-demand package from the approved, synopsis-ready structured story ledger without reopening the unchanged manuscript, and match the verified length, weighting, format, and delivery method. Otherwise do not generate one. If any static fact or positioning needs correction, revise and reconfirm the affected static state first, then regenerate the on-demand materials from it.

Never claim that an agent requested the work, met the author, represents a comparison title, or expressed a preference unless a current reliable source supports it.

Treat every existing on-demand ZIP as a terminal historical product that is never a source for later work. A material correction to static state also makes packages derived from the superseded state unusable. Reproduce a complete ZIP only after a new explicit named-agent build, rebuild, or regeneration request and after the current static package passes validation. Record `Build mode: fresh-reproduction` and `Prior on-demand source: none` in the new manifest. A freshly generated agent-specific synopsis must pass a new claim audit but requires no separate author approval.

Before delivery, run `scripts/validate_on_demand.py --new-zip <staged-zip>` and then `scripts/validate_on_demand.py --root <query-package/on-demand>`. The root check must not open existing ZIPs; it verifies only that no loose output or staging directory is present. Remove staging after atomic placement.
