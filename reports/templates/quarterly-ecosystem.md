# State of Agentic Software — {{quarter}} {{year}}

*Published by [Assay](https://assay.tools) — The quality layer for agentic software.*

---

## Executive Summary

{{executive_summary}}

---

## By the Numbers

| Metric | Value |
|--------|-------|
| Total packages tracked | {{total_packages}} |
| Packages evaluated | {{total_evaluated}} |
| Categories covered | {{total_categories}} |
| Average AF Score | {{avg_af_score}} / 100 |
| Highest AF Score | {{top_af_score}} / 100 |
| Lowest AF Score | {{bottom_af_score}} / 100 |

### Score Distribution

| Rating | AF Score Range | Count | % of Evaluated |
|--------|---------------|-------|----------------|
| Excellent | 80–100 | {{excellent_count}} | {{excellent_pct}}% |
| Good | 60–79 | {{good_count}} | {{good_pct}}% |
| Fair | 40–59 | {{fair_count}} | {{fair_pct}}% |
| Poor | Below 40 | {{poor_count}} | {{poor_pct}}% |

{{score_distribution_insight}}

---

## Top-Rated Packages

The highest-scoring packages across all categories this quarter:

| Rank | Package | Category | AF Score | Security | Reliability |
|------|---------|----------|----------|----------|-------------|
{{top_packages_table}}

{{top_packages_insight}}

---

## Category Landscape

### Category Overview

| Category | Packages | Evaluated | Avg AF Score | Top Score |
|----------|----------|-----------|--------------|-----------|
{{category_table}}

{{category_insight}}

### Category Spotlights

{{category_spotlights}}

---

## Security Posture

{{security_section}}

### Security Score Leaders

| Package | Category | Security Score | Key Strengths |
|---------|----------|---------------|---------------|
{{security_leaders_table}}

### Common Security Gaps

{{security_gaps}}

---

## Agent Readiness Patterns

### What Makes a Package Agent-Friendly?

{{agent_readiness_patterns}}

### Most Common Agent Gotchas

{{common_gotchas}}

---

## Emerging Trends

{{trends_section}}

---

## Methodology

Assay evaluates packages across five weighted dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| MCP Quality | 20% | Tool descriptions, schema completeness, error handling |
| Documentation | 20% | Accuracy, examples, completeness for agent consumption |
| Error Messages | 15% | Actionable errors that help agents self-correct |
| Security | 15% | Auth patterns, input validation, least-privilege design |
| Auth Complexity | 15% | How easy it is for an agent to authenticate |

Evaluations are performed by automated pipelines using consistent rubrics. All scores are independent — vendors cannot buy influence over ratings. Full methodology at [assay.tools/about](https://assay.tools/about).

---

## Get Your Package's Full Report

Every package in this report has a detailed evaluation on file. Package owners and maintainers can get a comprehensive **Package Evaluation Report** ($99) including:

- Full AF Score breakdown across all sub-components
- Specific, prioritized improvement recommendations
- Competitive positioning within your category
- Agent-readiness roadmap

Contact: hello@assay.tools

---

*Assay is an independent rating platform for agentic software. Browse the full directory at [assay.tools](https://assay.tools).*

*© {{year}} Assay Tools. This report may be freely distributed with attribution.*
