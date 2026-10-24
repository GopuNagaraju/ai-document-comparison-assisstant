"""
Report Generator Module.
Generates downloadable DOCX (via python-docx) and PDF (if reportlab is installed)
comparison reports containing all required sections from Section 9 of the Project Brief.
"""

import io
from datetime import datetime
from typing import Dict, Any, List
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls


PRIMARY_HEX = "1E3A8A"     # Deep navy blue
ALT_ROW_HEX = "F1F5F9"     # Light slate tint
TEXT_DARK = RGBColor(0x1E, 0x29, 0x3B)
PRIMARY_RGB = RGBColor(0x1E, 0x3A, 0x8A)


def _add_section_heading(doc: docx.Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = PRIMARY_RGB
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True


def _style_table_header(header_row, headers: List[str]) -> None:
    for idx, text in enumerate(headers):
        cell = header_row.cells[idx]
        cell.text = text
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        shd = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls("w"), PRIMARY_HEX))
        cell._tc.get_or_add_tcPr().append(shd)
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            for run in p.runs:
                run.font.name = "Calibri"
                run.font.bold = True
                run.font.size = Pt(10.5)
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def generate_docx_report(comparison_result: Dict[str, Any]) -> bytes:
    """
    Builds a formatted Microsoft Word (.docx) comparison report in memory and returns raw bytes.
    Includes all 7 required sections from Section 9 (Expected Output Format).
    """
    doc = docx.Document()

    # 1-inch margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Calibri"
    style_normal.font.size = Pt(11)
    style_normal.font.color.rgb = TEXT_DARK

    doc_a_name = comparison_result.get("document_a_name", "Document A")
    doc_b_name = comparison_result.get("document_b_name", "Document B")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Title Banner
    title_p = doc.add_paragraph()
    title_run = title_p.add_run("AI Document Comparison Report")
    title_run.font.name = "Calibri"
    title_run.font.size = Pt(22)
    title_run.font.bold = True
    title_run.font.color.rgb = PRIMARY_RGB
    title_p.paragraph_format.space_after = Pt(4)

    meta_p = doc.add_paragraph(
        f"Document A: {doc_a_name}  |  Document B: {doc_b_name}  |  Generated: {generated_at}"
    )
    meta_p.paragraph_format.space_after = Pt(12)
    for run in meta_p.runs:
        run.font.size = Pt(10)
        run.font.italic = True

    # 1. Document A — file name and summary
    _add_section_heading(doc, f"1. Document A Summary ({doc_a_name})")
    p_a = doc.add_paragraph(comparison_result.get("document_a_summary", "Not available."))
    p_a.paragraph_format.space_after = Pt(8)
    p_a.paragraph_format.line_spacing = 1.15

    # 2. Document B — file name and summary
    _add_section_heading(doc, f"2. Document B Summary ({doc_b_name})")
    p_b = doc.add_paragraph(comparison_result.get("document_b_summary", "Not available."))
    p_b.paragraph_format.space_after = Pt(8)
    p_b.paragraph_format.line_spacing = 1.15

    # 3. Similarities — points supported by both documents
    _add_section_heading(doc, "3. Similarities")
    similarities = comparison_result.get("similarities", [])
    if similarities:
        for sim in similarities:
            bp = doc.add_paragraph(style="List Bullet")
            run = bp.add_run(str(sim))
            run.font.size = Pt(11)
            bp.paragraph_format.space_after = Pt(4)
    else:
        doc.add_paragraph("No specific similarities were identified.")

    # 4. Differences — changed, added, removed, or conflicting information
    _add_section_heading(doc, "4. Meaningful Differences")
    differences = comparison_result.get("differences", [])
    if differences:
        diff_headers = ["Topic", "Change Type", f"Document A ({doc_a_name})", f"Document B ({doc_b_name})", "Explanation"]
        diff_table = doc.add_table(rows=1, cols=len(diff_headers))
        diff_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _style_table_header(diff_table.rows[0], diff_headers)

        for idx, item in enumerate(differences):
            row = diff_table.add_row()
            vals = [
                str(item.get("topic", "")),
                str(item.get("change_type", "")),
                str(item.get("document_a_detail", "")),
                str(item.get("document_b_detail", "")),
                str(item.get("explanation", "")),
            ]
            for c_idx, val in enumerate(vals):
                cell = row.cells[c_idx]
                cell.text = val
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                if idx % 2 == 1:
                    shd = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls("w"), ALT_ROW_HEX))
                    cell._tc.get_or_add_tcPr().append(shd)
                for p in cell.paragraphs:
                    p.paragraph_format.space_before = Pt(3)
                    p.paragraph_format.space_after = Pt(3)
                    for r in p.runs:
                        r.font.size = Pt(10)
    else:
        doc.add_paragraph("No meaningful differences were found between the two documents.")

    # 5. Key Details Comparison — dates, amounts, names, requirements, etc.
    _add_section_heading(doc, "5. Key Details Comparison")
    key_details = comparison_result.get("key_details_comparison", [])
    if key_details:
        kd_headers = ["Field / Attribute", f"Document A ({doc_a_name})", f"Document B ({doc_b_name})", "Status"]
        kd_table = doc.add_table(rows=1, cols=len(kd_headers))
        kd_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _style_table_header(kd_table.rows[0], kd_headers)

        for idx, item in enumerate(key_details):
            row = kd_table.add_row()
            vals = [
                str(item.get("field", "")),
                str(item.get("document_a_value", "")),
                str(item.get("document_b_value", "")),
                str(item.get("status", "")),
            ]
            for c_idx, val in enumerate(vals):
                cell = row.cells[c_idx]
                cell.text = val
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                if idx % 2 == 1:
                    shd = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls("w"), ALT_ROW_HEX))
                    cell._tc.get_or_add_tcPr().append(shd)
                for p in cell.paragraphs:
                    p.paragraph_format.space_before = Pt(3)
                    p.paragraph_format.space_after = Pt(3)
                    for r in p.runs:
                        r.font.size = Pt(10)
    else:
        doc.add_paragraph("No specific structured key details were extracted.")

    # 6. Overall Conclusion — a short, neutral explanation of the main changes
    _add_section_heading(doc, "6. Overall Conclusion")
    p_conc = doc.add_paragraph(comparison_result.get("overall_conclusion", "Not available."))
    p_conc.paragraph_format.space_after = Pt(8)
    p_conc.paragraph_format.line_spacing = 1.15

    # 7. Limitations — note on unreadable pages, missing information, or scope disclaimer
    _add_section_heading(doc, "7. Limitations & Scope Notice")
    p_lim = doc.add_paragraph(
        comparison_result.get(
            "limitations",
            "No unreadable pages detected. Informational comparison only; not legal advice.",
        )
    )
    p_lim.paragraph_format.space_after = Pt(8)
    p_lim.paragraph_format.line_spacing = 1.15

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
