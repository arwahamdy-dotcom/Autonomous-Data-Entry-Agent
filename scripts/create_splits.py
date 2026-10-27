"""
Create train/val/test splits from all processed JSONL files.

Split rules:
  - SROIE, CORD, CORU, invoices: 80/10/10, stratified by language + source
  - Synthetic: 80/10/10, plus 2 whole templates reserved for test only
  - Real: 50% val / 50% test (separate files), stratified by language + quality
  - A document lives in exactly one split
  - Seed = 42 everywhere

Usage (from Colab):
    %cd /content/drive/MyDrive/data-entry-ds
    !python scripts/create_splits.py

    # Custom split ratios
    !python scripts/create_splits.py --train 0.8 --val 0.1 --test 0.1

Produces:
    data/splits/train.jsonl
    data/splits/val.jsonl
    data/splits/test.jsonl
    data/splits/real_val.jsonl   (if real data exists)
    data/splits/real_test.jsonl  (if real data exists — LOCKED)
    data/splits/split_report.csv
"""

import sys
import csv
import argparse
import random
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import read_jsonl, write_jsonl, SPLITS_DIR, SEED

try:
    from sklearn.model_selection import train_test_split
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("  [WARN] scikit-learn not found. Using manual stratification.")


def stratified_split(records, train_ratio=0.80, val_ratio=0.15, test_ratio=0.05,
                     stratify_keys=("language", "source"), seed=SEED):
    """Split records with stratification.
    
    Falls back to manual stratification if sklearn is not available
    or if groups are too small.
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        f"Ratios must sum to 1.0, got {train_ratio + val_ratio + test_ratio}"

    if len(records) < 10:
        # Too few records for proper stratification
        random.seed(seed)
        random.shuffle(records)
        n_train = max(1, int(len(records) * train_ratio))
        n_val = max(1, int(len(records) * val_ratio))
        return records[:n_train], records[n_train:n_train + n_val], records[n_train + n_val:]

    # Build stratification key
    strat_labels = []
    for r in records:
        label = "_".join(str(r.get(k, "unknown")) for k in stratify_keys)
        strat_labels.append(label)

    # Check if any group has too few members
    label_counts = Counter(strat_labels)
    min_count = min(label_counts.values())

    if HAS_SKLEARN and min_count >= 3:
        try:
            # First split: train vs (val+test)
            train, rest, train_labels, rest_labels = train_test_split(
                records, strat_labels,
                test_size=(val_ratio + test_ratio),
                stratify=strat_labels,
                random_state=seed,
            )
            # Second split: val vs test
            val_ratio_adj = val_ratio / (val_ratio + test_ratio)
            val, test = train_test_split(
                rest,
                test_size=(1 - val_ratio_adj),
                stratify=rest_labels,
                random_state=seed,
            )
            return train, val, test
        except ValueError:
            pass  # Fall through to manual

    # Manual stratified split
    random.seed(seed)
    groups = defaultdict(list)
    for r, label in zip(records, strat_labels):
        groups[label].append(r)

    train, val, test = [], [], []
    for label, group in groups.items():
        random.shuffle(group)
        n = len(group)
        n_train = max(1, round(n * train_ratio))
        n_val = max(0, round(n * val_ratio))
        train.extend(group[:n_train])
        val.extend(group[n_train:n_train + n_val])
        test.extend(group[n_train + n_val:])

    return train, val, test


def create_splits(train_ratio=0.80, val_ratio=0.15, test_ratio=0.05,
                  holdout_templates=None):
    """Create train/val/test splits from all processed data."""
    print("=" * 60)
    print("Creating Train/Val/Test Splits")
    print(f"Ratios: {train_ratio}/{val_ratio}/{test_ratio}, Seed: {SEED}")
    print("=" * 60)

    SPLITS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Collect all processed records ──
    processed_dir = Path("data/processed")
    synth_dir = Path("data/synth/out")
    real_dir = Path("data/real/labeled")

    all_records = []
    real_records = []
    synth_records = []
    other_records = []

    # Load processed datasets
    for jsonl_file in sorted(processed_dir.glob("*.jsonl")):
        records = read_jsonl(jsonl_file)
        print(f"  Loaded {len(records)} from {jsonl_file.name}")
        other_records.extend(records)

    # Load synthetic
    for jsonl_file in sorted(synth_dir.glob("*.jsonl")):
        records = read_jsonl(jsonl_file)
        print(f"  Loaded {len(records)} synthetic from {jsonl_file.name}")
        synth_records.extend(records)

    # Load real (labeled)
    for jsonl_file in sorted(real_dir.glob("*.jsonl")):
        records = read_jsonl(jsonl_file)
        print(f"  Loaded {len(records)} real from {jsonl_file.name}")
        real_records.extend(records)

    print(f"\n  Total: {len(other_records)} processed + {len(synth_records)} synthetic + {len(real_records)} real")

    train_all, val_all, test_all = [], [], []

    # ── Split other sources (SROIE, CORD, CORU, invoices) ──
    if other_records:
        print(f"\n  Splitting {len(other_records)} processed records...")
        train, val, test = stratified_split(
            other_records, train_ratio, val_ratio, test_ratio,
            stratify_keys=("language", "source"),
        )
        train_all.extend(train)
        val_all.extend(val)
        test_all.extend(test)
        print(f"    → Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")

    # ── Split synthetic (with template holdout) ──
    if synth_records:
        print(f"\n  Splitting {len(synth_records)} synthetic records...")

        # Identify holdout templates (reserved for test only)
        if holdout_templates is None:
            # Auto-select: one Arabic template and one mixed template
            template_langs = defaultdict(set)
            for r in synth_records:
                tid = r.get("annotations", {}).get("template_id", "")
                lang = r.get("language", "")
                if tid:
                    template_langs[tid].add(lang)

            holdout_templates = set()
            found_ar = False
            found_mixed = False
            for tid, langs in template_langs.items():
                if not found_ar and "ar" in langs:
                    holdout_templates.add(tid)
                    found_ar = True
                elif not found_mixed and "mixed" in langs:
                    holdout_templates.add(tid)
                    found_mixed = True
                if found_ar and found_mixed:
                    break

        # Separate holdout records
        holdout = [
            r for r in synth_records
            if r.get("annotations", {}).get("template_id", "") in holdout_templates
        ]
        non_holdout = [
            r for r in synth_records
            if r.get("annotations", {}).get("template_id", "") not in holdout_templates
        ]

        if holdout:
            print(f"    Template holdout: {len(holdout)} records (templates: {holdout_templates})")
            test_all.extend(holdout)

        if non_holdout:
            train, val, test = stratified_split(
                non_holdout, train_ratio, val_ratio, test_ratio,
                stratify_keys=("language",),
            )
            train_all.extend(train)
            val_all.extend(val)
            test_all.extend(test)
            print(f"    → Train: {len(train)}, Val: {len(val)}, Test: {len(test)} + {len(holdout)} holdout")

    # ── Split real data (50/50 val/test, separate files) ──
    real_val, real_test = [], []
    if real_records:
        print(f"\n  Splitting {len(real_records)} real records (50/50 val/test)...")
        real_val_split, _, real_test_split = stratified_split(
            real_records, 0.0, 0.5, 0.5,
            stratify_keys=("language", "quality"),
        )
        # With 0 train ratio, all go to val+test
        real_val = real_val_split
        real_test = real_test_split
        if not real_val and not real_test:
            # Fallback: manual 50/50
            random.seed(SEED)
            random.shuffle(real_records)
            mid = len(real_records) // 2
            real_val = real_records[:mid]
            real_test = real_records[mid:]
        print(f"    → Real Val: {len(real_val)}, Real Test: {len(real_test)} (LOCKED)")

    # ── Write split files ──
    print(f"\n  Writing split files...")
    random.seed(SEED)
    random.shuffle(train_all)
    random.shuffle(val_all)
    random.shuffle(test_all)

    write_jsonl(train_all, SPLITS_DIR / "train.jsonl")
    write_jsonl(val_all, SPLITS_DIR / "val.jsonl")
    write_jsonl(test_all, SPLITS_DIR / "test.jsonl")

    if real_val:
        write_jsonl(real_val, SPLITS_DIR / "real_val.jsonl")
    if real_test:
        write_jsonl(real_test, SPLITS_DIR / "real_test.jsonl")

    # ── Generate split report ──
    print(f"\n  Generating split report...")
    report_rows = []

    all_splits = {
        "train": train_all,
        "val": val_all,
        "test": test_all,
        "real_val": real_val,
        "real_test": real_test,
    }

    for split_name, split_data in all_splits.items():
        if not split_data:
            continue
        for record in split_data:
            report_rows.append({
                "split": split_name,
                "source": record.get("source", "unknown"),
                "language": record.get("language", "unknown"),
                "quality": record.get("quality", "unknown"),
            })

    # Aggregate counts
    agg = Counter()
    for row in report_rows:
        key = (row["split"], row["source"], row["language"], row["quality"])
        agg[key] += 1

    report_path = SPLITS_DIR / "split_report.csv"
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["split", "source", "language", "quality", "count"])
        for (split, source, lang, quality), count in sorted(agg.items()):
            writer.writerow([split, source, lang, quality, count])
    print(f"  Wrote split report to {report_path}")

    # ── Final summary ──
    print(f"\n{'=' * 60}")
    print(f"SPLIT SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Train:     {len(train_all):6d} records")
    print(f"  Val:       {len(val_all):6d} records")
    print(f"  Test:      {len(test_all):6d} records")
    if real_val:
        print(f"  Real Val:  {len(real_val):6d} records")
    if real_test:
        print(f"  Real Test: {len(real_test):6d} records (🔒 LOCKED)")
    total = len(train_all) + len(val_all) + len(test_all) + len(real_val) + len(real_test)
    print(f"  ─────────────────────")
    print(f"  Total:     {total:6d} records")
    print(f"\n  Seed used: {SEED}")

    # Per-source breakdown
    print(f"\n  Per-source breakdown:")
    source_split_counts = defaultdict(Counter)
    for split_name, split_data in all_splits.items():
        for r in split_data:
            source_split_counts[r.get("source", "unknown")][split_name] += 1

    for source in sorted(source_split_counts.keys()):
        counts = source_split_counts[source]
        parts = ", ".join(f"{s}={c}" for s, c in sorted(counts.items()))
        print(f"    {source}: {parts}")


def main():
    parser = argparse.ArgumentParser(description="Create train/val/test splits")
    parser.add_argument("--train", "--train_ratio", type=float, default=0.80, help="Train ratio", dest="train")
    parser.add_argument("--val", "--val_ratio", type=float, default=0.15, help="Val ratio", dest="val")
    parser.add_argument("--test", "--test_ratio", type=float, default=0.05, help="Test ratio", dest="test")
    parser.add_argument("--input_dir", type=str, default="data/processed", help="Input directory")
    parser.add_argument("--output_dir", type=str, default="data/splits", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--holdout-templates", nargs="*",
                        help="Synthetic template IDs reserved for test only")
    args, _ = parser.parse_known_args()

    holdout = set(args.holdout_templates) if args.holdout_templates else None
    create_splits(args.train, args.val, args.test, holdout_templates=holdout)


if __name__ == "__main__":
    main()
