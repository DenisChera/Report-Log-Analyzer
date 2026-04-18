"""Generate a PDF summary of AI analysis results."""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

_styles = getSampleStyleSheet()

_TITLE = ParagraphStyle("Title2", parent=_styles["Title"], fontSize=18, spaceAfter=6)
_H1 = ParagraphStyle("H1", parent=_styles["Heading1"], fontSize=14, spaceAfter=4)
_H2 = ParagraphStyle("H2", parent=_styles["Heading2"], fontSize=11, spaceAfter=3)
_BODY = ParagraphStyle("Body2", parent=_styles["BodyText"], fontSize=9, leading=12)
_SMALL = ParagraphStyle("Small", parent=_styles["BodyText"], fontSize=8, leading=10, textColor=colors.grey)

_SEV_COLORS = {
    "critical": colors.HexColor("#DC2626"),
    "medium": colors.HexColor("#F59E0B"),
    "minor": colors.HexColor("#6B7280"),
}

_TYPE_LABELS = {
    "bug": "Bug",
    "environment": "Environment",
    "broken_test": "Broken Test",
}


def generate_pdf(reports: list[dict]) -> bytes:
    """Generate a PDF from a list of analysis result dicts.

    Each item in *reports* must have:
      - filename: str
      - data: dict (AnalysisResult shape)

    Returns the PDF as bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    story: list = []

    # ── Title page header ──
    story.append(Paragraph("MTS Report Analyzer — AI Analysis Summary", _TITLE))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  •  "
        f"{len(reports)} report(s)",
        _SMALL,
    ))
    story.append(Spacer(1, 0.5 * cm))

    # ── Aggregate summary ──
    total = sum(r["data"].get("total_tests", 0) for r in reports)
    passed = sum(r["data"].get("passed", 0) for r in reports)
    failed = sum(r["data"].get("failed", 0) for r in reports)

    summary_data = [
        ["Total Tests", "Passed", "Failed"],
        [str(total), str(passed), str(failed)],
    ]
    t = Table(summary_data, colWidths=[5 * cm, 5 * cm, 5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#D1FAE5")),
        ("BACKGROUND", (2, 1), (2, 1), colors.HexColor("#FEE2E2") if failed else colors.HexColor("#D1FAE5")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.6 * cm))

    # ── Per-report sections ──
    for idx, report in enumerate(reports):
        data = report["data"]

        if idx > 0:
            story.append(HRFlowable(width="100%", color=colors.lightgrey))
            story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph(f"📄 {report['filename']}", _H1))
        story.append(Paragraph(
            f"{data.get('total_tests', 0)} tests — "
            f"{data.get('passed', 0)} passed, {data.get('failed', 0)} failed",
            _SMALL,
        ))
        story.append(Spacer(1, 0.2 * cm))

        # Run summary
        if data.get("run_summary"):
            story.append(Paragraph(f"<i>{data['run_summary']}</i>", _BODY))
            story.append(Spacer(1, 0.2 * cm))

        # Top priority
        if data.get("top_priority"):
            story.append(Paragraph(
                f"<b>🎯 Top Priority:</b> {data['top_priority']}", _BODY
            ))
            story.append(Spacer(1, 0.3 * cm))

        # Patterns
        patterns = data.get("patterns", [])
        if patterns:
            story.append(Paragraph("Patterns", _H2))
            for p in patterns:
                affected = ", ".join(p.get("affected_tests", []))
                story.append(Paragraph(
                    f"<b>{p.get('pattern_title', '')}</b> — {p.get('explanation', '')}"
                    f"<br/><font size=7 color='grey'>Affected: {affected}</font>",
                    _BODY,
                ))
                story.append(Spacer(1, 0.15 * cm))
            story.append(Spacer(1, 0.2 * cm))

        # Test analyses table
        analyses = data.get("test_analyses", [])
        if analyses:
            story.append(Paragraph("Failed Tests", _H2))

            table_data = [["Test Name", "Severity", "Type", "Root Cause", "Recommendation"]]
            for a in analyses:
                table_data.append([
                    Paragraph(a.get("test_name", ""), _BODY),
                    a.get("severity", "").upper(),
                    _TYPE_LABELS.get(a.get("failure_type", ""), a.get("failure_type", "")),
                    Paragraph(a.get("root_cause", ""), _BODY),
                    Paragraph(a.get("recommendation", ""), _BODY),
                ])

            col_widths = [4 * cm, 1.8 * cm, 2 * cm, 5 * cm, 5 * cm]
            t = Table(table_data, colWidths=col_widths, repeatRows=1)

            # Build row-level severity coloring
            style_cmds = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ALIGN", (1, 1), (2, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
            for row_idx, a in enumerate(analyses, start=1):
                sev = a.get("severity", "")
                sev_color = _SEV_COLORS.get(sev, colors.white)
                style_cmds.append(("TEXTCOLOR", (1, row_idx), (1, row_idx), sev_color))

            t.setStyle(TableStyle(style_cmds))
            story.append(t)
            story.append(Spacer(1, 0.4 * cm))

    doc.build(story)
    return buf.getvalue()
