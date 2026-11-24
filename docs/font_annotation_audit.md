# Synthetic Font Annotation Audit

**Status:** Future-generation annotation corrected locally; the frozen v1.1 archive is unchanged. Actual resolved/rendered font faces and third-party permissions remain unverified.

## Evidence and correction

The `fix/font-annotation` branch (`5501477`) was reviewed as a focused source change, not merged. Its per-template map is consistent with the template CSS in `scripts/generate_synthetic.py`:

| Template ID | Declared CSS family/stack |
|---|---|
| `en_modern` | Inter |
| `en_receipt` | Courier New |
| `ar_formal` | Cairo |
| `ar_receipt` | Amiri |
| `ar_commercial` | Noto Naskh Arabic |
| `mixed_bilingual` | Cairo + Inter |
| `mixed_receipt` | Cairo |
| `mixed_corporate` | Cairo + Inter |

The mapping was implemented as `font_annotation_for_template()` and covered by regression tests. The annotation means the family/stack declared by the selected template; it does not establish which font file or fallback Chromium actually resolved at render time.

The release ZIP's existing records still carry generic values: the archive inspection found `Cairo` on Arabic and mixed records and `Inter` on English records. In particular, the 654 `ar_commercial` test records remain annotated `Cairo` rather than the template's declared Noto Naskh Arabic, and the 397 `mixed_bilingual` test records remain annotated `Cairo` rather than `Cairo + Inter`. These data were not rewritten because the v1.1 archive is frozen and the user explicitly required preserving it.

The template CSS references Google Fonts remotely. The archive does not provide the exact resolved font binaries, their versions, browser/font-loading logs, or render-time fallback evidence. The inspected material therefore confirms a **metadata mismatch**, but it does not establish that glyphs in the released images were rendered with an unintended face. No pixel-level font diagnosis is claimed.

## Licensing and limitations

The repository's license inventory correctly leaves Cairo, Amiri, Noto Naskh Arabic, and other third-party asset permissions subject to verification. Since exact downloaded copies/versions and their notices are unavailable in the handoff, the remediation does not claim redistribution or commercial-use clearance. See [`datasets_licenses.md`](datasets_licenses.md).
