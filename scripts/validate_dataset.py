"""Validate JSONL dataset files against the project data contract.

Usage:
    python scripts/validate_dataset.py data/splits/train.jsonl --check-images
    python scripts/validate_dataset.py data/processed/*.jsonl
    python scripts/validate_dataset.py --input_dir data/splits --check-images

Exit codes: 0 = all supplied files passed; 1 = validation error or no input.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import GROUND_TRUTH_KEYS, validate_record


def validate_file(filepath: str, check_images: bool = False) -> dict:
    """Validate one JSONL file; malformed lines are errors, never skipped."""
    path = Path(filepath)
    print(f"\n{'=' * 60}\nValidating: {path}\n{'=' * 60}")
    if not path.is_file():
        message = f"File not found: {path}"
        print(f"  ERROR: {message}")
        return {"file": str(path), "total_records": 0, "total_errors": 1,
                "duplicate_ids": 0, "malformed_json_lines": 0,
                "empty_fields": {}, "languages": {}, "sources": {},
                "errors": [message]}

    errors = []
    records = 0
    malformed_json_lines = 0
    ids = []
    empty_fields = Counter()
    languages = Counter()
    sources = Counter()
    qualities = Counter()

    with path.open("r", encoding="utf-8-sig") as stream:
        for line_num, raw_line in enumerate(stream, start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                malformed_json_lines += 1
                errors.append(f"Line {line_num}: malformed JSON: {exc.msg} (column {exc.colno})")
                continue

            records += 1
            record_errors = validate_record(record, check_image=check_images)
            record_id = record.get("doc_id", "???") if isinstance(record, dict) else "???"
            for message in record_errors:
                errors.append(f"Line {line_num} (doc_id={record_id}): {message}")

            if not isinstance(record, dict):
                continue
            doc_id = record.get("doc_id")
            if isinstance(doc_id, str) and doc_id:
                ids.append((doc_id, line_num))

            gt = record.get("ground_truth")
            if isinstance(gt, dict):
                for field in GROUND_TRUTH_KEYS:
                    value = gt.get(field)
                    if value == "":
                        empty_fields[field] += 1

            for key, counter in (("language", languages),
                                 ("source", sources),
                                 ("quality", qualities)):
                value = record.get(key, "unknown")
                counter[value if isinstance(value, (str, int, float, bool)) else f"<{type(value).__name__}>"] += 1

    seen = set()
    duplicates = []
    for doc_id, line_num in ids:
        if doc_id in seen:
            duplicates.append(doc_id)
            errors.append(f"Line {line_num}: duplicate doc_id {doc_id!r}")
        seen.add(doc_id)

    print(f"  Records parsed: {records}")
    print(f"  Malformed JSON lines: {malformed_json_lines}")
    print(f"  Languages: {dict(languages.most_common())}")
    print(f"  Sources:   {dict(sources.most_common())}")
    print(f"  Quality:   {dict(qualities.most_common())}")
    print(f"  Unique document IDs: {len(seen)}")
    print(f"  Duplicate ID rows: {len(duplicates)}")
    print("  Empty ground-truth fields: " + str(dict(sorted(empty_fields.items()))))

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for error in errors[:100]:
            print(f"    {error}")
        if len(errors) > 100:
            print(f"    ... {len(errors) - 100} additional errors omitted")
    else:
        print("  No errors found.")

    return {
        "file": str(path), "total_records": records,
        "total_errors": len(errors), "duplicate_ids": len(duplicates),
        "malformed_json_lines": malformed_json_lines,
        "empty_fields": dict(empty_fields), "languages": dict(languages),
        "sources": dict(sources), "errors": errors,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate JSONL dataset files against the data contract")
    parser.add_argument("files", nargs="*", help="JSONL files to validate")
    parser.add_argument("--input_dir", default="data/processed", help="Default input directory when no files are supplied")
    parser.add_argument("--check-images", action="store_true", help="Verify referenced images exist and decode")
    args, _unknown = parser.parse_known_args(argv)

    files = args.files
    if not files:
        files = [str(path) for path in sorted(Path(args.input_dir).glob("*.jsonl"))]
        if not files:
            files = [str(path) for path in sorted(Path("data/splits").glob("*.jsonl"))]
    if not files:
        print("VALIDATION FAILED: no JSONL input files found; specify files or --input_dir.")
        return 1

    results = []
    for item in files:
        path = Path(item)
        if any(char in item for char in "*?["):
            matches = sorted(path.parent.glob(path.name))
            if not matches:
                results.append(validate_file(item, check_images=args.check_images))
            else:
                results.extend(validate_file(str(match), check_images=args.check_images) for match in matches)
        else:
            results.append(validate_file(item, check_images=args.check_images))

    total_records = sum(result["total_records"] for result in results)
    total_errors = sum(result["total_errors"] for result in results)
    print(f"\n{'=' * 60}\nVALIDATION SUMMARY\n{'=' * 60}")
    print(f"  Files checked: {len(results)}")
    print(f"  Records parsed: {total_records}")
    print(f"  Total errors: {total_errors}")
    for result in results:
        status = "PASS" if result["total_errors"] == 0 else "FAIL"
        print(f"  {status}: {result['file']} ({result['total_records']} records, {result['total_errors']} errors)")
    print("  RESULT: " + ("ALL FILES PASSED" if total_errors == 0 else "VALIDATION FAILED"))
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
