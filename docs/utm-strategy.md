# Assay UTM Parameter Strategy

Standard UTM tags for tracking launch channel effectiveness.

## Format

```
https://assay.tools/?utm_source={source}&utm_medium={medium}&utm_campaign={campaign}
```

## Launch Campaign Tags

### Hacker News
```
?utm_source=hackernews&utm_medium=show_hn&utm_campaign=launch_2026
```

### Reddit
```
?utm_source=reddit&utm_medium=r-programming&utm_campaign=launch_2026
?utm_source=reddit&utm_medium=r-machinelearning&utm_campaign=launch_2026
?utm_source=reddit&utm_medium=r-artificial&utm_campaign=launch_2026
?utm_source=reddit&utm_medium=r-selfhosted&utm_campaign=launch_2026
?utm_source=reddit&utm_medium=r-sideproject&utm_campaign=launch_2026
```

### Discord
```
?utm_source=discord&utm_medium=fabric&utm_campaign=launch_2026
?utm_source=discord&utm_medium=mcp-community&utm_campaign=launch_2026
```

### Product Hunt
```
?utm_source=producthunt&utm_medium=launch&utm_campaign=launch_2026
```

### Blog Posts
```
?utm_source=devto&utm_medium=blog&utm_campaign=launch_2026
?utm_source=hashnode&utm_medium=blog&utm_campaign=launch_2026
```

### LinkedIn
```
?utm_source=linkedin&utm_medium=post&utm_campaign=launch_2026
```

### Direct Outreach
```
?utm_source=email&utm_medium=outreach&utm_campaign=maintainer_outreach
?utm_source=email&utm_medium=beta_invite&utm_campaign=beta_2026
```

### Ongoing Content
```
?utm_source=newsletter&utm_medium=email&utm_campaign=monthly_digest
?utm_source=github&utm_medium=readme&utm_campaign=badge
?utm_source=github&utm_medium=action&utm_campaign=ci_integration
```

## Rules

1. **Always lowercase** — no mixed case in UTM values
2. **Hyphens for spaces** — `r-programming` not `r_programming`
3. **Campaign = time period or initiative** — `launch_2026`, `beta_2026`, `monthly_digest`
4. **Source = platform** — `hackernews`, `reddit`, `discord`, `linkedin`
5. **Medium = specific channel** — `r-programming`, `show_hn`, `fabric`
6. **Track before posting** — Generate the full URL before publishing anywhere
