"""PDF generation for Assay reports.

Converts markdown reports to branded PDFs matching the assay.tools design.
Uses markdown -> HTML -> WeasyPrint PDF pipeline.
"""

import logging
from pathlib import Path

import markdown
from weasyprint import HTML

logger = logging.getLogger(__name__)


ASSAY_CSS = """\
/* ==========================================================================
   Page setup
   The page has a dark background edge-to-edge. A top header bar and bottom
   footer bar are rendered via @page margin boxes. Content sits in the middle
   with generous padding.
   ========================================================================== */

@page {
    size: A4;
    margin: 48pt 0 42pt 0;
    background: #0f1117;

    /* ---- Top bar: brand mark ---- */
    @top-left {
        content: "\\25C6  Assay";
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 8pt;
        font-weight: 600;
        color: #6366f1;
        background: #0f1117;
        padding: 0 0 0 48pt;
        margin: 0;
        border-bottom: 0.5pt solid #1e2231;
        display: block;
        width: 100%;
    }
    @top-right {
        content: string(section-title);
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 7.5pt;
        font-style: italic;
        color: #4b5563;
        background: #0f1117;
        padding: 0 48pt 0 0;
        margin: 0;
        border-bottom: 0.5pt solid #1e2231;
    }

    /* ---- Bottom bar: site + page number ---- */
    @bottom-left {
        content: "assay.tools  \\2014  The quality layer for agentic software";
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 7pt;
        color: #4b5563;
        background: #0f1117;
        padding: 0 0 0 48pt;
        margin: 0;
        border-top: 0.5pt solid #1e2231;
    }
    @bottom-right {
        content: "Page " counter(page);
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 7pt;
        color: #4b5563;
        background: #0f1117;
        padding: 0 48pt 0 0;
        margin: 0;
        border-top: 0.5pt solid #1e2231;
    }
}

/* First page: no section title in header */
@page :first {
    @top-right {
        content: none;
        border-bottom: 0.5pt solid #1e2231;
        background: #0f1117;
    }
}

/* ==========================================================================
   Base typography
   ========================================================================== */

body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 9.5pt;
    line-height: 1.7;
    color: #d1d5db;
    background: #0f1117;
    margin: 0;
    padding: 20pt 48pt 24pt 48pt;
}

/* ==========================================================================
   Headings
   ========================================================================== */

h1 {
    font-size: 24pt;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.02em;
    margin: 0 0 6pt 0;
    padding-bottom: 14pt;
    border-bottom: 2.5pt solid #6366f1;
}

h2 {
    font-size: 16pt;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: -0.01em;
    margin-top: 0;
    margin-bottom: 16pt;
    padding-top: 8pt;
    padding-bottom: 10pt;
    border-bottom: 1pt solid #242836;
    page-break-before: always;
    page-break-after: avoid;
    string-set: section-title content();
}

/* Suppress page break on the first h2 (it follows h1 on page 1) */
body > h2:first-of-type {
    page-break-before: avoid;
}

h3 {
    font-size: 11.5pt;
    font-weight: 600;
    color: #e5e7eb;
    margin-top: 18pt;
    margin-bottom: 8pt;
    page-break-after: avoid;
}

h4 {
    font-size: 10pt;
    font-weight: 600;
    color: #d1d5db;
    margin-top: 14pt;
    margin-bottom: 6pt;
    page-break-after: avoid;
}

/* ==========================================================================
   Body elements
   ========================================================================== */

p {
    margin: 0 0 10pt 0;
    orphans: 3;
    widows: 3;
}

strong {
    color: #ffffff;
    font-weight: 600;
}

em {
    color: #9ca3af;
}

a {
    color: #818cf8;
    text-decoration: none;
}

/* HRs in the markdown are section dividers — hide them, page breaks handle it */
hr {
    display: none;
}

/* ==========================================================================
   Tables
   ========================================================================== */

table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin: 14pt 0 18pt 0;
    font-size: 9pt;
    page-break-inside: avoid;
    border: 1pt solid #1e2231;
    border-radius: 6pt;
    overflow: hidden;
}

thead {
    page-break-after: avoid;
}

th {
    background: #161927;
    color: #9ca3af;
    font-weight: 600;
    font-size: 7.5pt;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    text-align: left;
    padding: 10pt 14pt;
    border-bottom: 1pt solid #242836;
}

td {
    padding: 9pt 14pt;
    color: #d1d5db;
    border-bottom: 1pt solid #1a1d27;
}

tr:nth-child(even) td {
    background: #12141c;
}

tr:nth-child(odd) td {
    background: #0f1117;
}

tr:last-child td {
    border-bottom: none;
}

/* Label column */
td:first-child {
    color: #9ca3af;
    font-weight: 500;
}

/* Score value column */
td:nth-child(2) {
    color: #ffffff;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

/* Rating column */
td:last-child {
    font-weight: 600;
}

/* ==========================================================================
   Lists
   ========================================================================== */

ul, ol {
    margin: 6pt 0 14pt 0;
    padding-left: 20pt;
    page-break-inside: avoid;
}

li {
    margin-bottom: 5pt;
    line-height: 1.6;
}

li::marker {
    color: #6366f1;
}

/* ==========================================================================
   Blockquotes
   ========================================================================== */

blockquote {
    margin: 14pt 0;
    padding: 14pt 18pt;
    background: #161927;
    border-left: 3pt solid #6366f1;
    border-radius: 0 6pt 6pt 0;
    color: #d1d5db;
    font-size: 9pt;
    line-height: 1.65;
    page-break-inside: avoid;
}

blockquote p {
    margin: 0;
}

/* ==========================================================================
   Code
   ========================================================================== */

code {
    background: #161927;
    padding: 2pt 5pt;
    border-radius: 3pt;
    font-size: 8.5pt;
    color: #a5b4fc;
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
}

pre {
    background: #161927;
    padding: 14pt 18pt;
    border-radius: 6pt;
    border: 1pt solid #1e2231;
    font-size: 8.5pt;
    line-height: 1.5;
    page-break-inside: avoid;
}

pre code {
    background: none;
    padding: 0;
    border-radius: 0;
}

/* ==========================================================================
   Special elements
   ========================================================================== */

/* Subtitle lines under h1 */
h1 + p em {
    font-size: 8.5pt;
    color: #6b7280;
    display: block;
    margin-top: 4pt;
}

/* Footer disclaimer text at end of document */
body > p:last-child,
body > p:nth-last-child(2),
body > p:nth-last-child(3),
body > p:nth-last-child(4) {
    font-size: 8pt;
    color: #4b5563;
    line-height: 1.5;
}

/* Rating color classes — applied by post-processing */
.score-excellent { color: #34d399; }
.score-good { color: #fbbf24; }
.score-fair { color: #fb923c; }
.score-poor { color: #f87171; }
.score-na { color: #6b7280; }
"""


def _post_process_html(html: str) -> str:
    """Enhance the raw markdown-generated HTML for better PDF rendering."""
    # Color-code rating cells
    rating_colors = {
        "Excellent": "score-excellent",
        "Good": "score-good",
        "Fair": "score-fair",
        "Poor": "score-poor",
        "N/A": "score-na",
    }
    for rating, css_class in rating_colors.items():
        html = html.replace(
            f"<td>{rating}</td>",
            f'<td class="{css_class}">{rating}</td>',
        )

    return html


def markdown_to_pdf(markdown_text: str, output_path: Path) -> Path:
    """Convert a markdown report to a branded PDF.

    Args:
        markdown_text: The complete markdown report content.
        output_path: Where to write the PDF. If it ends in .md, the extension
            is replaced with .pdf.

    Returns:
        Path to the generated PDF file.
    """
    if output_path.suffix == ".md":
        output_path = output_path.with_suffix(".pdf")

    html_body = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code"],
    )

    html_body = _post_process_html(html_body)

    html_doc = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>{ASSAY_CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    HTML(string=html_doc).write_pdf(str(output_path))

    logger.info("PDF generated: %s", output_path)
    return output_path
