# Dataset v1.1 Release Manifest

**Release date:** 2026-11-17
**Version:** 1.1.0
**Status:** Patched and validated
**Storage:** External to this Git repository (Google Drive)

## 1. Dataset composition

The v1.1 release contains 4,446 records.

| Split | CORD | Synthetic | Total |
|---|---:|---:|---:|
| Train | 781 | 1,959 | 2,740 |
| Validation | 121 | 367 | 488 |
| Test | 44 | 1,174 | 1,218 |
| **Total** | **946** | **3,500** | **4,446** |

## 2. Included sources

- **CORD v2:** 946 retained receipts from the original 1,000 records.
  - 28 records were excluded because no annotated total was available.
  - 24 unique cross-split duplicate records were removed after reviewing 29 candidate pairs (26 marked duplicate, 3 marked different).
  - Two additional records (`cord_train_00058` and `cord_train_00285`) were removed through separate historical manual duplicate-review steps.
  - Only `total.total_price` is retained as ground truth.
  - Supplier, date, and invoice number are empty.
  - Quality is `unassessed`.
  - `annotations.origin_language` is `id`.
- **Synthetic documents:** 3,500 generated records.

## 3. Split and holdout policy

- `ar_commercial`: 654 records; `mixed_bilingual`: 397 records (1,051 total).
- Both templates are reserved for the final test split.
- Records are tagged with `annotations.holdout_template=true`; their template names are stored in `annotations.template_id`.
- All 1,051 records have `source_split="train"`, representing their original synthetic generation split. Their final split is determined by the JSONL file containing them.
- The other six synthetic templates are distributed across the splits according to the dataset split procedure.

## 4. Validation results

- All three split JSONL files passed dataset validation with zero errors.
- All three OCR output JSONL files passed dataset validation with zero errors.
- All referenced images in the six validated JSONL files were found and opened successfully.
- Split and OCR output record IDs match exactly.
- No document-ID leakage across splits was detected.
- No identical image content was found across different splits.
- The latest leakage check confirmed zero cross-split image duplicates. Same-split duplicate images, if present, should be considered when interpreting training and evaluation results.

## 5. Files

The dataset itself is stored outside this Git repository.

Expected data artifacts:

- `data/splits/train.jsonl`
- `data/splits/val.jsonl`
- `data/splits/test.jsonl`
- `data/splits/split_report.csv`
- `ocr_output/train_with_ocr.jsonl`
- `ocr_output/val_with_ocr.jsonl`
- `ocr_output/test_with_ocr.jsonl`

The repository contains the validation and leakage-check scripts used to verify these artifacts.

## 6. Exclusions

SROIE, CORU / ReceiptSense, Hugging Face Invoices, FUNSD, and separately collected real documents are not included in this v1.1 release.

## 7. Related documentation

- [README](../README.md)
- [Data Contract](data_contract.md)
- [Dataset License Inventory](datasets_licenses.md)
- [Changelog](../CHANGELOG.md)

**License note:** Refer to `datasets_licenses.md`. CORD licensing and synthetic-font redistribution permissions remain subject to verification. This manifest does not grant additional usage rights.
