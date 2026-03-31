# pdf-redact

Redact personal information from a PDF. Metadata is always stripped.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pymupdf
```

## How to run

```bash
.venv/bin/python redact.py your-document.pdf [options]
```

The redacted file is saved automatically as `your-document_redacted_TIMESTAMP.pdf`
in the same folder. The original is never modified.

To choose your own output filename, add it as the second argument:

```bash
.venv/bin/python redact.py input.pdf clean-version.pdf [options]
```

## Important: repeating flags

Flags like `--name`, `--text`, `--after-header`, and `--region` must be
written **once per value**. You cannot list multiple values after one flag.

```bash
# Correct — one --name per variant:
--name "Jane Smith" --name "J. Smith" --name "Smith"

# Wrong — only the first name would be used:
--name "Jane Smith" "J. Smith" "Smith"
```

## Options

**Strings and locations:**

| Flag | What it does |
|---|---|
| `--name "..."` | Redact a name wherever it appears (case-insensitive) |
| `--text "..."` | Redact any exact string — address, company, reference number, etc. |
| `--after-header "..."` | Redact the value immediately after or below a label |
| `--region "x1,y1,x2,y2"` | Redact a specific rectangle on the page by coordinates |

**Automatic pattern categories:**

| Flag | What it redacts |
|---|---|
| `--emails` | Email addresses |
| `--phones` | Phone numbers (Dutch/international) |
| `--ids` | 9-digit ID numbers (Dutch BSN, Israeli Teudat Zehut, etc.) |
| `--iban` | IBAN bank account numbers (any country) |
| `--postcodes` | Dutch postal codes (e.g. 1234 AB) |
| `--israeli` | Israeli phone format (05X-XXX-XXXX) and 9-digit IDs |
| `--financial` | Currency amounts (anything with €, $, £, or ₪) |
| `--all` | All categories above |

## Examples

**Redact a name and all common patterns:**
```bash
.venv/bin/python redact.py letter.pdf --name "Jane Smith" --all
```

**Redact multiple name variants** (use `--name` once per variant):
```bash
.venv/bin/python redact.py letter.pdf \
    --name "Jane Smith" \
    --name "J. Smith" \
    --name "Smith"
```

**Redact the value under a label** (works for both same-line and next-line layouts):
```bash
.venv/bin/python redact.py document.pdf --after-header "Burgerservicenummer"
```

**Redact values under multiple labels** (use `--after-header` once per label):
```bash
.venv/bin/python redact.py document.pdf \
    --after-header "Burgerservicenummer" \
    --after-header "IBAN" \
    --after-header "Betaalkenmerk"
```

**Redact a specific area by coordinates.**
Open the PDF in Preview on Mac (Tools → Show Inspector) to find coordinates.
`x1,y1` is the top-left corner of the area, `x2,y2` is the bottom-right:
```bash
.venv/bin/python redact.py document.pdf --region "50,100,300,130"
```

**Redact multiple regions** (use `--region` once per region):
```bash
.venv/bin/python redact.py document.pdf \
    --region "50,100,300,130" \
    --region "50,200,400,220"
```

**Redact names, an address, and financial amounts together:**
```bash
.venv/bin/python redact.py payslip.pdf \
    --name "Jane Smith" \
    --text "Kerkstraat 12" \
    --text "1234 AB Amsterdam" \
    --financial
```

**Israeli document:**
```bash
.venv/bin/python redact.py tofes.pdf \
    --name "ישראל ישראלי" \
    --name "ישראלי" \
    --israeli \
    --financial
```

**Combine everything:**
```bash
.venv/bin/python redact.py invoice.pdf \
    --name "Jane Smith" \
    --after-header "Account number" \
    --region "50,400,300,420" \
    --emails \
    --financial
```

## Note

Only works on PDFs with a text layer. Scanned/image PDFs won't be changed —
check the output visually to confirm redactions appeared.
