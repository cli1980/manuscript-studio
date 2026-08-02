---
name: literary-agent-querying
description: Build complete literary-agent query packages for novels through manuscript-grounded positioning, claim-level evidence control, web research and priority ranking of suitable agents, a guided author interview, package drafting, customized website-or-email submission instructions, and agent-specific validation. Use when Codex needs to identify and rank agents for a novel; prepare or revise a fiction query letter, hook, synopsis, author bio, book metadata, comparable-title positioning, series overview, submission checklist, or explicitly requested tailored agent submission; gather missing information through dialogue; adapt the workflow to any fiction genre, prose style, audience, or book length; and deliver static general materials and on-demand agent packages only through Codex task artifacts or Outputs, outside Git control.
---

# Literary Agent Querying

Build a truthful, manuscript-grounded query package through a short guided dialogue. Keep the workflow lighter than an editorial review: acquire the necessary facts, confirm the positioning, draft the package, and validate it against the intended market or named agent.

## Governing Rules

1. Treat the author as the authority on intent, identity, publication history, rights, and career goals.
2. Read the complete supplied novel and existing pitch materials before asking questions they already answer. Treat positioning derived from an incomplete manuscript as provisional.
3. Ask only questions that materially affect the package. Use short conversational rounds organized by topic, not one long form.
4. Do not invent story facts, credentials, comparable titles, market claims, personalization, submission requirements, or rights status.
5. Distinguish an inference from an author-confirmed fact. Ask for confirmation before using a consequential inference.
6. Adapt recommendations to the book's actual category, genre, length, voice, structure, and intended market. Do not force every novel into one pitch formula.
7. Describe a book as `standalone with series potential` only when its principal dramatic movement resolves sufficiently on its own. Otherwise state its series dependency honestly.
8. Reveal the ending in the synopsis. Do not reveal it in the query pitch unless doing so is necessary to represent the premise accurately.
9. Follow each named agent's current official submission requirements exactly. Browse official agency or agent sources when current requirements or market status matter.
10. Treat agent rankings as evidence-based priorities, not guarantees of fit or representation. Use official agent or agency sources to verify identity, categories, exclusions, submission status, and requirements. Use reputable interviews or deal records only as supplementary fit evidence, and record source dates. Factor relevant, author-approved information into selection and ordering only when it was supplied or acquired with the manuscript at intake. Otherwise omit author-side factors rather than guessing, requesting disclosure solely for ranking, or treating missing credentials, platform, identity, or connections negatively.
11. Prepare materials only. Do not submit a query, contact an agent, upload a form, or send a message without separate explicit authorization.
12. Write all generated outputs only to the environment-provided Codex task-artifact or Outputs facility. Never write, stage, commit, or version query outputs in Git, the manuscript project, an editorial repository, or an editorial-process folder.
13. Preserve the two output categories defined in [references/package-spec.md](references/package-spec.md): `query-package/static/` for general information and `query-package/on-demand/` for explicitly requested named-agent ZIP packages.
14. Read manuscript and supporting inputs only from paths or attachments explicitly designated for this querying job. If a designated input is inside an editorial-process output folder, ask for an allowed source copy or attachment instead of reading it. Never use editorial assessments, normalized editorial manuscripts, proposals, style sheets, continuity records, reports, or exports as query evidence.
15. Treat manuscript sources as read-only evidence. Existing pitches, previous query drafts, model-generated summaries, and package prose are leads to verify, not factual authorities.
16. If no task-artifact or Outputs destination is available, return the applicable material in clearly labeled chat sections and state that persistent artifact writing was unavailable. Do not redirect it into any Git repository, manuscript project, or editorial-output folder.
17. Derive category, genre, target readership, prose essence, story type, tone, and reader promise from manuscript evidence. Use author input to confirm or correct the analysis, not as a substitute for reading the novel.
18. Do not create a named-agent package or agent-tailored query letter unless the author explicitly requests it and identifies the target agent. A shortlist entry, priority selection, named-agent discussion, or request for general agent research is not authorization to create one.
19. Deliver each explicitly requested named-agent result as an unversioned downloadable ZIP beneath `query-package/on-demand/`. Include the mandatory customized submission instructions and preserve the tailored internal layout defined in [references/package-spec.md](references/package-spec.md).
20. Do not state an inference, character belief, or ambiguity as objective fact. Do not assert causation from narrative adjacency, merge distinct entities or events for compression, or assign knowledge or motives to a character or faction without evidence.
21. When prerequisite query information already exists in the current conversation or an approved query-package state, show the author what would be reused and ask whether it needs refreshing before continuing. Do not silently reuse it or repeat the full intake. Reverify time-sensitive agent status and submission requirements regardless.
22. Treat the approved manuscript fact ledger as the reusable, agent-neutral source of truth. Do not create a static synopsis. Generate a synopsis only inside an explicitly requested named-agent package when that agent's verified guidelines require one or the author explicitly requests one. Ground it in the approved ledger, validate it without a separate synopsis-approval gate, and match the target agent's requested length and format.
23. Make every named-agent package independently usable. Include `submission-instructions.md` with a current official website or form route, or an official submission email supplied or verified from the agent or agency; provide exact numbered actions and map every requested field, pasted item, and attachment to the package. Mark the package `not-ready` when no current, unambiguous submission route can be verified.

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
- current task-artifact or Outputs destination.

Create durable state only beneath the artifact destination. General materials go beneath `query-package/static/`; named-agent results go beneath `query-package/on-demand/` only when explicitly requested. Record the artifact workspace identity in `query-package/static/package-manifest.md`. Do not inspect Git merely because a designated manuscript or editorial repository happens to contain it.

Read [references/questionnaire.md](references/questionnaire.md) in full before interviewing the author. Read [references/package-spec.md](references/package-spec.md) in full before drafting or validating outputs.

If the manuscript is unavailable, the skill may still build a package from the author's answers, but label all manuscript-dependent conclusions `author-supplied` and identify what remains unverified.

Before beginning a new intake, inspect the current conversation and allowed query-package state for already established prerequisites. These include manuscript identity and checksum, completion state, title, word count, language, market, publication and representation history, rights status, series architecture, approved fact ledger, positioning, biography, and comparisons. If any exist, present a compact freshness summary containing the source or approval date when available, changed-source indicators, open items, and the exact fields proposed for reuse. Ask the author whether to:

- reuse the established prerequisites as they stand;
- refresh all prerequisite information; or
- refresh named fields only.

Pause for the answer unless the author's current request already explicitly selects one of those actions. A refresh decision never permits stale agent research: reverify current agent status, agency rules, and submission requirements whenever preparing a named-agent result.

### 2. Derive the positioning profile

Before asking the author to classify the book, analyze the complete novel and propose:

- category and genre or subgenre;
- target and crossover readership;
- prose essence, including register, cadence, density, narrative distance, interiority, and tonal character;
- dominant story type or narrative engine;
- tone, themes, and reader promise;
- plausible comparable-title functions;
- the practical implication of each finding for the query's metadata, hook, emphasis, voice, and level of worldbuilding.

For each consequential classification, record manuscript evidence, confidence, and credible alternatives. Do not classify from character age, setting, isolated tropes, or word count alone.

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

Treat the shortlist as a research recommendation for author review. Do not generate or propose tailored variants automatically. Wait for a separate author request that explicitly asks for a tailored letter and identifies the target agent.

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
- named-agent requirements and personalization only after the author explicitly requests a tailored letter for an identified agent.

Permit `unknown`, `not applicable`, and `decide with me`. Offer reasoned options when the author is unsure, but do not silently select a consequential answer.

### 5. Confirm before drafting

Present a compact intake summary containing:

- confirmed facts;
- manuscript-derived positioning and its query implications;
- consequential inferences;
- unresolved items;
- proposed positioning;
- planned artifacts;
- proposed agent priorities and exclusions;
- any separately and explicitly requested tailoring target.

Ask the author to correct or approve the summary. Do not block on minor optional fields, but label omissions in the package manifest.

Before requesting approval, build a manuscript fact ledger in `query-package/static/intake-summary.md`. For every pitch-critical claim, record the proposed wording, claim type (`fact`, `character-belief`, `inference`, or `ambiguous`), manuscript location, confidence, and any required author confirmation. At minimum reconcile:

- opening situation, chronology, inciting event, objectives, opposition, stakes, final-act turn, choice, and ending;
- identities, aliases, ships, locations, artifacts, institutions, and programs that could be confused;
- object provenance and event sequence;
- each asserted causal connection;
- each important motive and each character or faction's knowledge at the relevant time;
- the timing and scope of major revelations.

Do not draft from memory or from an earlier generated summary. Draft story-side content only from the approved ledger. Author approval of positioning or the package as a whole is not blanket confirmation of an unlisted inference.

### 6. Generate the general package

Create the applicable static artifacts defined in [references/package-spec.md](references/package-spec.md). Always create a master query letter, author biography, book-positioning sheet, prioritized agent shortlist, submission checklist, package manifest, and the intake summary containing the approved manuscript fact ledger. Create a series overview when applicable. Do not create a general or static synopsis.

Derive story compression in the master query directly from the approved fact ledger and confirmed positioning. If the query requires a story claim or interpretation absent from the ledger, update the ledger and obtain confirmation only for the consequential new inference or resolved ambiguity before continuing.

Keep static materials independent of any single agent. Shape the query from the confirmed positioning profile: foreground the dominant story engine, use an appropriate amount of worldbuilding, align the pitch's register with the prose essence without imitating the novel, and select metadata and comparisons for the actual readership.

### 7. Generate an on-demand named-agent package

Create a named-agent result only after the author explicitly requests a package or tailored letter and identifies the target agent. Verify the agent's current official requirements before deciding which artifacts belong in the ZIP.

Always create `tailored/<agent-slug>/submission-instructions.md`. Use the target's current official website, official submission form, or an agent or agency email supplied by the author as the evidence source. Put a concise `Submit here` section first, followed by numbered actions that take the author from opening the form or composing the email through final review. For a web submission, include the direct URL and map each visible field to exact package content or a clearly labeled author-supplied value. For email, include the verified recipient address, subject line, body assembly order, paste-versus-attach rules, attachment filenames and formats, and the final sending sequence. Record source URLs or email provenance and dates.

Do not produce generic advice such as "follow the agency guidelines." Make the instructions sufficient for the author to submit without reopening the research. If the official sources omit, conflict on, or obscure a material step, state the conflict and exact unresolved decision in the instructions, mark the package `not-ready`, and do not guess. Remind the author that sending remains a separate action requiring explicit authorization.

Derive every story-side element of the tailored letter from the approved static package, especially `static/master-query-letter.md`, `static/book-positioning.md`, `static/author-bio.md`, `static/intake-summary.md`, and confirmed static package state. Add or change only agent-specific salutation, personalization, emphasis, ordering, formatting, and submission details supported by acquired agent evidence. Do not introduce new story facts, metadata, comparisons, biography claims, or positioning directly into a tailored result; revise and reconfirm the affected static state first when a general-package change is needed.

If the verified submission guidelines require a synopsis, or the author explicitly requests one for this agent, generate `tailored/<agent-slug>/synopsis.md` inside that agent's on-demand package. Match the required length, formatting, and paste-or-attachment instructions. Use only the approved fact ledger and confirmed positioning, include the ending, and audit every material atomic claim against the ledger and manuscript. Do not ask the author to approve the synopsis separately. If drafting exposes an unsupported claim, consequential inference, or unresolved ambiguity, correct the ledger and obtain only the confirmation required for that underlying ledger entry, then regenerate and revalidate the synopsis.

### 8. Validate

Check:

- every story claim through an atomic-claim audit: split each sentence into factual clauses and map every material clause to the fact ledger and its manuscript location;
- that facts, character beliefs, inferences, and ambiguities retain their evidentiary status and degree of certainty;
- that no causal relationship rests only on narrative adjacency;
- that entity identity, chronology, object provenance, motives, knowledge states, revelation timing, and ending remain accurate;
- title, category, genre, word count, and series language across all files;
- that category, genre, target readership, prose essence, story type, and query emphasis remain supported by the novel;
- that the query foregrounds character, conflict, choice, and stakes rather than explaining the whole world;
- that each generated synopsis was requested by the author or required by the target agent, matches that agent's verified length and format, and includes the ending and major causal turns;
- that every synopsis claim derives from the approved fact ledger and passed the atomic-claim audit without requiring a separate synopsis approval;
- that biography claims are relevant and supported;
- that comparable titles are real, suitable, and not presented as guarantees;
- that named-agent status and requirements come from current official sources;
- that every actively ranked agent is currently eligible, supported by cited evidence, and ordered using manuscript criteria plus author-approved intake information when such information was available;
- that rankings omit author-side claims when author information was not supplied with the manuscript, and never treat missing credentials, platform, identity, or connections as negative evidence;
- that closed, uncertain, or hard-conflict candidates are separated from the active query order;
- that requested page counts, attachment rules, form fields, and one-agent-per-agency policies are honored;
- that no placeholder remains hidden in a submission-ready file;
- that every named-agent ZIP contains `submission-instructions.md` with a verified direct website or email route, source provenance and date, and exact numbered steps;
- that website instructions map each requested form field to the exact file, text, or author-supplied value, and email instructions provide the recipient, subject, body order, attachment names, formats, and paste-or-attach rules;
- that the instructions identify agency concurrency rules, response policy, post-submission tracking, and any unresolved conflict, and are usable without returning to the research sources;
- that every tailored ZIP corresponds to a separate explicit author request naming its target agent;
- that each tailored letter derives its story, metadata, comparison, and biography content from the approved static package and differs only where verified agent evidence justifies tailoring;
- that every general artifact is beneath `query-package/static/` and every tailored result is an unversioned ZIP beneath `query-package/on-demand/`;
- that no query output entered Git control and no manuscript, editorial repository, or editorial-process output changed;
- that no editorial-process output was read as evidence.

Mark the package `not-ready` if any material story clause lacks manuscript support or separately recorded author confirmation, if a required agent-specific synopsis is missing or fails the claim audit, or if the current submission route and actionable steps cannot be verified. Polished prose and internal consistency cannot override this failure. Otherwise mark it `ready` or `ready-with-open-items`, with a short reason.

## Revision and Tailoring

When the author requests revisions, first show the established prerequisites and ask whether they should be reused or refreshed unless the request already makes that choice explicit. Preserve confirmed intake only after that refresh decision. Regenerate only affected artifacts and update the manifest.

Any correction to the fact ledger, master pitch, metadata, biography, comparisons, or positioning invalidates every on-demand package derived from the superseded static package. Regenerate a named-agent ZIP only after the corrected static package has passed validation and any required underlying fact or inference confirmation has been recorded. An agent-specific synopsis revision requires a new claim audit, not separate author approval.

Only after the author explicitly requests a named-agent package or tailored letter and identifies the agent:

1. verify that the agent is currently open to the book's category;
2. use official guidelines as the controlling source;
3. use the approved static query package as the sole source for story-side, metadata, comparison, and biography content;
4. acquire and record current agent evidence, including official source URLs or official email provenance and dates, in `submission-instructions.md`;
5. change only what the verified requirements or genuine personalization justify;
6. create `tailored/<agent-slug>/synopsis.md` only when the agent's verified guidelines require it or the author explicitly requests it, then package it when applicable with `tailored/<agent-slug>/query-letter.md` and the mandatory `tailored/<agent-slug>/submission-instructions.md` as `query-package/on-demand/tailored-<agent-slug>.zip` in the task-artifact or Outputs destination;
7. do not write or extract the tailored result in any Git repository, manuscript project, or editorial-process folder;
8. omit personalization when no credible connection exists;
9. never imply referral, acquaintance, request, or enthusiasm that is not documented;
10. update and reconfirm the static package first if the requested variant exposes a static-package problem, then derive the variant from that revision.

Do not treat an explicit named-agent tailoring request as permission to skip the prerequisite-refresh question. Do not require or seek separate approval for a synopsis generated from the approved ledger; stop only when its drafting reveals an underlying unsupported claim, consequential inference, or unresolved ambiguity that must be corrected in the ledger.

## Completion Boundary

A complete package means the applicable artifacts are internally consistent, evidence-grounded, and ready for author review. It does not mean the manuscript is publication-ready, the agent is a good fit, representation is likely, or a submission has been sent.
