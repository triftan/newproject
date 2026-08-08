#!/usr/bin/env python3
"""EchoRank site AI-readiness probe.

Checks how ready a site is to be read, cited, and quoted by AI search engines:
  - llms.txt / llms-full.txt presence
  - robots.txt policy toward AI crawlers (GPTBot, ClaudeBot, PerplexityBot, ...)
  - schema.org JSON-LD coverage on the homepage
  - sitemap presence
  - answer-extractability of the homepage (headings, text volume, FAQ signals)

Usage:
  python3 readiness.py <domain-or-url> [--out brands/<slug>/readiness.json]

Stdlib only. Honors HTTPS_PROXY; loads the agent-proxy CA bundle when present.
"""
import json
import os
import re
import ssl
import sys
import urllib.request
import urllib.error
from html.parser import HTMLParser

CA_BUNDLE = "/root/.ccr/ca-bundle.crt"
UA = "Mozilla/5.0 (compatible; EchoRankBot/0.1; +https://echorank.vercel.app/methodology)"

AI_CRAWLERS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",
    "ClaudeBot", "Claude-Web", "anthropic-ai",
    "PerplexityBot", "Perplexity-User",
    "Google-Extended", "GoogleOther",
    "CCBot", "Amazonbot", "meta-externalagent", "Bytespider",
]


def _ctx():
    if os.path.exists(CA_BUNDLE):
        return ssl.create_default_context(cafile=CA_BUNDLE)
    return ssl.create_default_context()


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            body = r.read(1_500_000)
            return r.status, body.decode("utf-8", errors="replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, "", {}
    except Exception as e:
        return None, str(e), {}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta_description = ""
        self.h1 = []
        self.h2 = []
        self.h3 = []
        self.jsonld = []
        self._stack = []
        self._text = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self._stack.append(tag)
        if tag in ("script", "style", "noscript", "svg"):
            self._skip += 1
            if tag == "script" and a.get("type", "").lower() == "application/ld+json":
                self._stack[-1] = "jsonld"
        if tag == "meta" and a.get("name", "").lower() == "description":
            self.meta_description = a.get("content", "")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg"):
            self._skip = max(0, self._skip - 1)
        while self._stack and self._stack.pop() not in (tag, "jsonld"):
            pass

    def handle_data(self, data):
        top = self._stack[-1] if self._stack else ""
        if top == "jsonld":
            self.jsonld.append(data)
            return
        if self._skip:
            return
        t = data.strip()
        if not t:
            return
        if top == "title" and not self.title:
            self.title = t
        elif top == "h1":
            self.h1.append(t)
        elif top == "h2":
            self.h2.append(t)
        elif top == "h3":
            self.h3.append(t)
        self._text.append(t)

    @property
    def text(self):
        return " ".join(self._text)


def parse_robots(body):
    """Return {crawler: 'allowed'|'blocked'|'unspecified'} for AI crawlers."""
    groups = []  # (set(agents_lower), [rules])
    agents, rules = set(), []
    for raw in body.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, val = [p.strip() for p in line.split(":", 1)]
        key = key.lower()
        if key == "user-agent":
            if rules:
                groups.append((agents, rules))
                agents, rules = set(), []
            agents.add(val.lower())
        elif key in ("allow", "disallow"):
            rules.append((key, val))
    if agents:
        groups.append((agents, rules))

    def verdict(name):
        nl = name.lower()
        matched = None
        for ag, rl in groups:
            if nl in ag:
                matched = rl
                break
        if matched is None:
            for ag, rl in groups:
                if "*" in ag:
                    matched = rl
                    break
        if matched is None:
            return "unspecified"
        for key, val in matched:
            if key == "disallow" and val == "/":
                return "blocked"
        return "allowed"

    return {name: verdict(name) for name in AI_CRAWLERS}


def extract_schema_types(jsonld_blocks):
    types = set()
    for block in jsonld_blocks:
        try:
            data = json.loads(block)
        except Exception:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                t = node.get("@type")
                if isinstance(t, str):
                    types.add(t)
                elif isinstance(t, list):
                    types.update(x for x in t if isinstance(x, str))
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    return sorted(types)


def probe(domain):
    domain = re.sub(r"^https?://", "", domain).strip("/").split("/")[0]
    base = f"https://{domain}"
    out = {"domain": domain, "base_url": base, "checks": {}}
    c = out["checks"]

    status, home, _ = fetch(base)
    c["homepage_reachable"] = bool(status and 200 <= status < 400)
    page = PageParser()
    if c["homepage_reachable"]:
        try:
            page.feed(home)
        except Exception:
            pass
    words = len(page.text.split())
    faq_signal = bool(re.search(r"\b(faq|frequently asked|common questions)\b", page.text, re.I))
    c["homepage"] = {
        "title": page.title[:200],
        "meta_description": page.meta_description[:300],
        "h1_count": len(page.h1),
        "h2_count": len(page.h2),
        "visible_word_count": words,
        "faq_signal": faq_signal,
        "schema_types": extract_schema_types(page.jsonld),
    }

    s, body, _ = fetch(f"{base}/llms.txt")
    c["llms_txt"] = bool(s == 200 and body.strip() and "<html" not in body[:500].lower())
    s, body, _ = fetch(f"{base}/llms-full.txt")
    c["llms_full_txt"] = bool(s == 200 and body.strip() and "<html" not in body[:500].lower())

    s, body, _ = fetch(f"{base}/robots.txt")
    c["robots_txt_present"] = bool(s == 200 and body.strip())
    c["ai_crawlers"] = parse_robots(body) if c["robots_txt_present"] else {n: "unspecified" for n in AI_CRAWLERS}
    c["sitemap_in_robots"] = bool(c["robots_txt_present"] and re.search(r"(?im)^sitemap\s*:", body))

    s, _, _ = fetch(f"{base}/sitemap.xml")
    c["sitemap_xml"] = bool(s and 200 <= s < 400)

    # --- scoring (0-100) ---
    score = 0
    notes = []
    if c["homepage_reachable"]:
        score += 10
    else:
        notes.append("Homepage unreachable to a plain HTTPS fetch — AI crawlers may see nothing at all.")
    hp = c["homepage"]
    if hp["h1_count"] >= 1:
        score += 5
    else:
        notes.append("No H1 on the homepage — answer engines lean on heading structure to extract claims.")
    if hp["h2_count"] >= 2:
        score += 5
    if hp["visible_word_count"] >= 250:
        score += 10
    else:
        notes.append(f"Only ~{hp['visible_word_count']} extractable words on the homepage — likely JS-rendered; "
                     "most AI crawlers read raw HTML and will see a near-empty page.")
    if hp["meta_description"]:
        score += 5
    if hp["faq_signal"]:
        score += 5
    schema_types = set(hp["schema_types"])
    if schema_types:
        score += 5
        if schema_types & {"Organization", "Corporation", "LocalBusiness"}:
            score += 5
        if schema_types & {"FAQPage", "Question", "HowTo"}:
            score += 5
        if schema_types & {"Product", "Service", "SoftwareApplication", "Offer"}:
            score += 5
    else:
        notes.append("No schema.org JSON-LD found — engines get zero structured facts about the business.")
    if c["llms_txt"]:
        score += 10
    else:
        notes.append("No llms.txt — the emerging standard for handing AI models a curated map of your site.")
    if c["llms_full_txt"]:
        score += 5
    blocked = [k for k, v in c["ai_crawlers"].items() if v == "blocked"]
    answer_bots = {"GPTBot", "OAI-SearchBot", "ClaudeBot", "PerplexityBot"}
    blocked_answer_bots = sorted(set(blocked) & answer_bots)
    if not blocked_answer_bots:
        score += 15
    else:
        notes.append("robots.txt blocks " + ", ".join(blocked_answer_bots) +
                     " — the site is invisible to those engines BY ITS OWN CHOICE.")
    if c["robots_txt_present"]:
        score += 5
    if c["sitemap_xml"] or c["sitemap_in_robots"]:
        score += 5

    out["score"] = min(100, score)
    out["max_score"] = 100
    out["notes"] = notes
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    domain = sys.argv[1]
    out_path = None
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]
    result = probe(domain)
    text = json.dumps(result, indent=2)
    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            f.write(text + "\n")
        print(f"wrote {out_path}  (score {result['score']}/100)")
    else:
        print(text)


if __name__ == "__main__":
    main()
