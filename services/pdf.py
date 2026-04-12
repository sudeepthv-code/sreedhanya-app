"""
A+BC Solutions — Sreedhanya AI Customisation App
PDF Generator: Quotations & GST Tax Invoices
Platypus-based layout matching KNX app quality.
A4 = 595.28 × 841.89 pt  |  margins = 18 mm = 51 pt each side
Usable width ≈ 493 pt
"""

from __future__ import annotations
import os
import io
import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image as RLImage
)

# ─── Paths ────────────────────────────────────────────────────────────────────
_HERE    = os.path.dirname(__file__)
STATIC   = os.path.join(_HERE, '..', 'static')
LOGO     = os.path.join(STATIC, 'abc_logo.png')

# On Railway: set PDF_STORAGE_DIR=/data/pdfs (persistent volume)
# Locally:    defaults to static/pdfs/
PDF_DIR  = os.environ.get('PDF_STORAGE_DIR', os.path.join(STATIC, 'pdfs'))

os.makedirs(PDF_DIR, exist_ok=True)

# ─── Company details ──────────────────────────────────────────────────────────
COMPANY = {
    "name":         "A+BC Solutions",
    "address1":     "Room No: 19/124-5, Atlas, Poothole",
    "address2":     "Thrissur, Kerala — 680003",
    "phone":        "8098019236",
    "email":        "sales@aplusbcsolutions.com",
    "website":      "www.aplusbcsolutions.com",
    "gst":          "32AVMPV9876C1ZY",
    "state":        "Kerala",
    "state_code":   "32",
    "validity_days": 30,
    "payment_terms": "50% Advance, 30% On Delivery, 20% On Commissioning",
    "warranty":     "1 year on workmanship",
    "bank_name":    "HDFC Bank",
    "bank_acc_name": "A PLUS BC SOLUTIONS",
    "bank_acc_type": "Current Account",
    "bank_account": "50200032087901",
    "bank_ifsc":    "HDFC0009078",
}

# ─── Dimensions ───────────────────────────────────────────────────────────────
PW, PH  = A4
MARGIN  = 18 * mm
USABLE  = PW - 2 * MARGIN      # ≈ 493 pt

# ─── Colours ──────────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#1F3864")
BLUE   = colors.HexColor("#2E75B6")
LBLUE  = colors.HexColor("#EBF0F8")
WHITE  = colors.white
BLACK  = colors.black
GREY   = colors.HexColor("#555555")
LGREY  = colors.HexColor("#F5F5F5")
DGREY  = colors.HexColor("#CCCCCC")

# ─── Column widths ────────────────────────────────────────────────────────────
# Quotation items: # | Description | Room | Qty | Unit | Rate | Amount
CW_QUOTE = [20, 180, 75, 30, 40, 68, 80]   # sum = 493

# Invoice items (intra-state): # | Description | HSN/SAC | Qty | Unit | Rate | Taxable | CGST | SGST | Total
CW_INV = [16, 115, 45, 26, 30, 56, 58, 48, 48, 51]   # sum = 493

# ─── Helpers ──────────────────────────────────────────────────────────────────

def Rs(v: float) -> str:
    """Format as Indian rupees with 2 decimal places."""
    return f"Rs. {v:,.2f}"

def _hr(color=DGREY, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness, color=color,
                      spaceAfter=4, spaceBefore=4)


# ─── Shared styles ────────────────────────────────────────────────────────────

def _make_styles() -> dict:
    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        # Company / header
        "co_name":   S("co_name",   fontName="Helvetica-Bold", fontSize=14, textColor=NAVY),
        "co_addr":   S("co_addr",   fontName="Helvetica",      fontSize=8,  textColor=GREY,  leading=12),
        "co_gstin":  S("co_gstin",  fontName="Helvetica-Bold", fontSize=8,  textColor=NAVY),
        # Document type title
        "doc_head":  S("doc_head",  fontName="Helvetica-Bold", fontSize=22, textColor=NAVY,  alignment=TA_RIGHT),
        "doc_sub":   S("doc_sub",   fontName="Helvetica",      fontSize=8,  textColor=GREY,  alignment=TA_RIGHT),
        "doc_val":   S("doc_val",   fontName="Helvetica-Bold", fontSize=9,  textColor=NAVY,  alignment=TA_RIGHT),
        # Client card labels
        "cl_label":  S("cl_label",  fontName="Helvetica-Bold", fontSize=8,  textColor=GREY),
        "cl_val":    S("cl_val",    fontName="Helvetica",      fontSize=9,  textColor=BLACK, leading=13),
        # Table content
        "tbl_hdr":   S("tbl_hdr",  fontName="Helvetica-Bold", fontSize=8,  textColor=WHITE),
        "tbl_hdr_r": S("tbl_hdr_r",fontName="Helvetica-Bold", fontSize=8,  textColor=WHITE, alignment=TA_RIGHT),
        "tbl_hdr_c": S("tbl_hdr_c",fontName="Helvetica-Bold", fontSize=8,  textColor=WHITE, alignment=TA_CENTER),
        "body":      S("body",      fontName="Helvetica",      fontSize=8.5,textColor=BLACK, leading=11),
        "body_r":    S("body_r",    fontName="Helvetica",      fontSize=8.5,textColor=BLACK, alignment=TA_RIGHT, leading=11),
        "body_c":    S("body_c",    fontName="Helvetica",      fontSize=8.5,textColor=BLACK, alignment=TA_CENTER, leading=11),
        "small":     S("small",     fontName="Helvetica",      fontSize=7.5,textColor=GREY,  leading=10),
        "small_r":   S("small_r",   fontName="Helvetica",      fontSize=7.5,textColor=GREY,  alignment=TA_RIGHT, leading=10),
        "small_c":   S("small_c",   fontName="Helvetica",      fontSize=7.5,textColor=GREY,  alignment=TA_CENTER, leading=10),
        "bold_r":    S("bold_r",    fontName="Helvetica-Bold", fontSize=9,  textColor=BLACK, alignment=TA_RIGHT),
        "bold_l":    S("bold_l",    fontName="Helvetica-Bold", fontSize=9,  textColor=BLACK),
        "sec_hdr":   S("sec_hdr",   fontName="Helvetica-Bold", fontSize=8.5,textColor=WHITE),
        # Totals
        "total_l":   S("total_l",   fontName="Helvetica-Bold", fontSize=11, textColor=NAVY),
        "total_r":   S("total_r",   fontName="Helvetica-Bold", fontSize=11, textColor=NAVY, alignment=TA_RIGHT),
        # Terms / footer
        "terms_h":   S("terms_h",   fontName="Helvetica-Bold", fontSize=8.5,textColor=NAVY),
        "terms_b":   S("terms_b",   fontName="Helvetica",      fontSize=7.5,textColor=GREY, leading=11),
        "words":     S("words",      fontName="Helvetica-Oblique", fontSize=8.5, textColor=NAVY),
        "footer":    S("footer",    fontName="Helvetica",      fontSize=7,  textColor=GREY, alignment=TA_CENTER),
    }


# ─── Header: logo left / doc type right ───────────────────────────────────────

def _build_header(doc_title: str, meta_rows: list[tuple[str, str]], st: dict) -> Table:
    """
    doc_title: e.g. "QUOTATION" or "TAX INVOICE"
    meta_rows: list of (label, value) pairs for right column
    """
    lw = USABLE * 0.58
    rw = USABLE * 0.42

    # Left column: logo + company details
    left_items = []
    if os.path.exists(LOGO):
        try:
            logo = RLImage(LOGO, width=44*mm, height=44*mm, kind="proportional")
            left_items.append([logo])
            left_items.append([Spacer(1, 4)])
        except Exception:
            pass

    for elem in [
        Paragraph(COMPANY["address1"],                                  st["co_addr"]),
        Paragraph(COMPANY["address2"],                                  st["co_addr"]),
        Paragraph(f"Ph: {COMPANY['phone']}  |  {COMPANY['email']}",    st["co_addr"]),
        Paragraph(COMPANY["website"],                                   st["co_addr"]),
        Paragraph(f"GST: {COMPANY['gst']}",                            st["co_addr"]),
    ]:
        left_items.append([elem])

    left_inner = Table(left_items, colWidths=[lw])
    left_inner.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 1),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
    ]))

    # Right column: document type + metadata
    right_items = [[Paragraph(doc_title, st["doc_head"])], [Spacer(1, 14)]]
    for label, value in meta_rows:
        right_items.append([_rv_row(label, value, rw, st)])

    right_inner = Table(right_items, colWidths=[rw])
    right_inner.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 1),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
    ]))

    outer = Table([[left_inner, right_inner]], colWidths=[lw, rw])
    outer.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
    ]))
    return outer


def _rv_row(label: str, val: str, width: float, st: dict) -> Table:
    """Right-aligned label: value row used in header."""
    lw = 28 * mm
    vw = width - lw
    lp = Paragraph(label, ParagraphStyle("rvl", fontName="Helvetica",
                   fontSize=8, textColor=GREY, alignment=TA_RIGHT))
    vp = Paragraph(val,   ParagraphStyle("rvv", fontName="Helvetica-Bold",
                   fontSize=8, textColor=NAVY, alignment=TA_RIGHT))
    t  = Table([[lp, vp]], colWidths=[lw, vw])
    t.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
    ]))
    return t


# ─── Client / apartment card ──────────────────────────────────────────────────

def _client_card(rows_data: list[tuple[str, str]], st: dict) -> Table:
    """Alternating-row table for client/apartment details."""
    rows = [[Paragraph(k, st["cl_label"]), Paragraph(v or "—", st["cl_val"])]
            for k, v in rows_data if v and str(v).strip()]
    t = Table(rows, colWidths=[30*mm, USABLE - 30*mm])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0),(-1,-1), [LGREY, WHITE]),
        ("TOPPADDING",     (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 4),
        ("LEFTPADDING",    (0,0),(-1,-1), 8),
        ("RIGHTPADDING",   (0,0),(-1,-1), 8),
        ("VALIGN",         (0,0),(-1,-1), "TOP"),
        ("BOX",            (0,0),(-1,-1), 0.5, DGREY),
    ]))
    return t


# ─── Bank details block ───────────────────────────────────────────────────────

def _bank_block(st: dict) -> Table:
    rows = [
        ("Account Name",  COMPANY["bank_acc_name"]),
        ("Bank",          f"{COMPANY['bank_name']}  ({COMPANY['bank_acc_type']})"),
        ("Account No.",   COMPANY["bank_account"]),
        ("IFSC Code",     COMPANY["bank_ifsc"]),
    ]
    data = [[Paragraph(r[0], st["cl_label"]), Paragraph(r[1], st["body"])]
            for r in rows]
    t = Table(data, colWidths=[30*mm, USABLE - 30*mm])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0),(-1,-1), [LGREY, WHITE]),
        ("TOPPADDING",     (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 3),
        ("LEFTPADDING",    (0,0),(-1,-1), 8),
        ("RIGHTPADDING",   (0,0),(-1,-1), 8),
        ("BOX",            (0,0),(-1,-1), 0.5, DGREY),
        ("INNERGRID",      (0,0),(-1,-1), 0.25, DGREY),
    ]))
    return t


# ─── Signature block ──────────────────────────────────────────────────────────

def _signature(st: dict) -> Table:
    half = (USABLE - 10*mm) / 2
    t = Table([
        [Paragraph(f"For {COMPANY['name']}", st["cl_label"]),
         Paragraph("Client / Receiver Acceptance", st["cl_label"])],
        [Spacer(1, 18*mm), Spacer(1, 18*mm)],
        [Paragraph("Authorised Signatory", st["small"]),
         Paragraph("Signature & Stamp", st["small"])],
    ], colWidths=[half, half])
    t.setStyle(TableStyle([
        ("LINEBELOW",     (0,1),(0,1), 0.5, GREY),
        ("LINEBELOW",     (1,1),(1,1), 0.5, GREY),
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
    ]))
    return t


# ─── Footer callback ──────────────────────────────────────────────────────────

def _footer_fn(st: dict):
    def fn(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GREY)
        canvas.drawCentredString(
            PW / 2, 12 * mm,
            f"{COMPANY['name']}  ·  GSTIN: {COMPANY['gst']}  ·  "
            f"{COMPANY['phone']}  ·  {COMPANY['email']}  ·  Page {doc.page}"
        )
        canvas.restoreState()
    return fn


# ═══════════════════════════════════════════════════════════════════════════════
#  QUOTATION PDF
# ═══════════════════════════════════════════════════════════════════════════════

def _quote_items_table(items_list: list[dict], st: dict) -> tuple[list, float]:
    """
    Build the line-items table grouped by room.
    Returns (flowables, net_total_excl_gst).
    """
    # Group items by room
    from collections import defaultdict
    rooms: dict[str, list[dict]] = defaultdict(list)
    for item in items_list:
        room = item.get('room', '').strip() or 'General'
        rooms[room].append(item)

    # Table header row
    hdrs = ["#", "Description", "Room", "Qty", "Unit", "Rate (Rs.)", "Amount (Rs.)"]
    hdr_styl = (
        [st["tbl_hdr"]] * 5 +
        [st["tbl_hdr_r"], st["tbl_hdr_r"]]
    )
    header_row = [Paragraph(h, s) for h, s in zip(hdrs, hdr_styl)]

    rows      = [header_row]
    sno       = 1
    room_rows = []      # row indices of room header rows
    grand_net = 0.0

    for room_name, room_items in rooms.items():
        room_rows.append(len(rows))
        # Room section header spanning all columns
        rows.append([
            Paragraph("", st["small"]),
            Paragraph(room_name.upper(), st["sec_hdr"]),
            *[Paragraph("", st["small"]) for _ in range(5)],
        ])

        room_total = 0.0
        for item in room_items:
            name        = item.get('item_name', '')
            description = item.get('description', '')
            room_cell   = item.get('room', '')
            qty         = float(item.get('quantity', 1))
            unit        = item.get('unit', 'per unit')
            unit_price  = float(item.get('unit_price', 0))
            line_total  = float(item.get('line_total', qty * unit_price))

            # Combine name + description
            display_name = name
            if description and description != name:
                display_name = f"{name}\n{description}"

            rows.append([
                Paragraph(str(sno), st["small_r"]),
                Paragraph(display_name, st["body"]),
                Paragraph(room_cell, st["body_c"]),
                Paragraph(str(int(qty)) if qty == int(qty) else f"{qty:.2f}", st["body_c"]),
                Paragraph(unit, st["small_c"]),
                Paragraph(Rs(unit_price), st["body_r"]),
                Paragraph(Rs(line_total), st["body_r"]),
            ])
            sno        += 1
            room_total += line_total
        grand_net += room_total

    # Grand row totals bar
    rows.append([
        Paragraph("", st["body"]),
        Paragraph("", st["body"]),
        Paragraph("", st["body"]),
        Paragraph("", st["body"]),
        Paragraph("", st["body"]),
        Paragraph("Net Total (excl. GST)", st["bold_r"]),
        Paragraph(Rs(grand_net), st["bold_r"]),
    ])

    tbl = Table(rows, colWidths=CW_QUOTE, repeatRows=1)
    ts  = [
        # Header row
        ("BACKGROUND",    (0,0),  (-1,0),   NAVY),
        ("TOPPADDING",    (0,0),  (-1,0),   5),
        ("BOTTOMPADDING", (0,0),  (-1,0),   5),
        # Data rows alternating
        ("ROWBACKGROUNDS",(0,1),  (-1,-2),  [WHITE, LGREY]),
        ("TOPPADDING",    (0,1),  (-1,-1),  3),
        ("BOTTOMPADDING", (0,1),  (-1,-1),  3),
        ("LEFTPADDING",   (0,0),  (-1,-1),  4),
        ("RIGHTPADDING",  (0,0),  (-1,-1),  4),
        # Total row
        ("BACKGROUND",    (0,-1), (-1,-1),  LBLUE),
        ("LINEABOVE",     (0,-1), (-1,-1),  0.75, NAVY),
        # Borders
        ("VALIGN",        (0,0),  (-1,-1),  "MIDDLE"),
        ("BOX",           (0,0),  (-1,-1),  0.5,  NAVY),
        ("LINEBELOW",     (0,0),  (-1,0),   0.75, BLUE),
        ("INNERGRID",     (0,1),  (-1,-2),  0.25, DGREY),
    ]
    # Room section header styling
    for ri in room_rows:
        ts += [
            ("BACKGROUND",    (0,ri), (-1,ri), BLUE),
            ("SPAN",          (1,ri), (-1,ri)),
            ("TOPPADDING",    (0,ri), (-1,ri), 5),
            ("BOTTOMPADDING", (0,ri), (-1,ri), 5),
        ]
    tbl.setStyle(TableStyle(ts))
    return [tbl], grand_net


def _quote_gst_block(net_total: float, gst_rate: float, st: dict) -> Table:
    """Three-row totals table: Net Total | GST | Grand Total."""
    cgst_rate = sgst_rate = gst_rate / 2
    cgst_amt  = round(net_total * cgst_rate / 100, 2)
    sgst_amt  = round(net_total * sgst_rate / 100, 2)
    grand     = net_total + cgst_amt + sgst_amt

    label_w = USABLE - 100
    val_w   = 100

    def _row(lbl, val, bold=False, bg=None):
        lp = Paragraph(lbl, ParagraphStyle("ql", fontName="Helvetica-Bold" if bold else "Helvetica",
                        fontSize=10 if bold else 9, textColor=NAVY if bold else BLACK, alignment=TA_RIGHT))
        vp = Paragraph(val, ParagraphStyle("qv", fontName="Helvetica-Bold" if bold else "Helvetica",
                        fontSize=10 if bold else 9, textColor=NAVY if bold else BLACK, alignment=TA_RIGHT))
        return [lp, vp], bg

    rows_data = [
        _row("Net Total (excl. GST):",             Rs(net_total)),
        _row(f"CGST @ {cgst_rate:.0f}%:",          Rs(cgst_amt)),
        _row(f"SGST @ {sgst_rate:.0f}%:",          Rs(sgst_amt)),
        _row("Grand Total (incl. GST):",            Rs(grand), bold=True, bg=LBLUE),
    ]

    table_rows = [rd[0] for rd in rows_data]
    t = Table(table_rows, colWidths=[label_w, val_w])
    ts = [
        ("ALIGN",        (0,0),(-1,-1), "RIGHT"),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("BOX",          (0,0),(-1,-1), 0.5, NAVY),
        ("LINEABOVE",    (0,-1),(-1,-1), 0.75, NAVY),
    ]
    for i, (_, bg) in enumerate(rows_data):
        if bg:
            ts.append(("BACKGROUND", (0,i),(-1,i), bg))
    t.setStyle(TableStyle(ts))
    return t


def _payment_schedule_table(milestones_list: list[dict], grand_total_incl_gst: float, st: dict) -> Table:
    """
    Payment schedule block showing milestone stage, %, and amount (GST-inclusive).
    """
    stage_labels = {
        'advance':          '50% — Advance',
        'on_delivery':      '30% — On Delivery',
        'on_commissioning': '20% — On Commissioning',
    }

    rows = [
        [
            Paragraph("#", st["tbl_hdr_c"]),
            Paragraph("Payment Stage", st["tbl_hdr"]),
            Paragraph("%", st["tbl_hdr_c"]),
            Paragraph("Amount (Rs.)", st["tbl_hdr_r"]),
        ]
    ]

    for idx, m in enumerate(milestones_list, 1):
        stage      = m.get('stage', '')
        pct        = float(m.get('percentage', 0))
        # Recalculate amount on GST-inclusive grand total
        amount_gst = round(grand_total_incl_gst * pct / 100, 2)
        label      = stage_labels.get(stage, stage.replace('_', ' ').title())
        rows.append([
            Paragraph(str(idx), st["body_c"]),
            Paragraph(label, st["body"]),
            Paragraph(f"{pct:.0f}%", st["body_c"]),
            Paragraph(Rs(amount_gst), st["body_r"]),
        ])

    col_w = [20, USABLE - 20 - 50 - 90, 50, 90]
    t = Table(rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  NAVY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LGREY]),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BOX",           (0,0),(-1,-1), 0.5, NAVY),
        ("LINEBELOW",     (0,0),(-1,0),  0.75, BLUE),
        ("INNERGRID",     (0,1),(-1,-1), 0.25, DGREY),
    ]))
    return t


def generate_quote_pdf(quote_dict: dict, items_list: list, milestones_list: list) -> str:
    """
    Generate a professional quotation PDF.

    Args:
        quote_dict: Quote fields including id, version, apartment_number, bedroom_type,
                    owner_name, total_amount, notes
        items_list: List of quote items (item_name, room, description, unit, quantity,
                    unit_price, line_total)
        milestones_list: Payment milestones (stage, percentage, amount)

    Returns:
        filepath: Full path to generated PDF
    """
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    filename  = f"quote_{quote_dict['id']}_v{quote_dict['version']}_{timestamp}.pdf"
    filepath  = os.path.join(PDF_DIR, filename)

    st  = _make_styles()
    buf = io.BytesIO()

    today      = datetime.date.today()
    date_str   = today.strftime("%d %b %Y")
    valid_str  = (today + datetime.timedelta(days=COMPANY["validity_days"])).strftime("%d %b %Y")
    ref        = f"ABC/Q{quote_dict['id']}-V{quote_dict['version']}/{today.strftime('%Y%m%d')}"
    apt_label  = f"{quote_dict.get('apartment_number', '')}  ({quote_dict.get('bedroom_type', '')})"

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN + 10*mm,
        title=f"Quotation — Apt {quote_dict.get('apartment_number', '')} — {COMPANY['name']}",
        author=COMPANY["name"],
    )

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(_build_header("QUOTATION", [
        ("Ref No",     ref),
        ("Date",       date_str),
        ("Valid till", valid_str),
    ], st))
    story.append(Spacer(1, 4*mm))
    story.append(_hr(NAVY, 1.5))
    story.append(Spacer(1, 4*mm))

    # ── Client card ───────────────────────────────────────────────────────────
    story.append(_client_card([
        ("Bill To",   quote_dict.get('owner_name', '')),
        ("Apartment", apt_label),
        ("Project",   "Sreedhanya AI Residential, Thrissur"),
    ], st))
    story.append(Spacer(1, 6*mm))

    # ── Items table ───────────────────────────────────────────────────────────
    elems, net_total = _quote_items_table(items_list, st)
    story.extend(elems)
    story.append(Spacer(1, 4*mm))

    # ── GST totals ────────────────────────────────────────────────────────────
    gst_rate             = 18.0   # CGST 9% + SGST 9%
    cgst_amt             = round(net_total * 9.0 / 100, 2)
    sgst_amt             = round(net_total * 9.0 / 100, 2)
    grand_total_incl_gst = net_total + cgst_amt + sgst_amt

    story.append(_quote_gst_block(net_total, gst_rate, st))
    story.append(Spacer(1, 6*mm))

    # ── Note on GST ───────────────────────────────────────────────────────────
    story.append(Paragraph(
        "Note: All amounts above are in Indian Rupees. GST @ 18% (CGST 9% + SGST 9%) applies "
        "on the net total as an intra-state Kerala supply. Cable pulling by electrical contractor; "
        "A+BC Solutions supervises.",
        st["terms_b"]
    ))
    story.append(Spacer(1, 6*mm))

    # ── Payment schedule ──────────────────────────────────────────────────────
    story.append(_hr())
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Payment Schedule", st["terms_h"]))
    story.append(Spacer(1, 3*mm))
    story.append(_payment_schedule_table(milestones_list, grand_total_incl_gst, st))
    story.append(Spacer(1, 6*mm))

    # ── Terms & Conditions ────────────────────────────────────────────────────
    story.append(_hr())
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Terms & Conditions", st["terms_h"]))
    story.append(Spacer(1, 3*mm))
    notes = quote_dict.get('notes', '').strip()
    if notes:
        story.append(Paragraph(f"Project Notes: {notes}", st["terms_b"]))
        story.append(Spacer(1, 3))
    for line in [
        "1.  Prices are inclusive of materials and exclude GST unless stated otherwise.",
        "2.  Installation includes complete wiring, programming and site commissioning.",
        f"3.  This quotation is valid for {COMPANY['validity_days']} days from the date of issue.",
        f"4.  Payment terms: {COMPANY['payment_terms']}.",
        f"5.  Warranty: {COMPANY['warranty']}.",
        "6.  Subject to Thrissur jurisdiction.",
    ]:
        story.append(Paragraph(line, st["terms_b"]))
    story.append(Spacer(1, 6*mm))

    # ── Bank details ──────────────────────────────────────────────────────────
    story.append(_hr())
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Bank Details for Payment", st["terms_h"]))
    story.append(Spacer(1, 3*mm))
    story.append(_bank_block(st))
    story.append(Spacer(1, 8*mm))

    # ── Signature ─────────────────────────────────────────────────────────────
    story.append(_hr())
    story.append(Spacer(1, 4*mm))
    story.append(_signature(st))

    doc.build(story, onFirstPage=_footer_fn(st), onLaterPages=_footer_fn(st))

    # Write bytes to file
    with open(filepath, 'wb') as f:
        f.write(buf.getvalue())

    return filepath


# ═══════════════════════════════════════════════════════════════════════════════
#  INVOICE PDF (GST Tax Invoice)
# ═══════════════════════════════════════════════════════════════════════════════

def _amount_in_words(amount: float) -> str:
    """Convert a number to Indian rupee words (Indian number system)."""
    ones = ["", "One","Two","Three","Four","Five","Six","Seven","Eight","Nine",
            "Ten","Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen",
            "Seventeen","Eighteen","Nineteen"]
    tens = ["","","Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"]

    def _two(n: int) -> str:
        if n == 0: return ""
        if n < 20: return ones[n]
        return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")

    def _three(n: int) -> str:
        if n == 0: return ""
        h = ""
        if n >= 100:
            h = ones[n // 100] + " Hundred"
            n = n % 100
            if n: h += " and "
        return h + _two(n)

    n = int(round(amount))
    paise = round((amount - n) * 100)

    if n == 0:
        return "Zero Rupees Only"

    parts = []
    crore = n // 10_000_000;  n %= 10_000_000
    lakh  = n // 100_000;     n %= 100_000
    thou  = n // 1_000;       n %= 1_000
    rem   = n

    if crore: parts.append(_three(crore) + " Crore")
    if lakh:  parts.append(_three(lakh)  + " Lakh")
    if thou:  parts.append(_three(thou)  + " Thousand")
    if rem:   parts.append(_three(rem))

    result = "Rupees " + " ".join(parts)
    if paise:
        result += f" and {_two(paise)} Paise"
    return result + " Only"


def _bill_from_to_card(milestone_dict: dict, st: dict) -> Table:
    """Two-column Bill From / Bill To card."""
    lw = USABLE * 0.50
    rw = USABLE * 0.50

    def _block(heading: str, rows_data: list[tuple[str, str]], width: float) -> Table:
        cells = [[Paragraph(heading, ParagraphStyle(
            "bh", fontName="Helvetica-Bold", fontSize=9, textColor=WHITE))]]
        for k, v in rows_data:
            if v and str(v).strip():
                cells.append([Table([[
                    Paragraph(k, ParagraphStyle("bk", fontName="Helvetica-Bold",
                              fontSize=7.5, textColor=GREY)),
                    Paragraph(str(v), ParagraphStyle("bv", fontName="Helvetica",
                              fontSize=8.5, textColor=BLACK)),
                ]], colWidths=[24*mm, width - 24*mm - 12],
                    style=[
                        ("TOPPADDING",    (0,0),(-1,-1), 2),
                        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
                        ("LEFTPADDING",   (0,0),(-1,-1), 0),
                        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
                    ])])

        t = Table(cells, colWidths=[width])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0),  NAVY),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
            ("RIGHTPADDING",  (0,0),(-1,-1), 6),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LGREY]),
        ]))
        return t

    from_block = _block("Bill From", [
        ("Name",    COMPANY["name"]),
        ("Address", f"{COMPANY['address1']}, {COMPANY['address2']}"),
        ("GSTIN",   COMPANY["gst"]),
        ("State",   f"{COMPANY['state']} ({COMPANY['state_code']})"),
        ("Phone",   COMPANY["phone"]),
        ("Email",   COMPANY["email"]),
    ], lw)

    apt     = milestone_dict.get('apartment_number', '')
    to_block = _block("Bill To", [
        ("Name",    milestone_dict.get('owner_name', 'Owner')),
        ("Project", "Sreedhanya AI Residential, Thrissur"),
        ("Apt No.", apt),
        ("GSTIN",   "Unregistered"),
        ("State",   "Kerala (32)"),
    ], rw)

    t = Table([[from_block, to_block]], colWidths=[lw, rw])
    t.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
        ("LEFTPADDING",  (1,0),(1,0),   6),
    ]))
    return t


def _invoice_line_table(milestone_dict: dict, taxable: float,
                        cgst_rate: float, sgst_rate: float, st: dict) -> Table:
    """Single-row line items table for the milestone invoice."""
    stage_labels = {
        'advance':          '50% Advance Payment',
        'on_delivery':      '30% On Delivery Payment',
        'on_commissioning': '20% On Commissioning Payment',
    }
    stage     = milestone_dict.get('stage', '')
    stage_lbl = stage_labels.get(stage, stage.replace('_', ' ').title())
    apt       = milestone_dict.get('apartment_number', '')
    desc      = f"KNX & Smart Home Automation Installation — Apt {apt}\n{stage_lbl}"

    cgst_amt  = round(taxable * cgst_rate / 100, 2)
    sgst_amt  = round(taxable * sgst_rate / 100, 2)
    total_amt = taxable + cgst_amt + sgst_amt

    # Headers
    hdrs   = ["#", "Description", "HSN/\nSAC", "Qty", "Unit", "Rate (Rs.)",
              "Taxable\nValue (Rs.)", f"CGST\n{cgst_rate:.0f}%", f"SGST\n{sgst_rate:.0f}%", "Total (Rs.)"]
    hstyl  = [st["tbl_hdr_c"]] + [st["tbl_hdr"]] + [st["tbl_hdr_c"]] * 3 + [st["tbl_hdr_r"]] * 5
    hdr_row = [Paragraph(h, s) for h, s in zip(hdrs, hstyl)]

    rows = [
        hdr_row,
        [
            Paragraph("1", st["body_c"]),
            Paragraph(desc, st["body"]),
            Paragraph("995469", st["small_c"]),
            Paragraph("1", st["body_c"]),
            Paragraph("Lot", st["small_c"]),
            Paragraph(Rs(taxable), st["body_r"]),
            Paragraph(Rs(taxable), st["body_r"]),
            Paragraph(Rs(cgst_amt), st["body_r"]),
            Paragraph(Rs(sgst_amt), st["body_r"]),
            Paragraph(Rs(total_amt), st["body_r"]),
        ],
    ]

    tbl = Table(rows, colWidths=CW_INV, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), NAVY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, LGREY]),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 3),
        ("RIGHTPADDING",  (0,0),(-1,-1), 3),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BOX",           (0,0),(-1,-1), 0.5, NAVY),
        ("LINEBELOW",     (0,0),(-1,0),  0.75, BLUE),
        ("INNERGRID",     (0,1),(-1,-1), 0.25, DGREY),
    ]))
    return tbl


def _invoice_gst_totals(taxable: float, cgst_rate: float, sgst_rate: float,
                        st: dict) -> Table:
    """GST totals block for invoice."""
    cgst_amt  = round(taxable * cgst_rate / 100, 2)
    sgst_amt  = round(taxable * sgst_rate / 100, 2)
    total_gst = cgst_amt + sgst_amt
    invoice_total = taxable + total_gst

    lw = USABLE - 110
    vw = 110

    def _row(lbl, val, bold=False, bg=None, big=False):
        fs = 11 if big else 9
        lp = Paragraph(lbl, ParagraphStyle("il", fontName="Helvetica-Bold" if bold else "Helvetica",
                        fontSize=fs, textColor=NAVY if bold else BLACK, alignment=TA_RIGHT))
        vp = Paragraph(val, ParagraphStyle("iv", fontName="Helvetica-Bold" if bold else "Helvetica",
                        fontSize=fs, textColor=NAVY if bold else BLACK, alignment=TA_RIGHT))
        return [lp, vp], bg

    rows_data = [
        _row("Taxable Value (excl. GST):", Rs(taxable)),
        _row(f"CGST @ {cgst_rate:.0f}%:",  Rs(cgst_amt)),
        _row(f"SGST @ {sgst_rate:.0f}%:",  Rs(sgst_amt)),
        _row("Total GST:",                  Rs(total_gst)),
        _row("Invoice Total (incl. GST):",  Rs(invoice_total), bold=True, bg=LBLUE, big=True),
    ]

    table_rows = [rd[0] for rd in rows_data]
    t = Table(table_rows, colWidths=[lw, vw])
    ts = [
        ("ALIGN",        (0,0),(-1,-1), "RIGHT"),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("BOX",          (0,0),(-1,-1), 0.5, NAVY),
        ("LINEABOVE",    (0,3),(-1,3),  0.5, NAVY),
        ("LINEABOVE",    (0,-1),(-1,-1),0.75, NAVY),
    ]
    for i, (_, bg) in enumerate(rows_data):
        if bg:
            ts.append(("BACKGROUND", (0,i),(-1,i), bg))
    t.setStyle(TableStyle(ts))
    return t


def generate_invoice_pdf(milestone_dict: dict, invoice_number: str) -> str:
    """
    Generate a GST-compliant Tax Invoice PDF.

    Args:
        milestone_dict: Milestone fields including stage, percentage, amount,
                        apartment_number, quote_id. Optionally owner_name.
        invoice_number: Pre-generated invoice number string.

    Returns:
        filepath: Full path to generated PDF
    """
    timestamp       = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    safe_inv_no     = invoice_number.replace('/', '-').replace('\\', '-')
    filename        = f"invoice_{safe_inv_no}_{timestamp}.pdf"
    filepath        = os.path.join(PDF_DIR, filename)

    st  = _make_styles()
    buf = io.BytesIO()

    today       = datetime.date.today()
    inv_date_s  = today.strftime("%d %b %Y")
    due_date_s  = (today + datetime.timedelta(days=30)).strftime("%d %b %Y")

    # GST rates — intra-state Kerala
    cgst_rate = sgst_rate = 9.0
    taxable   = float(milestone_dict.get('amount', 0))
    cgst_amt  = round(taxable * cgst_rate / 100, 2)
    sgst_amt  = round(taxable * sgst_rate / 100, 2)
    invoice_total = taxable + cgst_amt + sgst_amt

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN + 10*mm,
        title=f"Tax Invoice — {invoice_number}",
        author=COMPANY["name"],
    )

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(_build_header("TAX INVOICE", [
        ("Invoice No",   invoice_number),
        ("Invoice Date", inv_date_s),
        ("Due Date",     due_date_s),
        ("Supply Type",  "Intra-State  |  CGST 9% + SGST 9%"),
    ], st))
    story.append(Spacer(1, 4*mm))
    story.append(_hr(NAVY, 1.5))
    story.append(Spacer(1, 4*mm))

    # ── Bill From / Bill To ───────────────────────────────────────────────────
    story.append(_bill_from_to_card(milestone_dict, st))
    story.append(Spacer(1, 4*mm))

    # ── Reverse charge ────────────────────────────────────────────────────────
    story.append(Paragraph(
        "Whether tax is payable under reverse charge:  <b>No</b>",
        ParagraphStyle("rc", fontName="Helvetica", fontSize=8, textColor=GREY)
    ))
    story.append(Spacer(1, 4*mm))

    # ── Line items ────────────────────────────────────────────────────────────
    story.append(_invoice_line_table(milestone_dict, taxable, cgst_rate, sgst_rate, st))
    story.append(Spacer(1, 4*mm))

    # ── GST Totals ────────────────────────────────────────────────────────────
    story.append(_invoice_gst_totals(taxable, cgst_rate, sgst_rate, st))
    story.append(Spacer(1, 3*mm))

    # ── Amount in words ───────────────────────────────────────────────────────
    story.append(Paragraph(
        f"<b>Invoice Amount in Words:</b>  {_amount_in_words(invoice_total)}",
        st["words"]
    ))
    story.append(Spacer(1, 5*mm))

    # ── Bank details ──────────────────────────────────────────────────────────
    story.append(_hr())
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Bank Details for NEFT / RTGS Transfer:", st["terms_h"]))
    story.append(Spacer(1, 3*mm))
    story.append(_bank_block(st))
    story.append(Spacer(1, 5*mm))

    # ── Terms ─────────────────────────────────────────────────────────────────
    story.append(_hr())
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Terms & Conditions", st["terms_h"]))
    story.append(Spacer(1, 3*mm))
    for line in [
        f"1.  Payment terms: {COMPANY['payment_terms']}.",
        "2.  Goods once sold will not be taken back.",
        "3.  Subject to Thrissur jurisdiction.",
        "4.  E. & O.E.",
    ]:
        story.append(Paragraph(line, st["terms_b"]))
    story.append(Spacer(1, 10*mm))

    # ── Signature ─────────────────────────────────────────────────────────────
    story.append(_hr())
    story.append(Spacer(1, 4*mm))
    story.append(_signature(st))

    doc.build(story, onFirstPage=_footer_fn(st), onLaterPages=_footer_fn(st))

    with open(filepath, 'wb') as f:
        f.write(buf.getvalue())

    return filepath
