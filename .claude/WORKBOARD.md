# Assay Workboard

Coordination file for multiple Claude sessions working on this repo.

## Protocol

### Before Starting Work
1. `git pull` to get latest workboard and active claims
2. Read this file and check `.claude/active/` for in-progress work
3. Pick an unclaimed item (or propose new work)
4. Create a claim file: `.claude/active/<topic>.md` with your focus, files you'll touch, and timestamp
5. `git add .claude/active/<topic>.md && git commit -m "claim: <topic>" && git push`
6. **Use a worktree** (`git worktree add`) if touching files that other sessions might also edit

### While Working
- Commit and push regularly to your branch (if using worktree) or to main (if safe)
- If you discover work that overlaps with another claim, stop and note it in your claim file

### When Done
1. Merge your worktree branch (if applicable)
2. Move your item to "Completed" below
3. Delete your claim file from `.claude/active/`
4. Commit and push

### Conflict Avoidance
- **Claim files are per-session** — never edit another session's claim file
- **Workboard edits** — only add items or move your own items between sections
- **When in doubt, use a worktree** — especially for multi-file changes
- **File-level ownership** — if two claims touch the same file, coordinate via the workboard or ask AJ

---

## Available Work

Items ready to be claimed. Roughly priority-ordered.

### Infrastructure (Pre-Launch)
- [x] ~~**llms.txt** — moved to Completed~~
- [x] ~~**Rate limiting** — moved to Completed~~
- [x] ~~**OpenAPI spec polish** — moved to Completed~~

### API Completeness
- [x] ~~**Change feed endpoint** — moved to Completed~~
- [x] ~~**Filter by score dimension** — moved to Completed~~
- [x] ~~**Category leaderboards** — moved to Completed~~

### Testing & Quality
- [x] ~~**Test suite** — moved to Completed~~
- [x] ~~**CI/CD pipeline** — moved to Completed~~
- [x] ~~**Linting pass** — moved to Completed~~

### Website Polish
- [ ] **Staleness badge** — Visual indicator on package detail when last_evaluated > 90 days
- [ ] **Score visualization** — Radar/spider charts for AF/Security/Reliability breakdown
- [ ] **Display last_evaluated** — Surface evaluation date prominently in API responses and package detail

### CLI
- [ ] **CLI tool** — `assay check <pkg>`, `assay compare <a> <b>`, `assay stale --days 90`

---

## In Progress

*Check `.claude/active/` for details on each.*

(none currently)

---

## Completed

- [x] **Category consolidation** — 147→16 categories, stats consistency fix (2026-03-04)
- [x] **Package evaluation report** — $99 report template + generation script (2026-03-04)
- [x] **Q1 ecosystem report** — Quarterly report template + generation + full Q1-2026 output (2026-03-04)
- [x] **BUSINESS.md** — Business model, pricing, agentic operating philosophy (2026-03-04)
- [x] **SSL fix** — Railway cert provisioning via Cloudflare TXT record (2026-03-04)
- [x] **llms.txt + rate limiting** — `/llms.txt`, `/llms-full.txt` routes + slowapi 100/day on all `/v1/*` endpoints (2026-03-04)
- [x] **Test suite** — 49 pytest tests covering models, API routes (packages, categories, compare, stats, queue) (2026-03-04)
- [x] **CI/CD pipeline** — GitHub Actions lint (ruff) + test (pytest) on push/PR, CI badge in README (2026-03-04)
- [x] **Linting pass** — 64 violations fixed (25 auto-fix + 39 E501 line-length) (2026-03-04)
- [x] **OpenAPI spec polish** — tag descriptions, endpoint docstrings, schema field descriptions, API metadata (2026-03-04)
- [x] **API completeness** — score dimension filters, change feed endpoint, category leaderboards + 16 new tests (2026-03-04)
