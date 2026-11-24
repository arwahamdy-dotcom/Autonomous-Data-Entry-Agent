# Arabic-Indic Digit Audit (v1.1)

**Status:** Counts verified from the external release archive; the discrepancy from the configured conditional ratio is unresolved. No cause is asserted.

## Method

The reproducible source is the canonical `train.jsonl`, `val.jsonl`, and `test.jsonl` members in `OCR_Dataset_v1.1_Full_Handoff.zip`. The audit counts records with `source == "synthetic"` and `annotations.use_arabic_indic is true`, then independently searches all four `ground_truth` strings (`invoice_number`, `date`, `supplier`, `total`) for Arabic-Indic or Eastern Arabic-Indic digits (`٠–٩`, `۰–۹`). The archive audit script checks that the flag and text counts agree.

The generator source currently defines `ARABIC_INDIC_RATIO = 0.30` and applies a random draw only when `lang == "ar"` (`scripts/generate_synthetic.py`, configuration and `generate_document`). Therefore, that is a conditional target among Arabic-language synthetic records, not a target among all synthetic records.

## Verified observations

| Scope / denominator | Arabic-Indic records | Denominator | Rate |
|---|---:|---:|---:|
| Synthetic records labeled `language == "ar"` | 1,076 | 1,970 | **54.6193%** |
| All synthetic records | 1,076 | 3,500 | **30.7429%** |
| All released records, including CORD | 1,076 | 4,446 | **24.2015%** |

Per canonical split, flagged synthetic records are **571 train**, **108 validation**, and **397 test**. All 1,076 flagged records are Arabic-language synthetic records; the archive's `use_arabic_indic` flag and ground-truth digit check agree for every synthetic row.

Thus, a figure near 30% is obtained by dividing by all synthetic records, while 54.62% uses only Arabic-language synthetic records. Those are different denominators. Importantly, the observed conditional Arabic subset rate of 54.62% does **not** match the generator's configured conditional target of 30%. The checked-in files do not establish why: the exact generation inputs/RNG provenance or subsequent selection history needed to explain the difference is not present in the handoff. Treat the mismatch as unresolved, not as a confirmed cause or a validation failure of the archived records.

## Reproduction

```bash
python scripts/audit_release_archive.py /path/to/OCR_Dataset_v1.1_Full_Handoff.zip \
  --expected-sha256 0f7adb93c6617e47081b0dffbb4dd3d4a40106bcc22751d93bfedfe04cfc3608
```

The complete result is retained in [`evidence/archive_audit_v1.1.json`](evidence/archive_audit_v1.1.json). The ZIP is read in place; this procedure does not extract or modify release data.
