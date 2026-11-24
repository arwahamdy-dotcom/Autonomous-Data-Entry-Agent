# Data Contract — v1.1

> **Status:** FROZEN for the v1.1 dataset release
> **Owner:** Data Lead (Person 1)
> **Patch Date:** 2026-11-17
> **Seed:** `42` (used for the original dataset generation workflow)

---

## 1. Allowed Values

| Field | Allowed Values |
|---|---|
| `language` | `en`, `ar`, `mixed` |
| `source` | `cord`, `synthetic` in the v1.1 release; the schema may support additional sources in future versions |
| `quality` | `clear`, `blurry`, `tilted`, `noisy`, `unassessed` |

**Sources included in v1.1:** CORD v2 and generated synthetic documents only.

SROIE, CORU / ReceiptSense, HF Invoices, FUNSD, and separately collected real documents are not included in the v1.1 dataset splits.

- **`language`** refers to the language assigned to the document, not necessarily the original language of its source dataset. The original source language is stored in `annotations.origin_language`.
- **`quality`** defaults to `unassessed` until explicitly evaluated. All retained CORD records use `unassessed`.

---

## 2. Ground Truth Rules

| Rule | Detail |
|---|---|
| Missing field | Empty string `""`, never `null` or `None` |
| Arabic-Indic digits | Preserve as-is when present |
| Currency symbols | Preserve as-is |
| Whitespace | Preserve internal whitespace; trim leading/trailing whitespace |
| Ground-truth structure | Exactly four keys: `invoice_number`, `date`, `supplier`, `total` |

**Validator interpretation (no schema change):** all four values must be strings, and an empty string is valid when a value is unavailable. The v1.1 contract does not define one canonical date format or numeric/currency grammar. Preserve localized display strings (including Arabic-Indic digits and currency symbols); validation therefore checks types and structure rather than parsing or normalizing dates and totals. A non-string value such as `null` or a JSON number is invalid.

### CORD v1.1 annotation policy

CORD records use a restricted annotation policy:

- `total` is taken only from the CORD `total.total_price` annotation.
- `supplier`, `date`, and `invoice_number` are empty strings.
- Records without an annotated total are excluded.
- `quality` is `unassessed`.
- `annotations.origin_language` is `id`.
- `annotations.label_version` is `v1.1`.

Do not fill missing CORD fields by inference or by copying values from other annotation sections.

---

## 3. `doc_id` Format

```text
<source>_<split>_<id>
```

- `<source>` identifies the source.
- `<split>` identifies the source split.
- `<id>` is the source's unique identifier.
- `doc_id` must be globally unique across the dataset.

Examples:

- `cord_validation_00001`
- `synthetic_train_00001`

---

## 4. JSONL Schema

One JSON object per line.

### CORD v1.1 example

```json
{
  "doc_id": "cord_train_00214",
  "image_path": "data/processed/images/cord_train_00214.jpg",
  "language": "en",
  "source": "cord",
  "quality": "unassessed",
  "ground_truth": {
    "invoice_number": "",
    "date": "",
    "supplier": "",
    "total": "58,000"
  },
  "ocr": {
    "engine": "",
    "words": []
  },
  "prediction": {},
  "annotations": {
    "cord_split": "train",
    "origin_language": "id",
    "label_version": "v1.1",
    "image_width": 1108,
    "image_height": 1478
  },
  "source_split": "train",
  "source_key": "214"
}
```

This example is taken from an actual retained CORD record.
### Field Descriptions

| Field | Type | Required | Description |
|---|---|---|---|
| `doc_id` | string | Yes | Globally unique document identifier |
| `image_path` | string | Yes | Relative path to the image |
| `language` | string | Yes | `en`, `ar`, or `mixed` |
| `source` | string | Yes | Dataset source identifier |
| `quality` | string | Yes | Image quality assessment |
| `ground_truth` | object | Yes | Exactly four keys, all strings |
| `ground_truth.invoice_number` | string | Yes | Invoice/receipt number; empty if unavailable |
| `ground_truth.date` | string | Yes | Issue date; empty if unavailable |
| `ground_truth.supplier` | string | Yes | Issuing business name; empty if unavailable |
| `ground_truth.total` | string | Yes | Final amount due; empty if unavailable |
| `ocr` | object | Yes | OCR output |
| `ocr.engine` | string | Yes | OCR engine name |
| `ocr.words` | array | Yes | Word-level OCR results |
| `prediction` | object | Yes | Model predictions |
| `annotations` | object | Yes | Source-specific metadata |
| `source_split` | string | Yes | Original source split |
| `source_key` | string | Yes | Original source key or identifier |

### Required v1.1 Annotation Metadata

`image_width` and `image_height` are required on every retained v1.1 record. The `label_version` marker is required on records patched for v1.1 (the retained CORD records) and must be `v1.1` when present. The original synthetic records in the frozen handoff predate that CORD-specific patch and do not carry `annotations.label_version`; they are not retroactively rewritten. This scope follows the release patch history and the supplied archive.

| Field | Type | Description |
|---|---|---|
| `annotations.image_width` | integer | Image width in pixels |
| `annotations.image_height` | integer | Image height in pixels |
| `annotations.label_version` | string | Annotation contract version; `v1.1` for patched records |

### Additional Allowed Annotation Metadata

| Field | Description |
|---|---|
| `annotations.origin_language` | Original language of the source dataset, e.g. `id` for CORD |
| `annotations.cord_split` | Original CORD split |
| `annotations.template_id` | Template used for synthetic generation |
| `annotations.holdout_template` | Boolean identifying a reserved synthetic holdout template |
| `annotations.font` | Font used for synthetic generation |
| `annotations.seed` | Per-document generation seed |
| `annotations.degradations` | List of image degradations applied |
| `annotations.locale` | Faker locale used |
| `annotations.needs_manual_verification` | Flag for suspicious labels |
| `annotations.review_reason` | Reason a document needs review |

For v1.1, the synthetic templates `ar_commercial` and `mixed_bilingual` are reserved for the final test split. The test split contains 654 `ar_commercial` records and 397 `mixed_bilingual` records (1,051 total). All are tagged with `annotations.holdout_template=true` and their template names are stored in `annotations.template_id`. Their `source_split` value remains `train`, representing the original synthetic generation split; the final assigned split is determined by the JSONL file containing the record.

---

## 5. Image Format

- **Format:** RGB JPEG
- **Location:** `data/processed/images/` for CORD images; synthetic images are stored under `data/synth/out/images/`.
- **Filename:** `<doc_id>.jpg`
- **Dimensions:** Recorded in `annotations.image_width` and `annotations.image_height`.

---

## 6. v1.1 Dataset Contents and File Locations

The released dataset contains **4,446 retained records**:

| Split | CORD | Synthetic | Total |
|---|---:|---:|---:|
| Train | 781 | 1,959 | 2,740 |
| Validation | 121 | 367 | 488 |
| Test | 44 | 1,174 | 1,218 |
| **Total** | **946** | **3,500** | **4,446** |

| Artifact | Path |
|---|---|
| CORD images | `data/processed/images/` |
| Synthetic images | `data/synth/out/images/` |
| Train split | `data/splits/train.jsonl` |
| Validation split | `data/splits/val.jsonl` |
| Test split | `data/splits/test.jsonl` |
| Train OCR output | `ocr_output/train_with_ocr.jsonl` |
| Validation OCR output | `ocr_output/val_with_ocr.jsonl` |
| Test OCR output | `ocr_output/test_with_ocr.jsonl` |
| Split report | `data/splits/split_report.csv` |

The OCR output JSONL files correspond to the same retained records as their respective split files.

The following datasets and files are **not part of the v1.1 release**: SROIE, CORU / ReceiptSense, HF Invoices, separately collected real data, `real_val.jsonl`, and `real_test.jsonl`.

---

## 7. Changelog

Dataset changes and version history are tracked in `CHANGELOG.md` at the repository root.
