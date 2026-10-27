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
   - **Open Datasets Standardized:** Integrated and standardized benchmarks from Hugging Face including **CORD v2** (1,000 receipts) and **SROIE / ICDAR 2019** (970+ receipts).
   - **Arabic & Mixed Coverage:** Integrated and audited the **CORU / ReceiptSense** dataset for Middle Eastern Arabic/English receipts.

3. **High-Fidelity Synthetic Invoice Generator (`generate_synthetic.py`):**
   - Engineered an automated generator producing **8,000+ realistic Arabic, English, and mixed invoices/receipts**.
   - Incorporates RTL support, Google Arabic fonts (Cairo, Amiri), Western and Arabic-Indic numerals, realistic business names, line items, and dynamic image degradations (blur, noise, perspective skew, low contrast, JPEG artifacts).
   - **Correct-by-construction ground truth** eliminating human annotation errors.

4. **Zero-Error Data Validation & Quality Control (`validate_dataset.py`):**
   - Strict automated schema validation ensuring valid dates, positive amounts, unique `doc_id`s, and image integrity.

5. **Leakage-Free Splitting (`create_splits.py` & `check_leakage.py`):**
   - Stratified dataset split into **Train (80%)**, **Validation (15%)**, and **Test (5%)** with a fixed reproducible seed (`seed=42`).
   - Cryptographic MD5 hash check guaranteeing **0 duplicate images** or document overlap between splits.
   - Holdout synthetic templates and real test sets reserved exclusively for final evaluation.

6. **Exploratory Data Analysis & Reporting (`run_eda.py`):**
   - Automated profiling generating comprehensive distributions, token statistics, and visual charts.

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

1. Upload the `data-entry-ds` folder to your **Google Drive**.
2. Open `Data_Lead_Pipeline.ipynb` with **Google Colaboratory**.
3. Run the cells sequentially:
   - **Cell 1:** Mounts Google Drive and navigates to the project directory.
   - **Cell 2:** Installs dependencies (`datasets`, `playwright`, `pillow`, `arabic-reshaper`, etc.).
   - **Cell 3:** Downloads and standardizes CORD and SROIE datasets.
   - **Cell 4:** Generates synthetic invoices with ground truth.
   - **Cell 5:** Validates the dataset schema (`validate_dataset.py`).
   - **Cell 6:** Splits the data (`create_splits.py`) and checks for leakage (`check_leakage.py`).
   - **Cell 7:** Produces the EDA report (`run_eda.py`).
   - **Cell 8:** Runs final verification and displays readiness status.

---

## 🔒 Verification & Definition of Done (v1)

- [x] All document sources converted to single unified JSONL contract.
- [x] `validate_dataset.py` returns **0 errors**.
- [x] `check_leakage.py` confirms **0 cross-split duplicates** (hash-verified).
- [x] Stratified splits generated (`data/splits/train.jsonl`, `val.jsonl`, `test.jsonl`).
- [x] Synthetic Arabic/English dataset generated with full ground truth.
- [x] Comprehensive documentation and license audit completed.

## License

See [`docs/datasets_licenses.md`](docs/datasets_licenses.md) for dataset sources, provenance, and applicable terms. No repository-wide license is declared here; do not assume that dataset licenses apply to the code or vice versa.
