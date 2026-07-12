"""
Parasnivesh Capital — daily market-news headline fetcher.

Pulls ONLY the headline text and the article link from each source's public
news/blog listing page — never the article body. This is republished as a
"what's happening" pointer list with attribution and an outbound link, similar
to how a news aggregator works. It intentionally does not copy paragraphs,
summaries, or images from the source sites.

Run daily by .github/workflows/daily-news.yml
Writes: news.json (consumed by index.html at runtime)
"""
import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ParasniveshNewsBot/1.0; "
                  "+https://parasniveshcapital.com)"
}

SOURCES = [
    {
        "name": "UnlistedZone",
        "url": "https://unlistedzone.com/blogs",
        "base": "https://unlistedzone.com",
    },
    {
        "name": "Planify",
        "url": "https://www.planify.in/planify-news/",
        "base": "https://www.planify.in",
    },
    {
        "name": "Precize",
        "url": "https://www.precize.in/unlistedsharesnews",
        "base": "https://www.precize.in",
    },
]

MIN_HEADLINE_LEN = 25
MAX_HEADLINE_LEN = 160
ITEMS_PER_SOURCE = 6

# Anchor text / href patterns that are almost always nav/footer/legal links,
# not article headlines — skip these.
SKIP_PATTERNS = re.compile(
    r"(privacy|terms|disclaimer|contact|about|sign ?in|sign ?up|log ?in|"
    r"become a partner|download|app store|google play|screener|watchlist|"
    r"open an account|view all|read more|learn more|subscribe|whatsapp channel|"
    r"cookie|faq)",
    re.IGNORECASE,
)


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def fetch_source(source):
    items = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[warn] could not fetch {source['name']}: {exc}", file=sys.stderr)
        return items

    soup = BeautifulSoup(resp.text, "html.parser")
    seen = set()

    for a in soup.find_all("a", href=True):
        text = clean_text(a.get_text())
        href = a["href"]

        if not (MIN_HEADLINE_LEN <= len(text) <= MAX_HEADLINE_LEN):
            continue
        if SKIP_PATTERNS.search(text):
            continue

        full_url = urljoin(source["base"], href)
        if not full_url.startswith(source["base"]):
            continue
        if full_url in seen:
            continue
        seen.add(full_url)

        items.append({
            "source": source["name"],
            "headline": text,
            "url": full_url,
        })

        if len(items) >= ITEMS_PER_SOURCE:
            break

    return items


def main():
    all_items = []
    for source in SOURCES:
        all_items.extend(fetch_source(source))

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "items": all_items,
    }

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(all_items)} items to news.json")


if __name__ == "__main__":
    main()
