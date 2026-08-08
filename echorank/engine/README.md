# EchoRank audit engine

Two deterministic tools plus an analyst layer:

| Piece | What it does |
|---|---|
| `readiness.py <domain> --out brands/<slug>/readiness.json` | Automated site probe: llms.txt, robots.txt AI-crawler policy, schema.org JSON-LD, sitemap, extractable-text volume. Scores 0–100. |
| `report.py brands/<slug> --out ../site/r/<slug>/index.html` | Renders `findings.json` + `readiness.json` into the final self-contained HTML report. |
| Analyst layer (Claude) | Fills `findings.json`: samples AI-engine answers for the brand's money queries (via Apify / web research), maps the citation-source footprint (Reddit, Wikipedia, YouTube, review & comparison sites), writes the executive summary and the ranked fix roadmap. |

## `findings.json` schema

```json
{
  "brand": "Acme", "slug": "acme", "domain": "acme.com",
  "category": "Scheduling software", "competitors": ["Rival A", "Rival B"],
  "tagline": "one-line framing for the report header",
  "generated": "YYYY-MM-DD",
  "summary": "executive summary paragraph",
  "money_queries": [
    {"query": "best scheduling tool for startups", "presence": "cited|mentioned|absent",
     "winner": "Rival A", "evidence": "what the sampled answers actually said"}
  ],
  "sources": [
    {"channel": "Reddit", "status": "strong|weak|absent", "detail": "..."}
  ],
  "roadmap": [
    {"priority": 1, "title": "...", "why": "...", "effort": "low|medium|high"}
  ],
  "methodology_notes": ["exactly what was measured, and what wasn't"]
}
```

Visibility score = 50% AI-answer presence + 30% citation footprint + 20% site readiness.
