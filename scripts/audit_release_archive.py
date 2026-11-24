"""Read-only audit of a packaged v1.1 handoff ZIP.

Example:
    python scripts/audit_release_archive.py /path/to/OCR_Dataset_v1.1_Full_Handoff.zip \
      --expected-sha256 0f7adb93c6617e47081b0dffbb4dd3d4a40106bcc22751d93bfedfe04cfc3608

The script reads archive members in place and never extracts or modifies them.
"""

import argparse
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import PurePosixPath

from utils import validate_record

EXPECTED_SPLIT_COUNTS = {"train": 2740, "val": 488, "test": 1218}
ARCHIVE_ROOT = "OCR dataset v1/"
ARABIC_INDIC = re.compile(r"[٠-٩۰-۹]")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_archive(path, expected_sha256=None):
    errors = []
    actual_sha256 = sha256_file(path)
    if expected_sha256 and actual_sha256.lower() != expected_sha256.lower():
        errors.append(f"SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}")

    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        bad_member = archive.testzip()
        if bad_member:
            errors.append(f"ZIP CRC failure at member: {bad_member}")

        member_names = {info.filename for info in infos}
        image_members = {name for name in member_names
                         if name.lower().endswith((".jpg", ".jpeg", ".png"))}
        path_traversal = [name for name in member_names if ".." in PurePosixPath(name).parts]
        if path_traversal:
            errors.append(f"Archive contains {len(path_traversal)} path-traversal member(s)")

        split_counts = {}
        source_counts = Counter()
        language_counts = Counter()
        global_ids = defaultdict(list)
        missing_images = []
        referenced_images = set()
        schema_error_count = 0
        schema_error_examples = []
        indic_flag_counts = Counter()
        indic_text_counts = Counter()
        flag_text_mismatches = []
        template_fonts = defaultdict(Counter)
        holdouts = Counter()
        label_versions_by_source = defaultdict(Counter)
        split_id_sets = defaultdict(set)

        for split in ("train", "val", "test"):
            member = f"{ARCHIVE_ROOT}data/splits/{split}.jsonl"
            if member not in member_names:
                errors.append(f"Missing split file: {member}")
                split_counts[split] = 0
                continue
            count = 0
            try:
                lines = archive.read(member).decode("utf-8-sig").splitlines()
            except Exception as exc:
                errors.append(f"Could not read {member}: {type(exc).__name__}: {exc}")
                split_counts[split] = 0
                continue

            for line_num, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                count += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"Malformed JSON {member}:{line_num}: {exc.msg}")
                    continue
                record_errors = validate_record(record, check_image=False)
                if record_errors:
                    schema_error_count += len(record_errors)
                    if len(schema_error_examples) < 12:
                        schema_error_examples.append(f"{member}:{line_num}: {record_errors[0]}")
                if not isinstance(record, dict):
                    continue

                doc_id = record.get("doc_id")
                if isinstance(doc_id, str):
                    global_ids[doc_id].append(split)
                    split_id_sets[split].add(doc_id)
                source = record.get("source", "unknown")
                language = record.get("language", "unknown")
                source_counts[source if isinstance(source, str) else "<non-string>"] += 1
                language_counts[language if isinstance(language, str) else "<non-string>"] += 1

                image_path = record.get("image_path")
                if isinstance(image_path, str):
                    expected_member = ARCHIVE_ROOT + image_path.replace("\\", "/").lstrip("/")
                    referenced_images.add(expected_member)
                    if expected_member not in member_names:
                        missing_images.append((split, doc_id, image_path))

                annotations = record.get("annotations")
                if isinstance(annotations, dict):
                    template_fonts[str(annotations.get("template_id", "<missing>"))][str(annotations.get("font", "<missing>"))] += 1
                    label_versions_by_source[str(source)][str(annotations.get("label_version", "<missing>"))] += 1
                    if annotations.get("holdout_template") is True:
                        holdouts[(split, str(annotations.get("template_id", "<missing>")))] += 1
                    if source == "synthetic":
                        flag = annotations.get("use_arabic_indic") is True
                        indic_flag_counts[(language, flag)] += 1
                gt = record.get("ground_truth")
                text_has_indic = isinstance(gt, dict) and any(
                    isinstance(value, str) and ARABIC_INDIC.search(value)
                    for value in gt.values()
                )
                if source == "synthetic":
                    indic_text_counts[(language, bool(text_has_indic))] += 1
                    if isinstance(annotations, dict) and (annotations.get("use_arabic_indic") is True) != bool(text_has_indic):
                        flag_text_mismatches.append(doc_id)

            split_counts[split] = count
            if count != EXPECTED_SPLIT_COUNTS[split]:
                errors.append(f"{split} count mismatch: expected {EXPECTED_SPLIT_COUNTS[split]}, got {count}")

        ocr_output_counts = {}
        ocr_id_comparison = {}
        for split in ("train", "val", "test"):
            member = f"{ARCHIVE_ROOT}ocr_output/{split}_with_ocr.jsonl"
            if member not in member_names:
                errors.append(f"Missing OCR output file: {member}")
                ocr_output_counts[split] = 0
                ocr_id_comparison[split] = {"missing": None, "extra": None, "match": False}
                continue
            try:
                lines = archive.read(member).decode("utf-8-sig").splitlines()
            except Exception as exc:
                errors.append(f"Could not read {member}: {type(exc).__name__}: {exc}")
                ocr_output_counts[split] = 0
                ocr_id_comparison[split] = {"missing": None, "extra": None, "match": False}
                continue
            ocr_ids = set()
            count = 0
            for line_num, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                count += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"Malformed JSON {member}:{line_num}: {exc.msg}")
                    continue
                if isinstance(record, dict) and isinstance(record.get("doc_id"), str):
                    ocr_ids.add(record["doc_id"])
            missing = split_id_sets[split] - ocr_ids
            extra = ocr_ids - split_id_sets[split]
            match = not missing and not extra and count == split_counts.get(split, 0)
            ocr_output_counts[split] = count
            ocr_id_comparison[split] = {"missing": len(missing), "extra": len(extra), "match": match}
            if not match:
                errors.append(f"OCR output ID/count mismatch for {split}: missing={len(missing)}, extra={len(extra)}, rows={count}")

        duplicate_ids = {doc_id: splits for doc_id, splits in global_ids.items() if len(splits) > 1}
        unreferenced_images = image_members - referenced_images
        unreferenced_by_directory = Counter(
            name.rsplit("/", 1)[0] for name in unreferenced_images
        )
        if duplicate_ids:
            errors.append(f"Duplicate doc_ids across split files: {len(duplicate_ids)}")
        if missing_images:
            errors.append(f"Missing referenced image members: {len(missing_images)}")
        if schema_error_count:
            errors.append(f"Schema validation errors in archive: {schema_error_count}")
        if flag_text_mismatches:
            errors.append(f"Arabic-Indic flag/text mismatches: {len(flag_text_mismatches)}")

        synth_ar_total = indic_flag_counts.get(("ar", True), 0) + indic_flag_counts.get(("ar", False), 0)
        synth_total = sum(indic_flag_counts.values())
        flagged_ar = indic_flag_counts.get(("ar", True), 0)
        flagged_total = sum(count for (_, flagged), count in indic_flag_counts.items() if flagged)
        return {
            "archive": PurePosixPath(str(path).replace("\\", "/")).name,
            "sha256": actual_sha256,
            "expected_sha256": expected_sha256,
            "zip_members": len(infos),
            "image_members": len(image_members),
            "zip_crc": "PASS" if bad_member is None else "FAIL",
            "path_traversal_members": len(path_traversal),
            "split_records": split_counts,
            "total_split_records": sum(split_counts.values()),
            "ocr_output_records": ocr_output_counts,
            "ocr_output_id_comparison": ocr_id_comparison,
            "source_counts": dict(sorted(source_counts.items())),
            "language_counts": dict(sorted(language_counts.items())),
            "unique_doc_ids": len(global_ids),
            "duplicate_doc_ids": len(duplicate_ids),
            "missing_image_references": len(missing_images),
            "unreferenced_image_members": len(unreferenced_images),
            "unreferenced_image_members_by_directory": dict(sorted(unreferenced_by_directory.items())),
            "schema_errors": schema_error_count,
            "schema_error_examples": schema_error_examples,
            "arabic_indic_flag_vs_text_mismatches": len(flag_text_mismatches),
            "arabic_indic_flag_counts_by_language": {
                f"{lang}/flag={flag}": count for (lang, flag), count in sorted(indic_flag_counts.items())
            },
            "arabic_indic_text_counts_by_language": {
                f"{lang}/text={flag}": count for (lang, flag), count in sorted(indic_text_counts.items())
            },
            "arabic_indic_rate_among_ar_records_percent": round(100 * flagged_ar / synth_ar_total, 4) if synth_ar_total else None,
            "arabic_indic_rate_among_all_synthetic_percent": round(100 * flagged_total / synth_total, 4) if synth_total else None,
            "template_font_annotations": {template: dict(sorted(fonts.items())) for template, fonts in sorted(template_fonts.items())},
            "label_versions_by_source": {source: dict(sorted(counts.items())) for source, counts in sorted(label_versions_by_source.items())},
            "holdout_template_counts": {f"{split}/{template}": count for (split, template), count in sorted(holdouts.items())},
            "status": "PASS" if not errors else "FAIL",
            "errors": errors,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only v1.1 dataset handoff ZIP audit")
    parser.add_argument("archive", help="Path to the handoff ZIP")
    parser.add_argument("--expected-sha256", help="Optional expected SHA-256")
    args = parser.parse_args(argv)
    try:
        result = audit_archive(args.archive, args.expected_sha256)
    except (OSError, zipfile.BadZipFile) as exc:
        print(f"AUDIT FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
