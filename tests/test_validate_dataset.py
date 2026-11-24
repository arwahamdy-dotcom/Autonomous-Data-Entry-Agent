import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.generate_synthetic import font_annotation_for_template
from scripts.utils import validate_record
from scripts.validate_dataset import main, validate_file


def valid_record(**overrides):
    record = {
        "doc_id": "synthetic_train_00001",
        "image_path": "data/synth/out/images/synthetic_train_00001.jpg",
        "language": "ar",
        "source": "synthetic",
        "quality": "clear",
        "ground_truth": {
            "invoice_number": "INV-2026-001",
            "date": "٢٦ فبراير ٢٠٢١",
            "supplier": "شركة النور",
            "total": "٢,٨٥٣.٠٠ ج.م",
        },
        "ocr": {"engine": "", "words": []},
        "prediction": {},
        "annotations": {"image_width": 800, "image_height": 1000},
        "source_split": "train",
        "source_key": "00001",
    }
    record.update(overrides)
    return record


class ValidateRecordTests(unittest.TestCase):
    def test_valid_record_and_contract_allowed_localized_values(self):
        self.assertEqual(validate_record(valid_record(), check_image=False), [])

    def test_template_font_metadata_matches_template_css(self):
        expected = {
            "en_modern": "Inter",
            "en_receipt": "Courier New",
            "ar_formal": "Cairo",
            "ar_receipt": "Amiri",
            "ar_commercial": "Noto Naskh Arabic",
            "mixed_bilingual": "Cairo + Inter",
            "mixed_receipt": "Cairo",
            "mixed_corporate": "Cairo + Inter",
        }
        for template, family in expected.items():
            with self.subTest(template=template):
                self.assertEqual(font_annotation_for_template(template), family)
        self.assertEqual(font_annotation_for_template("future_template"), "unknown")

    def test_valid_cord_empty_non_total_ground_truth_is_allowed(self):
        record = valid_record(
            doc_id="cord_validation_00001",
            image_path="data/processed/images/cord_validation_00001.jpg",
            language="en", source="cord", quality="unassessed",
            ground_truth={"invoice_number": "", "date": "", "supplier": "", "total": "58,000"},
            annotations={"image_width": 1108, "image_height": 1478, "label_version": "v1.1"},
        )
        self.assertEqual(validate_record(record, check_image=False), [])

    def test_synthetic_record_may_omit_cord_patch_label_version(self):
        self.assertEqual(validate_record(valid_record(), check_image=False), [])

    def test_patched_cord_requires_v11_label_version(self):
        record = valid_record(source="cord")
        errors = validate_record(record, check_image=False)
        self.assertTrue(any("Missing required key: annotations.label_version" in error for error in errors))

    def test_non_object_json_values_are_reported_not_raised(self):
        for value in (None, [], "record", 7):
            with self.subTest(value=value):
                self.assertTrue(validate_record(value))

    def test_missing_required_fields_are_reported(self):
        record = valid_record()
        del record["source_key"]
        errors = validate_record(record, check_image=False)
        self.assertTrue(any("Missing required key: source_key" in error for error in errors))

    def test_invalid_enum_types_do_not_raise(self):
        for key in ("language", "source", "quality"):
            with self.subTest(key=key):
                self.assertTrue(validate_record(valid_record(**{key: []}), check_image=False))

    def test_non_string_dates_and_totals_are_rejected(self):
        for field, value in (("date", None), ("date", 20260101), ("total", 25.5), ("total", None)):
            with self.subTest(field=field, value=value):
                gt = valid_record()["ground_truth"]
                gt[field] = value
                errors = validate_record(valid_record(ground_truth=gt), check_image=False)
                self.assertTrue(any(f"ground_truth.{field} must be string" in error for error in errors))

    def test_empty_date_and_total_strings_remain_allowed_by_contract(self):
        gt = valid_record()["ground_truth"]
        gt["date"] = ""
        gt["total"] = ""
        self.assertEqual(validate_record(valid_record(ground_truth=gt), check_image=False), [])

    def test_non_object_nested_fields_are_reported(self):
        record = valid_record(ground_truth=[], ocr=None, prediction=[], annotations="bad")
        errors = validate_record(record, check_image=False)
        self.assertTrue(any("ground_truth must be a dict" in error for error in errors))
        self.assertTrue(any("ocr must be a dict" in error for error in errors))
        self.assertTrue(any("prediction must be a dict" in error for error in errors))
        self.assertTrue(any("annotations must be a dict" in error for error in errors))

    def test_missing_or_invalid_required_nested_contract_fields_are_reported(self):
        record = valid_record(ocr={}, annotations={"image_width": True, "image_height": 0, "label_version": "v1.0"})
        errors = validate_record(record, check_image=False)
        self.assertTrue(any("Missing required key: ocr.engine" in error for error in errors))
        self.assertTrue(any("Missing required key: ocr.words" in error for error in errors))
        self.assertTrue(any("annotations.image_width must be a positive integer" in error for error in errors))
        self.assertTrue(any("annotations.image_height must be a positive integer" in error for error in errors))
        self.assertTrue(any("annotations.label_version must be 'v1.1'" in error for error in errors))

    def test_invalid_image_path_types_empty_and_parent_traversal(self):
        for path in (None, 4, "", "../outside.jpg", r"..\\outside.jpg", "/absolute/image.jpg"):
            with self.subTest(path=path):
                self.assertTrue(validate_record(valid_record(image_path=path), check_image=False))

    def test_missing_and_corrupt_images_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            original_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                missing = validate_record(valid_record(image_path="missing.jpg"), check_image=True)
                self.assertTrue(any("Image not found" in error for error in missing))
                Path("broken.jpg").write_bytes(b"not an image")
                broken = validate_record(valid_record(image_path="broken.jpg"), check_image=True)
                self.assertTrue(any("Image is not readable" in error for error in broken))
            finally:
                os.chdir(original_cwd)

    def test_valid_image_is_opened_and_verified(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is required for image validation")
        with tempfile.TemporaryDirectory() as tmp:
            original_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                Image.new("RGB", (2, 2), "white").save("ok.jpg")
                self.assertEqual(validate_record(valid_record(image_path="ok.jpg"), check_image=True), [])
            finally:
                os.chdir(original_cwd)


class ValidateFileTests(unittest.TestCase):
    def test_malformed_json_is_counted_as_error_not_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text('{"doc_id":"ok"}\n{broken}\n', encoding="utf-8")
            result = validate_file(str(path))
            self.assertEqual(result["malformed_json_lines"], 1)
            self.assertGreater(result["total_errors"], 1)
            self.assertTrue(any("Line 2: malformed JSON" in error for error in result["errors"]))

    def test_duplicate_ids_within_file_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dupes.jsonl"
            row = valid_record()
            path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
            result = validate_file(str(path))
            self.assertEqual(result["duplicate_ids"], 1)
            self.assertTrue(any("duplicate doc_id" in error for error in result["errors"]))

    def test_missing_input_file_fails(self):
        result = validate_file("/definitely/missing/dataset.jsonl")
        self.assertEqual(result["total_errors"], 1)
        self.assertEqual(result["total_records"], 0)

    def test_cli_no_input_fails_instead_of_reporting_success(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("scripts.validate_dataset.Path") as path_mock:
            # Run against a directory with no JSONL files, preserving normal Path behavior.
            path_mock.side_effect = Path
            path_mock.return_value = Path(tmp)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["--input_dir", tmp])
            self.assertEqual(result, 1)
            self.assertIn("no JSONL input files", output.getvalue())


if __name__ == "__main__":
    unittest.main()
