"""
Exploratory Data Analysis (EDA) for the dataset.

Generates charts and statistics for each source:
  - Document counts per source, language, split
  - Image width/height distribution
  - Words per document
  - Empty-field rate per field
  - Date format patterns
  - Total amount distribution (log scale)
  - Quality distribution

Usage (from Colab):
    %cd /content/drive/MyDrive/data-entry-ds
    !python scripts/run_eda.py

    # Or for specific files
    !python scripts/run_eda.py --files data/processed/sroie.jsonl data/processed/cord.jsonl

Produces:
    docs/eda_report.md
    docs/figures/  (PNG charts)
"""

import sys
import re
import argparse
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import read_jsonl, GROUND_TRUTH_KEYS

FIGURES_DIR = Path("docs/figures")


def run_eda(files: list[str] = None):
    """Run EDA on all processed JSONL files."""
    print("=" * 60)
    print("Exploratory Data Analysis")
    print("=" * 60)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        HAS_MPL = True
    except ImportError:
        HAS_MPL = False
        print("  [WARN] matplotlib not installed. Charts will be skipped.")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Discover files
    if not files:
        files = []
        for d in [Path("data/processed"), Path("data/synth/out"), Path("data/real/labeled")]:
            if d.exists():
                files.extend(str(f) for f in sorted(d.glob("*.jsonl")))

    if not files:
        print("  No JSONL files found!")
        return

    # Load all records
    all_records = []
    per_source = defaultdict(list)

    for filepath in files:
        records = read_jsonl(filepath)
        print(f"  Loaded {len(records)} from {Path(filepath).name}")
        all_records.extend(records)
        for r in records:
            per_source[r.get("source", "unknown")].append(r)

    total = len(all_records)
    print(f"\n  Total records: {total}")

    # ── Statistics ──

    # 1. Counts per source
    source_counts = Counter(r.get("source", "unknown") for r in all_records)
    print(f"\n  Records per source:")
    for s, c in source_counts.most_common():
        print(f"    {s}: {c}")

    # 2. Counts per language
    lang_counts = Counter(r.get("language", "unknown") for r in all_records)
    print(f"\n  Records per language:")
    for l, c in lang_counts.most_common():
        print(f"    {l}: {c}")

    # 3. Counts per quality
    quality_counts = Counter(r.get("quality", "unknown") for r in all_records)
    print(f"\n  Records per quality:")
    for q, c in quality_counts.most_common():
        print(f"    {q}: {c}")

    # 4. Empty field rates
    print(f"\n  Empty field rates:")
    field_stats = {}
    for field in sorted(GROUND_TRUTH_KEYS):
        empty = sum(1 for r in all_records if not r.get("ground_truth", {}).get(field, ""))
        pct = (empty / total * 100) if total > 0 else 0
        field_stats[field] = {"empty": empty, "total": total, "pct": pct}
        print(f"    {field}: {empty}/{total} ({pct:.1f}%)")

    # 5. Empty field rates per source
    print(f"\n  Empty field rates per source:")
    for source, records in sorted(per_source.items()):
        print(f"    {source} ({len(records)} records):")
        for field in sorted(GROUND_TRUTH_KEYS):
            empty = sum(1 for r in records if not r.get("ground_truth", {}).get(field, ""))
            pct = (empty / len(records) * 100) if records else 0
            print(f"      {field}: {empty}/{len(records)} ({pct:.1f}%)")

    # 6. Image dimensions
    print(f"\n  Checking image dimensions (first 500)...")
    widths, heights = [], []
    try:
        from PIL import Image
        for r in all_records[:500]:
            img_path = Path(r.get("image_path", ""))
            if img_path.exists():
                with Image.open(img_path) as img:
                    w, h = img.size
                    widths.append(w)
                    heights.append(h)
        if widths:
            import numpy as np
            print(f"    Width:  min={min(widths)}, max={max(widths)}, median={np.median(widths):.0f}")
            print(f"    Height: min={min(heights)}, max={max(heights)}, median={np.median(heights):.0f}")
    except ImportError:
        print(f"    [WARN] PIL not installed, skipping image analysis")

    # 7. Date format patterns
    print(f"\n  Date format patterns:")
    date_patterns = Counter()
    for r in all_records:
        date_val = r.get("ground_truth", {}).get("date", "")
        if date_val:
            # Classify date format
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_val):
                date_patterns["YYYY-MM-DD (ISO)"] += 1
            elif re.match(r'^\d{2}/\d{2}/\d{4}$', date_val):
                date_patterns["DD/MM/YYYY"] += 1
            elif re.match(r'^\d{2}-\d{2}-\d{4}$', date_val):
                date_patterns["DD-MM-YYYY"] += 1
            elif re.search(r'[A-Z][a-z]+\s+\d', date_val):
                date_patterns["Written month (EN)"] += 1
            elif re.search(r'[\u0600-\u06FF]', date_val):
                date_patterns["Arabic date"] += 1
            elif re.search(r'[٠-٩]', date_val):
                date_patterns["Arabic-Indic digits"] += 1
            else:
                date_patterns["Other"] += 1

    for pattern, count in date_patterns.most_common():
        print(f"    {pattern}: {count}")

    # 8. Total amount distribution
    print(f"\n  Total amount statistics:")
    amounts = []
    for r in all_records:
        total_val = r.get("ground_truth", {}).get("total", "")
        if total_val:
            # Try to extract numeric value
            cleaned = total_val.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
            cleaned = re.sub(r'[^\d.,]', '', cleaned)
            cleaned = cleaned.replace(",", "")
            try:
                amounts.append(float(cleaned))
            except ValueError:
                pass

    if amounts:
        import numpy as np
        print(f"    Count: {len(amounts)}")
        print(f"    Min: {min(amounts):.2f}")
        print(f"    Max: {max(amounts):.2f}")
        print(f"    Mean: {np.mean(amounts):.2f}")
        print(f"    Median: {np.median(amounts):.2f}")
        print(f"    Std: {np.std(amounts):.2f}")

    # ── Generate Charts ──
    if HAS_MPL:
        import matplotlib.pyplot as plt
        import numpy as np

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("Dataset EDA Report", fontsize=16, fontweight="bold")

        # Chart 1: Records per source
        ax = axes[0, 0]
        sources = list(source_counts.keys())
        counts = [source_counts[s] for s in sources]
        colors = plt.cm.Set2(range(len(sources)))
        ax.barh(sources, counts, color=colors)
        ax.set_title("Records per Source")
        ax.set_xlabel("Count")
        for i, v in enumerate(counts):
            ax.text(v + 5, i, str(v), va="center", fontsize=10)

        # Chart 2: Language distribution
        ax = axes[0, 1]
        langs = list(lang_counts.keys())
        lang_vals = [lang_counts[l] for l in langs]
        ax.pie(lang_vals, labels=langs, autopct="%1.1f%%",
               colors=["#f59e0b", "#3b82f6", "#10b981"])
        ax.set_title("Language Distribution")

        # Chart 3: Quality distribution
        ax = axes[0, 2]
        quals = list(quality_counts.keys())
        qual_vals = [quality_counts[q] for q in quals]
        ax.pie(qual_vals, labels=quals, autopct="%1.1f%%")
        ax.set_title("Quality Distribution")

        # Chart 4: Empty field rates
        ax = axes[1, 0]
        fields = sorted(GROUND_TRUTH_KEYS)
        empty_rates = [field_stats[f]["pct"] for f in fields]
        bar_colors = ["#ef4444" if r > 50 else "#f59e0b" if r > 20 else "#10b981" for r in empty_rates]
        ax.bar(fields, empty_rates, color=bar_colors)
        ax.set_title("Empty Field Rate (%)")
        ax.set_ylabel("% Empty")
        ax.set_ylim(0, 105)
        for i, v in enumerate(empty_rates):
            ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=10)

        # Chart 5: Total amount distribution (log scale)
        ax = axes[1, 1]
        if amounts:
            ax.hist(amounts, bins=50, color="#6366f1", edgecolor="white", alpha=0.8)
            ax.set_xscale("log")
            ax.set_title("Total Amount Distribution (log scale)")
            ax.set_xlabel("Amount")
            ax.set_ylabel("Count")
        else:
            ax.text(0.5, 0.5, "No totals available", ha="center", va="center")
            ax.set_title("Total Amount Distribution")

        # Chart 6: Image dimensions
        ax = axes[1, 2]
        if widths and heights:
            ax.scatter(widths, heights, alpha=0.3, s=10, color="#8b5cf6")
            ax.set_title("Image Dimensions")
            ax.set_xlabel("Width (px)")
            ax.set_ylabel("Height (px)")
        else:
            ax.text(0.5, 0.5, "No image data", ha="center", va="center")
            ax.set_title("Image Dimensions")

        plt.tight_layout()
        chart_path = FIGURES_DIR / "eda_overview.png"
        plt.savefig(str(chart_path), dpi=150, bbox_inches="tight")
        plt.close()
        print(f"\n  Chart saved to {chart_path}")

        # Per-source empty field chart
        fig, ax = plt.subplots(figsize=(12, 6))
        x = range(len(sorted(per_source.keys())))
        width = 0.2
        for i, field in enumerate(sorted(GROUND_TRUTH_KEYS)):
            rates = []
            for source in sorted(per_source.keys()):
                records = per_source[source]
                empty = sum(1 for r in records if not r.get("ground_truth", {}).get(field, ""))
                rates.append(empty / len(records) * 100 if records else 0)
            ax.bar([xi + i * width for xi in x], rates, width, label=field)
        ax.set_xticks([xi + 1.5 * width for xi in x])
        ax.set_xticklabels(sorted(per_source.keys()), rotation=45)
        ax.set_ylabel("% Empty")
        ax.set_title("Empty Field Rate by Source")
        ax.legend()
        plt.tight_layout()
        chart_path = FIGURES_DIR / "empty_fields_by_source.png"
        plt.savefig(str(chart_path), dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  Chart saved to {chart_path}")

    # ── Write EDA Report ──
    report_path = Path("docs/eda_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# EDA Report\n\n")
        f.write(f"> Generated automatically. Total records: **{total}**\n\n")

        f.write("## Records per Source\n\n")
        f.write("| Source | Count | % |\n|---|---|---|\n")
        for s, c in source_counts.most_common():
            f.write(f"| {s} | {c} | {c/total*100:.1f}% |\n")

        f.write("\n## Language Distribution\n\n")
        f.write("| Language | Count | % |\n|---|---|---|\n")
        for l, c in lang_counts.most_common():
            f.write(f"| {l} | {c} | {c/total*100:.1f}% |\n")

        f.write("\n## Quality Distribution\n\n")
        f.write("| Quality | Count | % |\n|---|---|---|\n")
        for q, c in quality_counts.most_common():
            f.write(f"| {q} | {c} | {c/total*100:.1f}% |\n")

        f.write("\n## Empty Field Rates\n\n")
        f.write("| Field | Empty | Total | % |\n|---|---|---|---|\n")
        for field in sorted(GROUND_TRUTH_KEYS):
            s = field_stats[field]
            f.write(f"| {field} | {s['empty']} | {s['total']} | {s['pct']:.1f}% |\n")

        f.write("\n## Date Format Patterns\n\n")
        f.write("| Pattern | Count |\n|---|---|\n")
        for p, c in date_patterns.most_common():
            f.write(f"| {p} | {c} |\n")

        if amounts:
            import numpy as np
            f.write("\n## Total Amount Statistics\n\n")
            f.write(f"- Count: {len(amounts)}\n")
            f.write(f"- Min: {min(amounts):.2f}\n")
            f.write(f"- Max: {max(amounts):.2f}\n")
            f.write(f"- Mean: {np.mean(amounts):.2f}\n")
            f.write(f"- Median: {np.median(amounts):.2f}\n")

        f.write("\n## Surprises and Notes\n\n")
        f.write("<!-- Fill in 5-10 observations after reviewing the data -->\n\n")
        f.write("1. \n2. \n3. \n4. \n5. \n")

        if HAS_MPL:
            f.write("\n## Charts\n\n")
            f.write("![EDA Overview](figures/eda_overview.png)\n\n")
            f.write("![Empty Fields by Source](figures/empty_fields_by_source.png)\n\n")

    print(f"\n  EDA report saved to {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Run EDA on dataset files")
    parser.add_argument("--files", nargs="+", help="JSONL files to analyze")
    parser.add_argument("--dataset_dir", type=str, default=None, help="Directory containing dataset files")
    parser.add_argument("--output_report", type=str, default=None, help="Output report path")
    args, _ = parser.parse_known_args()

    files = args.files
    if not files and args.dataset_dir:
        files = [str(f) for f in sorted(Path(args.dataset_dir).glob("*.jsonl"))]

    run_eda(files=files)


if __name__ == "__main__":
    main()
