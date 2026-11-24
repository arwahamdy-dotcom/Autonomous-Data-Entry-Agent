# Autonomous Data Entry Agent — Data Lead Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Kaggle | Cloud](https://img.shields.io/badge/environment-Kaggle%20Cloud-20BEFF.svg?logo=kaggle)](https://www.kaggle.com/code/malaksobhyyyyy/notebook8306395ee0)

Welcome to the **Data Lead repository** for the **Autonomous Data Entry Agent** project.  
This subsystem is responsible for sourcing, standardizing, validating, augmenting, and splitting multilingual invoice and receipt data (Arabic, English, and Mixed) to train and evaluate state-of-the-art OCR and Document Information Extraction models.

## Project links

- **GitHub repository:** [Autonomous-Data-Entry-Agent](https://github.com/arwahamdy-dotcom/Autonomous-Data-Entry-Agent)
- **Kaggle pipeline notebook and saved outputs:** [Open the Kaggle notebook](https://www.kaggle.com/code/malaksobhyyyyy/notebook8306395ee0)
- **Download saved Kaggle kernel outputs** (requires the Kaggle CLI and configured Kaggle credentials):

  ```bash
  kaggle kernels output malaksobhyyyyy/notebook8306395ee0 -p ./kaggle_outputs
  ```

> **Dataset files are not committed to this GitHub repository.** The repository contains the pipeline code, notebooks, and documentation; generated dataset files and large artifacts are kept in the Kaggle environment. `.gitignore` excludes ZIP archives, images, and data directories.

> 📄 **Looking for the full delivery report?**  
> Read the complete, comprehensive [Data Lead Delivery Report](docs/DATA_LEAD_DELIVERY_REPORT.md) detailing all numbers, methodologies, and downstream hand-off guides.

---

## 📌 Executive Summary (What Was Done)

As the **Data Lead**, the following end-to-end data engineering pipeline has been established and executed:

1. **Unified Data Contract (`JSONL`):**
   - Defined and enforced a strict JSON Lines contract across all document sources.
   - Guaranteed extraction target for the core 4 fields: `invoice_number`, `date`, `supplier`, and `total`.

2. **Multilingual Dataset Integration:**
   - **Open Datasets Standardized:** The released dataset includes **CORD v2** (1,000 original receipts, 946 retained after annotation filtering) and 3,500 synthetic documents.
   - **Arabic & Mixed Coverage:** Arabic and mixed-language coverage in the released dataset is provided by synthetic documents. CORU / ReceiptSense was investigated but is not included in the released splits.

3. **High-Fidelity Synthetic Invoice Generator (`generate_synthetic.py`):**
   - Engineered an automated generator producing **3,500 Arabic, English, and mixed invoices/receipts in the released dataset**.
   - Incorporates RTL support, Google Arabic fonts (Cairo, Amiri), Western and Arabic-Indic numerals, realistic business names, line items, and dynamic image degradations (blur, noise, perspective skew, low contrast, JPEG artifacts).
   - Ground-truth labels are generated alongside synthetic documents, reducing manual annotation needs. Synthetic labels should still undergo quality checks.

4. **Dataset Validation & Quality Control (`validate_dataset.py`):**
   - Checks JSONL syntax, contract field types, allowed metadata values, ground-truth structure, unique `doc_id`s within each file, and (when requested) that referenced images decode.
   - Dates and totals remain localized display strings under the frozen contract; the validator does not normalize or semantically parse them.

5. **Leakage-Free Splitting (`create_splits.py` & `check_leakage.py`):**
   - Released split proportions: **Train (61.6%)**, **Validation (11.0%)**, and **Test (27.4%)**. These are the actual v1.1 proportions, not an 80/15/5 split.
   - Cryptographic MD5 hash check confirming **0 cross-split duplicate images** or document-ID overlap.
   - Synthetic holdout templates are confined to the test split, which contains both synthetic and CORD records.

6. **Exploratory Data Analysis & Reporting (`run_eda.py`):**
   - Automated profiling generating comprehensive distributions, token statistics, and visual charts.

---

## Dataset v1.1 — Released Dataset Status

See the [Dataset v1.1 Release Manifest](docs/dataset_v1.1_manifest.md) for the release inventory, and the [Person 1 Audit Status](docs/AUDIT_STATUS.md) for reproducible closure evidence. Arabic-Indic counts and font-annotation limitations are documented in [`docs/arabic_indic_audit.md`](docs/arabic_indic_audit.md) and [`docs/font_annotation_audit.md`](docs/font_annotation_audit.md).


The patched v1.1 dataset contains **4,446 retained documents**:

| Split | CORD | Synthetic | Total |
|---|---:|---:|---:|
| Train | 781 | 1,959 | 2,740 |
| Validation | 121 | 367 | 488 |
| Test | 44 | 1,174 | 1,218 |
| **Total** | **946** | **3,500** | **4,446** |

The corresponding split percentages are **61.63% train / 10.98% validation / 27.40% test**. The independently audited archive filename, SHA-256, and verification output are recorded in the [release manifest](docs/dataset_v1.1_manifest.md) and [audit status](docs/AUDIT_STATUS.md).

**CORD annotation policy:** Only the total is retained from the original CORD annotations. Supplier, date, and invoice number are blank. CORD records have `quality="unassessed"` and `annotations.origin_language="id"`. Twenty-eight CORD records without an annotated total were excluded.

**Synthetic holdout:** The `ar_commercial` and `mixed_bilingual` templates are reserved for the test split and tagged with `annotations.holdout_template=true` (1,051 records).

Every retained record includes `annotations.image_width` and `annotations.image_height`. The split JSONL files and their OCR output counterparts were patched consistently.

SROIE, CORU / ReceiptSense, HF Invoices, and separately collected real documents are **not included** in these v1.1 splits.

---

## 📂 Repository Structure

```text
data-entry-ds/
│
├── Data_Lead_Kaggle_Pipeline.ipynb # Kaggle Cloud end-to-end Pipeline notebook
├── Data_Lead_Pipeline.ipynb        # Google Colab Pipeline notebook
├── .gitignore                      # Excludes large binaries/images from Git
├── README.md                       # Project documentation and summary
│
├── docs/                        # Formal documentation and specifications
│   ├── data_contract.md         # Full JSONL schema and field specifications
│   ├── labeling_guide.md        # Annotation guidelines and edge cases
│   └── datasets_licenses.md     # Licensing, provenance, and citations
│
└── scripts/                     # Production Python scripts
    ├── utils.py                 # Common utilities (I/O, language detection, hashing)
    ├── convert_cord.py          # Hugging Face CORD v2 converter
    ├── convert_sroie.py         # ICDAR 2019 SROIE converter
    ├── convert_coru.py          # CORU / ReceiptSense Arabic receipt converter
    ├── convert_invoices.py      # Hugging Face Invoices converter
    ├── generate_synthetic.py    # Multilingual synthetic generator (Playwright / Pillow)
    ├── validate_dataset.py      # Dataset schema and integrity validator
    ├── create_splits.py         # Stratified train/val/test splitter
    ├── check_leakage.py         # Data leakage and duplicate hash verification
    └── run_eda.py               # Exploratory Data Analysis & chart generator
```

---

## 📋 Data Contract Specification

Every document in our dataset follows this exact JSON structure:

```json
{
  "doc_id": "synthetic_train_00001",
  "image_path": "data/processed/images/synthetic_train_00001.jpg",
  "language": "ar",
  "source": "synthetic",
  "quality": "clear",
  "ground_truth": {
    "invoice_number": "INV-2024-0042",
    "date": "2024-08-15",
    "supplier": "شركة النور للتجارة",
    "total": "1,450.00"
  },
  "ocr": {
    "engine": "",
    "words": []
  },
  "prediction": {},
  "annotations": {
    "template_id": "ar_tax_invoice",
    "locale": "ar_EG"
  },
  "source_split": "train",
  "source_key": "00001"
}
```

### Core Extraction Fields:
| Field | Description | Example |
| :--- | :--- | :--- |
| `supplier` | Merchant, business, or company name | `شركة النور للتجارة` / `Starbucks` |
| `invoice_number` | Unique identifier of the document | `INV-2024-0042` / `RCP-9812` |
| `date` | Transaction date | `2024-08-15` / `15/08/2024` |
| `total` | Final payable amount | `1,450.00` / `85.50` |

---

## 🚀 How to Run the Pipeline (Google Colab & Drive)

The entire pipeline is packaged in **[`Data_Lead_Pipeline.ipynb`](Data_Lead_Pipeline.ipynb)**:

For a local Python 3.12 environment, install the locked data-pipeline dependencies with `python -m pip install -r requirements.txt`. The lock covers the repository's data processing, generation, and EDA dependencies; OCR engines and their system/GPU-specific runtimes remain optional and are installed by the corresponding OCR notebook mode. Install the Playwright browser with `python -m playwright install chromium` when running synthetic rendering.

1. Upload the `data-entry-ds` folder to your **Google Drive**.
2. Open `Data_Lead_Pipeline.ipynb` with **Google Colaboratory**.
3. Run the cells sequentially:
   - **Cell 1:** Mounts Google Drive and navigates to the project directory.
   - **Cell 2:** Installs dependencies (`datasets`, `playwright`, `pillow`, `arabic-reshaper`, etc.).
   - **Cell 3:** Original dataset-ingestion workflow (CORD and SROIE); SROIE is not included in the v1.1 release.
   - **Cell 4:** Generates synthetic invoices with ground truth.
   - **Cell 5:** Validates the dataset schema (`validate_dataset.py`).
   - **Cell 6:** Splits the data (`create_splits.py`) and checks for leakage (`check_leakage.py`).
   - **Cell 7:** Produces the EDA report (`run_eda.py`).
   - **Cell 8:** Runs final verification and displays readiness status.

---

## 🔒 Verification & Definition of Done (v1)

- [x] All included v1.1 sources (CORD and synthetic documents) use the unified JSONL contract.
- [x] `validate_dataset.py` returns **0 errors**.
- [x] `check_leakage.py` confirms **0 cross-split duplicate images** and document-ID overlap.
- Same-split duplicate images, if present, may affect training or evaluation metrics. The latest leakage check confirmed zero cross-split image duplicates.
- [x] Stratified splits generated (`data/splits/train.jsonl`, `val.jsonl`, `test.jsonl`).
- [x] Synthetic Arabic/English dataset generated with full ground truth.
- [x] Dataset inventory and license limitations documented; **license clearance remains unresolved** for CORD terms and third-party font/asset permissions.

## License

See [`docs/datasets_licenses.md`](docs/datasets_licenses.md) for dataset sources, provenance, and applicable terms. No repository-wide license is declared here; do not assume that dataset licenses apply to the code or vice versa.

---

# Autonomous Data Entry Agent — OCR Lead Pipeline

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Platform: Google Colab | GPU](https://img.shields.io/badge/environment-Google%20Colab%20%7C%20GPU-F9AB00.svg?logo=googlecolab)](https://colab.research.google.com/)
[![Storage: Google Drive](https://img.shields.io/badge/storage-Google%20Drive-4285F4.svg?logo=googledrive)](https://drive.google.com/)

This is the OCR Lead section of the Autonomous Data Entry Agent project.
This subsystem is responsible for choosing, benchmarking and running the OCR engine that turns every Arabic, English and mixed invoice or receipt image into text, with a position and a confidence for each piece of text. The Document Information Extraction models (Person 3) are trained on this output.

## Project links

- Colab notebook: [OCR_Pipeline.ipynb](https://colab.research.google.com/drive/1Eybn4TiwdRO8CetTXoRZeJSgtE3rTXhr?usp=sharing)
- Saved final outputs on Google Drive in [OCR dataset v1/ocr_output](https://drive.google.com/drive/folders/1FESxKuDn_RZ_A0YNeP-ToP4tLz8IemuO?usp=sharing) and engines comparison results in [OCR dataset v1/ocr_benchmark](https://drive.google.com/drive/folders/1EKx-Fp-sYMlWfJJinlhfYx9UaVQvZxZE?usp=sharing). 

## 📌 Executive Summary (What Was Done)

1. **Unified engine interface (`engines.py`):**
   - Wrapped four OCR engines: Tesseract, EasyOCR, PaddleOCR and Surya.
   - All return the same format, `[{text, bbox, conf}]`, so an engine is swapped with one word: `run_ocr("surya", image_path)`.
   - No engine is trained by us. They are used as published.

2. **Fair benchmark on the validation split only:**
   - 164 val documents, sampled evenly across language and quality (15 per group, fixed seed), so every engine reads exactly the same documents.
   - Score = **field hit rate**: the share of the labelled fields (invoice number, supplier, total) found in the OCR text. The date is excluded from the main score because its printed format rarely matches the label.

3. **Decision: Surya 0.17.1**

   | Engine | Score (95% interval) | Arabic | Seconds per doc |
   |---|---|---|---|
   | **Surya 0.17.1** | **0.877** (0.843 to 0.912) | 0.733 | 2.45 |
   | PaddleOCR (GPU) | 0.796 (0.750 to 0.839) | 0.550 | 1.10 |
   | EasyOCR | 0.651 (0.599 to 0.703) | 0.517 | 1.26 |
   | Tesseract | 0.468 (0.412 to 0.522) | 0.200 | 3.47 |

   - Surya leads on every language and on both real (CORD) and synthetic documents. The reported intervals do not overlap. However, a paired statistical comparison is needed before interpreting the differences as statistically significant.
   - Routing (best engine per language and quality) was tested: 0.881 vs 0.877 for Surya alone. Not worth the extra complexity, so one engine is used for everything.
   - Cost: Surya is the slowest of the good engines. The original OCR run covered 4,500 documents before v1.1 filtering.

4. **Safe, resumable production run:**
   - The winner runs on val, train and test. Results are saved to Drive after every document.
   - If Colab disconnects, re-running the cell continues where it stopped.
   - Failed rows and rows made by another engine are redone, so the final files contain one engine only.
   - Existing files are copied to `ocr_output_backup_before_rerun` before any rewrite.
   - The run stops with a clear message if the engine cannot load, or after 5 errors in a row, instead of filling the files with errors.

## 📂 Structure

```
ocr/
│
├── OCR_Pipeline.ipynb            # Colab notebook: benchmark, winner selection, final run
├── engines.py                    # The four engine wrappers (the notebook also writes it into Colab)

Google Drive (OCR dataset v1/)
├── data/                         # Input from the Data Lead (never edited)
│   ├── processed/images/         # Real CORD receipts
│   ├── synth/out/images/         # Synthetic invoices
│   └── splits/                   # train.jsonl, val.jsonl, test.jsonl
├── ocr_benchmark/                # One CSV per engine + all_engines_val.csv
├── ocr_output/                   # Final train/val/test_with_ocr.jsonl
```

## 📋 OCR Data Contract Specification

The OCR step reads each record from the Data Lead's splits and fills in one field, `ocr`. Every other field is kept exactly as it was.

```json
"ocr": {
  "engine": "surya",
  "words": [
    {"text": "شركة النور للتجارة", "bbox": [120, 40, 610, 92], "conf": 0.97}
  ]
}
```
*(illustrative values)*

| Field | Description |
|---|---|
| `engine` | Engine that produced the result (`surya` for the final run) |
| `words[].text` | Recognized text |
| `words[].bbox` | `[x1, y1, x2, y2]` in pixels |
| `words[].conf` | Confidence from 0 to 1 |
| `error` | Only present if the document failed. Failed rows are redone on the next run |

**Granularity:** Surya returns text **lines**, not single words (Tesseract returns words). Each item in `words` is therefore a line.

## 🚀 How to Run the Pipeline (Google Colab & Drive)

The engines need different library versions and installing one can break another, so the notebook has three modes. Use a **fresh Colab session** for each (Runtime > Change runtime type > GPU).

| Session | `MODE` | Runs |
|---|---|---|
| 1 | `main` | Tesseract and EasyOCR |
| 2 | `paddle` | PaddleOCR on GPU (its install breaks PyTorch, which EasyOCR needs) |
| 3 | `surya` | Surya 0.17.1 (version 0.20 changed the API and returns blocks, not lines) |

Run the cells in order:

1. **Config:** set `MODE` (and `SKIP_INSTALL = True` after a runtime restart).
2. **Mount Drive and set paths.**
3. **Install** the engine for this mode.
4. **Write `engines.py`** and import it.
5. **Helpers:** loading, scoring, normalization.
6. **Benchmark (Part A):** each engine runs on the val sample and saves its CSV to Drive. Stop here in sessions 2 and 3.
7. **Results:** reads every engine's CSV, prints the tables, suggests a winner.
8. **Pick the winner and check the time estimate.**
9. **Part B:** run the winner on val, train, then test (val first, as a 20-minute sanity check).
10. **Final check:** records, errors and empty results per split.

## 🔒 Verification & Definition of Done

- ✅ Four engines wrapped with one shared output format.
- ✅ All four benchmarked on the same 164 val documents.
- ✅ Winner chosen on val only, with confidence intervals and a routing check.
- ✅ Run is resumable and does not overwrite good results.
- ⬜ `val`, `train` and `test` `_with_ocr.jsonl` complete: record counts match the splits (488 / 2,740 / 1,218) with 0 errors. *(confirm with the final check cell)*

## ⚠️ Notes

- **No full transcription in the data**, so CER and WER could not be computed. Engines were compared by field hit rate instead.
- **All Arabic and mixed documents are synthetic.** The Arabic ranking is not confirmed on real Arabic receipts. The validation split contains 140 retained English CORD receipts.
- **The benchmark used a 164-document sample**, not the full 488 validation documents.
