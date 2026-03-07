# Weekly Newsletter Session

YOUR TASK: Generate and send the Assay weekly newsletter.

This is a fully autonomous pipeline. Execute each step in order.

## Step 1: Collect Data

```bash
cd ~/git/assay
uv run python -m assay.cli newsletter collect
```

This queries the production database for the week's activity and saves:
- `newsletters/pending/digest-YYYY-MM-DD.json` — raw data
- `newsletters/pending/prompt-YYYY-MM-DD.md` — writing instructions

## Step 2: Read the Prompt and Data

Read the most recent prompt file from `newsletters/pending/`. It contains:
- Writing instructions (tone, structure, formatting)
- This week's data (new packages, score movers, newly evaluated, category stats)

## Step 3: Write the Newsletter

Following the instructions in the prompt file, write the newsletter content.

**Output two files:**

1. `newsletters/ready/newsletter-YYYY-MM-DD.html` — The full HTML email
2. `newsletters/ready/newsletter-YYYY-MM-DD.txt` — Plaintext version
3. `newsletters/ready/newsletter-YYYY-MM-DD.json` — Metadata: `{"subject": "...", "date": "YYYY-MM-DD"}`

Use the date from the digest filename for YYYY-MM-DD.

**IMPORTANT**: The HTML must be valid email HTML with inline styles only. Match the Assay brand (dark theme, #111827 background, #6366f1 accent). Do NOT include unsubscribe links — the sender adds those per-recipient.

## Step 4: Send

```bash
cd ~/git/assay
uv run python -m assay.cli newsletter send
```

This reads the ready newsletter, sends it to all confirmed subscribers via Resend, archives the files to `newsletters/sent/`, and records the issue in the database.

## Step 5: Clean Up

Remove the pending files:
```bash
rm -f newsletters/pending/digest-*.json newsletters/pending/prompt-*.md
```

## Step 6: Commit

```bash
cd ~/git/assay
git add newsletters/sent/
git commit -m "docs: archive weekly newsletter $(date +%Y-%m-%d)"
git push
```

## Error Handling

- If `newsletter collect` shows 0 new packages, 0 movers, and 0 newly evaluated: write a very short newsletter acknowledging a quiet week. Don't skip sending — subscribers expect consistency.
- If `newsletter send` shows 0 subscribers: that's fine, the issue is still saved to the DB for when subscribers arrive.
- If Resend fails: the issue is saved. Can retry with `assay newsletter send` later.

## Schedule

This session runs every Monday morning via launchd. The newsletter covers the previous 7 days.
