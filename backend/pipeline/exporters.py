import io
import json
import csv
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from typing import Dict, Any, List

# Register NotoSansDevanagari for Hindi/Marathi Unicode PDF rendering
_DEVANAGARI_FONT = "Helvetica"   # fallback default
_DEVANAGARI_FONT_BOLD = "Helvetica-Bold"
_FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
_DEVANAGARI_TTF = os.path.join(_FONT_DIR, "NotoSansDevanagari-Regular.ttf")

try:
    if os.path.exists(_DEVANAGARI_TTF):
        pdfmetrics.registerFont(TTFont("NotoDevanagari", _DEVANAGARI_TTF))
        _DEVANAGARI_FONT = "NotoDevanagari"
        _DEVANAGARI_FONT_BOLD = "NotoDevanagari"
        print("[Exporters] NotoSansDevanagari font registered for Devanagari PDF export.")
    else:
        print(f"[Exporters] Devanagari font not found at {_DEVANAGARI_TTF} — falling back to Helvetica.")
except Exception as _font_err:
    print(f"[Exporters] Font registration warning: {_font_err} — falling back to Helvetica.")


def export_json(case_data: Dict[str, Any], documents: List[Dict[str, Any]], extractions: List[Dict[str, Any]]) -> bytes:
    """Generates canonical machine-readable JSON export."""
    payload = {
        "export_version": "2.0.0",
        "case": case_data,
        "document_count": len(documents),
        "documents": []
    }
    for doc in documents:
        doc_id = doc.get("id")
        ext = next((e for e in extractions if e.get("document_id") == doc_id), {})
        payload["documents"].append({
            "document_id": doc_id,
            "filename": doc.get("filename_safe"),
            "status": doc.get("status"),
            "quality_score": doc.get("quality_score"),
            "quality_band": doc.get("quality_band"),
            "quality_flags": doc.get("quality_flags_json"),
            "schema_name": ext.get("schema_name"),
            "overall_confidence": ext.get("overall_confidence"),
            "review_status": ext.get("status"),
            "approved_at": ext.get("approved_at"),
            "approved_by": ext.get("approved_by"),
            "fields": ext.get("fields", [])
        })
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def export_csv(case_data: Dict[str, Any], documents: List[Dict[str, Any]], extractions: List[Dict[str, Any]]) -> bytes:
    """
    Generates a clean, well-structured business CSV export with UTF-8 BOM.
    Readable column headers and properly formatted extracted values.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    case_name = case_data.get("name", "Review Case")

    # Clean Business Headers
    writer.writerow([
        "Case Name",
        "Document Name",
        "Document Type",
        "Field Name",
        "Extracted Value",
        "Raw OCR Snippet",
        "Confidence Score",
        "Confidence State",
        "Validation Status",
        "Review Status",
        "Document Quality Score"
    ])

    for doc in documents:
        doc_id = doc.get("id")
        fname = doc.get("filename_safe", "Document")
        q_score = doc.get("quality_score", "N/A")
        ext = next((e for e in extractions if e.get("document_id") == doc_id), {})
        doc_type = (ext.get("schema_name") or "generic").upper()
        rev_status = ext.get("status", "needs_review").upper()
        fields = ext.get("fields", [])

        if not fields:
            writer.writerow([
                case_name,
                fname,
                doc_type,
                "[NO_FIELDS_EXTRACTED]",
                "",
                "",
                "0%",
                "Red",
                "missing",
                rev_status,
                f"{q_score}/100"
            ])
        else:
            for f in fields:
                val = f.get("normalized_value") or f.get("raw_value") or ""
                raw_v = f.get("raw_value") or ""
                score = f"{f.get('field_score', 0)}%"
                state = f.get("confidence_state", "Yellow")
                val_status = f.get("validation_status", "valid")
                f_rev = (f.get("review_state") or rev_status).upper()

                writer.writerow([
                    case_name,
                    fname,
                    doc_type,
                    f.get("label") or f.get("field_key", ""),
                    val,
                    raw_v,
                    score,
                    state,
                    val_status,
                    f_rev,
                    f"{q_score}/100"
                ])

    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def export_xlsx(case_data: Dict[str, Any], documents: List[Dict[str, Any]], extractions: List[Dict[str, Any]]) -> bytes:
    """
    Generates an executive, beautifully formatted multi-sheet Excel workbook.
    Sheet 1: Executive Summary & All Extracted Fields visible immediately.
    Sheet 2: Detailed OCR Forensic Audit & Reason Codes.
    """
    wb = openpyxl.Workbook()

    # Style definitions
    title_font = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
    title_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")

    section_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    section_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")

    meta_label_font = Font(name="Segoe UI", size=10, bold=True, color="475569")
    meta_val_font = Font(name="Segoe UI", size=10, color="0F172A")
    meta_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")

    data_font = Font(name="Segoe UI", size=10, color="1E293B")
    data_font_bold = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    # Status & Confidence Fills
    green_fill = PatternFill(start_color="ECFDF5", end_color="ECFDF5", fill_type="solid")
    green_font = Font(name="Segoe UI", size=10, bold=True, color="065F46")

    amber_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    amber_font = Font(name="Segoe UI", size=10, bold=True, color="92400E")

    red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    red_font = Font(name="Segoe UI", size=10, bold=True, color="991B1B")

    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    # ─────────────────────────────────────────────────────────────
    # SHEET 1: Executive Summary & Extracted Fields
    # ─────────────────────────────────────────────────────────────
    ws_summary = wb.active
    ws_summary.title = "Executive Summary & Fields"
    ws_summary.views.sheetView[0].showGridLines = True

    # 1. Top Title Banner
    ws_summary.merge_cells("A1:G1")
    title_cell = ws_summary.cell(row=1, column=1, value="DocRefine — Verified Document Extraction Audit Report")
    title_cell.font = title_font
    title_cell.fill = title_fill
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws_summary.row_dimensions[1].height = 36

    # 2. Metadata Block
    meta_info = [
        ("Case Name", case_data.get("name", "N/A"), "Export Timestamp", case_data.get("updated_at", "N/A")),
        ("Case ID", case_data.get("id", "N/A"), "Total Documents", len(documents)),
        ("Review Status", "Verified & Human-Approved" if any(e.get("status") == "approved" for e in extractions) else "Pending Review", "Platform Version", "DocRefine AI v2.8")
    ]

    for r_offset, (k1, v1, k2, v2) in enumerate(meta_info):
        r_idx = 3 + r_offset
        ws_summary.row_dimensions[r_idx].height = 20

        # Col A-B
        c_k1 = ws_summary.cell(row=r_idx, column=1, value=k1)
        c_k1.font = meta_label_font
        c_k1.fill = meta_fill
        c_k1.border = thin_border

        c_v1 = ws_summary.cell(row=r_idx, column=2, value=str(v1))
        c_v1.font = meta_val_font
        c_v1.fill = white_fill
        c_v1.border = thin_border

        # Col C-D
        c_k2 = ws_summary.cell(row=r_idx, column=4, value=k2)
        c_k2.font = meta_label_font
        c_k2.fill = meta_fill
        c_k2.border = thin_border

        c_v2 = ws_summary.cell(row=r_idx, column=5, value=str(v2))
        c_v2.font = meta_val_font
        c_v2.fill = white_fill
        c_v2.border = thin_border

    # 3. Documents Overview Table
    doc_headers = [
        "Filename", "Document Type", "Quality Score", "Quality Band",
        "Overall Confidence", "Extracted Fields", "Review Status"
    ]
    doc_header_row = 7
    ws_summary.row_dimensions[doc_header_row].height = 24

    for col_idx, text in enumerate(doc_headers, 1):
        cell = ws_summary.cell(row=doc_header_row, column=col_idx, value=text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    curr_row = doc_header_row + 1
    for doc in documents:
        doc_id = doc.get("id")
        ext = next((e for e in extractions if e.get("document_id") == doc_id), {})
        fields = ext.get("fields", [])
        field_count_str = f"{len(fields)} fields extracted" if fields else "None"
        q_score = doc.get("quality_score", 0)
        q_band = doc.get("quality_band", "acceptable")
        conf = f"{ext.get('overall_confidence', 0)}%"
        st = ext.get("status", "needs_review").upper()

        ws_summary.row_dimensions[curr_row].height = 22
        row_fill = alt_fill if curr_row % 2 == 0 else white_fill

        values = [
            (doc.get("filename_safe", "document"), Alignment(horizontal="left", vertical="center")),
            ((ext.get("schema_name") or "generic").upper(), Alignment(horizontal="center", vertical="center")),
            (f"{q_score}/100", Alignment(horizontal="center", vertical="center")),
            (q_band.title(), Alignment(horizontal="center", vertical="center")),
            (conf, Alignment(horizontal="center", vertical="center")),
            (field_count_str, Alignment(horizontal="center", vertical="center")),
            (st, Alignment(horizontal="center", vertical="center"))
        ]

        for col_idx, (val, align) in enumerate(values, 1):
            cell = ws_summary.cell(row=curr_row, column=col_idx, value=val)
            cell.font = data_font
            cell.fill = row_fill
            cell.alignment = align
            cell.border = thin_border

            if col_idx == 7:
                if st == "APPROVED":
                    cell.fill = green_fill
                    cell.font = green_font
                elif st in ("NEEDS_REVIEW", "PENDING"):
                    cell.fill = amber_fill
                    cell.font = amber_font
                else:
                    cell.fill = red_fill
                    cell.font = red_font
        curr_row += 1

    # 4. Prominent Extracted Data Section on Sheet 1
    curr_row += 2
    ws_summary.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=7)
    section_cell = ws_summary.cell(row=curr_row, column=1, value="VERIFIED EXTRACTED FIELDS BY DOCUMENT")
    section_cell.font = section_font
    section_cell.fill = section_fill
    section_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_summary.row_dimensions[curr_row].height = 28
    curr_row += 1

    ext_field_headers = [
        "Document", "Document Type", "Field Name", "Extracted Value",
        "Confidence Score", "Validation Status", "Review Status"
    ]
    ws_summary.row_dimensions[curr_row].height = 24
    for col_idx, text in enumerate(ext_field_headers, 1):
        cell = ws_summary.cell(row=curr_row, column=col_idx, value=text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    curr_row += 1

    has_any_fields = False
    for doc in documents:
        doc_id = doc.get("id")
        fname = doc.get("filename_safe", "document")
        ext = next((e for e in extractions if e.get("document_id") == doc_id), {})
        doc_type = (ext.get("schema_name") or "generic").upper()
        doc_fields = ext.get("fields", [])

        for f in doc_fields:
            has_any_fields = True
            ws_summary.row_dimensions[curr_row].height = 20
            row_fill = alt_fill if curr_row % 2 == 0 else white_fill

            norm_val = str(f.get("normalized_value") or f.get("raw_value") or "[MISSING]")
            score_num = f.get("field_score", 0)
            score_str = f"{score_num}%"
            state = f.get("confidence_state", "Yellow")
            val_st = f.get("validation_status", "valid").upper()
            rev_st = (f.get("review_state") or ext.get("status", "needs_review")).upper()

            f_values = [
                (fname, Alignment(horizontal="left", vertical="center")),
                (doc_type, Alignment(horizontal="center", vertical="center")),
                (f.get("label") or f.get("field_key", ""), Alignment(horizontal="left", vertical="center")),
                (norm_val, Alignment(horizontal="left", vertical="center")),
                (score_str, Alignment(horizontal="center", vertical="center")),
                (val_st, Alignment(horizontal="center", vertical="center")),
                (rev_st, Alignment(horizontal="center", vertical="center"))
            ]

            for col_idx, (val, align) in enumerate(f_values, 1):
                cell = ws_summary.cell(row=curr_row, column=col_idx, value=val)
                cell.font = data_font_bold if col_idx == 4 else data_font
                cell.fill = row_fill
                cell.alignment = align
                cell.border = thin_border

                if col_idx == 5: # Score
                    if state == "Green":
                        cell.fill = green_fill
                        cell.font = green_font
                    elif state == "Yellow":
                        cell.fill = amber_fill
                        cell.font = amber_font
                    else:
                        cell.fill = red_fill
                        cell.font = red_font
            curr_row += 1

    if not has_any_fields:
        ws_summary.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=7)
        c_none = ws_summary.cell(row=curr_row, column=1, value="No extracted fields available. Please run extraction on documents.")
        c_none.font = data_font
        c_none.alignment = Alignment(horizontal="center", vertical="center")
        curr_row += 1

    # ─────────────────────────────────────────────────────────────
    # SHEET 2: Forensic Field Audit & Raw OCR Snippets
    # ─────────────────────────────────────────────────────────────
    ws_fields = wb.create_sheet(title="Forensic Field Audit")
    ws_fields.views.sheetView[0].showGridLines = True

    field_headers = [
        "Document Filename", "Document Type", "Field Key", "Field Label", "Normalized Value",
        "Raw OCR Snippet", "Confidence Score", "Confidence State", "Validation Status", "Review State"
    ]
    ws_fields.row_dimensions[1].height = 26

    for col_idx, text in enumerate(field_headers, 1):
        cell = ws_fields.cell(row=1, column=col_idx, value=text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    current_field_row = 2
    for doc in documents:
        doc_id = doc.get("id")
        fname = doc.get("filename_safe", "document")
        ext = next((e for e in extractions if e.get("document_id") == doc_id), {})
        schema_type = (ext.get("schema_name") or "generic").upper()
        doc_fields = ext.get("fields", [])

        for f in doc_fields:
            ws_fields.row_dimensions[current_field_row].height = 20
            row_fill = alt_fill if current_field_row % 2 == 0 else white_fill

            norm_val = str(f.get("normalized_value") or f.get("raw_value") or "[MISSING]")
            raw_val = str(f.get("raw_value") or "")
            score_num = f.get("field_score", 0)
            score_str = f"{score_num}%"
            state = f.get("confidence_state", "Red")
            val_st = f.get("validation_status", "valid")
            rev_st = f.get("review_state", "needs_review")

            field_vals = [
                (fname, Alignment(horizontal="left", vertical="center")),
                (schema_type, Alignment(horizontal="center", vertical="center")),
                (f.get("field_key", ""), Alignment(horizontal="left", vertical="center")),
                (f.get("label", ""), Alignment(horizontal="left", vertical="center")),
                (norm_val, Alignment(horizontal="left", vertical="center")),
                (raw_val, Alignment(horizontal="left", vertical="center")),
                (score_str, Alignment(horizontal="center", vertical="center")),
                (state, Alignment(horizontal="center", vertical="center")),
                (val_st, Alignment(horizontal="center", vertical="center")),
                (rev_st, Alignment(horizontal="center", vertical="center"))
            ]

            for col_idx, (val, align) in enumerate(field_vals, 1):
                cell = ws_fields.cell(row=current_field_row, column=col_idx, value=val)
                cell.font = data_font
                cell.fill = row_fill
                cell.alignment = align
                cell.border = thin_border

                if col_idx == 8: # Confidence State
                    if state == "Green":
                        cell.fill = green_fill
                        cell.font = green_font
                    elif state == "Yellow":
                        cell.fill = amber_fill
                        cell.font = amber_font
                    else:
                        cell.fill = red_fill
                        cell.font = red_font

            current_field_row += 1

    # Auto-adjust column widths for both sheets
    for ws in [ws_summary, ws_fields]:
        for col_idx, col in enumerate(ws.columns, 1):
            max_len = 0
            col_letter = get_column_letter(col_idx)
            for cell in col:
                val = str(cell.value or "")
                if "\n" in val:
                    val = max(val.split("\n"), key=len)
                if len(val) > max_len and cell.row > 1: # Ignore title banner
                    max_len = len(val)
            ws.column_dimensions[col_letter].width = max(min(max_len + 4, 45), 16)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def export_pdf(case_data: Dict[str, Any], documents: List[Dict[str, Any]], extractions: List[Dict[str, Any]]) -> bytes:
    """
    Generates a clean executive PDF case report with Devanagari Unicode support,
    metadata blocks, and auto-wrapped table cells.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocRefineTitle',
        parent=styles['Heading1'],
        fontName=_DEVANAGARI_FONT_BOLD,
        fontSize=16,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=8
    )

    h2_style = ParagraphStyle(
        'DocRefineH2',
        parent=styles['Heading2'],
        fontName=_DEVANAGARI_FONT_BOLD,
        fontSize=12,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'DocRefineBody',
        parent=styles['Normal'],
        fontName=_DEVANAGARI_FONT,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    cell_style = ParagraphStyle(
        'DocRefineCell',
        parent=styles['Normal'],
        fontName=_DEVANAGARI_FONT,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1E293B')
    )

    cell_bold = ParagraphStyle(
        'DocRefineCellBold',
        parent=styles['Normal'],
        fontName=_DEVANAGARI_FONT_BOLD,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )

    story = []
    story.append(Paragraph("DocRefine: Verified Document Rescue & Extraction Report", title_style))
    story.append(Paragraph(f"<b>Case Name:</b> {case_data.get('name', 'N/A')} &nbsp;|&nbsp; <b>Case ID:</b> {case_data.get('id', 'N/A')}", body_style))
    story.append(Paragraph(f"<b>Total Documents:</b> {len(documents)} &nbsp;|&nbsp; <b>Export Timestamp:</b> {case_data.get('updated_at', 'UTC')}", body_style))
    story.append(Spacer(1, 12))

    for doc_item in documents:
        doc_id = doc_item.get("id")
        fname = doc_item.get("filename_safe", "Document")
        ext = next((e for e in extractions if e.get("document_id") == doc_id), {})
        doc_type = (ext.get("schema_name") or "generic").upper()
        rev_status = ext.get("status", "needs_review").upper()
        q_score = doc_item.get("quality_score", 0)

        story.append(Paragraph(f"Document: <b>{fname}</b> ({doc_type})", h2_style))
        story.append(Paragraph(f"Quality Score: <b>{q_score}/100</b> &nbsp;|&nbsp; Overall Status: <b>{rev_status}</b>", body_style))

        # Field table with Paragraph-wrapped cells
        fields = ext.get("fields", [])
        if fields:
            table_data = [[
                Paragraph("<b>Field Name</b>", cell_bold),
                Paragraph("<b>Extracted Value</b>", cell_bold),
                Paragraph("<b>Confidence</b>", cell_bold),
                Paragraph("<b>Validation</b>", cell_bold)
            ]]
            for f in fields:
                val = str(f.get("normalized_value") or f.get("raw_value") or "[MISSING]")
                state = f.get("confidence_state", "Red")
                score = f"{f.get('field_score', 0)}% ({state})"
                table_data.append([
                    Paragraph(f.get("label") or f.get("field_key", ""), cell_style),
                    Paragraph(val, cell_style),
                    Paragraph(score, cell_style),
                    Paragraph(f.get("validation_status", "valid"), cell_style)
                ])

            t = Table(table_data, colWidths=[140, 220, 90, 90])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(Spacer(1, 4))
            story.append(t)
        else:
            story.append(Paragraph("<i>No structured fields extracted.</i>", body_style))
        story.append(Spacer(1, 10))

    doc.build(story)
    return buffer.getvalue()
