# Full Evaluation Report: {{package_name}}

*Prepared by [Assay](https://assay.tools) — The quality layer for agentic software.*
*Evaluated: {{last_evaluated}} | Report generated: {{report_date}}*

---

## Executive Summary

**{{package_name}}** — {{what_it_does}}

| | |
|---|---|
| **Category** | {{category_name}} |
| **Homepage** | {{homepage}} |
| **Repository** | {{repo_url}} |
| **Package Type** | {{package_type}} |
| **Last Evaluated** | {{last_evaluated}} |

{{NARRATIVE: Write a 3-4 paragraph executive summary of {{package_name}}. Start with a clear verdict: is this package ready for production agent use? Then cover its strongest and weakest dimensions, how it compares to the category average AF Score of {{cat_avg}}, and who should care about this report. Be direct and authoritative — this sets the tone for a $99 report.}}

---

## AF Score Breakdown

### Overall: {{af_score}} / 100 — {{af_rating}}

| Dimension | Score | Rating |
|-----------|-------|--------|
| Documentation Accuracy | {{documentation_accuracy}} / 100 | {{documentation_rating}} |
| Error Message Quality | {{error_message_quality}} / 100 | {{error_message_rating}} |
| Auth Complexity | {{auth_complexity}} / 100 | {{auth_complexity_rating}} |
| MCP Server Quality | {{mcp_server_quality}} / 100 | {{mcp_quality_rating}} |
| Rate Limit Clarity | {{rate_limit_clarity}} / 100 | {{rate_limit_rating}} |

| Dimension | Score | Rating |
|-----------|-------|--------|
| **Security Score** | {{security_score}} / 100 | {{security_rating}} |
| **Reliability Score** | {{reliability_score}} / 100 | {{reliability_rating}} |

{{NARRATIVE: Provide detailed analysis of the AF Score dimensions. For each dimension, explain what the score means in practical terms — not just "documentation is good" but what specifically is well-documented and what gaps exist. Identify the strongest and weakest dimensions and explain the gap between them.}}

---

## Security Deep-Dive

| Sub-Component | Score | Rating |
|---------------|-------|--------|
| TLS Enforcement | {{tls_enforcement}} / 100 | {{tls_rating}} |
| Auth Strength | {{auth_strength}} / 100 | {{auth_strength_rating}} |
| Scope Granularity | {{scope_granularity}} / 100 | {{scope_rating}} |
| Secret Handling | {{secret_handling}} / 100 | {{secret_rating}} |
| Dependency Hygiene | {{dependency_hygiene}} / 100 | {{dep_hygiene_rating}} |

{{security_notes}}

{{NARRATIVE: Write a thorough security analysis. For each sub-component below 90, explain the specific risk and what an attacker or misconfigured agent could exploit. For sub-components below 70, flag these as urgent. Discuss what this means for teams in regulated industries. Be specific about what security properties agents should verify before making calls to this package.}}

---

## Reliability Deep-Dive

| Sub-Component | Score | Rating |
|---------------|-------|--------|
| Uptime (Documented) | {{uptime_documented}} / 100 | {{uptime_rating}} |
| Version Stability | {{version_stability}} / 100 | {{version_rating}} |
| Breaking Changes History | {{breaking_changes_history}} / 100 | {{breaking_changes_rating}} |
| Error Recovery | {{error_recovery}} / 100 | {{error_recovery_rating}} |

{{NARRATIVE: Analyze the reliability profile in depth. Cover: How stable is this package across releases? What's the breaking change risk? How well does it support retry and recovery patterns that agents need? If an agent relies on this package in a production loop, what's the failure mode?}}

---

## Agent Experience Audit

### Interface & Integration

{{interface_table}}

### Authentication

{{auth_section}}

{{NARRATIVE: Write from the perspective of an agent trying to integrate this package. Walk through the integration experience: What does setup look like? How complex is auth? What's the typical time-to-first-successful-call? Where do teams and agents get stuck? Reference the specific interfaces and auth methods from the data above.}}

### Known Gotchas

{{gotchas_section}}

### Error Handling

{{error_message_notes}}

---

## Cost Analysis

### Pricing

{{pricing_section}}

### Performance

{{performance_section}}

{{NARRATIVE: Provide detailed cost modeling for agent workloads. Project costs at three usage levels: light (100 calls/day), moderate (1,000 calls/day), and heavy (10,000 calls/day). Factor in rate limits, caching opportunities, and any volume discounts from the pricing data. If this is an open-source/self-hosted package, analyze infrastructure costs instead. Include a note on cost optimization strategies specific to this package.}}

---

## Agent Guidance

### Best When

{{best_when}}

### Avoid When

{{avoid_when}}

### Use Cases

{{use_cases}}

### Not For

{{not_for}}

---

## Competitive Positioning

{{competitive_section}}

{{NARRATIVE: Write a detailed competitive analysis. For each competitor in the table above, explain the specific tradeoffs: when would you choose the competitor instead, and when does this package win? Go beyond score comparison — discuss differences in pricing model, integration complexity, and reliability track record as reflected in the data.}}

---

## Dependency & Supply Chain Analysis

{{dependency_section}}

{{NARRATIVE: Analyze the dependency profile. How heavy is the install? Are there known-risky or unmaintained transitive dependencies? For agents that need lightweight, fast-starting integrations, is this package's dependency weight a concern? What's the supply chain risk posture?}}

---

## Improvement Roadmap

{{recommendations}}

{{NARRATIVE: Write a prioritized 5-7 step improvement roadmap. For each step: describe the specific action, estimate the effort (hours/days), project the expected score improvement, and explain the adoption impact. Order by expected impact descending. This is the most valuable section of the report — make it specific enough that an engineer could create tickets from it.}}

---

## Compliance & Governance

{{compliance_section}}

{{NARRATIVE: Summarize the compliance and governance posture. Cover: data residency implications, relevant certifications (SOC2, HIPAA, GDPR), and what enterprise procurement teams need to know. If compliance data is limited, note what's missing and what questions a buyer should ask the vendor before adopting in a regulated environment.}}

---

*This report was prepared by Assay's evaluation pipeline with AI-generated analysis grounded in structured evaluation data. Scores are independent — vendors cannot buy influence over ratings.*

*Questions or disputes? Contact hello@assay.tools*

*{{year}} Assay Tools. This report is licensed for use by the purchaser and may not be redistributed.*
