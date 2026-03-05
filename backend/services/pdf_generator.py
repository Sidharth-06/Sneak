"""
Generates a beautifully formatted PDF report from company insights data.
Uses reportlab for PDF construction.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── Brand colours ─────────────────────────────────────────────────────────────
DARK_BG    = colors.HexColor("#0f172a")
BLUE       = colors.HexColor("#3b82f6")
PURPLE     = colors.HexColor("#a855f7")
ORANGE     = colors.HexColor("#f97316")
EMERALD    = colors.HexColor("#10b981")
GREEN      = colors.HexColor("#22c55e")
CYAN       = colors.HexColor("#06b6d4")
INDIGO     = colors.HexColor("#6366f1")
PINK       = colors.HexColor("#ec4899")
WHITE      = colors.HexColor("#ffffff")
ZINC_400   = colors.HexColor("#a1a1aa")
ZINC_700   = colors.HexColor("#3f3f46")
ZINC_900   = colors.HexColor("#18181b")

SECTION_COLOURS = {
    "PR & Announcements":          BLUE,
    "Financial & Funding":         GREEN,
    "Market Analysis":             CYAN,
    "Product & Roadmap":           INDIGO,
    "Podcast Appearances":         PURPLE,
    "Social Media":                PINK,
    "Advertising & Campaigns":     ORANGE,
    "Influencer & Creator Collabs": EMERALD,
}

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm


def _styles():
    base = getSampleStyleSheet()

    company_title = ParagraphStyle(
        "CompanyTitle",
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=34,
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    subtitle = ParagraphStyle(
        "Subtitle",
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=ZINC_400,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=WHITE,
        spaceBefore=6,
        spaceAfter=4,
    )
    bullet_text = ParagraphStyle(
        "BulletText",
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=ZINC_400,
        leftIndent=12,
        spaceAfter=3,
    )
    no_data = ParagraphStyle(
        "NoData",
        fontName="Helvetica-Oblique",
        fontSize=10,
        leading=13,
        textColor=ZINC_700,
        leftIndent=12,
    )
    footer_style = ParagraphStyle(
        "Footer",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=ZINC_700,
        alignment=TA_CENTER,
    )
    return {
        "company_title": company_title,
        "subtitle": subtitle,
        "section_heading": section_heading,
        "bullet_text": bullet_text,
        "no_data": no_data,
        "footer_style": footer_style,
    }


class PDFGenerator:
    def generate(self, insights: dict) -> bytes:
        """Return raw PDF bytes for the given insights dict."""
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
            title=f"{insights.get('companyName', 'Company')} Insights Report",
            author="Sneak",
        )

        styles = _styles()
        story = []

        company_name = insights.get("companyName", "Unknown Company")
        generated_at = datetime.now().strftime("%B %d, %Y at %H:%M UTC")

        # ── Header block ──────────────────────────────────────────────────────
        # Dark background header using a single-cell table
        header_content = [
            [Paragraph(company_name, styles["company_title"])],
            [Paragraph("Sneak Intelligence Report", styles["subtitle"])],
            [Paragraph(f"Generated on {generated_at}", styles["subtitle"])],
        ]
        header_table = Table(
            header_content,
            colWidths=[PAGE_W - 2 * MARGIN],
        )
        header_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), DARK_BG),
            ("TOPPADDING",  (0, 0), (-1, 0),  20),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 20),
            ("LEFTPADDING",   (0, 0), (-1, -1), 16),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
            ("ROUNDEDCORNERS", [8]),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 8 * mm))

        # ── Summary badge row ─────────────────────────────────────────────────
        sections_meta = [
            ("PR & Announcements",          insights.get("pr",              []), BLUE),
            ("Financial & Funding",         insights.get("financial",       []), GREEN),
            ("Market Analysis",             insights.get("market_analysis", []), CYAN),
            ("Product & Roadmap",           insights.get("product_roadmap", []), INDIGO),
            ("Podcast Appearances",         insights.get("podcasts",        []), PURPLE),
            ("Social Media",                insights.get("social_media",    []), PINK),
            ("Advertising & Campaigns",     insights.get("ads",             []), ORANGE),
            ("Influencer & Creator Collabs",insights.get("influencers",     []), EMERALD),
        ]

        badge_cells = []
        for label, items, colour in sections_meta:
            count = len(items)
            badge_cells.append(
                Paragraph(
                    f'<font color="{colour.hexval()}" size="18"><b>{count}</b></font>'
                    f'<br/><font color="{ZINC_400.hexval()}" size="8">{label}</font>',
                    ParagraphStyle("b", alignment=TA_CENTER, leading=20),
                )
            )

        badge_table = Table(
            [badge_cells],
            colWidths=[(PAGE_W - 2 * MARGIN) / 4] * 4,
        )
        # Show badges in 2 rows of 4
        if len(badge_cells) > 4:
            row1 = badge_cells[:4]
            row2 = badge_cells[4:]
            # Pad row2 if needed
            while len(row2) < 4:
                row2.append(Paragraph("", ParagraphStyle("b", alignment=TA_CENTER)))
            badge_table = Table(
                [row1, row2],
                colWidths=[(PAGE_W - 2 * MARGIN) / 4] * 4,
            )
        badge_table.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), ZINC_900),
            ("TOPPADDING",   (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("ROUNDEDCORNERS", [6]),
        ]))
        story.append(badge_table)
        story.append(Spacer(1, 8 * mm))

        # ── Insight sections ───────────────────────────────────────────────────
        for label, items, colour in sections_meta:
            section_elements = []

            # Section heading with colour dot
            section_elements.append(
                Paragraph(
                    f'<font color="{colour.hexval()}">●</font>  {label}',
                    styles["section_heading"],
                )
            )
            section_elements.append(
                HRFlowable(
                    width="100%",
                    thickness=1,
                    color=colour,
                    spaceAfter=4,
                )
            )

            if items:
                for item in items:
                    if isinstance(item, dict):
                        # Rich structured insight
                        title   = item.get("title", "")
                        detail  = item.get("detail", "")
                        date    = item.get("date", "")
                        src_url = item.get("source_url", "")

                        if title:
                            section_elements.append(
                                Paragraph(f"<b>{title}</b>", styles["bullet_text"])
                            )
                        if detail:
                            section_elements.append(
                                Paragraph(detail, styles["bullet_text"])
                            )
                        meta_parts = []
                        if date:
                            meta_parts.append(f"<font color='{ZINC_400.hexval()}'>{date}</font>")
                        if src_url:
                            meta_parts.append(
                                f'<font color="#3b82f6"><a href="{src_url}" color="#3b82f6">{src_url}</a></font>'
                            )
                        if meta_parts:
                            section_elements.append(
                                Paragraph("  ".join(meta_parts), styles["bullet_text"])
                            )
                        section_elements.append(Spacer(1, 2 * mm))
                    else:
                        # Legacy plain string
                        section_elements.append(
                            Paragraph(f"→  {item}", styles["bullet_text"])
                        )
            else:
                section_elements.append(
                    Paragraph("No data found for this category.", styles["no_data"])
                )

            section_elements.append(Spacer(1, 5 * mm))
            story.append(KeepTogether(section_elements))

        # ── Footer ─────────────────────────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=0.5, color=ZINC_700, spaceAfter=4))
        story.append(
            Paragraph(
                "Generated by Sneak · Powered by AI · Data via SearXNG",
                styles["footer_style"],
            )
        )

        doc.build(story)
        return buf.getvalue()
