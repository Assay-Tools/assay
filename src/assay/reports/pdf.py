"""PDF generation for Assay reports.

Converts markdown reports to branded PDFs matching the assay.tools design.
Uses markdown -> HTML -> WeasyPrint PDF pipeline.
"""

import logging
from pathlib import Path

import markdown
from weasyprint import HTML

logger = logging.getLogger(__name__)

# Brand colors from assay.tools
ASSAY_CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;
    @bottom-center {
        content: "assay.tools";
        font-size: 8pt;
        color: #6b7280;
    }
    @bottom-right {
        content: counter(page);
        font-size: 8pt;
        color: #6b7280;
    }
}

body {
    font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #e5e7eb;
    background: #0f1117;
}

h1 {
    font-size: 22pt;
    color: #ffffff;
    border-bottom: 3px solid #6366f1;
    padding-bottom: 8px;
    margin-top: 0;
    margin-bottom: 16px;
}

h2 {
    font-size: 15pt;
    color: #ffffff;
    border-bottom: 1px solid #374151;
    padding-bottom: 6px;
    margin-top: 28px;
    margin-bottom: 12px;
    page-break-after: avoid;
}

h3 {
    font-size: 12pt;
    color: #d1d5db;
    margin-top: 20px;
    margin-bottom: 8px;
    page-break-after: avoid;
}

p {
    margin-bottom: 10px;
    orphans: 3;
    widows: 3;
}

strong {
    color: #ffffff;
}

em {
    color: #9ca3af;
}

a {
    color: #6366f1;
    text-decoration: none;
}

hr {
    border: none;
    border-top: 1px solid #242836;
    margin: 24px 0;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}

th {
    background: #1a1d27;
    color: #d1d5db;
    font-weight: 600;
    text-align: left;
    padding: 8px 12px;
    border: 1px solid #374151;
}

td {
    padding: 7px 12px;
    border: 1px solid #242836;
    color: #e5e7eb;
}

tr:nth-child(even) td {
    background: #13151d;
}

tr:nth-child(odd) td {
    background: #0f1117;
}

/* Lists */
ul, ol {
    margin-bottom: 10px;
    padding-left: 24px;
}

li {
    margin-bottom: 4px;
}

/* Blockquotes (used for security notes) */
blockquote {
    border-left: 3px solid #6366f1;
    margin: 12px 0;
    padding: 8px 16px;
    background: #1a1d27;
    border-radius: 0 6px 6px 0;
    color: #d1d5db;
    font-size: 9.5pt;
}

/* Code */
code {
    background: #1a1d27;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 9pt;
    color: #a5b4fc;
}

pre {
    background: #1a1d27;
    padding: 12px 16px;
    border-radius: 6px;
    border: 1px solid #242836;
    overflow-x: auto;
    font-size: 9pt;
    page-break-inside: avoid;
}

pre code {
    background: none;
    padding: 0;
}

/* Score styling - make Excellent/Good/etc visually distinct */
td:last-child {
    font-weight: 500;
}
"""


def markdown_to_pdf(markdown_text: str, output_path: Path) -> Path:
    """Convert a markdown report to a branded PDF.

    Args:
        markdown_text: The complete markdown report content.
        output_path: Where to write the PDF. If it ends in .md, the extension
            is replaced with .pdf.

    Returns:
        Path to the generated PDF file.
    """
    # Ensure .pdf extension
    if output_path.suffix == ".md":
        output_path = output_path.with_suffix(".pdf")

    # Convert markdown to HTML
    html_body = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code"],
    )

    # Wrap in full HTML document with brand CSS
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

    # Generate PDF
    HTML(string=html_doc).write_pdf(str(output_path))

    logger.info("PDF generated: %s", output_path)
    return output_path
