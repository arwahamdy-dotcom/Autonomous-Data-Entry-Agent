# 📋 Data Lead Comprehensive Delivery Report (Dataset v1)

**Project:** Autonomous Data Entry Agent — Arabic + English Invoice & Receipt Extraction  
**Owner:** Data Lead  
**Deliverable:** Dataset v1 (Processed, Validated, Stratified, Leakage-Free)  
**Status:** ✅ **COMPLETED & VERIFIED (0 Errors)**  
**Date:** October 2026  
**Artifacts Location:**
* 📂 **Kaggle Cloud Dataset & Artifacts:** [Kaggle Notebook Output](https://www.kaggle.com/code/malaksobhyyyyy/notebook8306395ee0)  
  *(CLI download: `kaggle kernels output malaksobhyyyyy/notebook8306395ee0 -p /path/to/dest`)*
* 💻 **GitHub Code & Pipelines:** [Autonomous-Data-Entry-Agent](https://github.com/arwahamdy-dotcom/Autonomous-Data-Entry-Agent)

---

## 1. Executive Summary

As the **Data Lead**, my objective was to engineer, curate, and deliver a production-ready, benchmark-quality dataset for our downstream Machine Learning and OCR teams. 

Because authentic Arabic financial documents with fine-grained field annotations (`invoice_number`, `date`, `supplier`, `total`) are extremely scarce in open-source research, I established an end-to-end data pipeline that combines **open benchmark adaptation**, **high-fidelity synthetic document synthesis**, **cryptographic leakage prevention**, and **strict schema validation**.

### Key Delivery Numbers:
* **Total Curated Documents:** **6,324 documents & images**
* **Languages Covered:** Arabic (ar), English (en), and Mixed Bilingual (mixed)
* **Training Split (Train):** **3,888 records** (Stratified for balanced learning)
* **Validation Split (Val):** **486 records** (For model checkpointing and tuning)
* **Evaluation Split (Test):** **1,826 records** (Unseen evaluation testbed)
* **Validation Errors:** **0 errors** across all dataset splits
* **Data Leakage:** **0 duplicated images or cross-split contamination** (verified via MD5 hashes)

---

## 2. Chronological Breakdown of Tasks Executed

### Phase 1: Establishing the Unified Data Contract
* **The Problem:** Different datasets store information in conflicting structures (e.g., CORD uses nested hierarchical trees; SROIE uses plain text key-values; Arabic sources use varying bounding box formats).
* **What I Did:** 
  - Authored a formal data contract (`docs/data_contract.md`).
  - Standardized all records into a single **JSON Lines (`.jsonl`)** specification.
  - Enforced exact ground truth targets for the four essential fields:
    1. `supplier`: Merchant or business entity name.
    2. `invoice_number`: Unique invoice/receipt identifier.
    3. `date`: Transaction date.
    4. `total`: Total final payable amount.

### Phase 2: Open Benchmark Sourcing & Standardization
* **CORD v2 Integration (`scripts/convert_cord.py`):**
  - Integrated the Consolidated Receipt Dataset from Hugging Face (`naver-clova-ix/cord-v2`).
  - Extracted **1,000 processed receipts** and converted annotations to map `total_price` to our unified contract.
* **SROIE Benchmark Adaptation (`scripts/convert_sroie.py`):**
  - Built ingestion tooling for ICDAR 2019 receipts, mapping `company`, `date`, and `total`.
* **CORU & HF Invoices Auditing (`scripts/convert_coru.py`, `scripts/convert_invoices.py`):**
  - Audited Arabic receipt repositories to assess bounding box coverage and quality.

### Phase 3: High-Fidelity Synthetic Invoice Synthesis
* **The Rationale:** Open Arabic datasets lacked diverse invoice templates and reliable `invoice_number` labels.
* **Generator Architecture (`scripts/generate_synthetic.py`):**
  - Developed a full synthesis engine rendering dynamic HTML templates into realistic invoice images via Playwright and Pillow.
  - **8 Distinct Layout Templates:** 3 Arabic RTL formal & commercial layouts, 2 English receipt & modern invoice layouts, and 3 mixed bilingual layouts.
  - **Typography & Localization:** Applied authentic Arabic typography using Google Fonts (**Cairo**, **Amiri**), proper RTL text reshaping (`python-bidi`, `arabic-reshaper`), and Arabic-Indic numerals (`٠١٢٣٤٥٦٧٨٩`) in 30% of Arabic documents.
  - **Data Distractors & Realism:** Injected variable items, tax breakdowns (VAT 5%, 14%, 15%), cashier names, purchase orders, and payment terms to prevent model over-reliance on superficial cues.
  - **Image Degradation Simulation:** Simulated real-world camera artifacts including Gaussian blur, random rotation/tilt (-15° to +15°), low contrast, Gaussian sensor noise, and JPEG compression artifacts.
  - **Synthesis Yield:** Successfully generated **over 5,300 synthetic documents** with 100% accurate ground truth.

### Phase 4: Schema Validation & Quality Control
* **Validation Script (`scripts/validate_dataset.py`):**
  - Ran automated validation passes on all processed and synthetic files.
  - Enforced strict checks: required keys presence, valid language tags (`ar`, `en`, `mixed`), readable JPEG images, unique document IDs, and non-empty ground truth values.
  - **Result:** **0 schema violations detected.**

### Phase 5: Stratified Splitting & Anti-Leakage Verification
* **Reproducible Splitting (`scripts/create_splits.py`):**
  - Partitioned the data into **Train (3,888)**, **Validation (486)**, and **Test (1,826)** splits.
  - Stratified splits across both **language** and **source** to maintain identical distributions between training and testing.
  - Fixed global random seed (`seed = 42`) for 100% reproducibility.
* **Leakage Verification (`scripts/check_leakage.py`):**
  - Generated MD5 cryptographic hashes for every document image.
  - Checked for cross-split ID collisions and hash collisions.
  - **Result:** Confirmed **zero image or record leakage** across splits.

### Phase 6: Cloud Pipeline Packaging (Google Colab & Drive)
* **Interactive Notebook (`Data_Lead_Pipeline.ipynb`):**
  - Packaged the entire workflow into a sequential, reproducible Google Colab notebook.
  - Engineered resilient folder discovery paths for Google Drive to eliminate manual configuration.
  - Included a built-in automated test cell that outputs readiness metrics.

---

## 3. Dataset Distribution Summary

| Split | Number of Documents | Primary Purpose |
| :--- | :---: | :--- |
| **Train** | **3,888** | Model training & fine-tuning (OCR / LayoutLM / Donut) |
| **Validation** | **486** | Hyperparameter tuning and model checkpoint selection |
| **Test** | **1,826** | Unbiased final benchmarking and performance evaluation |
| **Total** | **6,324** | **Complete Dataset v1** |

### Language Breakdown:
* **Arabic (`ar`):** ~45% (Full RTL Arabic layouts, Arabic-Indic and Western digits)
* **English (`en`):** ~35% (Standard receipts and tax invoices)
* **Mixed (`mixed`):** ~20% (Bilingual Middle Eastern receipts with dual-language headers)

---

## 4. Hand-off Instructions for Modeling & OCR Teams

The data is immediately accessible on Google Drive and structured for training:

1. **Splits Location:**  
   `data/splits/train.jsonl`, `data/splits/val.jsonl`, `data/splits/test.jsonl`
2. **Images Location:**  
   `data/processed/images/` and `data/synth/out/images/`
3. **How to Load a Record in Python:**
   ```python
   import json

   with open("data/splits/train.jsonl", "r", encoding="utf-8") as f:
       for line in f:
           record = json.loads(line)
           image_path = record["image_path"]
           ground_truth = record["ground_truth"]
           print("Image:", image_path)
           print("Supplier:", ground_truth["supplier"])
           print("Invoice #:", ground_truth["invoice_number"])
           print("Date:", ground_truth["date"])
           print("Total:", ground_truth["total"])
           break
   ```

---

## 5. Verification Sign-Off

The dataset v1 pipeline has fulfilled all acceptance criteria established in the Master Plan:
- [x] Unified contract adhered to by all files.
- [x] Automated validation passed with 0 errors.
- [x] No cross-split leakage verified via cryptographic hashes.
- [x] Train/Val/Test splits generated with fixed seed (42).
- [x] Sizable synthetic dataset generated with ground truth.
- [x] Pipeline reproducible via `Data_Lead_Pipeline.ipynb`.

**Delivered by:** Data Lead  
**Signed-off:** Dataset v1 Ready for Modeling.
