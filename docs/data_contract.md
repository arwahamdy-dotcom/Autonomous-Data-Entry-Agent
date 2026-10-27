# Data Contract — v1

> **Status:** FROZEN  
> **Owner:** Data Lead (Person 1)  
> **Date Frozen:** 2026-10-24  
> **Seed:** `42` (used everywhere)

---

## 1. Allowed Values

| Field | Allowed Values |
|---|---|
| `language` | `en`, `ar`, `mixed` |
| `source` | `sroie`, `cord`, `coru`, `invoices_hf`, `synthetic`, `real` |
| `quality` | `clear`, `blurry`, `tilted`, `noisy`, `unassessed` |

- **`language`** refers to the language of the document as we label it, not the origin language of the dataset. For example, CORD documents are originally Indonesian but may be labeled `en` if the text on the receipt is English. The original dataset language is stored in `annotations.origin_language`.
- **`quality`** defaults to `unassessed` until explicitly evaluated.

---

## 2. Ground Truth Rules

| Rule | Detail |
|---|---|
| Copy exactly as printed | No cleaning, no normalization. That is Person 4's job. |
| Missing field | Empty string `""`, **never** `null` or `None` |
| Arabic-Indic digits | Keep as-is (e.g. `٠١٢٣٤٥٦٧٨٩`) |
| Currency symbols | Keep as-is |
| Whitespace | Preserve internal whitespace; trim leading/trailing |

---

## 3. `doc_id` Format

```
<source>_<split>_<id>
```

- `<source>` is one of the allowed source values.
- `<split>` is `train`, `val`, or `test`.
- `<id>` is the source's own unique identifier (filename stem, index, etc.).
- **Must be globally unique across the entire dataset.**

Examples:
- `sroie_train_X51005433522`
- `cord_val_00042`
- `synthetic_train_00001`
- `real_test_invoice_007`

---

## 4. JSONL Schema (One JSON Object Per Line)

```json
{
  "doc_id": "sroie_train_X51005433522",
  "image_path": "data/processed/images/sroie_train_X51005433522.jpg",
  "language": "en",
  "source": "sroie",
  "quality": "unassessed",
  "ground_truth": {
    "invoice_number": "",
    "date": "",
    "supplier": "",
    "total": ""
  },
  "ocr": {
    "engine": "",
    "words": []
  },
  "prediction": {},
  "annotations": {},
  "source_split": "train",
  "source_key": "X51005433522"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|---|---|---|---|
| `doc_id` | string | ✅ | Globally unique document identifier |
| `image_path` | string | ✅ | Relative path to the processed image |
| `language` | string | ✅ | `en`, `ar`, or `mixed` |
| `source` | string | ✅ | Dataset source identifier |
| `quality` | string | ✅ | Image quality assessment |
| `ground_truth` | object | ✅ | Exactly 4 keys, all strings |
| `ground_truth.invoice_number` | string | ✅ | Invoice/receipt number as printed |
| `ground_truth.date` | string | ✅ | Issue date as printed |
| `ground_truth.supplier` | string | ✅ | Issuing business name as printed |
| `ground_truth.total` | string | ✅ | Final amount due (including tax) as printed |
| `ocr` | object | ✅ | OCR output (filled by Person 2) |
| `ocr.engine` | string | ✅ | OCR engine name (empty until filled) |
| `ocr.words` | array | ✅ | Word-level OCR results (empty until filled) |
| `prediction` | object | ✅ | Model predictions (filled by Person 3) |
| `annotations` | object | ✅ | Source-specific metadata, origin_language, etc. |
| `source_split` | string | ✅ | Original split in the source dataset |
| `source_key` | string | ✅ | Original key/ID in the source dataset |

### Extra Fields in `annotations`

These are allowed and encouraged:

| Field | Description |
|---|---|
| `annotations.origin_language` | Original language of the source dataset (e.g. `id` for CORD) |
| `annotations.template_id` | Template used for synthetic generation |
| `annotations.font` | Font used for synthetic generation |
| `annotations.seed` | Per-document seed for synthetic generation |
| `annotations.degradations` | List of degradations applied |
| `annotations.locale` | Faker locale used |
| `annotations.needs_manual_verification` | Flag for suspicious labels |
| `annotations.review_reason` | Why this document needs review |

---

## 5. Image Format

- **Format:** RGB JPEG
- **Quality:** 95 (for conversions), 30–70 (for synthetic degradations)
- **Location:** `data/processed/images/`
- **Filename:** `<doc_id>.jpg`

---

## 6. File Locations

| File | Path |
|---|---|
| Converted SROIE | `data/processed/sroie.jsonl` |
| Converted CORD | `data/processed/cord.jsonl` |
| Converted CORU | `data/processed/coru.jsonl` |
| Converted invoices | `data/processed/invoices.jsonl` |
| Synthetic data | `data/synth/out/synthetic.jsonl` |
| Real data (labeled) | `data/real/labeled/real.jsonl` |
| Train split | `data/splits/train.jsonl` |
| Validation split | `data/splits/val.jsonl` |
| Test split | `data/splits/test.jsonl` |
| Real validation | `data/splits/real_val.jsonl` |
| Real test (LOCKED) | `data/splits/real_test.jsonl` |
| Review items | `data/review/*.jsonl` |

---

## 7. Changelog

All dataset versions are tracked in `CHANGELOG.md` at the project root.
