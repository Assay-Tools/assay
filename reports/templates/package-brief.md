# Package Brief: {{package_name}}

*Prepared by [Assay](https://assay.tools) — The quality layer for agentic software.*
*Evaluated: {{last_evaluated}} | Report generated: {{report_date}}*

---

## Verdict

{{NARRATIVE: Write a clear 2-3 sentence verdict on whether to adopt {{package_name}}. Be direct: "Use this if..." / "Skip this if..." / "Use with caveats because...". Reference the AF Score of {{af_score}} and how it compares to the category average of {{cat_avg}}.}}

---

## Score Snapshot

| Dimension | Score | Rating |
|-----------|-------|--------|
| **AF Score (Overall)** | **{{af_score}} / 100** | **{{af_rating}}** |
| Security | {{security_score}} / 100 | {{security_rating}} |
| Reliability | {{reliability_score}} / 100 | {{reliability_rating}} |

| AF Dimension | Score |
|--------------|-------|
| Documentation | {{documentation_accuracy}} |
| Error Messages | {{error_message_quality}} |
| Auth Complexity | {{auth_complexity}} |
| MCP Server | {{mcp_server_quality}} |
| Rate Limit Clarity | {{rate_limit_clarity}} |

---

## Integration Guide

{{interface_table}}

{{auth_section}}

{{NARRATIVE: Write a practical 2-3 paragraph integration guide for {{package_name}}. Cover: typical setup steps, auth configuration, and estimated effort (hours/days) to get a working agent integration. Reference the specific interfaces and auth methods from the tables above.}}

---

## Cost Projection

{{pricing_section}}

{{NARRATIVE: Based on the pricing data above, project costs at three usage levels: light agent use (100 calls/day), moderate (1,000 calls/day), and heavy (10,000 calls/day). If the pricing model doesn't support this analysis (e.g., open source with no API costs), say so and explain what the actual cost drivers are.}}

---

## Gotchas & Workarounds

{{gotchas_section}}

{{NARRATIVE: For each gotcha listed above, suggest a specific workaround or mitigation strategy. If there are no gotchas documented, note what common integration pitfalls to watch for based on the package's interface type and auth model.}}

---

## Alternatives

{{competitive_section}}

{{NARRATIVE: Brief comparison of {{package_name}} against its closest alternatives from the table above. For each alternative, one sentence on when you'd choose it instead. Be specific about the tradeoff.}}

---

## When to Walk Away

{{NARRATIVE: Based on the scores and data in this report, identify 2-3 specific scenarios where {{package_name}} is NOT the right choice. Be honest and specific — this section exists to save the reader time and money.}}

---

*This brief was prepared by Assay's evaluation pipeline with AI-generated analysis. Scores are independent — vendors cannot buy influence over ratings.*

*Need the full deep-dive? [Get the Full Evaluation Report](https://assay.tools/packages/{{package_id}}) — $99 for complete security analysis, improvement roadmap, and competitive positioning.*

*Questions? Contact hello@assay.tools*

*{{year}} Assay Tools. Licensed for use by the purchaser.*
