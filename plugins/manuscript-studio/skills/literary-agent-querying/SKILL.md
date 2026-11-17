---
name: literary-agent-querying
description: Research and rank literary agents, develop market positioning, and draft truthful pitches, queries, bios, comparisons and submission packages from a revision-bound, author-approved manuscript-analysis story ledger. Delegate manuscript reading, ledger construction, evidence auditing and story review to manuscript-analysis. Build a fresh terminal agent-specific ZIP only after an explicit named-agent complete-package request, including a synopsis only when verified guidelines require it.
---

# Literary Agent Querying

Build a truthful, manuscript-grounded query package through a short guided dialogue. Keep the workflow lighter than an editorial review: acquire the necessary facts, confirm the positioning, draft the package, and validate it against the intended market or named agent.

## Governing Rules

1. Treat the author as the authority on intent, identity, publication history, rights, and career goals.
2. During a full flow, obtain a complete, source-bound reading through manuscript-analysis and inspect designated pitch materials before asking questions they already answer. Reuse valid approved analysis and static query state; do not repeat manuscript reading or intake solely for an incremental query revision. Treat incomplete coverage as provisional and not ready for story-dependent submission prose.
3. Ask only questions that materially affect the package. Use short conversational rounds organized by topic, not one long form.
4. Do not invent story facts, credentials, comparable titles, market claims, personalization, submission requirements, or rights status.
5. Distinguish an inference from an author-confirmed fact. Ask for confirmation before using a consequential inference.
6. Adapt recommendations to the book's actual category, genre, length, voice, structure, and intended market. Do not force every novel into one pitch formula.
7. Describe a book as `standalone with series potential` only when its principal dramatic movement resolves sufficiently on its own. Otherwise state its series dependency honestly.
8. Reveal the ending in the synopsis. Do not reveal it in the query pitch unless doing so is necessary to represent the premise accurately.
9. Follow each named agent's current official submission requirements exactly. Browse official agency or agent sources when current requirements or market status matter.
10. Treat agent rankings as evidence-based priorities, not guarantees of fit or representation. Use official agent or agency sources to verify identity, categories, exclusions, submission status, and requirements. Use reputable interviews or deal records only as supplementary fit evidence, and record source dates. Factor relevant, author-approved information into selection and ordering only when it was supplied or acquired with the manuscript at intake. Otherwise omit author-side factors rather than guessing, requesting disclosure solely for ranking, or treating missing credentials, platform, identity, or connections negatively.
11. Prepare materials only. Do not submit a query, contact an agent, upload a form, or send a message without separate explicit authorization.
12. In a writable project workspace, write all generated query artifacts beneath `<project-root>/query-package/`, creating that folder when needed. The designated shared `work.json` may receive this workflow's status summary and shared descriptive metadata updates under the metadata contract; it must not contain query prose or ledger content. Do not inspect or gate output on Git status, and do not stage or commit outputs unless the user separately asks. When no writable project root exists, including web chat, create Codex artifacts instead. Never write query outputs inside an editorial-process subfolder.
13. Preserve the two output categories defined in [references/package-spec.md](references/package-spec.md): `query-package/static/` for reusable general information and `query-package/on-demand/` for terminal ZIP products authorized by a named-agent build, rebuild, or complete-regeneration request.
14. Read manuscript and supporting inputs only from paths or attachments explicitly designated for this querying job. If a designated input is inside an editorial-process output folder, ask for an allowed source copy or attachment instead of reading it. Never use editorial assessments, normalized editorial manuscripts, proposals, style sheets, continuity records, reports, or exports as query evidence.
15. Treat manuscript sources as read-only evidence. The verified, author-approved manuscript-analysis ledger is the sole shared story authority under the handoff contract. Pitches, earlier drafts and other generated summaries are leads, not authorities. Analysis cannot launder forbidden editorial inputs. Every on-demand package remains a terminal deliverable, never evidence, prerequisite state or context for later work.
16. If neither a writable project root nor a Codex artifact facility is available, return only applicable static material in clearly labeled chat sections and state that persistent output was unavailable. Never emit an on-demand package or any of its component files into conversation context; report that the complete ZIP could not be persisted and stop.
17. Derive market positioning from the shared manuscript-grounded reading profile and approved ledger. Own category/reader-promise choices, comparable-title positioning and pitch strategy; delegate disputed source interpretation or profile repair to manuscript-analysis rather than generating another reading.
18. Recognize only one on-demand authorization class: the author explicitly asks to build, rebuild, or regenerate the complete package for a named agent. A request for a query letter, synopsis, tailoring advice, shortlist entry, priority selection, named-agent discussion, or general agent research is not authorization to create on-demand artifacts.
19. Deliver each authorized named-agent build, rebuild, or complete regeneration as an unversioned downloadable ZIP beneath `query-package/on-demand/`. Include the mandatory package manifest and customized submission instructions, and preserve the internal layout defined in [references/package-spec.md](references/package-spec.md).
20. Do not state an inference, character belief, or ambiguity as objective fact. Do not assert causation from narrative adjacency, merge distinct entities or events for compression, or assign knowledge or motives to a character or faction without evidence.
21. Run the full flow only when no reusable static query-package artifacts exist or the author explicitly forces a full refresh. When static artifacts exist, show a compact freshness summary, reuse approved static parts by default, and repair only missing, requested, or unsafe static parts. Exclude `query-package/on-demand/` and all prior on-demand deliverables from artifact discovery and context assembly. Never convert a static revision or on-demand package request into a silent full refresh. Reverify time-sensitive agent status and submission requirements for every on-demand package regardless.
22. Follow [the manuscript-analysis handoff](references/manuscript-analysis-handoff.md). Pin the external analysis, ledger and review identities in the static manifest; do not create query-local ledger/review copies. Require a passing source/evidence audit, an explicit disposition of every required atomic `HG` proposition, propagated corrections and separate final closure. Querying cannot grant or repair analysis approval. Reuse an unchanged approved ledger without rereading the raw manuscript; route gaps back to manuscript-analysis.
23. Make every on-demand package independently auditable and usable. Include `package-manifest.md` and `submission-instructions.md` with a current official website or form route, or an official submission email supplied or verified from the agent or agency. Always record the agent's sample-page requirement in the manifest, including `not-requested` when applicable, and make the instructions identify exactly where and how to append, paste, upload, or attach the sample. Provide exact numbered actions and map every requested field, pasted item, and attachment to the package. Mark the package `not-ready` when no current, unambiguous submission route can be verified.
24. Treat on-demand output as a complete, one-time product. For every authorized build or rebuild, start from an empty staging directory and reproduce the entire ZIP from approved static assets, the designated manuscript only where required to prepare submission material, and newly verified agent evidence. Never inspect, extract, quote, revise in place, copy from, or otherwise use a prior on-demand file or ZIP as context. The only exception is an explicit user request to audit a named prior package; an audit may read that package but may not promote or reuse its contents. Keep only complete `agent-package-<agent-slug>.zip` files in `query-package/on-demand/`; never leave loose synopses, letters, samples, manifests, instructions, drafts, or staging directories there.

## Run the Workflow

### 1. Resolve inputs and destination

Identify:

- manuscript or relevant source files;
- existing synopsis, pitch, or series notes;
- author biography or other author-profile material supplied alongside the manuscript, when available;
- requested package scope;
- target publishing market or territory, when known;
- named agent and the agent, agency, or submission-guidelines URL supplied by the author, when available;
- allowed manuscript and supporting-input locations outside editorial-process output folders;
- writable project root, or Codex artifact capability when no project filesystem exists.

When a writable project root exists, create `<project-root>/query-package/` and keep durable state there. General materials go beneath `query-package/static/`; terminal on-demand results go beneath `query-package/on-demand/` only after an authorized named-agent build, rebuild, or complete-regeneration request. When no writable project root exists, create the same logical tree as Codex artifacts. Record the project-root or artifact identity in `query-package/static/package-manifest.md`. Do not inspect Git to choose or approve the destination.

If the user designates a neutral prepared-manuscript package and its underlying
original as query inputs, consume its verified `work.json` and chapter manifest
under the sibling [preparation contract](../prepare-manuscript/references/preparation-contract.md).
This does not authorize reading editorial working copies or editorial-process
outputs. Full manuscript grounding requires verified whole-work coverage.
Maintain only `workflows.literary-agent-querying`, bound to that prepared revision
and scope, with the static package manifest as the state locator. The ledger's
evidence audit and human approval gate remain separate. If extraction is required,
delegate it to [prepare-manuscript](../prepare-manuscript/SKILL.md) within the
designated source location; do not introduce a Git preflight or broaden discovery.

Read and reuse the [shared metadata contract](../prepare-manuscript/references/manuscript-metadata.md)
before intake. Use its title, credited authors, languages, type/form, genres,
audience, series, and revision-scoped extent instead of collecting them again.
Check inferred positioning against the novel, preserve user edits, and save
explicitly confirmed common corrections back to shared metadata. Query-specific
emphasis and comparisons remain local. Shared descriptions never replace the
approved story ledger. Record the shared locator, metadata record revision,
prepared revision, and consumed metadata fields/values in the static manifest.
Source extraction belongs to preparation; agent-specific sample selection and
page-limit trimming remain querying operations.

Read [references/questionnaire.md](references/questionnaire.md) in full before interviewing the author. Read [references/package-spec.md](references/package-spec.md) in full before drafting or validating outputs.

Read [references/manuscript-analysis-handoff.md](references/manuscript-analysis-handoff.md) in full. Delegate reading, ledger creation/repair and story approval to the sibling [manuscript-analysis skill](../manuscript-analysis/SKILL.md). Querying consumes its verified output; it does not own those operations. If the source is unavailable, collect clearly unverified author-supplied intake but do not mark story-dependent prose or a package ready.

Before beginning work, inspect the current conversation and allowed `query-package/static/` state for reusable prerequisites. These include manuscript identity and checksum, completion state, title, word count, language, market, publication and representation history, rights status, series architecture, approved structured story ledger and synopsis readiness, positioning, biography, comparisons, and the static manifest. Do not enumerate, read, extract, summarize, or otherwise load `query-package/on-demand/` or prior on-demand artifacts into context.

- If no reusable static query-package artifacts exist, run the full flow in Steps 2-6.
- If static artifacts exist, present a compact freshness summary containing their source or approval date when available, changed-source indicators, open items, and the exact static artifacts and fields to reuse. Reuse them by default and perform only the requested incremental static work.
- Run the full flow again only when the author explicitly requests a full refresh or rebuild of static state.
- If a changed manuscript or broken provenance makes existing static artifacts unsafe to reuse, mark them `not-ready`, explain the mismatch, and ask the author to authorize a refresh; do not start one silently.

Time-sensitive agent research and on-demand output are never reusable. Reverify current agent status, agency rules, and submission requirements and reproduce the complete package whenever building for a named agent.

Steps 2-6 define the full flow. Skip them when reusable artifacts exist unless the author explicitly forces a refresh; route directly to the requested revision or Step 7 instead.

### 2. Derive the positioning profile

Before asking the author to classify the book, consume the shared reading profile and approved ledger, then propose query-facing positioning:

- category and genre or subgenre;
- target and crossover readership;
- query register informed by the recorded prose essence and narrative engine;
- reader promise and emphasis grounded in the recorded tone and themes;
- plausible comparable-title functions;
- the practical implication of each finding for the query's metadata, hook, emphasis, voice, and level of worldbuilding.

For each consequential classification, cite analysis evidence/claim IDs, confidence and credible alternatives. Do not classify from isolated tropes or word count alone. Source-reading gaps return to manuscript-analysis; market choices remain querying's responsibility.

### 3. Discover and prioritize suitable agents

Use the positioning profile to search the web for agents whose current interests plausibly match the novel. When author information was supplied or acquired alongside the manuscript, use relevant author-approved facts as additional matching evidence. If it was not available at intake, rank from the manuscript positioning and verified agent evidence alone. Unless the author declines agent discovery, create an ordered shortlist before drafting the package.

Build the candidate pool broadly, then verify each shortlisted agent through current official agent or agency pages. Exclude agents who are closed to queries, do not represent the category or genre, prohibit the submission because of agency concurrency rules, or have another documented hard conflict. Do not rank an unverified directory listing as if it were current official evidence.

Author-side evidence may include publishing background, relevant expertise or connection to the material, language and territory, career goals, previous books, meaningful platform, and any lived or cultural connection explicitly approved for matching. Never infer protected identity or expose information beyond the approved disclosure boundary.

Order the eligible agents by:

1. demonstrated fit with the novel's category, genre, readership, story engine, tone, themes, and differentiating promise;
2. when author information was available at intake, relevant author-agent fit supported by author-approved facts;
3. specificity and strength of current evidence, including named interests, representative clients or titles, and recent credible interviews or deal activity;
4. practical submission fit, including open status, territory, language, agency restrictions, and requested materials;
5. genuine personalization opportunities grounded in documented interests or connections.

Use `Priority 1`, `Priority 2`, and `Priority 3` tiers, with an ordered list within each tier. Explain the evidence, fit, limitations, and priority rationale for every agent. Record official source URLs, supplementary sources, and access dates. Keep uncertain or closed-but-promising agents on a separate watchlist rather than mixing them into the active query order.

Treat the shortlist as a research recommendation for author review. Do not generate or propose on-demand variants automatically. Wait for a separate author request to `build a package for <agent>`.

### 4. Build the intake record through dialogue

Extract what the sources establish, then interview for missing or ambiguous information. Ask one topic or a compact group of closely related questions at a time. Briefly explain why a difficult question matters when that helps the author answer.

Show the manuscript-derived profile, then ask the author to confirm, correct, or discuss it. Cover only the remaining applicable areas:

- project identity and completion state;
- category, genre, word count, language, and target market;
- protagonist, destabilizing event, objective, opposition, choice, stakes, and ending;
- themes, tone, readership, and comparable works;
- author biography and relevant connection or credentials for package drafting and tailoring; treat them as ranking inputs only if they were already available at intake or the author explicitly requests reranking;
- publication, representation, submission, and rights history;
- standalone or series architecture;
- shortlist priorities;
- agent requirements and personalization only after the author explicitly asks to `build a package for <agent>`.

Permit `unknown`, `not applicable`, and `decide with me`. Offer reasoned options when the author is unsure, but do not silently select a consequential answer.

Return corrections to source interpretation, story facts or ambiguities to
manuscript-analysis for propagation and required review. Author/rights intake
and query strategy stay here; this interview must not create a second ledger.

### 5. Confirm before drafting

Present a compact intake summary containing:

- confirmed facts;
- manuscript-derived positioning and its query implications;
- consequential inferences;
- unresolved items;
- proposed positioning;
- planned artifacts;
- proposed agent priorities and exclusions;
- any authorized `build a package for <agent>` request.

Ask the author to correct or approve the summary. Do not block on minor optional fields, but label omissions in the package manifest.

Before story-dependent drafting, require manuscript-analysis to complete its evidence audit and item-level human review with separate final closure. Verify the exact source, ledger, review and analysis bindings under the handoff contract. Approval of this intake/positioning summary is not story approval. If required analysis is missing or stale, delegate the authorized work and keep querying `not-ready`.

Keep general project, author, rights, publication and positioning state in `query-package/static/intake-summary.md`. Pin the approved shared analysis in the static manifest; do not duplicate its story ledger or review state.

### 6. Generate the general package

Create the applicable static artifacts defined in [references/package-spec.md](references/package-spec.md): master query letter, author biography, book-positioning sheet, prioritized agent shortlist, submission checklist, package manifest and intake summary. Reference the shared analysis/ledger/review rather than copying them. Create a series overview when applicable. Do not create story-dependent query prose until the shared ledger's human gate passes, and do not create a general or static query-package synopsis.

Derive story compression in the master query from the pinned approved ledger and confirmed positioning. If a claim or interpretation is missing, stop and return it to manuscript-analysis for evidence repair and all required item re-review/closure before repinning and continuing.

Keep static materials independent of any single agent. Shape the query from the confirmed positioning profile: foreground the dominant story engine, use an appropriate amount of worldbuilding, align the pitch's register with the prose essence without imitating the novel, and select metadata and comparisons for the actual readership.

### 7. Build a package for a specific agent

Create on-demand artifacts only after the author explicitly asks to `build a package for <agent>` or to rebuild/regenerate that named agent's complete package. This is the sole on-demand request type. Inspect only static artifacts, reuse approved static state, repair missing or unsafe static prerequisites, and skip the full flow when the static package is valid. If no reusable static package exists, complete the full flow first. Never inspect or reuse an existing on-demand package, even for the same agent. Reverify the agent's current official requirements, build every required artifact fresh in an empty staging directory outside `query-package/on-demand/`, validate the completed ZIP, then atomically replace the unversioned destination ZIP and remove staging.

Always create `agent-package/<agent-slug>/package-manifest.md`, `agent-package/<agent-slug>/query-letter.md`, `agent-package/<agent-slug>/claim-audit.md`, and `agent-package/<agent-slug>/submission-instructions.md`, plus every synopsis, sample, boundary report, form answer, email body, attachment, or assembly artifact required to execute the verified submission. Bind the manifest to the reused static package and manuscript source, declare `Build mode: fresh-reproduction` and `Prior on-demand source: none`, list every archive artifact, record the agent research date and sources, and state readiness and validation results. Use the target's current official website, official submission form, or an agent or agency email supplied by the author as the evidence source. Put a concise `Submit here` section first in the instructions, followed by numbered actions that take the author from opening the form or composing the email through final review. For a web submission, include the direct URL and map each visible field to exact package content or a clearly labeled author-supplied value. For email, include the verified recipient address, subject line, body assembly order, paste-versus-attach rules, attachment filenames and formats, and the final sending sequence. Record source URLs or email provenance and dates.

Always add a `Sample material` section to the on-demand manifest, even when the agent requests none. Record the verified page or chapter quantity, source-manuscript identity and version, exact start and end locators, delivery mode (`append-to-email`, `paste-into-field`, `upload`, or `attach`), required filename and format when applicable, and status (`prepared`, `author-supplied`, `not-requested`, or `missing`). Preserve manuscript order. In the submission instructions, identify the exact form field or upload slot, or the exact email-body insertion point relative to the query letter, synopsis, and closing; state explicitly whether to append, paste, upload, or attach the sample.

For a page-count sample, render the designated manuscript in its submission format to establish the hard physical-page limit, then use `scripts/sample_boundary.py` to build and validate the text sample. Never exceed the requested page count and never end with a partial sentence or paragraph. When the last permitted page cuts through a paragraph, omit that entire paragraph and end at the preceding complete paragraph. Save `sample-boundary.json` in the package and record the requested page count, physical cutoff, rollback decision, effective end locator, and validation result in the manifest and submission instructions. A failed boundary validation forces `not-ready`.

Do not produce generic advice such as "follow the agency guidelines." Make the instructions sufficient for the author to submit without reopening the research. If the official sources omit, conflict on, or obscure a material step, state the conflict and exact unresolved decision in the instructions, mark the package `not-ready`, and do not guess. Remind the author that sending remains a separate action requiring explicit authorization.

Treat `static/master-query-letter.md` as a factual coverage baseline, not a prose template. Draft each agent-specific query fresh from the approved ledger, positioning, metadata, biography, and comparisons. Before drafting, identify internally the agent's two or three strongest documented taste signals, the corresponding manuscript elements, and the best hook and rhetorical emphasis; generate at least two candidate openings internally and keep only the stronger one. Do not save the alternatives or create another artifact. Agent evidence may reshape the hook, emphasis, paragraph order, register, and emotional focus, but may not introduce or exaggerate facts, relationships, motives, credentials, comparisons, or market claims. Revise and reconfirm affected static state first when a general-package change is needed.

Make the selected opening a compact query pitch, not a synopsis-like story brief: normally use one short paragraph of two to four sentences to establish the protagonist, destabilizing problem, and immediate pressure or stakes. Apply this gate to the entire story-pitch block, not only its first paragraph. When the guidelines do not request a synopsis, normally keep that block to one or two short paragraphs containing only the turns needed to frame the central opposition, consequential choice, and stakes; omit resolution history, climax mechanics, and chains of discoveries. If the block could stand alone as a condensed synopsis, compress or reframe it before packaging. Place credible personalization before the pitch or in the transition to metadata rather than burying it after a multi-paragraph plot summary. Omit the separate synopsis and any synopsis substitute while still providing the short description or query pitch the guidelines request.

Keep every agent-facing draft as temporary working text outside the `agent-package/` archive tree until all tailoring and factual corrections are complete. Then run a final prose gate on the exact text to be packaged: reread every full sentence for grammar, parallelism, modifier attachment, pronoun antecedents, idiom, punctuation, semantic ambiguity, and natural rhythm. Never validate only the changed phrase. Any later wording change invalidates this gate and the claim audit; repeat both on the final text before copying it into `agent-package/`. Do not package a query, synopsis, email body, or form answer until both checks pass.

If verified guidelines request a synopsis, generate `agent-package/<agent-slug>/synopsis.md` under the [analysis handoff's drafting rules](references/manuscript-analysis-handoff.md). Verify the pinned external ledger is approved, synopsis-ready, gate-passed and bound to unchanged source. Match the requested length/format/delivery, include the ending and audit every atomic claim. Do not copy the neutral analysis synopsis, read a prior on-demand product or require separate synopsis approval. Preserve causal/emotional movement rather than exporting ledger rows. Route gaps to manuscript-analysis and do not generate a submission synopsis when the guidelines do not request one.

### 8. Validate

Check:

- that the external manuscript-analysis package passed its source/evidence audit and matches the analysis/ledger/review identities pinned in the static manifest;
- that its review records are synchronized, bound to the exact ledger/manuscript revisions and contain one atomic `HG` unit per required proposition;
- that the complete approval sheet was presented, every synopsis-eligible `HG` unit received an explicit item-level disposition, every response was persisted, corrections were propagated, and dependent approvals were invalidated and re-reviewed;
- that ledger status is not `approved` and synopsis readiness is not `ready` unless no human-review unit remains pending, correction-required, or invalidated and the author explicitly gave final closure;
- during query or synopsis generation, every story claim through an atomic-claim audit: split each sentence into factual clauses and map every material clause to structured story-ledger IDs and their recorded locators without reopening an unchanged manuscript;
- that the shared ledger satisfies [the handoff contract](references/manuscript-analysis-handoff.md), is approved and matches the current manuscript identity;
- that facts, character beliefs, inferences, and ambiguities retain their evidentiary status and degree of certainty;
- that no causal relationship rests only on narrative adjacency;
- that entity identity, chronology, object provenance, motives, knowledge states, revelation timing, and ending remain accurate;
- title, category, genre, word count, and series language across all files;
- that category, genre, target readership, prose essence, story type, and query emphasis remain supported by the novel;
- that the query foregrounds character, conflict, choice, and stakes rather than explaining the whole world;
- that no query/submission synopsis exists outside an authorized specific-agent package; the separate neutral analysis synopsis is not a submission artifact or drafting authority;
- that each generated submission synopsis was requested by verified guidelines, matches their length/format and includes the ending and major causal turns;
- that every synopsis claim derives from the approved structured story ledger and passed the atomic-claim audit without requiring a separate synopsis approval or raw-manuscript reread;
- that biography claims are relevant and supported;
- that comparable titles are real, suitable, and not presented as guarantees;
- that named-agent status and requirements come from current official sources;
- that every actively ranked agent is currently eligible, supported by cited evidence, and ordered using manuscript criteria plus author-approved intake information when such information was available;
- that rankings omit author-side claims when author information was not supplied with the manuscript, and never treat missing credentials, platform, identity, or connections as negative evidence;
- that closed, uncertain, or hard-conflict candidates are separated from the active query order;
- that every manifest contains a `Sample material` record with the verified quantity, source boundary, delivery mode, format, and status, including `not-requested` when applicable;
- that every page-count sample remains within the rendered page limit, ends at a complete sentence and paragraph, and has a passing `sample-boundary.json` report produced by `scripts/sample_boundary.py`;
- that no placeholder remains hidden in a submission-ready file;
- that every on-demand ZIP contains `package-manifest.md` binding it to the static package and manuscript source, declaring `Build mode: fresh-reproduction` and `Prior on-demand source: none`, listing every archive artifact, recording the sample material, and recording agent research dates, readiness, and validation results;
- that the package was assembled from an empty staging directory without reading, extracting, copying, or editing any prior on-demand output, and that `scripts/validate_on_demand.py --new-zip` passes before delivery;
- that `query-package/on-demand/` contains only complete `agent-package-<agent-slug>.zip` deliverables and passes `scripts/validate_on_demand.py --root`;
- that every on-demand ZIP contains `submission-instructions.md` with a verified direct website or email route, source provenance and date, and exact numbered steps;
- that website instructions map the sample to the exact field or upload slot, and email instructions identify the exact point where the sample is appended relative to the query letter, synopsis, and closing, with attachment names, formats, and paste-or-attach rules;
- that the instructions identify agency concurrency rules, response policy, post-submission tracking, and any unresolved conflict, and are usable without returning to the research sources;
- that every on-demand ZIP corresponds to a separate explicit build, rebuild, or regenerate-complete-package request naming its target agent;
- that each agent-specific query is drafted fresh from approved static facts and treats the master query only as a coverage baseline;
- that the query's entire story-pitch block, not only its opening paragraph, remains a compact forward-driving pitch; uses no more plot turns than needed to frame the central opposition, consequential choice, and stakes; could not stand alone as a condensed synopsis; and reflects agent research beyond the salutation or first sentence;
- that the exact final text of every agent-facing prose artifact passed the final prose gate after its last wording change, and that its claim audit was rerun afterward;
- that the synopsis connects causes, choices, and consequences around the protagonist rather than primarily enumerating characters, discoveries, and revelations;
- that every general output is beneath the selected project-root or Codex-artifact `query-package/static/` tree, every agent package is an unversioned ZIP beneath its `query-package/on-demand/` tree, and no loose file or staging directory exists there;
- that no query output was written inside an editorial-process subfolder and no source manuscript or editorial-process output changed;
- that no editorial-process output was read as evidence.

Mark the package `not-ready` if it is incomplete, was derived from or edited from any prior on-demand output, lacks the fresh-reproduction declarations, or fails `scripts/validate_on_demand.py`; if the story-ledger human gate is incomplete or mismatched; if any agent-facing prose artifact lacks a final prose-gate pass after its last wording change; if any material story clause lacks manuscript support and its required individual author confirmation; if a required agent-specific synopsis is missing or fails the claim audit; if required sample material is missing, exceeds its page limit, ends with a partial sentence or paragraph, lacks a passing boundary report, or its source boundary and placement cannot be verified; or if the current submission route and actionable steps cannot be verified. Polished prose, internal consistency, paragraph-level ID mapping, and blanket author approval cannot override this failure. Otherwise mark it `ready` or `ready-with-open-items`, with a short reason.

## Revision and On-Demand Packages

When the author requests revisions to static state, show a compact freshness summary, reuse established static prerequisites by default, regenerate only affected static artifacts, and update the static manifest. Do not run the full flow unless the author explicitly requests a full static refresh. If provenance or a changed manuscript blocks safe static reuse, mark the static artifacts `not-ready` and ask for refresh authorization. Never revise an on-demand product incrementally: a request to change, rebuild, or regenerate a named agent package must reproduce the complete package without reading the prior product.

A story-ledger correction belongs to manuscript-analysis, which invalidates affected review units/dependents and requires re-review and renewed closure. Querying marks affected static drafts and products unusable, then repins only after that gate passes. Corrections to pitch, metadata, biography, comparisons or positioning also invalidate affected packages. Never use an existing on-demand product as a rebuild source. Reproduce a complete ZIP only after a new authorized named-agent request and a valid current static package and analysis gate. Fresh synopsis prose needs a new claim audit, not separate author approval or a raw-source reread.

Only after the author explicitly asks to build, rebuild, or regenerate the complete package for a named agent:

1. exclude all prior on-demand files and ZIPs from context and create an empty staging directory outside `query-package/on-demand/`;
2. verify that the agent is currently open to the book's category;
3. use official guidelines as the controlling source;
4. use the pinned approved external manuscript-analysis ledger as the sole story source, and approved static query metadata, comparisons, positioning and biography for the remaining content;
5. acquire and record current agent evidence, including official source URLs or official email provenance and dates, and the required sample material and its exact placement, in `package-manifest.md` and `submission-instructions.md`;
6. draft the query and any requested synopsis as temporary working text with the fresh-tailoring and narrative-quality rules in Step 7;
7. after the last factual or rhetorical edit, run the final prose gate and rerun the claim audit on the exact final text; only then copy agent-facing prose into `agent-package/`;
8. create every remaining required package artifact fresh, including `synopsis.md` only when the verified guidelines request it, and declare the non-reuse build mode in the manifest;
9. create and validate the complete staged ZIP with `scripts/validate_on_demand.py --new-zip`, then atomically place it at `<project-root>/query-package/on-demand/agent-package-<agent-slug>.zip` or deliver the equivalent Codex artifact;
10. validate the on-demand root with `scripts/validate_on_demand.py --root`, remove staging, and never leave loose output in `query-package/on-demand/`;
11. do not inspect Git, stage or commit the package unless separately asked, or write or extract the package inside an editorial-process subfolder;
12. omit personalization when no credible connection exists;
13. never imply referral, acquaintance, request, or enthusiasm that is not documented;
14. update and reconfirm the static package first if the requested variant exposes a static-package problem, then reproduce the complete package from that revision.

Do not treat a query-letter request, synopsis request, shortlist selection, or tailoring discussion as on-demand authorization; the author must ask to build, rebuild, or regenerate the complete package for a named agent. When reusable static artifacts exist, do not repeat the full flow or ask a generic refresh question. Never read a prior on-demand synopsis or package into context. Do not require separate approval for a synopsis freshly generated from the approved ledger; stop only when its drafting reveals an underlying unsupported claim, consequential inference, or unresolved ambiguity that must be corrected in the ledger.

## Completion Boundary

A complete package means one freshly reproduced ZIP contains every artifact needed to execute the named agent's currently verified submission: mandatory manifest, query letter, claim audit, customized instructions, and all applicable synopsis, sample, boundary-report, form-answer, email-body, and attachment files. No required component may be delivered separately or left loose in `query-package/on-demand/`. It does not mean the manuscript is publication-ready, the agent is a good fit, representation is likely, or a submission has been sent.
