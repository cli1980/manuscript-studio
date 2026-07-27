# Style Sheet and Continuity Concordance

Maintain these records across the project so chapter-level work remains consistent and whole-book passes can reconcile global facts. Treat them as editorial evidence, not as an excuse to invent canon.

## Style sheet

Store approved and proposed conventions separately. Record:

- language variety, dictionary, and editorial references;
- punctuation, quotation, ellipsis, dash, and typography treatment;
- capitalization, hyphenation, compounds, abbreviations, and italics;
- numbers, dates, times, measurements, and currencies;
- names, titles, invented terms, place names, and special spellings;
- dialogue, thought, letters, messages, and foreign-language treatment;
- intentional nonstandard grammar, dialect, code-switching, and voice exceptions;
- chapter, scene-break, heading, note, and extract formatting;
- permissions or attribution conventions.

Each entry should include the rule or term, example, source location, status (`observed`, `proposed`, `approved`, or `superseded`), and notes. Only approved entries govern future changes.

## Continuity concordance

Track facts with source locations and status. Useful categories include:

- characters: names, appearance, age, relationships, history, voice, knowledge, and goals;
- chronology: dates, durations, sequence, travel time, seasons, and ages;
- locations: geography, layout, distance, access, and recurring description;
- world rules: technology, magic, institutions, terminology, and constraints;
- state changes: injuries, clothing, objects, evidence, weather, and resources;
- information flow: secrets, discoveries, promises, lies, and who knows what when;
- plot threads, motifs, callbacks, unresolved setups, and permissions items.

Use a stable entity or thread ID, the asserted fact, source location, status, and notes. Distinguish explicit text from inference. If sources conflict or the intended canon is unclear, create an editorial query; never choose a fact silently.

## Updating records

During verdict work, add observations and proposed conventions without converting them to approved canon. After the author approves and an application batch succeeds:

1. update affected entries to `approved` or `superseded`;
2. record the applying Git commit and proposal IDs;
3. propagate consequences to dependent records;
4. mark conflicting or location-sensitive verdicts stale when necessary.

Do not rewrite manuscript text merely to match a proposed style entry. The manuscript changes only through the approval workflow.

## Whole-book reconciliation

Before whole-book completion for line editing or copyediting, review the entire style sheet and concordance against all manuscript files. Resolve or clearly defer contradictions, recurring variants, timeline gaps, knowledge-state errors, and outstanding queries. Record what remains intentionally variable.
