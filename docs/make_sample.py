#!/usr/bin/env python3
"""
Generate a sample PDF with fake PII for documentation purposes,
then produce before/after PNG screenshots.
"""

import fitz
from pathlib import Path

OUT_DIR = Path(__file__).parent


def make_sample_pdf(path):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    BL   = (0, 0, 0)       # black
    GRAY = (0.4, 0.4, 0.4)
    LGRAY= (0.85, 0.85, 0.85)

    def text(x, y, s, size=11, color=BL, bold=False):
        font = "helv" if not bold else "hebo"
        page.insert_text((x, y), s, fontname=font, fontsize=size, color=color)

    def hline(y, x0=50, x1=545, width=0.5, color=LGRAY):
        page.draw_line((x0, y), (x1, y), color=color, width=width)

    def rect_fill(x0, y0, x1, y1, color=LGRAY):
        page.draw_rect(fitz.Rect(x0, y0, x1, y1), color=None, fill=color)

    # ── Header bar ────────────────────────────────────────────────────────────
    rect_fill(0, 0, 595, 70, (0.18, 0.35, 0.58))
    page.insert_text((50, 38), "UWV", fontname="hebo", fontsize=22,
                     color=(1, 1, 1))
    page.insert_text((50, 56), "Uitvoeringsinstituut Werknemersverzekeringen",
                     fontname="helv", fontsize=9, color=(0.85, 0.9, 1.0))

    page.insert_text((380, 38), "Betalingsspecificatie",
                     fontname="hebo", fontsize=13, color=(1, 1, 1))
    page.insert_text((380, 56), "Periode: februari 2026",
                     fontname="helv", fontsize=9, color=(0.85, 0.9, 1.0))

    # ── Recipient block ───────────────────────────────────────────────────────
    y = 100
    text(50, y,      "Aan",          size=8, color=GRAY)
    text(50, y + 16, "Jan de Vries", size=11, bold=True)
    text(50, y + 31, "Kerkstraat 12")
    text(50, y + 46, "1234 AB Amsterdam")
    text(50, y + 61, "Nederland")

    text(380, y,      "Datum",            size=8, color=GRAY)
    text(380, y + 16, "28 februari 2026")
    text(380, y + 36, "Kenmerk",          size=8, color=GRAY)
    text(380, y + 52, "WW-2026-02-4471823")
    text(380, y + 72, "Pagina",           size=8, color=GRAY)
    text(380, y + 88, "1 van 1")

    hline(180)

    # ── Personal details ──────────────────────────────────────────────────────
    y = 200
    text(50, y, "Uw gegevens", size=11, bold=True)
    hline(y + 6, x0=50, x1=200, color=(0.18, 0.35, 0.58))

    rows = [
        ("Burgerservicenummer (BSN)", "123 456 789"),
        ("Naam",                      "Jan de Vries"),
        ("Adres",                     "Kerkstraat 12, 1234 AB Amsterdam"),
        ("E-mailadres",               "jan.devries@example.com"),
        ("Telefoonnummer",            "06-12 34 56 78"),
        ("IBAN",                      "NL91 ABNA 0417 1643 00"),
    ]

    for i, (label, value) in enumerate(rows):
        ry = y + 22 + i * 22
        if i % 2 == 0:
            rect_fill(50, ry - 13, 545, ry + 5, (0.96, 0.96, 0.96))
        text(55,  ry, label, size=9, color=GRAY)
        text(270, ry, value, size=9)

    hline(y + 22 + len(rows) * 22 + 4)

    # ── Payment breakdown ─────────────────────────────────────────────────────
    y = 370
    text(50, y, "Uitkeringsspecificatie", size=11, bold=True)
    hline(y + 6, x0=50, x1=300, color=(0.18, 0.35, 0.58))

    rect_fill(50, y + 16, 545, y + 32, (0.18, 0.35, 0.58))
    page.insert_text((55,  y + 28), "Omschrijving", fontname="hebo",
                     fontsize=9, color=(1, 1, 1))
    page.insert_text((380, y + 28), "Periode",      fontname="hebo",
                     fontsize=9, color=(1, 1, 1))
    page.insert_text((470, y + 28), "Bedrag",       fontname="hebo",
                     fontsize=9, color=(1, 1, 1))

    spec_rows = [
        ("WW-uitkering",              "01-02 t/m 28-02-2026", "€ 1.456,80"),
        ("Vakantietoeslag",           "01-02 t/m 28-02-2026", "€   116,54"),
        ("Loonheffing (inhouding)",   "",                      "€  -382,10"),
        ("Arbeidskorting (inhouding)","",                      "€   -87,33"),
    ]

    for i, (desc, period, amount) in enumerate(spec_rows):
        ry = y + 48 + i * 22
        if i % 2 == 0:
            rect_fill(50, ry - 13, 545, ry + 5, (0.96, 0.96, 0.96))
        text(55,  ry, desc,   size=9)
        text(380, ry, period, size=9)
        text(470, ry, amount, size=9)

    hline(y + 48 + len(spec_rows) * 22 + 4)

    ty = y + 48 + len(spec_rows) * 22 + 18
    rect_fill(380, ty - 14, 545, ty + 4, (0.18, 0.35, 0.58))
    page.insert_text((385, ty), "Netto te ontvangen",
                     fontname="hebo", fontsize=9, color=(1, 1, 1))
    page.insert_text((470, ty), "€ 1.103,91",
                     fontname="hebo", fontsize=9, color=(1, 1, 1))

    # ── Payment destination ───────────────────────────────────────────────────
    y = ty + 30
    text(50, y, "Uitbetaling op rekeningnummer: ", size=9, color=GRAY)
    text(270, y, "NL91 ABNA 0417 1643 00", size=9)

    # ── Footer ────────────────────────────────────────────────────────────────
    hline(790)
    text(50,  806, "UWV | Postbus 58285 | 1040 HG Amsterdam", size=8, color=GRAY)
    text(380, 806, "uwv.nl  |  0900-9294", size=8, color=GRAY)

    doc.save(str(path), garbage=4, deflate=True)
    doc.close()
    print(f"Created: {path}")


def render_png(pdf_path, png_path, dpi=150):
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    pix.save(str(png_path))
    doc.close()
    print(f"Rendered: {png_path}")


if __name__ == "__main__":
    import subprocess, sys

    sample    = OUT_DIR / "sample.pdf"
    redacted  = OUT_DIR / "sample_redacted.pdf"
    before_png = OUT_DIR / "before.png"
    after_png  = OUT_DIR / "after.png"

    make_sample_pdf(sample)
    render_png(sample, before_png)

    # Run redaction via the CLI
    script = OUT_DIR.parent / "redact.py"
    result = subprocess.run([
        sys.executable, str(script),
        str(sample), str(redacted),
        "--name", "Jan de Vries",
        "--name", "de Vries",
        "--ids", "--iban", "--phones", "--emails", "--postcodes", "--financial",
        "--after-header", "Burgerservicenummer (BSN)",
        "--after-header", "IBAN",
        "--after-header", "E-mailadres",
        "--after-header", "Telefoonnummer",
        "--after-header", "Uitbetaling op rekeningnummer:",
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    render_png(redacted, after_png)
    print("Done. before.png and after.png are ready.")
