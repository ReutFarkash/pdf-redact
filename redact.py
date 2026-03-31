#!/usr/bin/env python3
"""
redact.py — Redact personal information from a PDF.

PDF metadata is always stripped. Everything else is opt-in.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO RUN THIS SCRIPT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Open a terminal, go to the pdf-redact folder, and run:

    .venv/bin/python3 redact.py your-document.pdf [options]

The redacted file is saved automatically in the same folder as:
    your-document_redacted_20240101_120000.pdf

The original is never modified. To choose your own output name,
add it as the second argument:

    .venv/bin/python3 redact.py input.pdf output.pdf [options]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT: REPEATING FLAGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Flags like --name, --text, --after-header, and --region must be
written once per value. You cannot list multiple values after one flag.

    CORRECT:   --name "Jane Smith" --name "J. Smith"
    WRONG:     --name "Jane Smith" "J. Smith"   ← only first name is used

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Redact a name and all common patterns (emails, phone numbers, IDs, etc.):

    .venv/bin/python3 redact.py letter.pdf --name "Jane Smith" --all

Redact multiple variants of a name — use --name once per variant:

    .venv/bin/python3 redact.py letter.pdf \\
        --name "Jane Smith" \\
        --name "J. Smith" \\
        --name "Smith"

Redact the value that appears under a label in a document
(works for both "Label: value" on one line and "Label" / value on separate lines):

    .venv/bin/python3 redact.py document.pdf --after-header "Burgerservicenummer"

Redact values under multiple headers — use --after-header once per header:

    .venv/bin/python3 redact.py document.pdf \\
        --after-header "Burgerservicenummer" \\
        --after-header "IBAN" \\
        --after-header "Betaalkenmerk"

Redact a specific rectangle on the page by coordinates.
x1,y1 is the top-left corner; x2,y2 is the bottom-right corner.
(Open the PDF in a viewer that shows coordinates to find the right values.
In Preview on Mac: Tools > Show Inspector, then hover over the area.
Coordinates start from the top-left of the page.):

    .venv/bin/python3 redact.py document.pdf --region "50,100,300,130"

Redact multiple regions — use --region once per region:

    .venv/bin/python3 redact.py document.pdf \\
        --region "50,100,300,130" \\
        --region "50,200,400,220"

Redact names, addresses, and financial amounts together:

    .venv/bin/python3 redact.py payslip.pdf \\
        --name "Jane Smith" \\
        --text "Kerkstraat 12" \\
        --text "1234 AB Amsterdam" \\
        --financial

Redact an Israeli document:

    .venv/bin/python3 redact.py tofes.pdf \\
        --name "ישראל ישראלי" \\
        --name "ישראלי" \\
        --israeli \\
        --financial

Combine everything — names, headers, a specific region, and pattern categories:

    .venv/bin/python3 redact.py invoice.pdf \\
        --name "Jane Smith" \\
        --after-header "Account number" \\
        --region "50,400,300,420" \\
        --emails \\
        --financial
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import fitz
except ImportError:
    print("Error: pymupdf is not installed. Run: pip3 install pymupdf", file=sys.stderr)
    sys.exit(1)


# ── Pattern library ────────────────────────────────────────────────────────────

def patterns_for(args):
    patterns = []

    if args.ids or args.all:
        # BSN / Israeli Teudat Zehut / any 9-digit ID
        # Matches: 123456789  123.456.789  123 456 789
        patterns.append(re.compile(r"\b\d{3}[.\s]?\d{3}[.\s]?\d{3}\b"))

    if args.iban or args.all:
        # Any IBAN: 2-letter country code + 2 digits + up to 30 alphanumeric chars
        patterns.append(re.compile(
            r"\b[A-Z]{2}\d{2}[\s]?(?:[A-Z0-9]{4}[\s]?){2,7}[A-Z0-9]{1,4}\b"
        ))

    if args.phones or args.all:
        # International (+XX / 00XX) and Dutch/Israeli local formats
        patterns.append(re.compile(
            r"(?<!\w)"
            r"(?:(?:\+\d{1,3}|00\d{1,3})[\s\-]?(?:\(0\)[\s\-]?)?|0)"
            r"(?:\d[\s\-]?){8,11}\d"
            r"\b"
        ))

    if args.israeli or args.all:
        # Israeli mobile: 05X-XXX-XXXX
        patterns.append(re.compile(
            r"(?<!\w)0(?:5[0-9]|[2-489])[\s\-]\d{3}[\s\-]\d{4}\b"
        ))
        # Israeli 9-digit ID (standalone)
        patterns.append(re.compile(r"\b\d{9}\b"))

    if args.emails or args.all:
        patterns.append(re.compile(
            r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
        ))

    if args.postcodes or args.all:
        # Dutch: 1234 AB or 1234AB
        patterns.append(re.compile(r"\b\d{4}\s?[A-Z]{2}\b"))

    if args.financial or args.all:
        # Currency symbol before amount: €1,234.56 / € 1.234,56 / $500 / ₪1234
        patterns.append(re.compile(r"[€$£₪]\s*\d[\d\s,.']*\d"))
        # Currency symbol after amount: 1,234.56 € / 500$
        patterns.append(re.compile(r"\d[\d\s,.']*\d\s*[€$£₪]"))
        # European decimal format: 1.234,56 or 1 234,56
        patterns.append(re.compile(r"\b\d{1,3}(?:[.\s]\d{3})+,\d{2}\b"))

    # Literal strings: names, addresses, free text
    # Sorted longest-first so "Jane Smith" is matched before "Smith"
    literals = sorted(
        [s for s in (args.name or []) + (args.text or []) if s.strip()],
        key=len, reverse=True,
    )
    for s in literals:
        patterns.append(re.compile(re.escape(s.strip()), re.IGNORECASE))

    return patterns


# ── Region redaction ───────────────────────────────────────────────────────────

def redact_regions(page, regions):
    """Redact explicit coordinate rectangles: 'x1,y1,x2,y2'."""
    for region in (regions or []):
        try:
            coords = [float(x.strip()) for x in region.split(",")]
            if len(coords) != 4:
                raise ValueError
            page.add_redact_annot(fitz.Rect(coords), fill=(0, 0, 0))
        except ValueError:
            print(f"Warning: invalid --region value {region!r} — expected x1,y1,x2,y2",
                  file=sys.stderr)
    if regions:
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)


# ── After-header redaction ─────────────────────────────────────────────────────

def redact_after_headers(page, headers):
    """
    For each header string, find it on the page and redact:
    - text to the right on the same line (for "Label: value" layouts)
    - the single line immediately below (for stacked "Label / value" layouts)

    Only the nearest line below is redacted, not multiple lines.
    """
    for header in headers:
        instances = page.search_for(header)
        for h_rect in instances:

            # Right of header, same line
            right_area = fitz.Rect(h_rect.x1, h_rect.y0, page.rect.x1, h_rect.y1)
            for word in page.get_text("words", clip=right_area):
                page.add_redact_annot(fitz.Rect(word[:4]), fill=(0, 0, 0))

            # Exactly the next line below — find the nearest y0 and redact only that line
            below_area = fitz.Rect(0, h_rect.y1, page.rect.x1, page.rect.y1)
            words_below = page.get_text("words", clip=below_area)
            if words_below:
                nearest_y = min(w[1] for w in words_below)
                tolerance = h_rect.height * 0.6
                for w in words_below:
                    if abs(w[1] - nearest_y) <= tolerance:
                        page.add_redact_annot(fitz.Rect(w[:4]), fill=(0, 0, 0))

    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)


# ── Pattern-based redaction ────────────────────────────────────────────────────

def _char_map(page):
    """Returns (full_text, char_bboxes) — char_bboxes[i] is fitz.Rect or None."""
    full_text = ""
    char_bboxes = []
    blocks = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                for ch in span["chars"]:
                    full_text += ch["c"]
                    char_bboxes.append(fitz.Rect(ch["bbox"]))
            full_text += " "
            char_bboxes.append(None)
    return full_text, char_bboxes


def redact_patterns(page, patterns):
    if not patterns:
        return
    full_text, char_bboxes = _char_map(page)
    for pattern in patterns:
        for match in pattern.finditer(full_text):
            start, end = match.start(), match.end()
            rects = [char_bboxes[i] for i in range(start, end) if char_bboxes[i] is not None]
            if not rects:
                continue
            bbox = rects[0]
            for r in rects[1:]:
                bbox |= r
            page.add_redact_annot(bbox, fill=(0, 0, 0))
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)


# ── Table redaction (experimental) ────────────────────────────────────────────

def redact_table_cells(page, table_rows, table_cols, table_cells, table_col_headers):
    """
    Redact specific cells in auto-detected tables. All indexes are 1-based.
    Note: table detection requires PDFs with explicit drawn grid lines and may
    produce unexpected results on documents that use spacing/positioning for layout.
    """
    tabs = page.find_tables()
    if not tabs.tables:
        return

    for tab in tabs.tables:
        n_rows = tab.row_count
        n_cols = tab.col_count

        # Build a spatial grid sorted by (y0, x0) — tab.cells ordering is not guaranteed
        valid = [fitz.Rect(c) for c in tab.cells if c is not None]
        valid.sort(key=lambda r: (round(r.y0), round(r.x0)))
        grid = [[None] * n_cols for _ in range(n_rows)]
        for idx, rect in enumerate(valid):
            r, c = divmod(idx, n_cols)
            if r < n_rows:
                grid[r][c] = rect

        def get_rect(r, c):
            if 0 <= r < n_rows and 0 <= c < n_cols:
                return grid[r][c]
            return None

        to_redact = set()

        for row_n in (table_rows or []):
            for c in range(n_cols):
                to_redact.add((row_n - 1, c))

        for col_n in (table_cols or []):
            for r in range(n_rows):
                to_redact.add((r, col_n - 1))

        for spec in (table_cells or []):
            try:
                row_s, col_s = spec.split(",")
                to_redact.add((int(row_s) - 1, int(col_s) - 1))
            except ValueError:
                print(f"Warning: invalid --table-cell value {spec!r}, expected R,C",
                      file=sys.stderr)

        for header_text in (table_col_headers or []):
            for c, name in enumerate(tab.header.names):
                if name and header_text.lower() in name.lower():
                    for r in range(1, n_rows):
                        to_redact.add((r, c))

        for (r, c) in to_redact:
            rect = get_rect(r, c)
            if rect:
                page.add_redact_annot(rect, fill=(0, 0, 0))

    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)


# ── Main redact ────────────────────────────────────────────────────────────────

def redact(input_path, output_path, patterns, regions, after_headers,
           table_rows, table_cols, table_cells, table_col_headers):
    doc = fitz.open(input_path)
    for page in doc:
        # Order matters — each step physically removes text before the next runs.
        #
        # 1. after_headers first: searches for header text by content.
        #    Must run before patterns (which might redact a word that is also a header)
        #    and before regions (which might erase a header label by coordinates).
        #
        # 2. table_cells next: uses structural table detection.
        #    Must run before patterns modify the text layer.
        #
        # 3. patterns next: all regex/literal patterns are applied to the same
        #    original char map in a single pass, so no pattern can eat a substring
        #    before a longer overlapping pattern gets a chance to match.
        #    Literals are pre-sorted longest-first as an extra safeguard.
        #
        # 4. regions last: purely coordinate-based, no text search involved.
        #    Running last ensures it never accidentally removes a header or label
        #    that an earlier step was relying on.
        if after_headers:
            redact_after_headers(page, after_headers)
        if table_rows or table_cols or table_cells or table_col_headers:
            redact_table_cells(page, table_rows, table_cols, table_cells, table_col_headers)
        redact_patterns(page, patterns)
        if regions:
            redact_regions(page, regions)
    doc.set_metadata({})
    doc.del_xml_metadata()
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()


# ── CLI ────────────────────────────────────────────────────────────────────────

def default_output(input_path):
    p = Path(input_path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(p.parent / f"{p.stem}_redacted_{stamp}.pdf")


def main():
    parser = argparse.ArgumentParser(
        description="Redact personal information from a PDF. Metadata is always stripped.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.strip(),
    )

    parser.add_argument("input", help="PDF file to redact")
    parser.add_argument("output", nargs="?",
                        help="Output file path (default: input_redacted_TIMESTAMP.pdf in same folder)")

    strings = parser.add_argument_group(
        "what to redact — strings and locations",
        "Use each flag once per value. See EXAMPLES below for details."
    )
    strings.add_argument("--name", metavar="NAME", action="append",
                         help='Redact a name wherever it appears. '
                              'Use once per variant: --name "Jane Smith" --name "J. Smith"')
    strings.add_argument("--text", metavar="TEXT", action="append",
                         help='Redact any exact string: address, company name, reference number, etc. '
                              'Use once per value: --text "Kerkstraat 12" --text "1234 AB"')
    strings.add_argument("--after-header", metavar="HEADER", action="append", dest="after_header",
                         help='Redact the value that appears after or below a label. '
                              'e.g. --after-header "Burgerservicenummer" '
                              'Use once per label.')
    strings.add_argument("--region", metavar="X1,Y1,X2,Y2", action="append",
                         help='Redact a specific rectangular area by page coordinates. '
                              'X1,Y1 = top-left corner; X2,Y2 = bottom-right corner. '
                              'Use once per region: --region "50,100,300,130"')

    cats = parser.add_argument_group(
        "automatic pattern categories",
        "Switch these on to redact common types of information automatically. "
        "Use --all to enable everything at once."
    )
    cats.add_argument("--emails",    action="store_true", help="Email addresses")
    cats.add_argument("--phones",    action="store_true", help="Phone numbers (Dutch/international)")
    cats.add_argument("--ids",       action="store_true",
                      help="9-digit ID numbers (Dutch BSN, Israeli Teudat Zehut, etc.)")
    cats.add_argument("--iban",      action="store_true", help="IBAN bank account numbers (any country)")
    cats.add_argument("--postcodes", action="store_true", help="Dutch postal codes (e.g. 1234 AB)")
    cats.add_argument("--israeli",   action="store_true",
                      help="Israeli phone format (05X-XXX-XXXX) and 9-digit ID numbers")
    cats.add_argument("--financial", action="store_true",
                      help="Currency amounts (anything with €, $, £, or ₪)")
    cats.add_argument("--all",       action="store_true", help="Enable all categories above")

    table = parser.add_argument_group(
        "table redaction (advanced, experimental)",
        "Redact specific rows, columns, or cells in tables. Only works reliably on PDFs "
        "with explicit drawn grid lines. All indexes are 1-based (row 1 = first row)."
    )
    table.add_argument("--table-col-header", metavar="TEXT", action="append",
                       dest="table_col_headers",
                       help="Redact all data cells in the column with this header text "
                            "(header row itself is kept)")
    table.add_argument("--table-col",  metavar="N", type=int, action="append",
                       dest="table_cols",  help="Redact entire column N")
    table.add_argument("--table-row",  metavar="N", type=int, action="append",
                       dest="table_rows",  help="Redact entire row N")
    table.add_argument("--table-cell", metavar="R,C", action="append",
                       dest="table_cells",
                       help='Redact one specific cell, e.g. --table-cell 2,3 '
                            '(row 2, column 3)')

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        parser.error(f"File not found: {args.input}")

    table_args = [args.table_col_headers, args.table_cols, args.table_rows, args.table_cells]
    has_something = args.all or args.after_header or args.region or any(table_args) or any([
        args.emails, args.phones, args.ids, args.iban, args.postcodes,
        args.israeli, args.financial, args.name, args.text,
    ])
    if not has_something:
        parser.error(
            "Nothing to redact. Add at least one option, for example:\n"
            '  --name "Your Name" --all\n'
            '  --after-header "Burgerservicenummer"\n'
            '  --financial\n'
            "Run with --help to see all options."
        )

    output       = args.output or default_output(args.input)
    patterns     = patterns_for(args)
    after_headers = args.after_header or []
    regions       = args.region or []

    print(f"Input:  {args.input}")
    print(f"Output: {output}")
    active = []
    if patterns:      active.append(f"{len(patterns)} pattern(s)")
    if after_headers: active.append(f"after-header: {after_headers}")
    if regions:       active.append(f"{len(regions)} region(s)")
    if any(table_args):
        active.append(f"table rows={args.table_rows} cols={args.table_cols} "
                      f"cells={args.table_cells} headers={args.table_col_headers}")
    print(f"Active: {', '.join(active)}")

    redact(args.input, output, patterns, regions, after_headers,
           args.table_rows, args.table_cols, args.table_cells, args.table_col_headers)
    print("Done.")


if __name__ == "__main__":
    main()
