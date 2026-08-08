# EchoRank — company state

_Last updated: 2026-08-08 by the AI co-founder (founding session)._

## What EchoRank is
AI-search visibility audits ("when AI answers your customers, does it say your name?").
Free audit in beta → US$39/mo monitoring at the validation gate (10 audit requests OR 3 buying-intent replies).
Decisions of record: pre-revenue launch, $0 budget (free tiers only), cold email approved from an agent-run inbox, subscription-first pricing, site must dogfood its own recommendations. Human co-founder: triftan888@gmail.com (owns payments/legal; AI does not custody funds).

## Built and working (all in `echorank/`)
- `engine/readiness.py` — automated site AI-readiness probe (0–100). `engine/report.py` — HTML report renderer. Schema in `engine/README.md`.
- 4 published-ready audits in `brands/`: Cal.com 68/B, Plausible 79/B+, Buttondown 60/C+, EchoRank self-audit 23/F (day-zero baseline; readiness 90/100).
- `site/` — complete static site (landing, methodology, about, thanks, llms.txt, robots.txt, sitemap, 4 reports). Form posts to FormSubmit → triftan888@gmail.com (first submission triggers a FormSubmit activation email that the human must click once).
- `outreach/` — 10 probed targets (`probes/*.json`), CRM `leads.csv`, personalized drafts `emails.md` (honest AI signature + opt-out).

## Infrastructure status (2026-08-08, after "Go")
- Approvals now flow; connector calls work.
- **Vercel deploy still blocked**: integration token returns 403 "You don't have permission to create a project" on team triftans-projects. FIX (human, ~30s): either create an empty Vercel project named `echorank` in the dashboard (then our deploy into the existing project should succeed), or grant the Claude/Vercel integration access to create projects. Retry deploy each ops cycle.
- **Gmail connector has NO send tool** — drafts only. Cold email flow = AI drafts, human clicks send. True auto-send requires AgentMail (human signup + AGENTMAIL_API_KEY env var).
- Routines LIVE (self-bind to founding session): trig_015vh18iiQE7gu3gEbtn3YxB "EchoRank ops cycle" (0 1 */2 * *), trig_01DexHxxHMKP9vYzTEQx1yFe "EchoRank weekly investor update" (0 1 * * 1).
- CRM sheet LIVE: "EchoRank — Leads & Ops" https://docs.google.com/spreadsheets/d/10L1Nxcqco0HSfI0CIpIGfGnqIRX2zfLF3YCO_XUZ9zY/ (10 leads loaded; keep leads.csv as the source of truth, mirror to sheet).

## Pending queue (execute in order once approvals exist)
1. **Deploy site**: Vercel MCP `deploy_to_vercel`, project name `echorank`, team `team_fKxdgmT2HhVeGqqYeOeE0Fb8`, target production, static files from `site/` (root = site contents; reports at `r/<slug>/index.html`). Verify https://echorank.vercel.app/ serves; if the project slug is taken, redeploy under `echorank-ai` and update canonical URLs + llms.txt + sitemap in repo first.
2. **Test the form** end-to-end; click the FormSubmit activation email (human).
3. **Send outreach batch 1**: verify each address in `outreach/leads.csv`, send from Gmail ≤15/day, update `status` column per send; log replies.
4. **Create routines**: (a) ops cycle every 2 days `0 1 */2 * *`; (b) weekly investor update Monday `0 1 * * 1` to triftan888@gmail.com. Prompts drafted in founding session; keep self-bind.
5. **Leads/Ops sheet**: optional once Sheets approved — otherwise `leads.csv` stays the CRM.
6. At validation gate: ask human for Stripe payment link; wire pricing page.

## KPIs (as of founding)
Site live: NO (Vercel 403 — needs human project creation). Audit requests: 0. Outreach sent: 0 (10 drafted). Replies: 0. Self-audit score: 23/100 (F) — baseline to beat publicly.

## Principles (do not drift)
Honest findings only; disclose methodology in every report; AI-founder signature on all outreach; opt-outs honored instantly; ≤15 cold emails/day; never claim engine coverage we didn't measure; all work committed to `claude/ai-cofounder-startup-dm1ybm`.
