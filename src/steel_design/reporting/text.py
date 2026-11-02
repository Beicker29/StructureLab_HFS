"""The report as plain text."""
from .glossary import STATUS_TEXT, fmt


def _text_table(headers, rows) -> list[str]:
    cells = [[str(h) for h in headers]] + [[fmt(v) for v in row] for row in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(headers))]
    line = lambda row: "  ".join(c.ljust(w) for c, w in zip(row, widths)).rstrip()  # noqa: E731
    return [line(cells[0]), "  ".join("-" * w for w in widths)] + [line(r) for r in cells[1:]]


def render_text(blocks: list[dict]) -> str:
    out = []
    for b in blocks:
        kind = b["kind"]
        if kind == "title":
            out.append(f"# Memoria de cálculo — {b['action']} {b['member']}"
                       + (f" · {b['case']}" if b.get("case") else ""))
            out += [f"{k}: {v}" for k, v in b["meta"]]
            out += ["", f"RESULTADO: {b['status']} ({STATUS_TEXT[b['status']]})"
                    + (f"   Demanda/capacidad máx. = {fmt(b['ratio'])}" if b["ratio"] is not None else "")]
        elif kind == "summary":
            out.append("  |  ".join(f"{title} {', '.join(lines)}" for title, lines in b["items"]))
        elif kind == "h1":
            out += ["", f"## {b['text']}"]
        elif kind == "h2":
            out += ["", f"### {b['text']}"]
        elif kind == "h3":
            out += ["", f"#### {b['text']}"]
        elif kind == "kv":
            out += [("  " if b.get("compact") else "") + f"{k}: {v}" for k, v in b["items"]]
        elif kind == "table":
            out += _text_table(b["headers"], b["rows"])
        elif kind == "p":
            out.append(b["text"])
        elif kind == "note":
            out.append(f"- {b['text']}")
        elif kind == "alert":
            out.append(f"! {b['text']}" + (f"\n  Detalle: {b['detail']}" if b.get("detail") else ""))
    return "\n".join(out) + "\n"
