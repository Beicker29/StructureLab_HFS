"""Calculation report (memoria de cálculo) of one member, from the results of all its load cases: plain text and PDF.

Presentation only: every value comes from the engine result; nothing is recomputed. Each review shows the load case
with the largest DCR. document.report_blocks() builds one neutral document model (title, summary, headings, key-value lists,
tables, notes); text.render_text() and pdf.pdf_bytes() draw that same model.
"""
