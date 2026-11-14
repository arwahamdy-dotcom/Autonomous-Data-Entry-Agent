"""
ocr/engines.py  (Person 2)  -- v2

One wrapper per OCR engine, all returning the same output:
    [{"text": str, "bbox": [x1, y1, x2, y2], "conf": float 0..1}, ...]

This matches the "ocr.words" field of the team data contract.

Usage:
    from ocr.engines import run_ocr, ENGINES
    words = run_ocr("tesseract", "data/processed/images/cord_0001.jpg")
    words, seconds = run_ocr("paddle", path, timed=True)

Granularity differs per engine:
    tesseract -> words      easyocr / paddle / surya -> text lines (or blocks for surya >= 0.20)

Heavy libraries are imported lazily, so a missing engine only fails
when you actually call it.

v2 changes:
    - Paddle: oneDNN (mkldnn) turned off, which avoids the NotImplementedError on paddle 3.x
    - Surya: works with both the old API (surya-ocr 0.17.x) and the new one (0.20+)
"""
import re
import time
from functools import lru_cache

Word = dict  # {"text": str, "bbox": [x1,y1,x2,y2], "conf": float}


# ---------- helpers ----------
def _poly_to_bbox(poly):
    """Convert a polygon [[x,y],...] to [x1,y1,x2,y2] with ints."""
    xs = [float(p[0]) for p in poly]
    ys = [float(p[1]) for p in poly]
    return [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]


def _clamp01(x):
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 0.0


def _word(text, bbox, conf):
    return {"text": str(text).strip(), "bbox": [int(v) for v in bbox], "conf": _clamp01(conf)}


def _clean(words):
    return [w for w in words if w["text"]]


def _strip_tags(s):
    """Remove simple HTML tags (<b>, <br>, ...) and squeeze whitespace."""
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


# ---------- Tesseract ----------
def ocr_tesseract(image_path, lang="ara+eng", psm=6) -> list[Word]:
    import pytesseract
    from PIL import Image

    img = Image.open(image_path).convert("RGB")
    data = pytesseract.image_to_data(
        img, lang=lang, config=f"--psm {psm}", output_type=pytesseract.Output.DICT
    )
    words = []
    for i, txt in enumerate(data["text"]):
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            continue
        if conf < 0 or not str(txt).strip():
            continue  # -1 means "not a word" (layout block)
        x, y, w, h = (data[k][i] for k in ("left", "top", "width", "height"))
        words.append(_word(txt, [x, y, x + w, y + h], conf / 100.0))
    return _clean(words)


# ---------- EasyOCR ----------
@lru_cache(maxsize=2)
def _easyocr_reader(langs=("ar", "en"), gpu=True):
    import easyocr
    return easyocr.Reader(list(langs), gpu=gpu)


def ocr_easyocr(image_path, langs=("ar", "en"), gpu=True) -> list[Word]:
    reader = _easyocr_reader(tuple(langs), gpu)
    results = reader.readtext(str(image_path))  # [(poly, text, conf), ...]
    return _clean([_word(t, _poly_to_bbox(p), c) for p, t, c in results])


# ---------- PaddleOCR (paddle 3.x and 2.x) ----------
@lru_cache(maxsize=2)
def _paddle_engine(lang="ar"):
    from paddleocr import PaddleOCR

    v3 = dict(lang=lang, use_doc_orientation_classify=False,
              use_doc_unwarping=False, use_textline_orientation=False)
    attempts = [
        dict(v3, enable_mkldnn=False),            # 3.x, oneDNN off (fixes the NotImplementedError)
        v3,                                        # 3.x without the flag
        dict(lang=lang, use_angle_cls=True, show_log=False),  # 2.x
    ]
    last = None
    for kwargs in attempts:
        try:
            return PaddleOCR(**kwargs)
        except (TypeError, ValueError) as e:
            last = e
    raise last


def ocr_paddle(image_path, lang="ar") -> list[Word]:
    engine = _paddle_engine(lang)
    words = []
    if hasattr(engine, "predict"):  # v3.x
        for res in engine.predict(str(image_path)):
            data = getattr(res, "json", None)
            r = data["res"] if isinstance(data, dict) and "res" in data else res
            texts = r.get("rec_texts", [])
            scores = r.get("rec_scores", [])
            polys = r.get("rec_polys", r.get("dt_polys", []))
            for t, s, p in zip(texts, scores, polys):
                words.append(_word(t, _poly_to_bbox(p), s))
    else:  # v2.x
        out = engine.ocr(str(image_path), cls=True)
        for page in out or []:
            for poly, (t, s) in page or []:
                words.append(_word(t, _poly_to_bbox(poly), s))
    return _clean(words)


# ---------- Surya ----------
# surya-ocr 0.17.x  ("v1"): FoundationPredictor + DetectionPredictor, output has text_lines
# surya-ocr 0.20+  ("v2"): SuryaInferenceManager (starts a model server), output has blocks with html
@lru_cache(maxsize=1)
def _surya_api():
    try:
        from surya.inference import SuryaInferenceManager  # only exists in 0.20+
        from surya.recognition import RecognitionPredictor
        return "v2", RecognitionPredictor(SuryaInferenceManager()), None
    except ImportError:
        pass
    from surya.detection import DetectionPredictor
    from surya.foundation import FoundationPredictor
    from surya.recognition import RecognitionPredictor
    return "v1", RecognitionPredictor(FoundationPredictor()), DetectionPredictor()


def ocr_surya(image_path) -> list[Word]:
    from PIL import Image

    version, rec, det = _surya_api()
    img = Image.open(image_path).convert("RGB")
    words = []
    if version == "v2":
        page = rec([img])[0]
        for b in page.blocks:
            words.append(_word(_strip_tags(b.html), b.bbox, getattr(b, "confidence", 0.0)))
    else:
        result = rec([img], det_predictor=det)[0]
        for line in result.text_lines:
            words.append(_word(_strip_tags(line.text), line.bbox, getattr(line, "confidence", 0.0)))
    return _clean(words)


# ---------- registry ----------
ENGINES = {
    "tesseract": ocr_tesseract,
    "easyocr": ocr_easyocr,
    "paddle": ocr_paddle,
    "surya": ocr_surya,
}


def run_ocr(engine: str, image_path, timed=False, **kwargs):
    """Run one engine. If timed=True returns (words, seconds)."""
    if engine not in ENGINES:
        raise ValueError(f"Unknown engine '{engine}'. Choose from {list(ENGINES)}")
    t0 = time.perf_counter()
    words = ENGINES[engine](image_path, **kwargs)
    dt = time.perf_counter() - t0
    return (words, dt) if timed else words


def words_to_text(words: list[Word]) -> str:
    """Join words into reading order (top-to-bottom, then left-to-right).
    For RTL-heavy lines you may want to sort right-to-left instead."""
    ordered = sorted(words, key=lambda w: (round(w["bbox"][1] / 15), w["bbox"][0]))
    return " ".join(w["text"] for w in ordered)


if __name__ == "__main__":
    import json
    import sys

    path = sys.argv[1]
    for name in ENGINES:
        try:
            w, dt = run_ocr(name, path, timed=True)
            print(f"{name}: {len(w)} items, {dt:.2f}s")
            print(json.dumps(w[:3], ensure_ascii=False))
        except Exception as e:  # one broken engine must not stop the others
            print(f"{name}: FAILED -> {type(e).__name__}: {e}")
