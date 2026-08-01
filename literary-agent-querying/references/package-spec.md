# Query Package Specification

Write the complete output tree only beneath an environment-provided Codex task-artifact or Outputs destination, whose path or identifier must not be invented. Query outputs are never Git-managed. Do not write into a Git repository, manuscript project, editorial repository, or editorial-process folder. Explicitly designated manuscript and supporting inputs are read-only evidence, never part of the generated package unless a submission requirement and the user specifically request a manuscript artifact.

## Artifact layout

```text
query-package/
|-- static/
|   |-- package-manifest.md
|   |-- intake-summary.md
|   |-- master-query-letter.md
|   |-- synopsis.md
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
                `-- submission-checklist.md
```

Do not copy the full manuscript into the package unless the user asks and the submission requirements require a separate manuscript artifact.

## Package manifest

Record:

- book title and source identity;
- manuscript path or attachment identity without relocating it;
- manuscript version, modification time, checksum, or Git SHA when available;
- artifact workspace identity;
- package creation and revision date;
- confirmed target market;
- artifact list;
- evidence basis: manuscript, author-confirmed, or inferred;
- manuscript-derived positioning status: confirmed, provisional, or disputed;
- unresolved placeholders or open items;
- readiness: `ready`, `ready-with-open-items`, or `not-ready`;
- validation summary.

The validation summary must report the number of material atomic claims audited, manuscript-mapped, separately author-confirmed, and unresolved. Any unsupported or overstated material claim forces `not-ready`.

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

Default to a clear 1-2-page single-spaced synopsis unless the user or agent specifies otherwise. Include:

- protagonist and initial situation;
- inciting disruption;
- major causal turns and escalating choices;
- central relationship or subplot only when it changes the main plot;
- climax;
- ending and material resolution.

Use present tense and identify major characters clearly. Preserve the manuscript's actual causality. Do not conceal twists or end on a teaser.

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

## Submission checklist

The master checklist covers:

- manuscript completion and formatting;
- query, synopsis, biography, and sample readiness;
- title, genre, word-count, and series consistency;
- publication and submission-history disclosure;
- file naming and contact details;
- tracking fields for agent, agency, date, channel, materials, status, and response;
- a transfer of the active priority order from `agent-shortlist.md`;
- a reminder that sending requires separate explicit authorization.

When the author explicitly requests a tailored letter for an identified agent, create the corresponding tailored checklist with verified requirements and record:

- author-supplied agent, agency, or submission-guidelines URL, when available;
- official source URL;
- date accessed;
- open status;
- fit and exclusions;
- exact form or email requirements;
- page or chapter quantity;
- attachment or paste rules;
- agency concurrency rule;
- response policy;
- personalization evidence;
- unresolved conflicts.

## Tailored variants

Create `query-package/on-demand/tailored-<agent-slug>.zip` only after the author explicitly requests a tailored query letter and identifies that agent. Write the archive to the environment-provided task-artifact or Outputs destination so it is downloadable. Do not create, extract, stage, commit, or otherwise version a tailored folder or archive in any Git repository, and do not change the static package manifest solely to record it. If no downloadable artifact destination is available, state that the ZIP could not be persisted; do not redirect it into a repository or project folder.

Use the approved static query results as the sole source for the tailored letter's story-side content. Derive the pitch, metadata, comparable-title language, biography, and positioning from `static/master-query-letter.md`, `static/book-positioning.md`, `static/author-bio.md`, `static/intake-summary.md`, and confirmed static package state. Do not return to the manuscript to invent a different pitch for the agent, and never use editorial-process outputs.

Acquire current information about the identified agent and agency, using official sources as controlling evidence. Tailor only the salutation, genuine personalization, emphasis or ordering, formatting, and submission details that this agent evidence justifies. Preserve the static package's factual pitch, metadata, comparisons, biography claims, and positioning. If any of those need correction, revise and reconfirm the static package first, then regenerate the tailored letter from it.

Never claim that an agent requested the work, met the author, represents a comparison title, or expressed a preference unless a current reliable source supports it.

Treat every existing on-demand ZIP as invalid after a material correction to the static package from which it was derived. Regenerate it only upon the author's explicit request after the corrected static package passes the atomic-claim audit.
