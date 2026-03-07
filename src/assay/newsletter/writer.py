"""Newsletter content generation — prompt and data preparation.

The actual writing is done by Claude Code (via subscription), not the
Anthropic API. This module prepares the data and prompt, and parses
the output after Claude writes it.
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path

from assay.newsletter.collector import WeeklyDigest

logger = logging.getLogger(__name__)

NEWSLETTER_PROMPT = """\
You are the editor of the Assay weekly newsletter — the authoritative digest \
on agentic software quality. Assay rates MCP servers, APIs, and SDKs across \
three dimensions: Agent Friendliness (AF Score), Security, and Reliability.

Your job: turn this week's raw data into a compelling, concise newsletter that \
developers and agent builders actually want to read.

TONE & STYLE:
- Professional but warm. Like a knowledgeable colleague sharing insights.
- Data-driven — always reference specific numbers and packages.
- Opinionated — highlight what matters and why. Don't just list facts.
- Concise — respect the reader's time. Every sentence should earn its place.
- No marketing fluff, no hype, no filler.

STRUCTURE (follow this exactly):
1. **Opening** (2-3 sentences) — The single most interesting thing from this week. \
Hook the reader immediately.
2. **This Week in Numbers** — Quick ecosystem snapshot: new packages, evaluations, \
freshness %. Use a brief table or bullet list.
3. **Biggest Movers** — Packages with the most significant score changes. Explain \
what likely drove the change (new version, security fix, API improvement, etc.) \
based on the direction and magnitude of the change. If no movers, skip this section.
4. **Fresh Evaluations** — Highlight 3-5 notable newly-evaluated packages. Brief \
verdict on each: what it does, its standout score, and one key insight.
5. **Category Spotlight** — Pick the most interesting category from the stats \
(highest growth, or most activity). 2-3 sentences on trends in that category.
6. **Closing** — One sentence. Forward-looking or thought-provoking.

FORMATTING:
- Output valid HTML suitable for email (inline styles only, no CSS classes).
- Use the Assay brand colors: background #111827, text #e5e7eb, accent #6366f1, \
muted #9ca3af, headings #fff.
- Use the same email styling as other Assay emails (body font: -apple-system, \
max-width 560px, 24px padding).
- Include the full HTML document structure (<!DOCTYPE html> through </html>).
- After the HTML, output a separator line "---PLAINTEXT---" followed by the \
plaintext version of the same content.
- In the plaintext version, use simple formatting: caps for headers, dashes for \
bullets, plain URLs.
- Do NOT include unsubscribe links — those are added automatically by the sender.

DATA NOTES:
- AF scores are 0-100. Above 70 is good, above 85 is excellent.
- Score deltas: positive = improved, negative = declined.
- "Freshness %" = packages evaluated within the last 30 days out of all evaluated.
- If the data is thin (few movers, few new evaluations), write a shorter newsletter. \
Never pad with filler. A short, punchy issue is better than a long, boring one.
"""

# Where newsletter artifacts are staged
NEWSLETTER_DIR = Path(__file__).parent.parent.parent.parent / "newsletters"


def prepare_digest_data(digest: WeeklyDigest) -> dict:
    """Serialize digest to a JSON-compatible dict."""
    data = asdict(digest)
    for key in ("week_start", "week_end"):
        if data.get(key):
            data[key] = data[key].isoformat()
    return data


def save_digest_for_session(digest: WeeklyDigest) -> Path:
    """Save digest data + writing prompt for a Claude Code session.

    Creates:
      newsletters/pending/digest-YYYY-MM-DD.json  — raw data
      newsletters/pending/prompt-YYYY-MM-DD.md    — writing instructions

    Returns:
        Path to the prompt file.
    """
    pending_dir = NEWSLETTER_DIR / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    date_str = digest.week_end.strftime("%Y-%m-%d")
    digest_data = prepare_digest_data(digest)

    # Save raw data
    data_path = pending_dir / f"digest-{date_str}.json"
    data_path.write_text(json.dumps(digest_data, indent=2, default=str))

    # Save prompt
    prompt_path = pending_dir / f"prompt-{date_str}.md"
    week_label = (
        f"{digest.week_start.strftime('%B %d')} — "
        f"{digest.week_end.strftime('%B %d, %Y')}"
    )
    prompt_path.write_text(
        f"{NEWSLETTER_PROMPT}\n\n---\n\n"
        f"Here is this week's data for the Assay newsletter.\n\n"
        f"Week: {week_label}\n\n"
        f"```json\n{json.dumps(digest_data, indent=2, default=str)}\n```\n\n"
        f"Write the newsletter now. Remember: HTML first, then "
        f"---PLAINTEXT--- separator, then plaintext.\n"
    )

    logger.info("Newsletter data saved to %s", pending_dir)
    return prompt_path


def parse_newsletter_output(raw_content: str) -> tuple[str, str]:
    """Parse Claude's output into HTML and plaintext parts.

    Args:
        raw_content: The full output from Claude Code.

    Returns:
        Tuple of (html_content, text_content).
    """
    if "---PLAINTEXT---" in raw_content:
        html_part, text_part = raw_content.split("---PLAINTEXT---", 1)
    else:
        html_part = raw_content
        text_part = raw_content

    return html_part.strip(), text_part.strip()


def save_newsletter_content(
    date_str: str, subject: str, html_content: str, text_content: str,
) -> Path:
    """Save the written newsletter to the ready directory.

    Creates:
      newsletters/ready/newsletter-YYYY-MM-DD.html
      newsletters/ready/newsletter-YYYY-MM-DD.txt
      newsletters/ready/newsletter-YYYY-MM-DD.json  (metadata)

    Returns:
        Path to the metadata file.
    """
    ready_dir = NEWSLETTER_DIR / "ready"
    ready_dir.mkdir(parents=True, exist_ok=True)

    (ready_dir / f"newsletter-{date_str}.html").write_text(html_content)
    (ready_dir / f"newsletter-{date_str}.txt").write_text(text_content)

    meta = {"subject": subject, "date": date_str}
    meta_path = ready_dir / f"newsletter-{date_str}.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    logger.info("Newsletter content saved to %s", ready_dir)
    return meta_path


def generate_subject(digest: WeeklyDigest) -> str:
    """Generate a newsletter subject line from the digest data."""
    date_str = digest.week_end.strftime("%b %d")
    parts = []

    if digest.score_movers:
        top = digest.score_movers[0]
        direction = "up" if top.af_delta > 0 else "down"
        parts.append(f"{top.name} scores {direction}")

    if digest.newly_evaluated:
        parts.append(f"{len(digest.newly_evaluated)} new evaluations")

    if digest.new_packages:
        parts.append(f"{len(digest.new_packages)} packages discovered")

    if parts:
        highlights = ", ".join(parts[:2])
        return f"Assay Weekly ({date_str}): {highlights}"
    return f"Assay Weekly Digest — {date_str}"
