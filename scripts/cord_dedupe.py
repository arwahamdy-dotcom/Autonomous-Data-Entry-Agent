import argparse
import csv
import itertools
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path

SPLITS = ["train", "val", "test"]
COLUMNS = [
    "keep_doc", "keep_split", "drop_doc", "drop_split",
    "jaccard", "exact_ocr_match", "tokens_keep", "tokens_drop",
    "total_keep", "total_drop", "image_keep", "image_drop",
    "decision", "note"
]


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    path = Path(path)
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def tokens(row):
    words = (row.get("ocr") or {}).get("words", [])
    text = " ".join(w.get("text", "") for w in words)
    return set(re.sub(r"[\W_]+", " ", text.lower()).split())


def detect(args):
    root = Path(args.root)
    ocr_dir = Path(args.ocr_dir) if args.ocr_dir else root / "ocr_output"

    docs = []
    for split in SPLITS:
        path = ocr_dir / f"{split}_with_ocr.jsonl"
        for row in read_jsonl(path):
            if row.get("source") == "cord":
                docs.append((split, row, tokens(row)))

    found = {}

    for first, second in itertools.combinations(docs, 2):
        s1, r1, t1 = first
        s2, r2, t2 = second

        if s1 == s2 or len(t1) < args.min_tokens or len(t2) < args.min_tokens:
            continue

        union = t1 | t2
        score = len(t1 & t2) / len(union) if union else 0

        if score < args.threshold:
            continue

        if SPLITS.index(s1) > SPLITS.index(s2):
            s1, r1, t1, s2, r2, t2 = s2, r2, t2, s1, r1, t1

        found[(r1["doc_id"], r2["doc_id"])] = {
            "keep_doc": r1["doc_id"],
            "keep_split": s1,
            "drop_doc": r2["doc_id"],
            "drop_split": s2,
            "jaccard": round(score, 3),
            "exact_ocr_match": t1 == t2,
            "tokens_keep": len(t1),
            "tokens_drop": len(t2),
            "total_keep": (r1.get("ground_truth") or {}).get("total", ""),
            "total_drop": (r2.get("ground_truth") or {}).get("total", ""),
            "image_keep": r1.get("image_path", ""),
            "image_drop": r2.get("image_path", ""),
            "decision": "",
            "note": ""
        }

    out = Path(args.out) if args.out else root / "cord_duplicate_pairs.csv"

    if out.exists():
        with open(out, encoding="utf-8") as f:
            for old in csv.DictReader(f):
                key = (old["keep_doc"], old["drop_doc"])
                if key in found:
                    found[key]["decision"] = old.get("decision", "")
                    found[key]["note"] = old.get("note", "")

    rows = sorted(
        found.values(),
        key=lambda row: (-row["jaccard"], row["keep_doc"])
    )

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} cross-split pairs found.")
    print(f"Exact token-set matches: {sum(r['exact_ocr_match'] for r in rows)}")
    print("Pairs by split:", dict(Counter(
        (r["keep_split"], r["drop_split"]) for r in rows
    )))
    print("CSV:", out)


def review(args):
    from PIL import Image, ImageDraw

    root = Path(args.root)
    out = Path(args.out) if args.out else root / "cord_duplicate_pairs.csv"
    out_dir = root / "data" / "review" / "dup_pairs"
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out, encoding="utf-8") as f:
        pairs = list(csv.DictReader(f))

    for index, pair in enumerate(pairs, 1):
        images = []
        for key in ("image_keep", "image_drop"):
            path = root / pair[key]
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.thumbnail((800, 800))
                images.append(im.copy())

        width = images[0].width + images[1].width + 40
        sheet = Image.new("RGB", (width, 850), "white")
        x = 10

        for im in images:
            sheet.paste(im, (x, 40))
            x += im.width + 20

        draw = ImageDraw.Draw(sheet)
        draw.text(
            (10, 10),
            f"{index:02d} KEEP {pair['keep_doc']} | "
            f"DROP? {pair['drop_doc']} | overlap {pair['jaccard']}",
            fill="black"
        )

        filename = f"{index:02d}_{pair['keep_doc']}__{pair['drop_doc']}.jpg"
        sheet.save(out_dir / filename, quality=85)

    print(f"{len(pairs)} review images saved to: {out_dir}")


def apply(args):
    root = Path(args.root)
    ocr_dir = Path(args.ocr_dir) if args.ocr_dir else root / "ocr_output"
    out = Path(args.out) if args.out else root / "cord_duplicate_pairs.csv"

    with open(out, encoding="utf-8") as f:
        pairs = list(csv.DictReader(f))

    invalid = [
        p for p in pairs
        if p["decision"].strip().lower() not in ("", "duplicate", "different")
    ]
    if invalid:
        raise SystemExit("Invalid decision. Use duplicate, different, or blank.")

    drop_by_split = {}
    for pair in pairs:
        if pair["decision"].strip().lower() == "duplicate":
            split = pair["drop_split"]
            doc = pair["drop_doc"]
            if split == "train":
                raise SystemExit(f"Refusing to remove training document: {doc}")
            drop_by_split.setdefault(split, set()).add(doc)

    undecided = sum(not p["decision"].strip() for p in pairs)
    print(f"Pairs: {len(pairs)}")
    print(f"Confirmed removal candidates: {sum(map(len, drop_by_split.values()))}")
    print(f"Undecided pairs: {undecided}")
    if undecided:
        print("Undecided pairs will be kept.")

    files = {}
    for split in SPLITS:
        files[split] = {
            "split": root / "data" / "splits" / f"{split}.jsonl",
            "ocr": ocr_dir / f"{split}_with_ocr.jsonl"
        }

    plan = {}
    for split, paths in files.items():
        split_rows = read_jsonl(paths["split"])
        ocr_rows = read_jsonl(paths["ocr"])

        split_ids = [r["doc_id"] for r in split_rows]
        ocr_ids = [r["doc_id"] for r in ocr_rows]

        if len(split_ids) != len(set(split_ids)):
            raise SystemExit(f"Duplicate doc_id in {split} split file.")
        if len(ocr_ids) != len(set(ocr_ids)):
            raise SystemExit(f"Duplicate doc_id in {split} OCR file.")
        if set(split_ids) != set(ocr_ids):
            raise SystemExit(f"Split/OCR doc IDs do not match for {split}.")

        drops = drop_by_split.get(split, set())
        for doc in drops:
            if split_ids.count(doc) != 1:
                raise SystemExit(f"{doc} must occur exactly once in {split} split.")
            if ocr_ids.count(doc) != 1:
                raise SystemExit(f"{doc} must occur exactly once in {split} OCR.")

        plan[split] = {
            "split": [r for r in split_rows if r["doc_id"] not in drops],
            "ocr": [r for r in ocr_rows if r["doc_id"] not in drops]
        }

        print(
            f"{split}: {len(split_rows)} -> {len(plan[split]['split'])} "
            f"(removed {len(drops)})"
        )

    if not args.write:
        print("PREVIEW ONLY. No files changed. Add --write to apply.")
        return

    for split, paths in files.items():
        for kind in ("split", "ocr"):
            path = paths[kind]
            backup = Path(str(path) + ".pre_dedupe.bak")
            if not backup.exists():
                shutil.copy2(path, backup)
            write_jsonl(path, plan[split][kind])

    report = Counter()
    for split in SPLITS:
        for row in plan[split]["split"]:
            report[(
                split,
                row.get("source", ""),
                row.get("language", ""),
                row.get("quality", "")
            )] += 1

    report_path = root / "data" / "splits" / "split_report.csv"
    report_backup = Path(str(report_path) + ".pre_dedupe.bak")
    if report_path.exists() and not report_backup.exists():
        shutil.copy2(report_path, report_backup)

    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["split", "source", "language", "quality", "records"])
        for key, count in sorted(report.items(), key=lambda x: tuple(map(str, x[0]))):
            writer.writerow([*key, count])

    print("Changes written. Backups created where absent.")
    print("split_report.csv regenerated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["detect", "review", "apply"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--ocr-dir", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--min-tokens", type=int, default=8)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    {"detect": detect, "review": review, "apply": apply}[args.cmd](args)
