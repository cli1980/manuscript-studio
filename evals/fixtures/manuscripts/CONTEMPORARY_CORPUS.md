# Contemporary corpus text license and provenance

The Chinese excerpts under `contemporary-*/` and their English counterparts in
`evals/cases/literary-translation/zh-en-contemporary-*/` were imported from the
local `contemporary_corpus/contemporary_pairs.jsonl` collection.

These texts are licensed under **Creative Commons Attribution-ShareAlike 3.0**
([license](https://creativecommons.org/licenses/by-sa/3.0/)). They are not public
domain and are not covered by the repository's MIT license for code and skills.
Keep the recorded author and translator credits, source URLs, license link, and
modification notices with copies of these materials. Redistribution and adaptations
must follow the attribution and share-alike terms.

Individual `passage.json` and `case.json` files retain the corpus's attribution,
source credits, URLs, retrieval date, source snapshot hash, extraction range, and
AI alignment-review notes. Where a translator was not separately named, the
original credit note and English page-history URL are retained instead of an
inferred identity.

The import made no wording, punctuation, paragraph, or whitespace changes to the
Chinese and English strings in the corpus JSONL. The upstream collection had
already removed HTML, navigation, footnote markers, and formatting directives and
normalized typography; its modification notices are retained in metadata.
No source illustrations or HTML snapshots are part of the imported evaluation data.

The source collection records license links on both language pages. The importer
checks the supplied license records, saved source flags, and snapshot hashes.
This preserves the collection's rights evidence; it is not a new legal
determination about model training or generated outputs.

The [import manifest](../../imports/contemporary-corpus/manifest.json) maps all
50 pairs to their case and passage files and records their text hashes.
