# make_sample_boq.py — generates the BoQ fixture PDFs from scripts/boq_data.py.
#
#   python3 scripts/make_sample_boq.py            # fixtures/sample_boq.pdf (Ravi, seeded flaws)
#   python3 scripts/make_sample_boq.py --clean    # fixtures/clean_boq.pdf (negative test)
#   python3 scripts/make_sample_boq.py --all      # both
#
# Seeded flaws in the Ravi variant (edit them in boq_data.py):
#   F1  RCC rate inflated (₹9,800/cum vs ₹8,036 benchmark)          -> RATE_OUTLIER
#   F2  Waterproofing, external plaster, anti-termite absent        -> MISSING_SCOPE
#   F3  "TMT bars" with no grade named                              -> UNDERSPECIFIED
#   F4  Payment schedule: 45% due before slab                       -> FRONT_LOADED
#   Also deliberately silent on GST                                 -> GST_SILENT

import argparse
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Runnable both as `python3 scripts/make_sample_boq.py` and as a module.
try:
    from boq_data import VARIANTS
except ImportError:
    from scripts.boq_data import VARIANTS

styles = getSampleStyleSheet()
small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=10)


def build(variant="ravi"):
    items, payment, meta = VARIANTS[variant]
    out = meta["out"]
    doc = SimpleDocTemplate(out, pagesize=A4,
                            leftMargin=14*mm, rightMargin=14*mm,
                            topMargin=14*mm, bottomMargin=14*mm)
    story = []
    story.append(Paragraph(meta["firm"], styles["Title"]))
    story.append(Paragraph("Bill of Quantities — Proposed Residential Building (G+0)",
                           styles["Heading2"]))
    story.append(Paragraph(
        f"Client: {meta['client']} &nbsp;&nbsp;|&nbsp;&nbsp; Site: {meta['site']} "
        f"&nbsp;&nbsp;|&nbsp;&nbsp; Built-up area: {meta['area']}",
        styles["Normal"]))
    story.append(Spacer(1, 6*mm))

    rows = [["Item", "Description", "Qty", "Unit", "Rate (Rs)", "Amount (Rs)"]]
    total = 0
    for sec, iid, desc, qty, unit, rate in items:
        if sec:
            rows.append([sec, "", "", "", "", ""])
        amt = round(qty * rate)
        total += amt
        rows.append([iid, Paragraph(desc, small), f"{qty:g}", unit,
                     f"{rate:,}", f"{amt:,}"])
    rows.append(["", "TOTAL", "", "", "", f"{total:,}"])

    t = Table(rows, colWidths=[16*mm, 78*mm, 14*mm, 13*mm, 22*mm, 26*mm],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDD8CE")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("Payment Schedule", styles["Heading3"]))
    ps = Table([["Stage", "Payment"]] + list(payment),
               colWidths=[120*mm, 30*mm])
    ps.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDD8CE")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
    ]))
    story.append(ps)
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(meta["terms"], small))
    doc.build(story)
    print(f"Wrote {out}  (BoQ total Rs {total:,})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clean", action="store_true", help="build fixtures/clean_boq.pdf")
    ap.add_argument("--all", action="store_true", help="build both fixtures")
    args = ap.parse_args()
    if args.all:
        build("ravi"); build("clean")
    elif args.clean:
        build("clean")
    else:
        build("ravi")
