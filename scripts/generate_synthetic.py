"""
Synthetic Invoice/Receipt Generator.

Generates Arabic, English, and mixed invoices/receipts with:
  - Jinja2 HTML templates → rendered to images via Playwright (Chromium)
  - Faker-generated content (en_US, ar_EG, ar_SA)
  - Multiple invoice number patterns, date formats, total formats
  - Image degradations (blur, rotation, noise, shadows, JPEG compression)
  - Ground truth is exactly the rendered string (correct by construction)

Target: 10,000 documents
Distribution:
  - Language: 40% Arabic, 35% English, 25% Mixed
  - Quality: 40% clear, 20% blurry, 20% tilted, 20% noisy
  - Arabic-Indic digits in 30% of Arabic docs
  - At least 8 templates: 2 English, 3 Arabic RTL, 3 mixed

Usage (from Colab):
    %cd /content/drive/MyDrive/data-entry-ds

    # Step 1: Generate 200-document pilot
    !python scripts/generate_synthetic.py --count 200 --pilot

    # Step 2: Generate 1000 after reviewing pilot
    !python scripts/generate_synthetic.py --count 1000

    # Step 3: Generate remaining (with resume)
    !python scripts/generate_synthetic.py --count 10000 --resume

Produces:
    data/synth/out/synthetic.jsonl
    data/synth/out/images/synthetic_<index>.jpg
"""

import sys
import os
import json
import random
import argparse
import hashlib
from pathlib import Path
from collections import Counter
from string import Template

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import detect_lang, write_jsonl, SEED

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

SYNTH_OUT = Path("data/synth/out")
SYNTH_IMAGES = SYNTH_OUT / "images"
SYNTH_FONTS = Path("data/synth/fonts")
SYNTH_TEMPLATES = Path("data/synth/templates")

# Language distribution (prioritize Arabic & Mixed to balance out public English datasets)
LANG_DIST = {"ar": 0.55, "mixed": 0.35, "en": 0.10}

# Quality distribution
QUALITY_DIST = {"clear": 0.40, "blurry": 0.20, "tilted": 0.20, "noisy": 0.20}

# Arabic-Indic digit ratio for Arabic docs
ARABIC_INDIC_RATIO = 0.30

# ──────────────────────────────────────────────
# Arabic-Indic Digit Conversion
# ──────────────────────────────────────────────

WESTERN_TO_INDIC = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
INDIC_TO_WESTERN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def to_arabic_indic(text: str) -> str:
    """Convert Western digits to Arabic-Indic digits."""
    return text.translate(WESTERN_TO_INDIC)


# ──────────────────────────────────────────────
# Content Generation
# ──────────────────────────────────────────────

# Curated Arabic company names (Faker ar_EG can be weak)
ARABIC_COMPANIES = [
    "شركة النور للتجارة", "مؤسسة الأمان", "مطعم الشرق الأوسط",
    "سوبرماركت الخير", "مكتبة المعرفة", "صيدلية الشفاء",
    "شركة الرياض للمقاولات", "مجموعة البركة التجارية", "مطاعم الوادي",
    "شركة السلام للتوريدات", "محلات الزهور", "مركز الحياة الطبي",
    "شركة المستقبل للتقنية", "مؤسسة الفجر", "سوق الجمعة",
    "مطبخ البيت", "شركة الخليج للشحن", "مغسلة النظافة",
    "محل الأناقة", "صالون الجمال", "ورشة الإتقان",
    "مكتب الأعمال", "شركة الوفاء للتجارة", "مطعم الريف",
    "بقالة السعادة", "معرض الأثاث الحديث", "محطة الوقود",
    "شركة القمة للاستثمار", "مؤسسة الإبداع", "مركز التدريب المتقدم",
    "شركة الشرق للإلكترونيات", "مطعم الأصالة", "شركة البناء الحديث",
    "معهد اللغات", "مركز العناية بالسيارات", "شركة النسيم للسياحة",
    "مؤسسة الحرفيين", "شركة الواحة للعقارات", "مطبعة الإخلاص",
    "شركة المدينة للنقل", "محلات بيت الموضة", "مستشفى الرحمة",
    "مؤسسة الثقة للتجارة", "شركة السماء الزرقاء", "مطعم ليالي الشام",
    "شركة التفوق الهندسية", "مؤسسة الكوثر", "مركز الرعاية الصحية",
    "شركة دار السلام", "مجموعة الفلاح التجارية",
    # Additional names for variety
    "هايبر ماركت الأسرة", "شركة أطياف للتصميم", "مطعم بيت الكبسة",
    "مغاسل الدانة", "مركز اللؤلؤة التجاري", "شركة إتمام للخدمات",
    "مؤسسة الأندلس", "شركة الحصاد الزراعية", "مطعم أم علي",
    "معرض الديار للعقارات", "شركة كنوز للمجوهرات", "صيدلية الدواء",
    "محلات الفرسان", "شركة إنجاز للمقاولات", "مطعم زهرة دمشق",
    "مؤسسة الراية", "مركز الحوسبة", "شركة الصقر للنقل",
    "مطعم السدرة", "محلات النخبة", "شركة المنال للتوزيع",
    "مطابخ الشيف", "شركة الجزيرة للاتصالات", "مؤسسة الرائد",
    "مركز البسمة الطبي", "شركة الأفق للاستشارات", "مطعم حدائق الشام",
    "محلات الزين", "شركة قرطبة للتجارة", "مغسلة القصر",
    "شركة السنابل للأغذية", "معرض الواحة للسيارات", "صالة الملتقى",
    "مطعم الفنار", "مؤسسة التميز", "شركة الرواد للتقنية",
    "محلات أسواق الندى", "شركة الربيع للزراعة", "مركز العلوم الطبي",
    "مطعم الباشا", "شركة الهدف للتسويق", "مؤسسة الصفوة",
    "محلات بيت العطور", "شركة الأرز للمواد الغذائية", "مركز البرمجة",
    "شركة أسرار الجمال", "مطعم المشوي العربي", "مؤسسة السفير",
    "شركة الماسة للألماس", "معرض دار الضيافة", "مطعم عرائس الشام",
]

# Invoice number patterns
INVOICE_PATTERNS = {
    "en": [
        "INV-{year}-{num:04d}",
        "F/{num:02d}/{year}",
        "{num:05d}",
        "A-{num:06d}",
        "RCP-{year}{month:02d}-{num:04d}",
        "#{num:06d}",
    ],
    "ar": [
        "فاتورة-{year}-{num:04d}",
        "{num:05d}",
        "ف/{num:02d}/{year}",
        "رقم-{num:06d}",
        "إيصال-{year}{month:02d}-{num:04d}",
        "{num:05d}",  # plain number
    ],
}

# Date formats
DATE_FORMATS = {
    "en": [
        "{day:02d}/{month:02d}/{year}",
        "{year}-{month:02d}-{day:02d}",
        "{month_name} {day}, {year}",
        "{day:02d}-{month:02d}-{year}",
    ],
    "ar": [
        "{day:02d}/{month:02d}/{year}",
        "{year}/{month:02d}/{day:02d}",
        "{day} {month_name_ar} {year}",
        "{day:02d}-{month:02d}-{year}",
    ],
}

MONTH_NAMES_EN = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

MONTH_NAMES_AR = [
    "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]


def generate_invoice_number(lang: str, rng: random.Random, use_indic: bool = False) -> str:
    """Generate a random invoice number."""
    patterns = INVOICE_PATTERNS.get("ar" if lang == "ar" else "en", INVOICE_PATTERNS["en"])
    pattern = rng.choice(patterns)
    year = rng.randint(2020, 2026)
    month = rng.randint(1, 12)
    num = rng.randint(1, 999999)

    result = pattern.format(year=year, month=month, num=num)
    if use_indic:
        result = to_arabic_indic(result)
    return result


def generate_date(lang: str, rng: random.Random, use_indic: bool = False) -> str:
    """Generate a random date string."""
    year = rng.randint(2020, 2026)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)

    formats = DATE_FORMATS.get("ar" if lang == "ar" else "en", DATE_FORMATS["en"])
    fmt = rng.choice(formats)

    result = fmt.format(
        year=year, month=month, day=day,
        month_name=MONTH_NAMES_EN[month],
        month_name_ar=MONTH_NAMES_AR[month],
    )
    if use_indic:
        result = to_arabic_indic(result)
    return result


def generate_total(lang: str, rng: random.Random, use_indic: bool = False) -> str:
    """Generate a random total amount."""
    amount = round(rng.uniform(5.0, 50000.0), 2)

    # Various formats
    fmt_choice = rng.randint(0, 4)
    if fmt_choice == 0:
        result = f"{amount:,.2f}"           # 1,250.50
    elif fmt_choice == 1:
        result = f"{amount:.2f}"            # 1250.50
    elif fmt_choice == 2:
        # European style: 1.250,50
        int_part = int(amount)
        dec_part = round((amount - int_part) * 100)
        int_str = f"{int_part:,}".replace(",", ".")
        result = f"{int_str},{dec_part:02d}"
    elif fmt_choice == 3 and lang in ("ar", "mixed"):
        # With currency
        currencies = ["ر.س", "ج.م", "د.إ", "ريال", "جنيه"]
        currency = rng.choice(currencies)
        result = f"{amount:,.2f} {currency}"
    else:
        result = f"{amount:,.2f}"

    if use_indic:
        result = to_arabic_indic(result)
    return result


def generate_supplier(lang: str, rng: random.Random) -> str:
    """Generate a supplier name."""
    try:
        from faker import Faker
        if lang == "ar":
            return rng.choice(ARABIC_COMPANIES)
        elif lang == "mixed":
            # Mix: Arabic name with English suffix or vice versa
            ar_name = rng.choice(ARABIC_COMPANIES)
            en_suffixes = ["Trading Co.", "Group", "Corp.", "LLC", "Est."]
            return f"{ar_name} - {rng.choice(en_suffixes)}"
        else:
            fake = Faker("en_US")
            Faker.seed(rng.randint(0, 2**31))
            return fake.company()
    except ImportError:
        if lang == "ar":
            return rng.choice(ARABIC_COMPANIES)
        return f"Company {rng.randint(1, 9999)}"


# ──────────────────────────────────────────────
# HTML Templates
# ──────────────────────────────────────────────

def get_templates():
    """Return all HTML invoice templates.
    
    At least 8 templates: 2 English, 3 Arabic RTL, 3 mixed.
    Each template returns ground-truth-accurate HTML.
    """
    templates = {}

    # ── English Template 1: Modern Invoice ──
    templates["en_modern"] = {
        "lang": "en",
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
body {{ font-family: 'Inter', sans-serif; margin: 40px; background: #fff; color: #333; width: 700px; }}
.header {{ display: flex; justify-content: space-between; border-bottom: 3px solid #2563eb; padding-bottom: 20px; margin-bottom: 30px; }}
.company {{ font-size: 24px; font-weight: 700; color: #1e40af; }}
.inv-details {{ text-align: right; }}
.inv-label {{ color: #6b7280; font-size: 12px; text-transform: uppercase; }}
.inv-value {{ font-size: 16px; font-weight: 600; }}
table {{ width: 100%; border-collapse: collapse; margin: 30px 0; }}
th {{ background: #eff6ff; color: #1e40af; padding: 12px; text-align: left; font-size: 12px; text-transform: uppercase; }}
td {{ padding: 12px; border-bottom: 1px solid #e5e7eb; }}
.total-row {{ font-size: 20px; font-weight: 700; color: #1e40af; text-align: right; padding-top: 20px; border-top: 2px solid #2563eb; }}
.distractor {{ color: #9ca3af; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>
<div class="header">
  <div class="company">{supplier}</div>
  <div class="inv-details">
    <div><span class="inv-label">Invoice #</span><br><span class="inv-value">{invoice_number}</span></div>
    <div style="margin-top:10px"><span class="inv-label">Date</span><br><span class="inv-value">{date}</span></div>
    <div style="margin-top:10px"><span class="inv-label">PO Number</span><br><span class="inv-value">{po_number}</span></div>
  </div>
</div>
<table>
<tr><th>Description</th><th>Qty</th><th>Unit Price</th><th>Amount</th></tr>
{line_items}
</table>
<div style="text-align:right">
  <div class="distractor">Subtotal: {subtotal}</div>
  <div class="distractor">Tax ({tax_rate}%): {tax_amount}</div>
  <div class="total-row">Total Due: {total}</div>
</div>
<div class="distractor">
  <p>Due Date: {due_date} | Payment Terms: {payment_terms}</p>
  <p>Bill To: {client_name}</p>
</div>
</body>
</html>""",
    }

    # ── English Template 2: Receipt Style ──
    templates["en_receipt"] = {
        "lang": "en",
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
body {{ font-family: 'Courier New', monospace; margin: 20px; background: #fff; width: 350px; font-size: 14px; }}
.center {{ text-align: center; }}
.company {{ font-size: 20px; font-weight: bold; }}
hr {{ border: 1px dashed #333; }}
.row {{ display: flex; justify-content: space-between; }}
.total {{ font-size: 18px; font-weight: bold; margin-top: 10px; }}
.small {{ font-size: 11px; color: #666; }}
</style>
</head>
<body>
<div class="center">
  <div class="company">{supplier}</div>
  <div class="small">{address}</div>
  <div class="small">Tel: {phone}</div>
</div>
<hr>
<div class="row"><span>Receipt #:</span><span>{invoice_number}</span></div>
<div class="row"><span>Date:</span><span>{date}</span></div>
<div class="row"><span>Cashier:</span><span>{cashier}</span></div>
<hr>
{line_items_receipt}
<hr>
<div class="row"><span>Subtotal:</span><span>{subtotal}</span></div>
<div class="row"><span>Tax:</span><span>{tax_amount}</span></div>
<div class="row total"><span>TOTAL:</span><span>{total}</span></div>
<hr>
<div class="row"><span>Cash:</span><span>{cash_tendered}</span></div>
<div class="row"><span>Change:</span><span>{change}</span></div>
<hr>
<div class="center small">
  <p>Order #: {order_number}</p>
  <p>Thank you for your purchase!</p>
</div>
</body>
</html>""",
    }

    # ── Arabic Template 1: Formal Invoice ──
    templates["ar_formal"] = {
        "lang": "ar",
        "html": """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
body {{ font-family: 'Cairo', sans-serif; margin: 40px; background: #fff; color: #333; width: 700px; direction: rtl; }}
.header {{ display: flex; justify-content: space-between; border-bottom: 3px solid #059669; padding-bottom: 20px; margin-bottom: 30px; }}
.company {{ font-size: 24px; font-weight: 700; color: #065f46; }}
.inv-details {{ text-align: left; }}
.label {{ color: #6b7280; font-size: 12px; }}
.value {{ font-size: 16px; font-weight: 600; }}
table {{ width: 100%; border-collapse: collapse; margin: 30px 0; direction: rtl; }}
th {{ background: #ecfdf5; color: #065f46; padding: 12px; text-align: right; font-size: 13px; }}
td {{ padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right; }}
.total-row {{ font-size: 20px; font-weight: 700; color: #065f46; text-align: left; padding-top: 20px; border-top: 2px solid #059669; }}
.meta {{ color: #9ca3af; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>
<div class="header">
  <div class="company">{supplier}</div>
  <div class="inv-details">
    <div><span class="label">رقم الفاتورة</span><br><span class="value">{invoice_number}</span></div>
    <div style="margin-top:10px"><span class="label">التاريخ</span><br><span class="value">{date}</span></div>
  </div>
</div>
<table>
<tr><th>الوصف</th><th>الكمية</th><th>سعر الوحدة</th><th>المبلغ</th></tr>
{line_items_ar}
</table>
<div style="text-align:left">
  <div class="meta">المجموع الفرعي: {subtotal}</div>
  <div class="meta">الضريبة ({tax_rate}٪): {tax_amount}</div>
  <div class="total-row">الإجمالي: {total}</div>
</div>
<div class="meta">
  <p>رقم الطلب: {po_number} | تاريخ الاستحقاق: {due_date}</p>
  <p>العميل: {client_name}</p>
</div>
</body>
</html>""",
    }

    # ── Arabic Template 2: Receipt ──
    templates["ar_receipt"] = {
        "lang": "ar",
        "html": """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
body {{ font-family: 'Amiri', serif; margin: 20px; background: #fff; width: 350px; font-size: 15px; direction: rtl; }}
.center {{ text-align: center; }}
.company {{ font-size: 22px; font-weight: bold; color: #1a1a1a; }}
hr {{ border: 1px dashed #333; }}
.row {{ display: flex; justify-content: space-between; direction: rtl; padding: 2px 0; }}
.total {{ font-size: 18px; font-weight: bold; margin-top: 10px; }}
.small {{ font-size: 12px; color: #666; }}
</style>
</head>
<body>
<div class="center">
  <div class="company">{supplier}</div>
  <div class="small">{address}</div>
</div>
<hr>
<div class="row"><span>رقم الإيصال:</span><span>{invoice_number}</span></div>
<div class="row"><span>التاريخ:</span><span>{date}</span></div>
<hr>
{line_items_ar_receipt}
<hr>
<div class="row"><span>المجموع الفرعي:</span><span>{subtotal}</span></div>
<div class="row"><span>الضريبة:</span><span>{tax_amount}</span></div>
<div class="row total"><span>المجموع:</span><span>{total}</span></div>
<hr>
<div class="center small">
  <p>رقم العملية: {order_number}</p>
  <p>شكراً لتسوقكم معنا</p>
</div>
</body>
</html>""",
    }

    # ── Arabic Template 3: Commercial ──
    templates["ar_commercial"] = {
        "lang": "ar",
        "html": """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;700&display=swap');
body {{ font-family: 'Noto Naskh Arabic', serif; margin: 30px; background: #fff; width: 700px; direction: rtl; color: #222; }}
.header {{ background: linear-gradient(135deg, #1e3a5f 0%, #2d5f8a 100%); color: white; padding: 25px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
.company {{ font-size: 26px; font-weight: 700; }}
.badge {{ background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 20px; font-size: 14px; }}
.info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px; }}
.info-box {{ background: #f8fafc; padding: 12px; border-radius: 6px; border-right: 3px solid #2d5f8a; }}
.info-label {{ font-size: 11px; color: #64748b; }}
.info-value {{ font-size: 16px; font-weight: 600; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
th {{ background: #1e3a5f; color: white; padding: 12px; text-align: right; }}
td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-align: right; }}
.total-section {{ background: #f0f9ff; padding: 20px; border-radius: 8px; margin-top: 20px; }}
.grand-total {{ font-size: 22px; font-weight: 700; color: #1e3a5f; }}
.footer {{ font-size: 11px; color: #94a3b8; margin-top: 25px; text-align: center; }}
</style>
</head>
<body>
<div class="header">
  <div class="company">{supplier}</div>
  <div class="badge">فاتورة تجارية</div>
</div>
<div class="info-grid">
  <div class="info-box">
    <div class="info-label">رقم الفاتورة</div>
    <div class="info-value">{invoice_number}</div>
  </div>
  <div class="info-box">
    <div class="info-label">التاريخ</div>
    <div class="info-value">{date}</div>
  </div>
  <div class="info-box">
    <div class="info-label">رقم أمر الشراء</div>
    <div class="info-value">{po_number}</div>
  </div>
  <div class="info-box">
    <div class="info-label">العميل</div>
    <div class="info-value">{client_name}</div>
  </div>
</div>
<table>
<tr><th>البند</th><th>الكمية</th><th>السعر</th><th>المبلغ</th></tr>
{line_items_ar}
</table>
<div class="total-section">
  <div class="row" style="display:flex;justify-content:space-between;margin-bottom:8px"><span>المجموع الفرعي:</span><span>{subtotal}</span></div>
  <div class="row" style="display:flex;justify-content:space-between;margin-bottom:8px"><span>ضريبة القيمة المضافة ({tax_rate}٪):</span><span>{tax_amount}</span></div>
  <hr style="border:1px solid #cbd5e1">
  <div style="display:flex;justify-content:space-between;margin-top:10px" class="grand-total"><span>الإجمالي المستحق:</span><span>{total}</span></div>
</div>
<div class="footer">
  <p>تاريخ الاستحقاق: {due_date}</p>
  <p>هذه الفاتورة صادرة إلكترونياً ولا تحتاج إلى توقيع</p>
</div>
</body>
</html>""",
    }

    # ── Mixed Template 1: Bilingual Invoice ──
    templates["mixed_bilingual"] = {
        "lang": "mixed",
        "html": """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&family=Inter:wght@400;600&display=swap');
body {{ font-family: 'Cairo', 'Inter', sans-serif; margin: 30px; background: #fff; width: 700px; direction: rtl; }}
.header {{ border-bottom: 2px solid #7c3aed; padding-bottom: 15px; margin-bottom: 25px; }}
.company {{ font-size: 22px; font-weight: 700; color: #5b21b6; }}
.bilingual {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 20px 0; }}
.field {{ background: #faf5ff; padding: 10px; border-radius: 6px; }}
.label-ar {{ font-size: 12px; color: #7c3aed; }}
.label-en {{ font-size: 11px; color: #a78bfa; direction: ltr; }}
.value {{ font-size: 15px; font-weight: 600; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
th {{ background: #7c3aed; color: white; padding: 10px; text-align: right; font-size: 12px; }}
td {{ padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right; }}
.total {{ font-size: 20px; font-weight: 700; color: #5b21b6; text-align: left; margin-top: 15px; }}
.footer {{ font-size: 11px; color: #9ca3af; margin-top: 20px; }}
</style>
</head>
<body>
<div class="header">
  <div class="company">{supplier}</div>
</div>
<div class="bilingual">
  <div class="field">
    <div class="label-ar">رقم الفاتورة / <span class="label-en">Invoice #</span></div>
    <div class="value">{invoice_number}</div>
  </div>
  <div class="field">
    <div class="label-ar">التاريخ / <span class="label-en">Date</span></div>
    <div class="value">{date}</div>
  </div>
  <div class="field">
    <div class="label-ar">رقم الطلب / <span class="label-en">PO #</span></div>
    <div class="value">{po_number}</div>
  </div>
  <div class="field">
    <div class="label-ar">العميل / <span class="label-en">Client</span></div>
    <div class="value">{client_name}</div>
  </div>
</div>
<table>
<tr><th>الوصف / Description</th><th>الكمية / Qty</th><th>السعر / Price</th><th>المبلغ / Amount</th></tr>
{line_items_mixed}
</table>
<div style="text-align:left">
  <div class="footer">Subtotal / المجموع الفرعي: {subtotal}</div>
  <div class="footer">VAT / ضريبة ({tax_rate}%): {tax_amount}</div>
  <div class="total">Total / الإجمالي: {total}</div>
</div>
</body>
</html>""",
    }

    # ── Mixed Template 2: Modern Bilingual Receipt ──
    templates["mixed_receipt"] = {
        "lang": "mixed",
        "html": """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
body {{ font-family: 'Cairo', sans-serif; margin: 20px; background: #fff; width: 380px; direction: rtl; font-size: 14px; }}
.center {{ text-align: center; }}
.company {{ font-size: 20px; font-weight: bold; }}
.divider {{ border-top: 2px solid #333; margin: 8px 0; }}
.dotted {{ border-top: 1px dotted #999; margin: 6px 0; }}
.row {{ display: flex; justify-content: space-between; padding: 3px 0; }}
.total {{ font-size: 17px; font-weight: bold; }}
.small {{ font-size: 11px; color: #777; }}
</style>
</head>
<body>
<div class="center">
  <div class="company">{supplier}</div>
  <div class="small">{address}</div>
</div>
<div class="divider"></div>
<div class="row"><span>رقم الفاتورة Invoice #</span><span>{invoice_number}</span></div>
<div class="row"><span>التاريخ Date</span><span>{date}</span></div>
<div class="dotted"></div>
{line_items_mixed_receipt}
<div class="dotted"></div>
<div class="row"><span>المجموع الفرعي Subtotal</span><span>{subtotal}</span></div>
<div class="row"><span>الضريبة VAT</span><span>{tax_amount}</span></div>
<div class="divider"></div>
<div class="row total"><span>الإجمالي Total</span><span>{total}</span></div>
<div class="divider"></div>
<div class="center small">
  <p>Order # رقم الطلب: {order_number}</p>
  <p>Thank you! شكراً لزيارتكم</p>
</div>
</body>
</html>""",
    }

    # ── Mixed Template 3: Corporate ──
    templates["mixed_corporate"] = {
        "lang": "mixed",
        "html": """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&family=Inter:wght@400;600&display=swap');
body {{ font-family: 'Cairo', 'Inter', sans-serif; margin: 35px; background: #fff; width: 700px; direction: rtl; }}
.top-bar {{ background: #0f172a; color: white; padding: 20px 25px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }}
.company {{ font-size: 24px; font-weight: 700; }}
.tag {{ background: #eab308; color: #0f172a; padding: 5px 15px; border-radius: 4px; font-weight: 600; font-size: 13px; }}
.details {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 25px 0; }}
.detail-box {{ padding: 12px; border: 1px solid #e2e8f0; border-radius: 6px; }}
.detail-label {{ font-size: 11px; color: #64748b; }}
.detail-value {{ font-size: 15px; font-weight: 600; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
th {{ background: #f1f5f9; padding: 10px; text-align: right; font-size: 12px; color: #475569; }}
td {{ padding: 10px; border-bottom: 1px solid #f1f5f9; text-align: right; }}
.summary {{ display: flex; justify-content: flex-start; margin-top: 20px; }}
.summary-box {{ background: #0f172a; color: white; padding: 20px 30px; border-radius: 8px; min-width: 250px; }}
.summary-row {{ display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px; }}
.summary-total {{ font-size: 20px; font-weight: 700; color: #eab308; border-top: 1px solid #334155; padding-top: 10px; margin-top: 8px; }}
.note {{ font-size: 11px; color: #94a3b8; margin-top: 20px; }}
</style>
</head>
<body>
<div class="top-bar">
  <div class="company">{supplier}</div>
  <div class="tag">TAX INVOICE / فاتورة ضريبية</div>
</div>
<div class="details">
  <div class="detail-box">
    <div class="detail-label">Invoice No. / رقم الفاتورة</div>
    <div class="detail-value">{invoice_number}</div>
  </div>
  <div class="detail-box">
    <div class="detail-label">Date / التاريخ</div>
    <div class="detail-value">{date}</div>
  </div>
  <div class="detail-box">
    <div class="detail-label">Due Date / تاريخ الاستحقاق</div>
    <div class="detail-value">{due_date}</div>
  </div>
</div>
<table>
<tr><th>#</th><th>Item / البند</th><th>Qty / الكمية</th><th>Price / السعر</th><th>Amount / المبلغ</th></tr>
{line_items_mixed}
</table>
<div class="summary">
  <div class="summary-box">
    <div class="summary-row"><span>Subtotal / المجموع الفرعي</span><span>{subtotal}</span></div>
    <div class="summary-row"><span>VAT ({tax_rate}%) / ضريبة</span><span>{tax_amount}</span></div>
    <div class="summary-row summary-total"><span>Total / الإجمالي</span><span>{total}</span></div>
  </div>
</div>
<div class="note">
  <p>PO: {po_number} | Client: {client_name}</p>
</div>
</body>
</html>""",
    }

    return templates


# ──────────────────────────────────────────────
# Line Item Generation
# ──────────────────────────────────────────────

ITEMS_EN = [
    "Office Supplies", "Laptop Computer", "Printer Paper A4", "Desk Chair",
    "Monitor 27-inch", "USB Cable", "Wireless Mouse", "Keyboard",
    "External Hard Drive", "Software License", "Cloud Storage 1TB",
    "Consultation Service", "Training Session", "Maintenance Fee",
    "Shipping & Handling", "Web Hosting", "Domain Registration",
    "Graphic Design", "Data Entry Service", "Translation Service",
]

ITEMS_AR = [
    "لوازم مكتبية", "حاسب محمول", "ورق طباعة A4", "كرسي مكتب",
    "شاشة عرض", "كابل USB", "فأرة لاسلكية", "لوحة مفاتيح",
    "قرص صلب خارجي", "ترخيص برمجيات", "تخزين سحابي",
    "خدمة استشارية", "جلسة تدريبية", "رسوم صيانة",
    "شحن وتوصيل", "استضافة مواقع", "تسجيل نطاق",
    "تصميم جرافيك", "خدمة إدخال بيانات", "خدمة ترجمة",
]


def generate_line_items(lang: str, rng: random.Random, use_indic: bool = False):
    """Generate random line items for an invoice."""
    n_items = rng.randint(2, 8)
    items = []
    total = 0.0

    for _ in range(n_items):
        if lang == "ar":
            desc = rng.choice(ITEMS_AR)
        elif lang == "mixed":
            desc_en = rng.choice(ITEMS_EN)
            desc_ar = rng.choice(ITEMS_AR)
            desc = f"{desc_ar} / {desc_en}"
        else:
            desc = rng.choice(ITEMS_EN)

        qty = rng.randint(1, 20)
        price = round(rng.uniform(5.0, 2000.0), 2)
        amount = round(qty * price, 2)
        total += amount
        items.append({"desc": desc, "qty": qty, "price": price, "amount": amount})

    return items, total


def format_line_items_html(items, template_type, use_indic=False):
    """Format line items as HTML table rows."""
    rows = []
    for item in items:
        price_str = f"{item['price']:,.2f}"
        amount_str = f"{item['amount']:,.2f}"
        qty_str = str(item['qty'])
        if use_indic:
            price_str = to_arabic_indic(price_str)
            amount_str = to_arabic_indic(amount_str)
            qty_str = to_arabic_indic(qty_str)

        if "receipt" in template_type:
            rows.append(f'<div class="row"><span>{item["desc"]}</span><span>{amount_str}</span></div>')
        elif "mixed" in template_type and "receipt" in template_type:
            rows.append(f'<div class="row"><span>{item["desc"]}</span><span>{amount_str}</span></div>')
        else:
            if "mixed" in template_type:
                rows.append(f'<tr><td>{len(rows)+1}</td><td>{item["desc"]}</td><td>{qty_str}</td><td>{price_str}</td><td>{amount_str}</td></tr>')
            else:
                rows.append(f'<tr><td>{item["desc"]}</td><td>{qty_str}</td><td>{price_str}</td><td>{amount_str}</td></tr>')
    return "\n".join(rows)


# ──────────────────────────────────────────────
# Image Degradations
# ──────────────────────────────────────────────

def apply_degradation(image, quality_type: str, rng: random.Random):
    """Apply image degradations based on quality type.
    
    Returns the degraded image and a list of applied degradations.
    """
    import numpy as np
    import cv2

    img_array = np.array(image)
    degradations = []

    if quality_type == "clear":
        # No degradation
        pass

    elif quality_type == "blurry":
        kernel_size = rng.choice([3, 5, 7])
        img_array = cv2.GaussianBlur(img_array, (kernel_size, kernel_size), 0)
        degradations.append(f"gaussian_blur_k{kernel_size}")

    elif quality_type == "tilted":
        angle = rng.uniform(-15, 15)
        h, w = img_array.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        # Calculate new bounding box
        cos = abs(matrix[0, 0])
        sin = abs(matrix[0, 1])
        new_w = int(h * sin + w * cos)
        new_h = int(h * cos + w * sin)
        matrix[0, 2] += (new_w - w) / 2
        matrix[1, 2] += (new_h - h) / 2
        img_array = cv2.warpAffine(
            img_array, matrix, (new_w, new_h),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )
        degradations.append(f"rotation_{angle:.1f}deg")

    elif quality_type == "noisy":
        # Gaussian noise
        noise_level = rng.randint(10, 40)
        noise = np.random.RandomState(rng.randint(0, 2**31)).normal(0, noise_level, img_array.shape)
        img_array = np.clip(img_array.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        degradations.append(f"gaussian_noise_sigma{noise_level}")

        # Optional: add low contrast
        if rng.random() < 0.5:
            alpha = rng.uniform(0.5, 0.8)
            beta = rng.randint(20, 60)
            img_array = np.clip(alpha * img_array.astype(np.float32) + beta, 0, 255).astype(np.uint8)
            degradations.append(f"low_contrast_a{alpha:.2f}_b{beta}")

    # Optional JPEG compression artifact (for non-clear)
    if quality_type != "clear" and rng.random() < 0.4:
        jpeg_quality = rng.randint(30, 70)
        from PIL import Image
        import io
        pil_img = Image.fromarray(img_array)
        buf = io.BytesIO()
        pil_img.save(buf, "JPEG", quality=jpeg_quality)
        buf.seek(0)
        pil_img = Image.open(buf)
        img_array = np.array(pil_img)
        degradations.append(f"jpeg_compression_q{jpeg_quality}")

    from PIL import Image
    return Image.fromarray(img_array), degradations


# ──────────────────────────────────────────────
# Main Generator
# ──────────────────────────────────────────────

def generate_document(index: int, template_id: str, template: dict,
                      quality_type: str, rng: random.Random):
    """Generate a single synthetic document.
    
    Returns (record_dict, html_string) or None on failure.
    """
    lang = template["lang"]
    use_indic = (lang == "ar" and rng.random() < ARABIC_INDIC_RATIO)

    # Generate content
    supplier = generate_supplier(lang, rng)
    invoice_number = generate_invoice_number(lang, rng, use_indic)
    date_str = generate_date(lang, rng, use_indic)
    line_items, subtotal_float = generate_line_items(lang, rng, use_indic)
    tax_rate = rng.choice([5, 10, 14, 15])
    tax_float = round(subtotal_float * tax_rate / 100, 2)
    total_float = round(subtotal_float + tax_float, 2)
    total_str = generate_total(lang, rng, use_indic)

    # Override total_str with the calculated total for consistency
    total_str_calc = f"{total_float:,.2f}"
    if use_indic:
        total_str_calc = to_arabic_indic(total_str_calc)
    # Use generated format for ground truth (more diverse)
    # total_str is the ground truth

    subtotal_str = f"{subtotal_float:,.2f}"
    tax_str = f"{tax_float:,.2f}"
    if use_indic:
        subtotal_str = to_arabic_indic(subtotal_str)
        tax_str = to_arabic_indic(tax_str)

    # Distractor content
    po_number = f"PO-{rng.randint(1000, 9999)}"
    due_date = generate_date(lang, rng, use_indic)
    client_name = generate_supplier("en", rng) if lang != "ar" else rng.choice(ARABIC_COMPANIES[:20])
    cashier = f"Cashier {rng.randint(1, 20)}"
    order_number = f"{rng.randint(100000, 999999)}"
    address = f"{rng.randint(1, 999)} Street {rng.randint(1, 50)}"
    phone = f"+966-{rng.randint(50, 59)}-{rng.randint(1000000, 9999999)}"
    payment_terms = rng.choice(["Net 30", "Net 60", "Due on receipt", "COD"])
    cash_f = total_float + rng.randint(1, 50)
    change_f = round(cash_f - total_float, 2)
    cash_tendered = f"{cash_f:,.2f}"
    change_str = f"{change_f:,.2f}"

    # Format line items HTML
    line_items_html = format_line_items_html(line_items, template_id, use_indic)

    # Fill template
    try:
        html = template["html"].format(
            supplier=supplier,
            invoice_number=invoice_number,
            date=date_str,
            total=total_str,
            subtotal=subtotal_str,
            tax_rate=tax_rate,
            tax_amount=tax_str,
            po_number=po_number,
            due_date=due_date,
            client_name=client_name,
            cashier=cashier,
            order_number=order_number,
            address=address,
            phone=phone,
            payment_terms=payment_terms,
            cash_tendered=cash_tendered,
            change=change_str,
            line_items=line_items_html,
            line_items_receipt=line_items_html,
            line_items_ar=line_items_html,
            line_items_ar_receipt=line_items_html,
            line_items_mixed=line_items_html,
            line_items_mixed_receipt=line_items_html,
        )
    except KeyError as e:
        print(f"  [WARN] Template '{template_id}' missing key: {e}")
        return None

    # Build record
    doc_id = f"synthetic_train_{index:05d}"
    ground_truth = {
        "invoice_number": invoice_number,
        "date": date_str,
        "supplier": supplier,
        "total": total_str,
    }

    record = {
        "doc_id": doc_id,
        "image_path": f"data/synth/out/images/{doc_id}.jpg",
        "language": lang,
        "source": "synthetic",
        "quality": quality_type,
        "ground_truth": ground_truth,
        "ocr": {"engine": "", "words": []},
        "prediction": {},
        "annotations": {
            "template_id": template_id,
            "font": "Cairo" if lang in ("ar", "mixed") else "Inter",
            "seed": SEED + index,
            "degradations": [],  # filled after rendering
            "locale": "ar_EG" if lang == "ar" else "en_US" if lang == "en" else "mixed",
            "use_arabic_indic": use_indic,
        },
        "source_split": "train",
        "source_key": f"{index:05d}",
    }

    return record, html


class PlaywrightBatchRenderer:
    """Persistent Playwright browser renderer for high-speed batch image generation."""

    def __init__(self, width: int = 800):
        self.width = width
        self.playwright = None
        self.browser = None
        self.page = None
        self.available = None

    def start(self):
        if self.available is False:
            return False
        try:
            from playwright.sync_api import sync_playwright
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                ],
            )
            self.page = self.browser.new_page(viewport={"width": self.width, "height": 1200})
            self.available = True
            return True
        except Exception as e:
            print(f"  [WARN] Playwright persistent browser init failed: {e}")
            self.available = False
            return False

    def render(self, html: str, output_path: Path) -> bool:
        if self.available is None:
            self.start()

        if self.available and self.page is not None:
            try:
                self.page.set_content(html, wait_until="load")
                height = self.page.evaluate("document.body.scrollHeight")
                self.page.set_viewport_size({"width": self.width, "height": max(int(height) + 30, 400)})
                self.page.screenshot(path=str(output_path), full_page=True, type="jpeg", quality=90)
                return True
            except Exception as e:
                # Attempt one restart on crash
                try:
                    self.page = self.browser.new_page(viewport={"width": self.width, "height": 1200})
                    self.page.set_content(html, wait_until="load")
                    height = self.page.evaluate("document.body.scrollHeight")
                    self.page.set_viewport_size({"width": self.width, "height": max(int(height) + 30, 400)})
                    self.page.screenshot(path=str(output_path), full_page=True, type="jpeg", quality=90)
                    return True
                except Exception:
                    pass

        # Fallback to saving HTML + wkhtmltoimage
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")
        try:
            import subprocess
            result = subprocess.run(
                ["wkhtmltoimage", "--quality", "90", "--width", str(self.width),
                 str(html_path), str(output_path)],
                capture_output=True, timeout=30,
            )
            if result.returncode == 0:
                html_path.unlink()
                return True
        except Exception:
            pass

        return False

    def close(self):
        if self.page:
            try:
                self.page.close()
            except Exception:
                pass
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass


def generate_synthetic(count: int = 3500, pilot: bool = False, resume: bool = False):
    """Generate synthetic invoice/receipt documents.
    
    Args:
        count: Number of documents to generate (default: 3500).
        pilot: If True, only generate 200 for review.
        resume: If True, resume from last checkpoint.
    """
    if pilot:
        count = min(count, 200)

    print("=" * 60)
    print(f"Generating {count} Synthetic Documents" + (" (PILOT)" if pilot else ""))
    print("=" * 60)

    SYNTH_IMAGES.mkdir(parents=True, exist_ok=True)

    templates = get_templates()
    print(f"  Templates: {len(templates)}")
    for tid, t in templates.items():
        print(f"    {tid} ({t['lang']})")

    # Check resume
    existing_records = []
    start_index = 0
    checkpoint_path = SYNTH_OUT / "checkpoint.json"

    if resume and checkpoint_path.exists():
        with open(checkpoint_path, "r") as f:
            checkpoint = json.load(f)
        start_index = checkpoint.get("last_index", 0) + 1
        # Load existing records
        jsonl_path = SYNTH_OUT / "synthetic.jsonl"
        if jsonl_path.exists():
            from utils import read_jsonl
            existing_records = read_jsonl(jsonl_path)
        print(f"  Resuming from index {start_index} ({len(existing_records)} existing)")

    # Build generation plan
    plan = []
    for i in range(start_index, count):
        # Determine language
        r = random.Random(SEED + i)
        roll = r.random()
        if roll < LANG_DIST["ar"]:
            lang = "ar"
        elif roll < LANG_DIST["ar"] + LANG_DIST["mixed"]:
            lang = "mixed"
        else:
            lang = "en"

        # Pick template matching language
        matching = [(tid, t) for tid, t in templates.items() if t["lang"] == lang]
        if not matching:
            matching = list(templates.items())
        tid, template = r.choice(matching)

        # Determine quality
        qroll = r.random()
        cumulative = 0
        quality = "clear"
        for q, prob in QUALITY_DIST.items():
            cumulative += prob
            if qroll < cumulative:
                quality = q
                break

        plan.append((i, tid, template, quality))

    print(f"  Documents to generate: {len(plan)}")

    # Distribution check
    lang_dist = Counter(templates[tid]["lang"] for _, tid, _, _ in plan)
    quality_dist = Counter(q for _, _, _, q in plan)
    print(f"  Language distribution: {dict(lang_dist)}")
    print(f"  Quality distribution: {dict(quality_dist)}")

    # Initialize batch renderer
    renderer = PlaywrightBatchRenderer(width=800)
    renderer.start()

    # Generate!
    records = list(existing_records)
    batch_size = 250
    success = 0
    failures = 0

    try:
        for batch_start in range(0, len(plan), batch_size):
            batch = plan[batch_start:batch_start + batch_size]
            print(f"\n  Batch {batch_start // batch_size + 1}: "
                  f"documents {batch[0][0]}–{batch[-1][0]}")

            for idx, tid, template, quality in batch:
                rng = random.Random(SEED + idx)
                result = generate_document(idx, tid, template, quality, rng)

                if result is None:
                    failures += 1
                    continue

                record, html = result
                output_img = SYNTH_IMAGES / f"{record['doc_id']}.jpg"

                # Fast render
                rendered = renderer.render(html, output_img)
                if not rendered:
                    failures += 1
                    continue

                # Apply degradation
                if quality != "clear" and output_img.exists():
                    try:
                        from PIL import Image
                        img = Image.open(output_img)
                        img, degradation_list = apply_degradation(img, quality, rng)
                        img.save(str(output_img), "JPEG", quality=85)
                        record["annotations"]["degradations"] = degradation_list
                    except Exception as e:
                        print(f"  [WARN] Degradation failed for {record['doc_id']}: {e}")

                records.append(record)
                success += 1

            # Checkpoint after each batch
            write_jsonl(records, SYNTH_OUT / "synthetic.jsonl")
            with open(checkpoint_path, "w") as f:
                json.dump({"last_index": batch[-1][0], "total": len(records)}, f)
            print(f"  ✅ Checkpoint saved: {len(records)} records rendered")
    finally:
        renderer.close()

    # Final write
    write_jsonl(records, SYNTH_OUT / "synthetic.jsonl")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"SYNTHETIC GENERATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Requested: {count}")
    print(f"  Generated: {success}")
    print(f"  Failed:    {failures}")
    print(f"  Total in file: {len(records)}")

    lang_final = Counter(r["language"] for r in records)
    qual_final = Counter(r["quality"] for r in records)
    templ_final = Counter(r["annotations"].get("template_id", "?") for r in records)
    print(f"\n  Language: {dict(lang_final)}")
    print(f"  Quality:  {dict(qual_final)}")
    print(f"  Template: {dict(templ_final)}")

    if pilot:
        print(f"\n  🔍 PILOT MODE: Review the images in {SYNTH_IMAGES}")
        print(f"  Check for:")
        print(f"    - Arabic letters are connected (not isolated)")
        print(f"    - RTL direction is correct")
        print(f"    - Arabic-Indic digits render properly")
        print(f"    - Text is readable")
        print(f"  Then run: !python scripts/generate_synthetic.py --count 10000")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic invoices/receipts")
    parser.add_argument("--count", type=int, default=10000,
                        help="Number of documents to generate")
    parser.add_argument("--pilot", action="store_true",
                        help="Pilot mode: generate only 200 for review")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last checkpoint")
    args = parser.parse_args()

    generate_synthetic(count=args.count, pilot=args.pilot, resume=args.resume)


if __name__ == "__main__":
    main()
