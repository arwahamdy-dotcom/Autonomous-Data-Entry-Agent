# Labeling Guide — Real Document Annotation

> **Version:** 1.0  
> **Date:** 2026-10-24  
> **For:** All team members labeling real invoices/receipts

---

## Overview

You will label **4 fields** on each invoice or receipt:

1. **`supplier`** — The issuing business name
2. **`date`** — The invoice/issue date
3. **`total`** — The final amount due
4. **`invoice_number`** — The invoice or receipt number

---

## General Rules

| Rule | Detail |
|---|---|
| **Copy exactly as printed** | Type the text exactly as it appears on the document. Include Arabic-Indic digits (٠١٢٣), currency symbols, punctuation, etc. |
| **No cleaning or normalization** | Do NOT convert date formats, remove currency symbols, or standardize numbers. |
| **Field is absent** | Leave the field **empty** (blank). Never guess or infer. |
| **Field is unreadable** | Leave the field **empty** and add a note in the comments. |
| **Multiple candidates** | Choose the most prominent one. Add a note if ambiguous. |
| **Trim whitespace** | Remove leading and trailing spaces, but preserve internal whitespace. |

---

## Field-by-Field Instructions

### 1. `supplier` — Issuing Business Name

✅ **This IS the supplier:**
- The name of the store, restaurant, company, or business that **issued** the invoice/receipt
- The business name at the **top** of the document
- The registered trade name

❌ **This is NOT the supplier:**
- The customer's name
- The delivery company's name
- "Bill To" or "Ship To" names
- Bank or payment processor names

**Examples:**
- `MEGA MART` (English receipt)
- `مطعم الشرق` (Arabic receipt)
- `Carrefour كارفور` (mixed — copy both)

### 2. `date` — Invoice/Issue Date

✅ **This IS the date:**
- The **issue date** or **invoice date** printed on the document
- The date the transaction occurred

❌ **This is NOT the date:**
- Due date / payment deadline
- Delivery date
- Print date (if different from issue date)

**Copy the format exactly as printed:**
- `25/10/2024` → label as `25/10/2024`
- `2024-10-25` → label as `2024-10-25`
- `October 25, 2024` → label as `October 25, 2024`
- `٢٥/١٠/٢٠٢٤` → label as `٢٥/١٠/٢٠٢٤`
- `25 أكتوبر 2024` → label as `25 أكتوبر 2024`

### 3. `total` — Final Amount Due

✅ **This IS the total:**
- The **final amount** the customer pays
- Usually labeled "Total", "Grand Total", "المجموع", "الإجمالي"
- **Includes tax** (VAT, sales tax, etc.)

❌ **This is NOT the total:**
- Subtotal (before tax)
- Individual line item amounts
- Tax amount alone
- Change / cash tendered

**Copy the format exactly as printed:**
- `1,250.50` → label as `1,250.50`
- `SAR 1,250.50` → label as `SAR 1,250.50`
- `١٬٢٥٠٫٥٠ ر.س` → label as `١٬٢٥٠٫٥٠ ر.س`
- `$25.99` → label as `$25.99`

### 4. `invoice_number` — Invoice or Receipt Number

✅ **This IS the invoice number:**
- Invoice number / receipt number / فاتورة رقم
- Transaction number (if no invoice number exists)
- Usually labeled "Invoice #", "Receipt No.", "رقم الفاتورة"

❌ **This is NOT the invoice number:**
- Purchase Order (PO) number
- Order number (unless it's the only identifier)
- Table number
- Customer ID
- Reference number (unless it's clearly the invoice number)

**Examples:**
- `INV-2024-0012`
- `F/45/2024`
- `00123`
- `٠٠١٢٣`

---

## Arabic-Specific Notes

1. **Arabic-Indic digits** (٠١٢٣٤٥٦٧٨٩): Copy them as-is. Do NOT convert to Western digits.
2. **Mixed text**: If a field contains both Arabic and English, copy both exactly as they appear.
3. **Right-to-left**: Copy the text in reading order. The labeling tool should handle direction.

---

## Ambiguous Cases — Quick Reference

| Situation | Action |
|---|---|
| Two dates on the document | Use the **issue/invoice date**, not the due date |
| "Total" and "Grand Total" both present | Use **Grand Total** |
| VAT-inclusive and VAT-exclusive totals | Use the **VAT-inclusive** (larger) amount |
| Multiple business names | Use the **most prominent** one (usually largest, at the top) |
| Stamped or handwritten over printed text | Use the **printed** text if readable; note the stamp |
| Receipt has no invoice number | Leave empty |
| Field is partially cut off | Leave empty and add a note |

---

## Anonymization (Before Labeling)

Before uploading any document, **remove or redact**:
- Personal names (customer names)
- Phone numbers
- Credit/debit card numbers
- National ID numbers
- Email addresses
- Home addresses

**Business names and addresses should be kept** — they are not personal data in this context.

---

## Quality Notes

When labeling, also assess the image quality:
- `clear` — Text is fully readable, image is straight
- `blurry` — Some text is hard to read due to blur
- `tilted` — Document is rotated or skewed
- `noisy` — Background noise, stains, shadows, or poor lighting

---

## Agreement Check

- After the first round, **20 random documents** will be relabeled by a second annotator.
- We will compute **exact-match agreement** per field.
- Any field below **90% agreement** → we will revise this guide and relabel affected documents.
- 20 documents is a small sample. We will report the numbers honestly with this caveat.
