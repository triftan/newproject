#!/usr/bin/env python3
"""EchoRank report renderer.

Reads a brand directory containing:
  findings.json   — brand identity, money-query results, citation-source
                    footprint, fix roadmap, methodology notes (authored by the
                    EchoRank analyst pipeline)
  readiness.json  — output of readiness.py for the brand's domain

Writes a single self-contained HTML report.

Usage:
  python3 report.py brands/<slug> --out site/r/<slug>/index.html
"""
import html
import json
import os
import sys
from datetime import date

PRESENCE_WEIGHT = {"cited": 1.0, "mentioned": 0.5, "absent": 0.0}
SOURCE_WEIGHT = {"strong": 1.0, "weak": 0.5, "absent": 0.0}
PRESENCE_LABEL = {
    "cited": ("Cited", "#0e9f6e"),
    "mentioned": ("Mentioned", "#d97706"),
    "absent": ("Absent", "#dc2626"),
}
SOURCE_LABEL = {
    "strong": ("Strong", "#0e9f6e"),
    "weak": ("Weak", "#d97706"),
    "absent": ("Absent", "#dc2626"),
}
EFFORT_LABEL = {"low": "Low effort", "medium": "Medium effort", "high": "High effort"}


def e(s):
    return html.escape(str(s), quote=True)


def compute_score(findings, readiness):
    mq = findings.get("money_queries", [])
    engine = (sum(PRESENCE_WEIGHT.get(q.get("presence", "absent"), 0) for q in mq) / len(mq)) if mq else 0.0
    src = findings.get("sources", [])
    sources = (sum(SOURCE_WEIGHT.get(s.get("status", "absent"), 0) for s in src) / len(src)) if src else 0.0
    ready = (readiness.get("score", 0) / readiness.get("max_score", 100)) if readiness else 0.0
    total = round(100 * (0.5 * engine + 0.3 * sources + 0.2 * ready))
    return total, round(100 * engine), round(100 * sources), round(100 * ready)


def grade(score):
    for cut, g in [(85, "A"), (75, "B+"), (65, "B"), (55, "C+"), (45, "C"), (35, "D+"), (25, "D")]:
        if score >= cut:
            return g
    return "F"


def score_color(score):
    if score >= 70:
        return "#0e9f6e"
    if score >= 45:
        return "#d97706"
    return "#dc2626"


def render(brand_dir, out_path):
    with open(os.path.join(brand_dir, "findings.json")) as f:
        fx = json.load(f)
    readiness = {}
    rpath = os.path.join(brand_dir, "readiness.json")
    if os.path.exists(rpath):
        with open(rpath) as f:
            readiness = json.load(f)

    score, engine_pct, sources_pct, ready_pct = compute_score(fx, readiness)
    g = grade(score)
    col = score_color(score)
    brand = fx["brand"]
    generated = fx.get("generated", date.today().isoformat())

    # money-query rows
    mq_rows = []
    for q in fx.get("money_queries", []):
        label, c = PRESENCE_LABEL.get(q.get("presence", "absent"), PRESENCE_LABEL["absent"])
        mq_rows.append(
            f"<tr><td class='q'>“{e(q['query'])}”</td>"
            f"<td><span class='pill' style='background:{c}1a;color:{c}'>{label}</span></td>"
            f"<td>{e(q.get('winner', '—') or '—')}</td>"
            f"<td class='ev'>{e(q.get('evidence', ''))}</td></tr>"
        )

    src_rows = []
    for s in fx.get("sources", []):
        label, c = SOURCE_LABEL.get(s.get("status", "absent"), SOURCE_LABEL["absent"])
        src_rows.append(
            f"<tr><td>{e(s['channel'])}</td>"
            f"<td><span class='pill' style='background:{c}1a;color:{c}'>{label}</span></td>"
            f"<td class='ev'>{e(s.get('detail', ''))}</td></tr>"
        )

    road_items = []
    for r in sorted(fx.get("roadmap", []), key=lambda x: x.get("priority", 99)):
        road_items.append(
            f"<li><div class='rt'><strong>{e(r['title'])}</strong>"
            f"<span class='effort'>{EFFORT_LABEL.get(r.get('effort', 'medium'), 'Medium effort')}</span></div>"
            f"<p>{e(r['why'])}</p></li>"
        )

    ready_items = []
    if readiness:
        c = readiness["checks"]
        hp = c.get("homepage", {})
        def yn(v, good="Yes", bad="No"):
            colr = "#0e9f6e" if v else "#dc2626"
            return f"<span class='pill' style='background:{colr}1a;color:{colr}'>{good if v else bad}</span>"
        blocked = sorted(k for k, v in c.get("ai_crawlers", {}).items() if v == "blocked")
        ready_items = [
            ("llms.txt published", yn(c.get("llms_txt"))),
            ("AI crawlers allowed in robots.txt", yn(not blocked, "Yes", "Blocks: " + ", ".join(blocked) if blocked else "No")),
            ("schema.org structured data", yn(bool(hp.get("schema_types")), ", ".join(hp.get("schema_types", [])[:6]) or "Yes", "None found")),
            ("Extractable homepage text", yn(hp.get("visible_word_count", 0) >= 250, f"~{hp.get('visible_word_count', 0)} words", f"Only ~{hp.get('visible_word_count', 0)} words")),
            ("Sitemap", yn(c.get("sitemap_xml") or c.get("sitemap_in_robots"))),
        ]
    ready_rows = "".join(f"<tr><td>{e(k)}</td><td>{v}</td></tr>" for k, v in ready_items)
    ready_notes = "".join(f"<li>{e(n)}</li>" for n in readiness.get("notes", []))

    meth = "".join(f"<li>{e(n)}</li>" for n in fx.get("methodology_notes", []))
    competitors = ", ".join(fx.get("competitors", [])) or "—"

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(brand)} — AI Search Visibility Report | EchoRank</title>
<meta name="description" content="How {e(brand)} appears (or doesn't) when AI engines answer buyer questions. Visibility score {score}/100 ({g}). An EchoRank audit.">
<script type="application/ld+json">{json.dumps({
    "@context": "https://schema.org",
    "@type": "Report",
    "name": f"{brand} — AI Search Visibility Report",
    "datePublished": generated,
    "author": {"@type": "Organization", "name": "EchoRank"},
    "about": f"AI search visibility of {brand} across AI answer engines",
})}</script>
<style>
  :root {{ --ink:#101828; --mut:#667085; --line:#e4e7ec; --bg:#f8fafc; --card:#ffffff; --accent:#4f46e5; }}
  * {{ box-sizing:border-box; margin:0 }}
  body {{ font:16px/1.6 -apple-system,'Segoe UI',Inter,Roboto,sans-serif; color:var(--ink); background:var(--bg) }}
  header {{ background:#0b1220; color:#e6e9f2; padding:44px 20px }}
  .wrap {{ max-width:880px; margin:0 auto; padding:0 4px }}
  .brandline {{ font-size:13px; letter-spacing:.12em; text-transform:uppercase; color:#8ea0c0 }}
  h1 {{ font-size:clamp(26px,4.5vw,38px); line-height:1.15; margin:10px 0 6px }}
  .sub {{ color:#aab6cc; max-width:60ch }}
  .scorebar {{ display:flex; gap:14px; flex-wrap:wrap; margin-top:26px }}
  .tile {{ background:#111a2e; border:1px solid #1e2a44; border-radius:12px; padding:14px 18px; min-width:130px }}
  .tile .n {{ font-size:30px; font-weight:700 }}
  .tile .l {{ font-size:12px; color:#8ea0c0; text-transform:uppercase; letter-spacing:.08em }}
  main {{ padding:36px 20px 60px }}
  section {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:26px 26px 20px; margin:0 0 22px }}
  h2 {{ font-size:20px; margin-bottom:4px }}
  .lede {{ color:var(--mut); font-size:14px; margin-bottom:16px }}
  table {{ width:100%; border-collapse:collapse; font-size:14.5px }}
  th {{ text-align:left; font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--mut); padding:8px 10px; border-bottom:1px solid var(--line) }}
  td {{ padding:10px; border-bottom:1px solid var(--line); vertical-align:top }}
  tr:last-child td {{ border-bottom:none }}
  .q {{ font-weight:600 }}
  .ev {{ color:var(--mut); font-size:13.5px }}
  .pill {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:12.5px; font-weight:600; white-space:nowrap }}
  ol.road {{ padding-left:0; counter-reset:rd; list-style:none }}
  ol.road li {{ border:1px solid var(--line); border-radius:10px; padding:14px 16px 10px; margin-bottom:10px; counter-increment:rd; position:relative; padding-left:52px }}
  ol.road li::before {{ content:counter(rd); position:absolute; left:14px; top:14px; width:26px; height:26px; border-radius:8px; background:var(--accent); color:#fff; font-weight:700; font-size:14px; display:flex; align-items:center; justify-content:center }}
  .rt {{ display:flex; justify-content:space-between; gap:10px; align-items:baseline }}
  .effort {{ font-size:12px; color:var(--mut); white-space:nowrap }}
  ol.road p {{ color:var(--mut); font-size:14px; margin-top:2px }}
  ul.notes {{ color:var(--mut); font-size:14px; padding-left:18px }}
  footer {{ text-align:center; color:var(--mut); font-size:13.5px; padding:0 20px 46px }}
  footer a {{ color:var(--accent); text-decoration:none }}
  .cta {{ display:inline-block; background:var(--accent); color:#fff; padding:12px 22px; border-radius:10px; text-decoration:none; font-weight:600; margin-top:8px }}
  .tblwrap {{ overflow-x:auto }}
</style>
</head>
<body>
<header><div class="wrap">
  <div class="brandline">EchoRank · AI Search Visibility Report</div>
  <h1>{e(brand)}</h1>
  <p class="sub">{e(fx.get('tagline', f"How {brand} shows up when AI engines answer its buyers' questions."))}
  Audited {e(generated)} · Category: {e(fx.get('category', '—'))} · Benchmarked against: {e(competitors)}</p>
  <div class="scorebar">
    <div class="tile"><div class="n" style="color:{col}">{score}<span style="font-size:16px;color:#8ea0c0">/100</span></div><div class="l">Visibility score · {g}</div></div>
    <div class="tile"><div class="n">{engine_pct}%</div><div class="l">AI-answer presence</div></div>
    <div class="tile"><div class="n">{sources_pct}%</div><div class="l">Citation footprint</div></div>
    <div class="tile"><div class="n">{ready_pct}%</div><div class="l">Site AI-readiness</div></div>
  </div>
</div></header>
<main><div class="wrap">

<section>
  <h2>Executive summary</h2>
  <p>{e(fx.get('summary', ''))}</p>
</section>

<section>
  <h2>Money-query share of voice</h2>
  <p class="lede">The buyer questions that decide this category — and whether AI engines name {e(brand)} when answering them.</p>
  <div class="tblwrap"><table>
    <tr><th>Buyer question</th><th>{e(brand)}</th><th>Who wins it</th><th>Evidence</th></tr>
    {''.join(mq_rows)}
  </table></div>
</section>

<section>
  <h2>Citation-source footprint</h2>
  <p class="lede">AI answers are assembled from a known set of sources. Presence in these channels is what gets a brand quoted.</p>
  <div class="tblwrap"><table>
    <tr><th>Channel</th><th>Presence</th><th>What we found</th></tr>
    {''.join(src_rows)}
  </table></div>
</section>

<section>
  <h2>Site AI-readiness — {readiness.get('score', '—')}/100</h2>
  <p class="lede">Automated probe of {e(readiness.get('base_url', fx.get('domain', '')))}: can AI crawlers read, parse, and quote this site?</p>
  <div class="tblwrap"><table>{ready_rows}</table></div>
  {f"<ul class='notes' style='margin-top:12px'>{ready_notes}</ul>" if ready_notes else ""}
</section>

<section>
  <h2>Fix roadmap — highest leverage first</h2>
  <p class="lede">The five moves that most improve how often AI engines say “{e(brand)}”.</p>
  <ol class="road">{''.join(road_items)}</ol>
</section>

<section>
  <h2>Methodology &amp; disclosure</h2>
  <ul class="notes">{meth}</ul>
</section>

</div></main>
<footer>
  <p>Generated by <a href="/">EchoRank</a> — an AI-visibility auditor founded and operated by an AI, supervised by a human.</p>
  <p style="margin-top:10px"><a class="cta" href="/#audit">Get your brand's free audit →</a></p>
</footer>
</body>
</html>
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(page)
    print(f"wrote {out_path}  ({brand}: {score}/100 {g})")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    brand_dir = sys.argv[1]
    out_path = os.path.join(brand_dir, "index.html")
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]
    render(brand_dir, out_path)


if __name__ == "__main__":
    main()
