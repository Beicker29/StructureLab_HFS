"""The report as PDF, drawn from the document model. Requires fpdf2 ([pdf] extra)."""
import logging
import math
from pathlib import Path

from .glossary import STATUS_TEXT, fmt

_INK, _MUTED, _RULE, _NAVY = (31, 41, 55), (107, 114, 128), (209, 213, 219), (23, 50, 84)
_HEAD_FILL, _ZEBRA, _CARD, _HIGHLIGHT = (234, 239, 245), (248, 250, 252), (243, 246, 250), (255, 248, 225)
_STATUS_COLOR = {"PASS": (46, 125, 50), "FAIL": (183, 28, 28), "INCOMPLETE": (178, 106, 0)}
_FONT_CANDIDATES = [  # (regular, bold); first pair found on this machine is embedded
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
]
_LATIN1 = {"φ": "phi", "λ": "lambda", "Σ": "sum", "≤": "<=", "→": "->", "—": "-", "–": "-",
           "−": "-", "²": "2", "⁴": "4", "⁶": "6", "r̄o": "ro", "α": "alpha"}


def _column_widths(minimums: list[float], weights: list[float], total: float) -> list[float]:
    """Column widths (mm): each one holds its longest word; what remains is shared by weight. A word breaks only if they exceed
    the total."""
    spare = total - sum(minimums)
    if spare <= 0:
        return [total * m / sum(minimums) for m in minimums]
    return [m + spare * w / sum(weights) for m, w in zip(minimums, weights)]
_HEADINGS = {"h1": (12, 4), "h2": (10, 2.5), "h3": (8.8, 1.5)}


def _axis_scale(largest: float) -> tuple[float, float]:
    """Round axis maximum and step, about four intervals: 1, 2, 2.5 or 5 times a power of ten."""
    raw = (largest or 1.0) / 4
    power = 10 ** math.floor(math.log10(raw))
    step = next(s * power for s in (1, 2, 2.5, 5, 10) if s * power >= raw)
    return step * math.ceil(largest / step + 1e-9) if largest else step * 4, step


class _Renderer:
    """One PDF: each kind of block has its own method."""

    def __init__(self, FPDF, FontFace):
        renderer = self
        self.font_face = FontFace

        class Report(FPDF):
            member = ""

            def header(self):
                if self.page_no() == 1 or self.member is None:
                    return
                self.set_font(renderer.font, "", 7.5)
                self.set_text_color(*_MUTED)
                self.cell(0, 5, renderer.clean(f"Memoria de cálculo — {self.member}"), new_x="LMARGIN", new_y="NEXT")
                self.set_draw_color(*_RULE)
                self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
                self.ln(4)

            def footer(self):
                self.set_y(-12)
                self.set_draw_color(*_RULE)
                self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
                self.set_font(renderer.font, "", 7.5)
                self.set_text_color(*_MUTED)
                self.cell(0, 6, renderer.clean("StructureLab_HFS · ANSI/AISC 360-22"))
                self.cell(0, 6, f"{self.page_no()} / {{nb}}", align="R")

        self.pdf = pdf = Report(format="A4")
        pdf.set_margins(18, 16, 18)
        pdf.set_auto_page_break(True, margin=18)
        self.font = "Helvetica"
        self.unicode_font = next(((r, b) for r, b in _FONT_CANDIDATES if Path(r).is_file() and Path(b).is_file()), None)
        if self.unicode_font:
            pdf.add_font("Body", "", self.unicode_font[0])
            pdf.add_font("Body", "B", self.unicode_font[1])
            self.font = "Body"

    def clean(self, text: str) -> str:
        if self.unicode_font:
            return text
        for k, v in _LATIN1.items():
            text = text.replace(k, v)
        return text.encode("latin-1", "replace").decode("latin-1")

    def width(self):
        return self.pdf.w - self.pdf.l_margin - self.pdf.r_margin

    def heading(self, text, size, space):
        pdf, FONT, clean = self.pdf, self.font, self.clean
        if pdf.get_y() > pdf.h - (85 if size >= 11 else 60):   # keep a heading with its first lines; a chapter also with its subheading
            pdf.add_page()
        pdf.ln(space)
        pdf.set_font(FONT, "B", size)
        pdf.set_text_color(*(_NAVY if size >= 9.5 else _INK))
        pdf.multi_cell(0, size * 0.5, clean(text), new_x="LMARGIN", new_y="NEXT")
        if size >= 11:
            pdf.set_draw_color(*_NAVY)
            pdf.set_line_width(0.4)
            pdf.line(pdf.l_margin, pdf.get_y() + 0.8, pdf.l_margin + 14, pdf.get_y() + 0.8)
            pdf.set_line_width(0.2)
            pdf.ln(3)
        else:
            pdf.ln(1)

    def chart(self, b):
        """P-M diagram: thin lines, one axis, legend for the two series, direct labels on the nominal points only."""
        pdf, FONT, clean = self.pdf, self.font, self.clean
        w, h = 120.0, 70.0
        if pdf.get_y() + h + 22 > pdf.h - pdf.b_margin:
            pdf.add_page()
        x0, y0 = pdf.l_margin + 16, pdf.get_y() + 12
        all_points = [q for series in b["series"] for q in series["points"]]
        demand = b.get("demand")
        top_x, step_x = _axis_scale(max([q[0] for q in all_points] + ([demand[0]] if demand else [])))
        top_y, step_y = _axis_scale(max([q[1] for q in all_points] + ([demand[1]] if demand else [])))
        to_xy = lambda m, p: (x0 + m / top_x * w, y0 + h - p / top_y * h)  # noqa: E731
        pdf.set_font(FONT, "B", 8)
        pdf.set_text_color(*_INK)
        pdf.set_xy(pdf.l_margin, y0 - 11)
        pdf.cell(w + 16, 4, clean(b["title"]))
        pdf.set_font(FONT, "", 7)
        pdf.set_text_color(*_MUTED)
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.1)
        for i in range(round(top_y / step_y) + 1):
            gy = y0 + h - i * step_y / top_y * h
            pdf.line(x0, gy, x0 + w, gy)
            pdf.set_xy(x0 - 15, gy - 2)
            pdf.cell(14, 4, f"{i * step_y:g}", align="R")
        for i in range(round(top_x / step_x) + 1):
            gx = x0 + i * step_x / top_x * w
            pdf.set_xy(gx - 10, y0 + h + 0.5)
            pdf.cell(20, 4, f"{i * step_x:g}", align="C")
        pdf.set_xy(x0, y0 + h + 4.5)
        pdf.cell(w, 4, clean(b["x_label"]), align="C")
        pdf.set_xy(pdf.l_margin, y0 - 7)
        pdf.cell(30, 3, clean(b["y_label"]))
        pdf.set_draw_color(*_MUTED)
        pdf.line(x0, y0, x0, y0 + h)
        pdf.line(x0, y0 + h, x0 + w, y0 + h)
        colors = {True: (42, 120, 214), False: (235, 104, 52)}             # first two hues of the validated palette
        for series in b["series"]:
            color = colors[series["dash"]]
            pdf.set_draw_color(*color)
            pdf.set_fill_color(*color)
            pdf.set_line_width(0.5)
            if series["dash"]:
                pdf.set_dash_pattern(dash=1.6, gap=1.0)
            line = [to_xy(q[0], q[1]) for q in series["points"]]
            for a, c in zip(line, line[1:]):
                pdf.line(a[0], a[1], c[0], c[1])
            pdf.set_dash_pattern()
            pdf.set_font(FONT, "", 7.5)
            pdf.set_text_color(*_INK)
            for (x, y), q in zip(line, series["points"]):
                pdf.ellipse(x - 0.8, y - 0.8, 1.6, 1.6, style="F")
                if q[2]:
                    pdf.set_xy(x + 0.8, y - 4.2)
                    pdf.cell(4, 3.5, q[2])
        legend_y = y0 + h + 9
        cursor = x0
        pdf.set_font(FONT, "", 7.5)
        pdf.set_text_color(*_INK)
        for series in b["series"]:
            pdf.set_draw_color(*colors[series["dash"]])
            pdf.set_line_width(0.5)
            if series["dash"]:
                pdf.set_dash_pattern(dash=1.6, gap=1.0)
            pdf.line(cursor, legend_y + 2, cursor + 7, legend_y + 2)
            pdf.set_dash_pattern()
            pdf.set_xy(cursor + 8, legend_y)
            label = clean(series["name"])
            pdf.cell(pdf.get_string_width(label) + 1, 4, label)
            cursor += pdf.get_string_width(label) + 13
        if demand:
            mx, my = to_xy(demand[0], demand[1])
            pdf.set_fill_color(*_INK)
            pdf.set_draw_color(255, 255, 255)
            pdf.set_line_width(0.3)
            pdf.ellipse(mx - 1.2, my - 1.2, 2.4, 2.4, style="DF")
            pdf.set_xy(mx + 1.4, my - 1.8)
            pdf.cell(16, 3.5, "(Mu, Pu)")
            pdf.ellipse(cursor, legend_y + 0.9, 2.2, 2.2, style="DF")
            pdf.set_xy(cursor + 3, legend_y)
            pdf.cell(25, 4, "Demanda (Mu, Pu)")
        pdf.set_line_width(0.2)
        pdf.set_draw_color(*_RULE)
        pdf.set_xy(pdf.l_margin, legend_y + 7)

    def table(self, headers, rows, highlight=None, compact=False, kv=False):
        pdf, FONT, clean, FontFace, width = self.pdf, self.font, self.clean, self.font_face, self.width
        texts = [[clean(fmt(v)) for v in row] for row in rows]
        if len(rows) <= 12 and pdf.get_y() + (len(rows) + 1) * 6.5 > pdf.h - pdf.b_margin:
            pdf.add_page()
        # Wide enough for the longest word of the column, with a cap so that a long cell does not squeeze the others.
        cap = max(14, 150 // len(headers))
        weights = [max(8, max((len(w) for w in " ".join([str(h)] + [r[i] for r in texts]).split()), default=1),
                       min(max([len(str(h))] + [len(r[i]) for r in texts]), cap)) + 2 for i, h in enumerate(headers)]
        numeric = [all(isinstance(r[i], (int, float)) for r in rows) for i in range(len(headers))]
        pdf.set_font(FONT, "", 8.5 if not compact else 8)
        pdf.set_text_color(*_INK)
        pdf.set_draw_color(*_RULE)
        fill = _CARD if kv else _ZEBRA
        pdf.set_fill_color(*fill)  # never inherit a previous fill (status badge, cards)
        natural = sum(weights) * 2.1  # mm, about one character of 8.5 pt per weight unit
        pdf.set_font(FONT, "B", 8.5)  # headings and the highlighted row are bold, so the widest case
        minimums = [
            max(pdf.get_string_width(word) for word in " ".join([clean(str(h))] + [r[i] for r in texts]).split() or [""]) + 3.2 + 0.6
            for i, h in enumerate(headers)
        ]
        pdf.set_font(FONT, "", 8.5 if not compact else 8)
        total = min(width(), max(natural, 70, sum(minimums)))
        style = dict(width=total, col_widths=_column_widths(minimums, weights, total), line_height=5.2, padding=(1, 1.6),
                     text_align=["RIGHT" if n else "LEFT" for n in numeric], align="LEFT",
                     cell_fill_color=fill)
        if kv:
            style.update(width=width(), borders_layout="NONE", first_row_as_headings=False, col_widths=(28, 72),
                         cell_fill_mode="ALL")
        else:
            style.update(borders_layout="HORIZONTAL_LINES", cell_fill_mode="ROWS",
                         headings_style=FontFace(emphasis="BOLD", color=_NAVY, fill_color=_HEAD_FILL),
                         repeat_headings=1)
        with pdf.table(**style) as t:
            if not kv:
                head = t.row()
                for h in headers:
                    head.cell(clean(h))
            for i, row in enumerate(texts):
                r = t.row()
                for j, cell in enumerate(row):
                    if kv and j == 0:
                        r.cell(cell, style=FontFace(color=_MUTED))
                    elif i == highlight:
                        r.cell(cell, style=FontFace(emphasis="BOLD", fill_color=_HIGHLIGHT))
                    else:
                        r.cell(cell)
        pdf.ln(2)

    def keep_headings_with_table(self, blocks, index):
        """Headings go to the next page with the short table that they announce, which table() would move there alone."""
        pdf = self.pdf
        needed, following = 0.0, index
        while following < len(blocks) and blocks[following]["kind"] in {"h1", "h2", "h3"}:
            needed += {"h1": 16.0, "h2": 10.0, "h3": 8.0}[blocks[following]["kind"]]
            following += 1
        short_table = following < len(blocks) and blocks[following]["kind"] == "table" and len(blocks[following]["rows"]) <= 12
        rows = (len(blocks[following]["rows"]) + 1) * 6.5 if short_table else 0.0
        if pdf.get_y() + needed + rows > pdf.h - pdf.b_margin or pdf.get_y() + needed > pdf.h - 60:
            pdf.add_page()

    def title(self, b):
        pdf, FONT, clean, width = self.pdf, self.font, self.clean, self.width
        pdf.member = b["member"] + (f" · {b['case']}" if b.get("case") else "")
        pdf.set_fill_color(*_NAVY)
        pdf.rect(0, 0, pdf.w, 4, style="F")
        pdf.set_y(14)
        pdf.set_font(FONT, "", 9)
        pdf.set_text_color(*_MUTED)
        pdf.multi_cell(width() - 42, 4.2, clean(f"MEMORIA DE CÁLCULO · {b['action'].upper()}"), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(FONT, "B", 18)
        pdf.set_text_color(*_NAVY)
        pdf.multi_cell(width() - 42, 9, clean(b["member"]), new_x="LMARGIN", new_y="NEXT")
        if b.get("case"):
            pdf.set_font(FONT, "", 10.5)
            pdf.set_text_color(*_INK)
            pdf.multi_cell(width() - 42, 5.5, clean(b["case"]), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)
        title_bottom = pdf.get_y()                           # the status badge below moves the cursor
        color = _STATUS_COLOR[b["status"]]
        pdf.set_fill_color(*color)
        pdf.rect(pdf.w - pdf.r_margin - 38, 19, 38, 10, style="F", round_corners=True, corner_radius=2)
        pdf.set_xy(pdf.w - pdf.r_margin - 38, 19)
        pdf.set_font(FONT, "B", 10)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(38, 10, clean(STATUS_TEXT[b["status"]]), align="C")
        pdf.set_xy(pdf.l_margin, max(title_bottom, 31) + 2)
        pdf.set_font(FONT, "", 8.5)
        pdf.set_text_color(*_MUTED)
        for key, value in b["meta"]:
            pdf.multi_cell(0, 4.5, clean(f"{key}: {value}"), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*_RULE)
        pdf.line(pdf.l_margin, pdf.get_y() + 2, pdf.w - pdf.r_margin, pdf.get_y() + 2)
        pdf.ln(6)

    def summary(self, b):
        pdf, FONT, clean, width = self.pdf, self.font, self.clean, self.width
        gap, n = 3, min(len(b["items"]), 3)                  # at most three cards per row
        card_w, y = (width() - gap * (n - 1)) / n, pdf.get_y()
        pdf.set_font(FONT, "", 7.5)
        labels = [pdf.multi_cell(card_w - 6, 3.4, clean(label), dry_run=True, output="LINES") for label, _ in b["items"]]
        for start in range(0, len(b["items"]), n):           # each row as tall as its longest label
            label_h = 3.4 * max(len(lines) for lines in labels[start:start + n])
            height = label_h + 5.0 + 5.0 * max(len(values) for _, values in b["items"][start:start + n])
            for i, (_, values) in enumerate(b["items"][start:start + n]):
                x = pdf.l_margin + i * (card_w + gap)
                pdf.set_fill_color(*_CARD)
                pdf.rect(x, y, card_w, height, style="F", round_corners=True, corner_radius=1.5)
                pdf.set_font(FONT, "", 7.5)
                pdf.set_text_color(*_MUTED)
                for row, line in enumerate(labels[start + i]):
                    pdf.set_xy(x + 3, y + 2 + row * 3.4)
                    pdf.cell(card_w - 6, 3.4, line)
                size = 10.5
                pdf.set_font(FONT, "B", size)
                while max(pdf.get_string_width(clean(value)) for value in values) > card_w - 6 and size > 6:
                    size -= 0.5
                    pdf.set_font(FONT, "B", size)
                pdf.set_text_color(*_INK)
                for row, value in enumerate(values):
                    pdf.set_xy(x + 3, y + 3 + label_h + row * 5.0)
                    pdf.cell(card_w - 6, 5.0, clean(value))
            y += height + 3
        pdf.set_xy(pdf.l_margin, y + 1)

    def paragraph(self, b, kind):
        pdf, FONT, clean = self.pdf, self.font, self.clean
        pdf.set_font(FONT, "", 8.5 if kind == "p" else 8)
        pdf.set_text_color(*(_INK if kind == "p" else _MUTED))
        text = clean(("•  " if kind == "note" else "") + b["text"])
        pdf.multi_cell(0, 4.6, text, align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def alert(self, b):
        pdf, FONT, clean = self.pdf, self.font, self.clean
        pdf.set_fill_color(255, 243, 224)
        pdf.set_draw_color(*_STATUS_COLOR["INCOMPLETE"])
        pdf.set_font(FONT, "B", 8.5)
        pdf.set_text_color(*_INK)
        text = b["text"] + (f"\nDetalle: {b['detail']}" if b.get("detail") else "")
        pdf.multi_cell(0, 4.8, clean(text), border="L", fill=True, padding=2.5, align="L",
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def draw(self, blocks: list[dict]):
        self.pdf.member = None
        self.pdf.add_page()
        for index, b in enumerate(blocks):
            kind = b["kind"]
            if kind in _HEADINGS and blocks[index - 1]["kind"] not in _HEADINGS:
                self.keep_headings_with_table(blocks, index)
            if kind in _HEADINGS:
                self.heading(b["text"], *_HEADINGS[kind])
            elif kind == "title":
                self.title(b)
            elif kind == "summary":
                self.summary(b)
            elif kind == "kv":
                self.table(["", ""], [list(item) for item in b["items"]], kv=True, compact=b.get("compact", False))
            elif kind == "table":
                self.table(b["headers"], b["rows"], highlight=b.get("highlight"))
            elif kind in {"p", "note"}:
                self.paragraph(b, kind)
            elif kind == "chart":
                self.chart(b)
            elif kind == "alert":
                self.alert(b)


def pdf_bytes(documents: list[list[dict]]) -> bytes:
    """PDF in memory from report_blocks() documents (one page sequence each). Requires fpdf2 ([pdf] extra)."""
    try:
        from fpdf import FPDF
        from fpdf.fonts import FontFace
    except ImportError as exc:
        raise RuntimeError('PDF output requires fpdf2: pip install -e ".[pdf]"') from exc
    logging.getLogger("fontTools").setLevel(logging.ERROR)  # font subsetting chatter
    renderer = _Renderer(FPDF, FontFace)
    for blocks in documents:
        renderer.draw(blocks)
    return bytes(renderer.pdf.output())
