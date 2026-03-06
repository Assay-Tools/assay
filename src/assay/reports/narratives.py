"""AI narrative generation for package reports.

Uses Claude Opus to write analysis narratives grounded in the package's
structured data. The AI receives the partially-rendered report (with all
scores and tables filled in) and writes only the narrative sections.

This ensures narratives reference the exact same numbers visible in the
report — no hallucinated scores or invented facts.
"""

import logging
import re

from anthropic import Anthropic

from assay.config import settings

logger = logging.getLogger(__name__)

REPORT_MODEL = "claude-opus-4-6"

# ---------------------------------------------------------------------------
# System prompts — one per report type
# ---------------------------------------------------------------------------

BRIEF_SYSTEM_PROMPT = """\
You are a senior technical analyst writing for Assay, the independent quality \
rating platform for agentic software. You are writing narrative sections for \
a Package Brief — a concise, actionable report that helps someone decide \
whether to adopt this package for agent use.

CRITICAL RULES:
1. Base your analysis SOLELY on the data provided in the report. Do not \
reference information from your training data about this package's history, \
outages, controversies, or features not reflected in the scores.
2. When referencing scores, use the EXACT values from the tables in the report.
3. Be direct, honest, and useful. If a package has problems, say so clearly.
4. Write in a professional but accessible tone — no marketing fluff.
5. Keep narratives concise. This is a brief, not an essay.

You will receive a partially-rendered report with {{NARRATIVE: ...}} and \
{{RECOMMENDATION: ...}} placeholders. For each placeholder, write the \
requested content. Return your response as a JSON object where keys are the \
placeholder identifiers (NARRATIVE_1, NARRATIVE_2, etc.) and values are the \
markdown text to insert."""

FULL_REPORT_SYSTEM_PROMPT = """\
You are a senior technical analyst writing for Assay, the independent quality \
rating platform for agentic software. You are writing narrative sections for \
a Full Evaluation Report — a comprehensive technical deep-dive worth $99.

CRITICAL RULES:
1. Base your analysis SOLELY on the data provided in the report. Do not \
reference information from your training data about this package's history, \
outages, controversies, or features not reflected in the scores.
2. When referencing scores, use the EXACT values from the tables in the report.
3. Be direct, honest, and intellectually rigorous. Customers pay for candor, \
not flattery. If something is bad, explain why and what to do about it.
4. Write in a professional, authoritative tone appropriate for a paid \
technical report.
5. Provide genuinely actionable analysis — specific enough that someone could \
hand this to an engineer and they'd know what to do.
6. When making improvement recommendations, include projected score impact \
where the data supports it.

You will receive a partially-rendered report with {{NARRATIVE: ...}} and \
{{RECOMMENDATION: ...}} placeholders. For each placeholder, write the \
requested content. Return your response as a JSON object where keys are the \
placeholder identifiers (NARRATIVE_1, NARRATIVE_2, etc.) and values are the \
markdown text to insert.

Make the Full Evaluation Report worth every penny. The customer is paying for \
depth, specificity, and honest expert analysis they can't get anywhere else."""


def generate_narratives(
    report_markdown: str,
    report_type: str = "report",
) -> str:
    """Fill narrative placeholders in a report using Claude Opus.

    Args:
        report_markdown: The partially-rendered report with {{NARRATIVE: ...}}
            and {{RECOMMENDATION: ...}} placeholders still present.
        report_type: "brief" or "report" — determines system prompt and depth.

    Returns:
        The report with all placeholders replaced by AI-generated narratives.
    """
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — returning report without narratives")
        return _strip_placeholders(report_markdown)

    # Find all placeholders and assign IDs
    placeholders = re.findall(r"\{\{(NARRATIVE|RECOMMENDATION):.*?\}\}", report_markdown)
    if not placeholders:
        logger.info("No narrative placeholders found — report is already complete")
        return report_markdown

    # Number them for structured response
    placeholder_map = {}
    for i, match in enumerate(re.finditer(r"\{\{(NARRATIVE|RECOMMENDATION):.*?\}\}", report_markdown)):
        key = f"{match.group(1)}_{i + 1}"
        placeholder_map[key] = match.group(0)

    # Build user prompt with numbered placeholders
    numbered = report_markdown
    for i, match in enumerate(re.finditer(r"\{\{(NARRATIVE|RECOMMENDATION):.*?\}\}", report_markdown)):
        original = match.group(0)
        key = f"{match.group(1)}_{i + 1}"
        # Add the key label before the placeholder so the AI knows which is which
        numbered = numbered.replace(
            original,
            f"[{key}] {original}",
            1,
        )

    system_prompt = FULL_REPORT_SYSTEM_PROMPT if report_type == "report" else BRIEF_SYSTEM_PROMPT
    user_prompt = (
        "Here is the partially-rendered report. Fill in all placeholders.\n\n"
        f"{numbered}\n\n"
        "Return a JSON object with keys matching the [IDENTIFIER] labels "
        "(e.g., NARRATIVE_1, RECOMMENDATION_3) and values containing the "
        "markdown text to insert. Return ONLY valid JSON, no markdown fences."
    )

    client = Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.messages.create(
            model=REPORT_MODEL,
            max_tokens=4096 if report_type == "report" else 2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text.strip()

        # Parse JSON — handle markdown fences if present
        json_text = raw_text
        if json_text.startswith("```"):
            json_text = re.sub(r"^```(?:json)?\s*", "", json_text)
            json_text = re.sub(r"\s*```$", "", json_text)

        import json
        narratives = json.loads(json_text)

        logger.info(
            "Narratives generated: %d sections, %d input tokens, %d output tokens",
            len(narratives),
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        # Replace placeholders with generated content
        result = report_markdown
        for key, placeholder_text in placeholder_map.items():
            if key in narratives:
                result = result.replace(placeholder_text, narratives[key])
            else:
                logger.warning("Narrative key %s not found in AI response", key)
                # Strip the placeholder rather than leaving it in
                result = result.replace(placeholder_text, "")

        return result

    except Exception:
        logger.exception("Narrative generation failed — returning report without narratives")
        return _strip_placeholders(report_markdown)


def _strip_placeholders(report: str) -> str:
    """Remove unfilled placeholders from a report (fallback)."""
    return re.sub(r"\{\{(?:NARRATIVE|RECOMMENDATION):.*?\}\}", "", report)
