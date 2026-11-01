"""Build the TechPulse user, technical and demo PDFs from checked-in Markdown.

Run from any working directory with `python scripts/build_redesign_pdfs.py`.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCREENSHOTS = ROOT / "outputs" / "redesign_screenshots"
INK = colors.HexColor("#3A3734")
TAUPE = colors.HexColor("#8B7D6B")
LINEN = colors.HexColor("#E8DFD2")
SURFACE = colors.HexColor("#F3EEE7")

QUERY_INFO = {
    1: ("Most active technologies", "Ranks tags by question volume; outputs total questions, unanswered totals, average unanswered share and active dates."),
    2: ("Unanswered question share", "Finds tags with high unanswered share after a minimum volume condition."),
    3: ("Monthly activity trend", "Returns monthly questions, unanswered measures and a three-month lag for trend comparison."),
    4: ("Company technology breadth", "Counts distinct tags linked to each company and orders companies by portfolio breadth."),
    5: ("Category-level activity", "Summarizes volume, unanswered share and variation by technology category."),
    6: ("Hardest technology per company", "Ranks the highest-friction technology for each company using question volume and unanswered share."),
    7: ("Growth momentum", "Compares a recent 30-day window with earlier activity windows."),
    8: ("Parent-company portfolio", "Compares parent-company and subsidiary technology portfolios and question totals."),
    9: ("Technology health composite", "Builds a descriptive health score from activity, unanswered share and active-day coverage."),
    10: ("Question quality", "Summarizes question volume, unanswered share and quality groups by tag."),
    11: ("Daily activity pattern", "Compares aggregate community activity by weekday."),
    12: ("Company diversity", "Uses technology category breadth to describe company portfolio diversity."),
}


def clean_text(value: str) -> str:
    """Replace typography unsupported by the selected PDF fonts."""
    return value.translate(str.maketrans({
        "–": "-", "—": "-", "−": "-", "‑": "-", "→": "->", "×": "x",
        "≥": ">=", "≤": "<=", "’": "'", "‘": "'", "“": '"', "”": '"',
        "·": "-", "…": "...", "é": "e", "ü": "u", "’": "'",
    }))


def inline_markup(text: str) -> str:
    """Convert a small safe subset of Markdown inline syntax to ReportLab XML."""
    text = clean_text(text)
    tokens: list[str] = []

    def store(value: str) -> str:
        tokens.append(value)
        return f"@@TOKEN{len(tokens)-1}@@"

    text = re.sub(r"`([^`]+)`", lambda m: store(f'<font name="Courier" size="8">{escape(m.group(1))}</font>'), text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: store(f'<link href="{escape(clean_text(m.group(2)), {chr(34): "&quot;"})}" color="#6D6255">{escape(m.group(1))}</link>'), text)
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    for i, value in enumerate(tokens):
        text = text.replace(f"@@TOKEN{i}@@", value)
    return text


class NumberedList(Flowable):
    """Marker used by the Markdown parser to group ordered lists."""


class TechPulseDoc(BaseDocTemplate):
    """A4 document with live page-numbered contents and consistent furniture."""

    def __init__(self, path: Path, title: str):
        self.title = title
        super().__init__(str(path), pagesize=A4, leftMargin=19 * mm, rightMargin=19 * mm,
                         topMargin=19 * mm, bottomMargin=18 * mm, title=title,
                         author="TechPulse project", subject="Academic research documentation")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=self._furniture))

    def _furniture(self, canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(TAUPE)
        canvas.setLineWidth(0.45)
        canvas.line(doc.leftMargin, height - 12 * mm, width - doc.rightMargin, height - 12 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TAUPE)
        canvas.drawString(doc.leftMargin, height - 9 * mm, "TECHPULSE  |  RESEARCH DOCUMENTATION")
        canvas.line(doc.leftMargin, 13 * mm, width - doc.rightMargin, 13 * mm)
        canvas.setFillColor(INK)
        canvas.drawRightString(width - doc.rightMargin, 8.5 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and getattr(flowable, "_toc_level", None) is not None:
            level = flowable._toc_level
            text = flowable.getPlainText()
            key = f"toc-{self.page}-{len(text)}-{hash(text)}"
            self.canv.bookmarkPage(key)
            # PDF outline levels are zero-based; Markdown heading levels are one-based.
            self.canv.addOutlineEntry(text, key, level=max(0, level - 1), closed=False)
            self.notify("TOCEntry", (level, text, self.page, key))


def styles_for_doc():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TPTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24, leading=30, textColor=INK, alignment=TA_LEFT, spaceAfter=14),
        "subtitle": ParagraphStyle("TPSubtitle", parent=base["Normal"], fontName="Helvetica", fontSize=12, leading=17, textColor=TAUPE, spaceAfter=10),
        "h1": ParagraphStyle("TPH1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=INK, spaceBefore=13, spaceAfter=8, keepWithNext=True),
        "h2": ParagraphStyle("TPH2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=TAUPE, spaceBefore=11, spaceAfter=6, keepWithNext=True),
        "h3": ParagraphStyle("TPH3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=INK, spaceBefore=8, spaceAfter=4, keepWithNext=True),
        "body": ParagraphStyle("TPBody", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=13.3, textColor=INK, spaceAfter=6, alignment=TA_LEFT),
        "bullet": ParagraphStyle("TPBullet", parent=base["BodyText"], fontName="Helvetica", fontSize=8.8, leading=12, textColor=INK, leftIndent=10, firstLineIndent=-7, spaceAfter=3),
        "code": ParagraphStyle("TPCode", fontName="Courier", fontSize=7, leading=8.7, textColor=INK, backColor=SURFACE, borderColor=TAUPE, borderWidth=0.3, borderPadding=7, leftIndent=4, rightIndent=4, spaceBefore=3, spaceAfter=8, splitLongWords=1),
        "quote": ParagraphStyle("TPQuote", parent=base["BodyText"], fontName="Helvetica-Oblique", fontSize=8.8, leading=12.5, textColor=INK, leftIndent=8, rightIndent=8, backColor=LINEN, borderColor=TAUPE, borderWidth=0.4, borderPadding=7, spaceBefore=4, spaceAfter=8),
        "toc_title": ParagraphStyle("TPTOCTitle", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=17, leading=22, textColor=INK, spaceAfter=12),
        "toc0": ParagraphStyle("TPTOC0", fontName="Helvetica-Bold", fontSize=9, leading=13, textColor=INK, leftIndent=0, firstLineIndent=0, spaceBefore=3),
        "toc1": ParagraphStyle("TPTOC1", fontName="Helvetica", fontSize=8, leading=11, textColor=TAUPE, leftIndent=13, firstLineIndent=0),
    }


def make_contents_flowable():
    toc = TableOfContents()
    toc.levelStyles = [styles_for_doc()["toc0"], styles_for_doc()["toc1"]]
    toc.dotsMinLevel = 0
    return toc


def md_to_story(md_path: Path, doc_title: str) -> list:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    styles = styles_for_doc()
    story: list = [Spacer(1, 32 * mm), Paragraph("TechPulse", styles["title"]), Paragraph(inline_markup(doc_title), styles["subtitle"]), Spacer(1, 5 * mm), Paragraph("KCA University - Bachelor of Science in Data Science", styles["body"]), Paragraph("Research documentation | 1 November 2026", styles["body"]), Spacer(1, 25 * mm), Paragraph("A practical guide to the current research prototype, its evidence and its limits.", styles["quote"]), PageBreak(), Paragraph("Contents", styles["toc_title"]), make_contents_flowable(), PageBreak()]
    i = 0
    skip_contents = False
    seen_main_title = False
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        if not line:
            i += 1
            continue
        if line.startswith("# ") and not seen_main_title:
            seen_main_title = True
            i += 1
            continue
        if line == "## Contents":
            skip_contents = True
            i += 1
            continue
        if skip_contents:
            if line.startswith("## "):
                skip_contents = False
            else:
                i += 1
                continue
        if line.startswith("<!-- AUTO:"):
            i += 1
            continue
        if line.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(clean_text(lines[i]))
                i += 1
            i += 1
            wrapped = "\n".join(textwrap.fill(s, width=100, subsequent_indent="    ", replace_whitespace=False, drop_whitespace=False) if len(s) > 105 else s for s in code_lines)
            story.append(Preformatted(wrapped, styles["code"], maxLineLength=105))
            continue
        image_match = re.match(r"!\[([^]]*)\]\(([^)]+)\)", line)
        if image_match:
            img_path = (md_path.parent / image_match.group(2)).resolve()
            if img_path.exists():
                img = Image(str(img_path))
                max_w, max_h = 500, 440
                scale = min(max_w / img.imageWidth, max_h / img.imageHeight, 1.0)
                img.drawWidth, img.drawHeight = img.imageWidth * scale, img.imageHeight * scale
                img.hAlign = "CENTER"
                story.extend([img, Paragraph(inline_markup(image_match.group(1)), styles["quote"]), Spacer(1, 4)])
            else:
                story.append(Paragraph("[Screenshot unavailable in this build]", styles["quote"]))
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+", cell or "-") for cell in row):
                    rows.append([Paragraph(inline_markup(cell), styles["body"]) for cell in row])
                i += 1
            if rows:
                cols = max(len(row) for row in rows)
                widths = [500 / cols] * cols
                table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0), LINEN), ("TEXTCOLOR", (0,0), (-1,-1), INK),
                    ("GRID", (0,0), (-1,-1), 0.35, TAUPE), ("VALIGN", (0,0), (-1,-1), "TOP"),
                    ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
                    ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, SURFACE]),
                ]))
                story.extend([table, Spacer(1, 6)])
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2)
            stylename = {1: "h1", 2: "h2", 3: "h3"}[level]
            p = Paragraph(inline_markup(text), styles[stylename])
            if level in (1,2):
                p._toc_level = 0 if level == 1 else 1
            story.append(p)
            i += 1
            continue
        if line.startswith("> "):
            story.append(Paragraph(inline_markup(line[2:]), styles["quote"]))
            i += 1
            continue
        if line.startswith("---"):
            story.append(Spacer(1, 6))
            i += 1
            continue
        if re.match(r"^[-*]\s+", line) or re.match(r"^\d+\.\s+", line):
            ordered = bool(re.match(r"^\d+\.\s+", line))
            items = []
            while i < len(lines):
                item_line = lines[i].strip()
                m = re.match(r"^(?:[-*]|\d+\.)\s+(.*)$", item_line)
                if not m:
                    break
                items.append(Paragraph(inline_markup(m.group(1)), styles["bullet"]))
                i += 1
            for number, item in enumerate(items, 1):
                prefix = f"{number}. " if ordered else "- "
                story.append(Paragraph(prefix + item.text, styles["bullet"]))
            story.append(Spacer(1, 3))
            continue
        # Join adjacent prose lines into one paragraph, preserving sentence boundaries.
        para = [line]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or nxt.startswith(("#", "|", "```", "> ", "![", "---")) or re.match(r"^(?:[-*]|\d+\.)\s+", nxt):
                break
            para.append(nxt)
            i += 1
        story.append(Paragraph(inline_markup(" ".join(para)), styles["body"]))
    return story


def build_pdf(md_path: Path, filename: str, title: str) -> None:
    output = DOCS / filename
    doc = TechPulseDoc(output, title)
    doc.multiBuild(md_to_story(md_path, title), maxPasses=5)
    print(f"created {output}")


def query_appendix() -> str:
    root = ROOT / "queries"
    files = sorted(root.rglob("query*.sql"), key=lambda path: int(re.search(r"query(\d+)", path.name).group(1)))
    sections = []
    for path in files:
        m = re.search(r"query(\d+)", path.name)
        number = int(m.group(1))
        title, purpose = QUERY_INFO.get(number, (path.stem, "Repository SQL query."))
        sql = path.read_text(encoding="utf-8").rstrip()
        sections.append(f"### Query {number:02d}: {title}\n\n**Research question:** {purpose}\n\n**Source file:** `{path.relative_to(ROOT).as_posix()}`\n\n**Expected output:** The query's selected aliases and records, depending on the source schema and filters. This is descriptive output, not a prediction.\n\n```sql\n{sql}\n```\n")
    if len(files) != 12:
        raise RuntimeError(f"Expected 12 SQL files, found {len(files)}")
    return "\n".join(sections)


def annotate_screenshot(source: str, target: str, points: list[tuple[float,float,str]]) -> None:
    path = SCREENSHOTS / source
    if not path.exists():
        return
    image = PILImage.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", max(19, image.width // 48))
    except OSError:
        font = ImageFont.load_default()
    radius = max(17, image.width // 45)
    for fx, fy, text in points:
        x, y = int(image.width * fx), int(image.height * fy)
        draw.ellipse((x-radius,y-radius,x+radius,y+radius), fill="#8B7D6B", outline="#FFFFFF", width=3)
        box = draw.textbbox((0,0), text, font=font)
        draw.text((x-(box[2]-box[0])/2,y-(box[3]-box[1])/2-2), text, fill="#FFFFFF", font=font)
    image.save(SCREENSHOTS / target, quality=95)


def main() -> None:
    tech = DOCS / "TechPulse_Technical_Reference.md"
    current = tech.read_text(encoding="utf-8")
    current = current.replace("<!-- AUTO:QUERY_APPENDIX -->", query_appendix())
    tech.write_text(current, encoding="utf-8")

    annotate_screenshot("02-technology-explorer.png", "demo-annotated-explorer.png", [(0.31,0.30,"1"),(0.32,0.45,"2"),(0.52,0.79,"3")])
    annotate_screenshot("05-prediction-explorer.png", "demo-annotated-prediction.png", [(0.31,0.43,"1"),(0.32,0.64,"2"),(0.68,0.52,"3")])
    annotate_screenshot("06-model-performance.png", "demo-annotated-model.png", [(0.31,0.31,"1"),(0.31,0.43,"2"),(0.34,0.59,"3")])

    index = ["# Redesigned application screenshot index", "", "Captured from the real TechPulse Streamlit app running at `http://127.0.0.1:8501` on 1 November 2026 using `scripts/capture_redesign_screenshots.py` with Microsoft Edge. The annotated variants are used in the five-minute demo guide.", "", "| File | Page/state | Evidence shown |", "|---|---|---|"]
    entries = [
        ("01-start-here.png","Start Here","purpose, data mode, record counts and artifact warnings"),
        ("02-technology-explorer.png","Technology Explorer","ActionScript search, saved row and matching activity trend"),
        ("03-technology-rankings.png","Technology Rankings","filters, saved risk indicator chart and table"),
        ("04-community-health.png","Community Health","observed question metrics, unanswered share and monthly trend"),
        ("05-prediction-explorer.png","Prediction Explorer","saved ActionScript class, probability chart, risk and signals"),
        ("06-model-performance.png","Model Performance & Validation","recorded metrics with split and baseline warnings"),
        ("07-methodology-data.png","Methodology & Data","source mode, six-table contract and validation notes"),
        ("08-about-user-guide.png","About & User Guide","quick navigation guide, glossary and FAQ"),
        ("demo-annotated-explorer.png","Annotated Explorer","numbered search, record and trend callouts"),
        ("demo-annotated-prediction.png","Annotated Prediction","numbered class, score and risk callouts"),
        ("demo-annotated-model.png","Annotated Model audit","numbered recorded-metric and caution callouts"),
    ]
    for name, page, description in entries:
        if (SCREENSHOTS / name).exists():
            index.append(f"| `{name}` | {page} | {description} |")
    (SCREENSHOTS / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")

    build_pdf(DOCS / "TechPulse_User_Manual.md", "TechPulse_User_Manual.pdf", "Beginner User Manual")
    build_pdf(tech, "TechPulse_Technical_Reference.pdf", "Technical Reference for Assessors")
    build_pdf(DOCS / "TechPulse_5_Minute_Demo_Guide.md", "TechPulse_5_Minute_Demo_Guide.pdf", "Five-Minute Assessor Demo Guide")


if __name__ == "__main__":
    main()
