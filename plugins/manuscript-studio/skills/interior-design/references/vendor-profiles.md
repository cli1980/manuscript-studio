# Vendor profiles

The bundled [IngramSpark profile](../profiles/ingramspark.json) contains shared
interior rules and paperback/hardcover variants. Resolve the variant from the
user's binding after selecting IngramSpark; do not ask for a second profile ID.
Do not infer that a vendor has been selected from the manuscript.

For standalone use, obtain the exact snapshot without a workflow:

```text
python scripts/vendor_profiles.py --binding hardcover
```

Copy the supplied/resolved snapshot into `vendor_profile`, or use null if no
vendor was selected. It includes profile/version/variant identity, source
provenance, rules, DOCX guidance and a canonical SHA-256 of `data` (UTF-8 JSON,
sorted keys, compact separators). Preserve it exactly. Each vendor production
target names the same vendor and binding, matches the proposed page trim and
references `{ "locator": "vendor_profile/data", "sha256": "<snapshot sha256>" }`.

Use applicable rules when proposing geometry and explaining choices. Preserve
the distinction between vendor requirements, recommendations and Studio
guidance. The safety recommendation includes the actual binding-side allowance:
inside margin plus additional gutter. A profile does not prescribe a body font
or an invented extra hardcover gutter. Cover/board/jacket dimensions are not
interior page dimensions.

Custom-trim ranges are sourced, binding/paper-specific reference data, not a
complete standard-product matrix or proof of availability. Report conflicts
and unknown combinations, including hardcover construction, for confirmation.
The validator returns advisory geometry/bleed warnings without turning
recommendations or incomplete catalog coverage into hard vendor prohibitions.

Font embedding, applicable PDF standard, color, bleed, page count and other
rendered-output checks remain unresolved until supported evidence exists.
Do not turn these technical checks into author approval questions. Profile
selection and design approval do not establish compliance or human page approval.
