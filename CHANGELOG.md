# Changelog

All notable dataset and documentation changes are recorded here.

## [1.1.0] — 2026-11-17

### Dataset changes

- Patched the existing v1.0 dataset without regenerating the original documents.
- Updated CORD ground truth to use only the `total.total_price` annotation.
- Set CORD `supplier`, `date`, and `invoice_number` fields to empty strings.
- Set CORD `quality` to `unassessed`.
- Added `annotations.origin_language="id"` to CORD records.
- Added `annotations.label_version="v1.1"`.
- Added measured `annotations.image_width` and `annotations.image_height` metadata.
- Excluded 28 CORD records without an annotated total.
- Reviewed 29 cross-split candidate pairs: 26 pairs were marked duplicate and 3 were marked different, resulting in 24 unique cross-split CORD record removals.
- Separately removed `cord_train_00058` from validation and `cord_train_00285` from training to reproduce the historical manual duplicate-review decisions.
- Tagged synthetic test records from `ar_commercial` and `mixed_bilingual` with `annotations.holdout_template=true`.
- Applied the patch consistently to the three split JSONL files and their three OCR output counterparts.
- Created `.v1_0.bak` backups before modifying the existing files.
- Rebuilt `data/splits/split_report.csv`.

### Released dataset statistics

| Split | CORD | Synthetic | Total |
|---|---:|---:|---:|
| Train | 781 | 1,959 | 2,740 |
| Validation | 121 | 367 | 488 |
| Test | 44 | 1,174 | 1,218 |
| **Total** | **946** | **3,500** | **4,446** |

- Original CORD records: 1,000.
- CORD records excluded for missing totals: 28.
- Additional CORD records removed during duplicate review: 24 cross-split records plus 2 separate historical manual removals (26 records total).
- Retained synthetic records: 3,500.
- Synthetic holdout-template records tagged: 1,051.

### Validation

- Confirmed all six split and OCR-output JSONL files passed dataset validation with zero errors.
- Confirmed CORD ground-truth structure and annotation policy.
- Confirmed image dimension metadata is present.
- Confirmed no empty ground-truth records remain.
- Confirmed holdout-template tags are correct.
- Confirmed split and OCR output record counts match after the duplicate removal.
- Re-ran the leakage checker: no cross-split document-ID or image-content leakage. It reports 26 same-split duplicate-image groups; these are not cross-split leakage.

- Reproduced v1.1 from the v1.0 backups in an isolated directory using `patch_v1_1.py`, the historical manual removals, and `cord_dedupe.py`.
- Restored the historical deduplication decisions: 26 duplicate pairs and 3 different pairs, resulting in 24 unique cross-split removals.
- Compared document-ID sets against the validated dataset: exact match for train (2,740), validation (488), and test (1,218); zero missing or extra IDs.

### Documentation

- Updated `README.md` with the v1.1 dataset inventory and corrected counts.
- Updated `docs/data_contract.md` to document the v1.1 schema and annotation policy.
- Updated `docs/datasets_licenses.md` to distinguish included datasets from candidates not included in v1.1.
- Documented outstanding dataset and font-license verification requirements.

### Not included in v1.1

- SROIE
- CORU / ReceiptSense
- HF Invoices
- FUNSD
- Separately collected real documents

---

## [1.0.0] — 2026-10-24

Initial dataset contract and dataset release baseline.

See the v1.0 backup files (`.v1_0.bak`) for the original split and OCR JSONL artifacts.
