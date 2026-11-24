# Person 1 Final Closure Status — v1.1

**Audit date:** 2026-11-24
**Working branch:** `audit/remediation-v1.1`
**Base commit:** `0d1e394` (`docs: correct v1.1 dataset documentation`)
**Publication scope:** Person 1 remediation only; intended for the existing `audit/remediation-v1.1` branch. No changes to `main`, release publication, or tag movement are in scope.

## Release identity and integrity

- Authoritative archive: `OCR_Dataset_v1.1_Full_Handoff.zip` (454,814,485 bytes; approximately 434 MiB), held externally in Google Drive.
- SHA-256: `0f7adb93c6617e47081b0dffbb4dd3d4a40106bcc22751d93bfedfe04cfc3608`.
- Reproducible ZIP audit: [`evidence/archive_audit_v1.1.json`](evidence/archive_audit_v1.1.json) reports matching expected hash, valid CRCs, 4,563 archive members, 4,532 image members, zero traversal paths, and `PASS`. All 4,446 canonical image references exist; 86 image members are not referenced by canonical splits (54 in `data/processed/images`, 32 in `data/review/dup_pairs`). These extras are inventory findings, not missing canonical images, and were not altered.
- Canonical split counts: train 2,740 (781 CORD / 1,959 synthetic), validation 488 (121 / 367), test 1,218 (44 / 1,174); total 4,446 (946 CORD / 3,500 synthetic). Recomputed split proportions: 61.63% / 10.98% / 27.40%.
- 4,446 unique record IDs; no duplicates across canonical splits; zero missing referenced image members; zero schema errors under the clarified v1.1 contract. All three OCR-output files match the corresponding split ID sets and record counts exactly.
- All three canonical splits and all three OCR-output files were run through the hardened validator with image decoding enabled: 8,892 records parsed, **0 errors**. Complete output: [`evidence/release_validation_v1.1.txt`](evidence/release_validation_v1.1.txt).
- Existing leakage checker ran against actual extracted release files: no document-ID or cross-split image duplicates, 4,446 images checked, zero missing; both reserved templates are test-only. Complete output: [`evidence/leakage_check_v1.1.txt`](evidence/leakage_check_v1.1.txt).
- The archive contains older `.bak`, `.pre_dedupe.bak`, and `.v1_0.bak` files. They were not treated as canonical splits and were not changed.

## Validator and tests

The validator now fails on malformed JSON lines and non-object JSON records; verifies required top-level and nested contract types; checks duplicate IDs within a file; detects empty, absolute, and traversal image paths; and, with `--check-images`, verifies that referenced images exist and decode. Empty ground-truth strings and localized date/total display strings remain allowed. The frozen contract specifies string types but no canonical date or amount grammar, so the validator deliberately does not invent one.

A contract scope discrepancy was resolved from source and archive evidence: all **946 CORD** rows have `annotations.label_version="v1.1"`; all **3,500 synthetic** rows omit that marker. The patch history describes the label-version marker as part of the CORD v1.1 patch, while the generator's original synthetic records did not add it. The contract now states this source-specific scope: image dimensions are required throughout; label version is required for patched CORD and must equal `v1.1` whenever present. No archive record was amended.

Permanent regression tests: **19 passed** under the clean pinned environment. They cover valid localized records, CORD empty fields, malformed JSON and non-object records, required/missing and invalid nested fields, bad date/total types, duplicate IDs, image absence/corruption, invalid paths, and font mapping. Complete output: [`evidence/regression_tests_final.txt`](evidence/regression_tests_final.txt).

## Dependencies

- [`requirements.in`](../requirements.in) records direct data-pipeline dependencies.
- [`requirements.txt`](../requirements.txt) is a fully pinned environment lock resolved on Python 3.12.3. It covers repository data processing, validation, synthetic generation, and EDA. OCR engine model stacks remain mode-specific/optional in the OCR notebook because their system, GPU, and framework compatibility differs.
- A fresh Python 3.12.3 virtual environment installed the lock successfully; `pip check` found no broken requirements; declared core imports passed; the 19-test suite passed. Full install/test transcript: [`evidence/clean_install_and_tests.txt`](evidence/clean_install_and_tests.txt).

## Arabic-Indic investigation

The archive has 1,076 flagged synthetic rows, and the flag agrees with Arabic-Indic digit occurrence in ground truth for all synthetic records. That is **1,076 / 1,970 Arabic-language synthetic rows = 54.6193%**, and **1,076 / 3,500 synthetic rows = 30.7429%**. The latter denominator explains why an overall-synthetic figure is near 30%; it does not explain the mismatch between the configured `ARABIC_INDIC_RATIO = 0.30` conditional target and the observed 54.62% among Arabic records. Generation RNG/source provenance and any selection history needed to explain that difference are unavailable. No cause is asserted. Calculation and reproduction command: [`arabic_indic_audit.md`](arabic_indic_audit.md).

## Font annotations and licensing

The font branch (`fix/font-annotation`, commit `5501477`) was inspected but not merged. Its template-specific map is consistent with CSS family declarations and is implemented locally through a tested helper. The release archive retains its generic historical annotations: notably `ar_commercial` and `mixed_bilingual` records do not show the more specific declared CSS stacks. The frozen archive was not changed. The record annotation now means the declared CSS family/stack, not a proven render-time resolved font. No exact font binaries, versions, browser logs, or pixel-level font verification were available.

Licensing remains unresolved: the repository does not provide evidence sufficient to confirm CORD source terms or the exact third-party font copies/notices and redistribution rights. No commercial-use, redistribution, or sublicensing clearance is claimed. The license inventory preserves those limitations. See [`font_annotation_audit.md`](font_annotation_audit.md) and [`datasets_licenses.md`](datasets_licenses.md).

## Documentation reconciliation

The old `docs/DATA_LEAD_DELIVERY_REPORT.md` figures (6,324 total and 3,888 / 486 / 1,826 splits) are preserved but prominently labeled as a historical Dataset v1 snapshot. The v1.1 manifest and README use the verified archive counts and split percentages. The README no longer claims the validator proves semantic date validity or positive totals, and it does not present the license inventory as clearance.

## Release and Git safety

- At the final pre-publication integrity review, `audit/remediation-v1.1` was based on remote tip `0d1e394`; `main` was not modified.
- This audit records artifact verification, not the later Git operation result. The commit and push status is verifiable in the branch history.
- No merge to `main`, tag movement, release publication, or history rewrite is part of this remediation.
- `v1.1.0` remains the existing annotated tag object `7f79349017b71a41428c8bb3c7edf4bbd43671dc`, peeled to commit `1d9b4f200eba5716611c79cc03fb51e89300054c`.
- Archive checksum was checked before and after the work and remains the value above. The archive was only read, never modified.

## Remaining blockers

1. Explain the Arabic-Indic conditional-rate deviation only if generation RNG/source provenance or selection history can be supplied.
2. Verify CORD and exact font/asset permissions from authoritative terms and versioned source artifacts before making any licensing or commercial-use claim.
3. Determine actual rendered font faces only if font files, browser loading/render logs, or suitable image/font evidence become available. The committed metadata correction is for future generated records and does not retroactively fix the frozen archive.
