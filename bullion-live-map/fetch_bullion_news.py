#!/usr/bin/env python3
"""Daily news-headline fetch for the Bullion news bar.

Pulls Yahoo Finance's general RSS feed (free, no key) and writes news.json:
a short list of recent, sentiment-tagged headlines for the Markets tab's
scrolling ticker. Deliberately does NOT call any LLM/paid API — sentiment is
a local bullish/bearish keyword scan, same spirit as the map's existing
runLocalAnalysis JS fallback, just done once here in Python so there is one
wordlist, not two copies that can drift apart.

The raw feed mixes today's real market news with evergreen listicles
("best credit cards of 2026") that carry stale pubDates — filter_recent()
is what separates them; it is not optional polish.
"""
import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

NEWS_RSS_URL = "https://finance.yahoo.com/news/rssindex"
NEWS_OUT_PATH = "news.json"
MAX_AGE_HOURS = 48
MAX_HEADLINES = 20

# A deliberately small, literal keyword scan -- not NLP, not weighted, just
# enough to separate "clearly up" from "clearly down" headlines. Ties (or no
# match) fall back to neutral rather than guessing.
BULLISH_WORDS = [
    "rally", "rallies", "surge", "surges", "soar", "soars", "jump", "jumps",
    "rate cut", "gains", "gain", "record high", "upgrade", "upgrades",
    "beat", "beats", "breakout", "rebound", "rebounds",
]
BEARISH_WORDS = [
    "recession", "selloff", "sell-off", "plunge", "plunges", "slump",
    "slumps", "downgrade", "downgrades", "miss", "misses", "crash",
    "crashes", "tumble", "tumbles", "drop", "drops", "falls", "fall",
    "weigh", "weighs",
]


def _parse_pub_date(raw):
    """Yahoo's real feed ships ISO 8601 (`2026-08-31T15:33:00Z`), not the
    RFC822 the RSS 2.0 spec mandates (confirmed against the live feed
    2026-09-01) -- try both rather than assume the spec-compliant format.
    """
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        try:
            dt = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_rss_items(xml_text):
    """Extract title/link/pubDate from an RSS 2.0 <item> list.

    Regex, not an XML parser -- this project already parses SDMX/JSON via
    stdlib only elsewhere; Yahoo's feed is small and consistently shaped, so
    a targeted regex avoids pulling in a new dependency for one feed.
    """
    items = []
    for block in re.findall(r"<item>(.*?)</item>", xml_text, re.S):
        title_m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.S)
        link_m = re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", block, re.S)
        pub_m = re.search(r"<pubDate>(.*?)</pubDate>", block, re.S)
        if not (title_m and link_m and pub_m):
            continue
        published = _parse_pub_date(pub_m.group(1).strip())
        if published is None:
            continue
        items.append({
            "title": html.unescape(title_m.group(1).strip()),
            "link": link_m.group(1).strip(),
            "published": published,
        })
    return items


def filter_recent(items, now, max_age_hours=MAX_AGE_HOURS):
    cutoff = now - timedelta(hours=max_age_hours)
    return [i for i in items if i["published"] >= cutoff]


_LISTICLE_TITLE = re.compile(r"^\d+\s")


def filter_listicles(items):
    """Drop generic personal-finance listicles ("5 Easy Side Gigs...").

    The 48h recency filter doesn't catch these -- they're freshly published,
    just not market news. They're also the dominant noise in Yahoo's general
    feed (confirmed against the live feed 2026-09-01): about half of a
    same-day pull is this shape. A leading "<digits><space>" title is a
    cheap, reliable tell; a real headline like "161-year-old kids clothing
    giant closes 29 more stores" has no space right after its digits, so it
    survives.
    """
    return [i for i in items if not _LISTICLE_TITLE.match(i["title"])]


def tag_sentiment(title):
    lower = title.lower()
    bull = sum(1 for w in BULLISH_WORDS if w in lower)
    bear = sum(1 for w in BEARISH_WORDS if w in lower)
    if bull > bear:
        return "bullish"
    if bear > bull:
        return "bearish"
    return "neutral"


def build_news_envelope(items, generated_at):
    headlines = []
    for i in items:
        headlines.append({
            "headline": i["title"],
            "link": i["link"],
            "published": i["published"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sentiment": tag_sentiment(i["title"]),
        })
    return {"generated_at": generated_at, "headlines": headlines}


def fetch_news_rss(url=NEWS_RSS_URL, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main():
    now = datetime.now(timezone.utc)
    try:
        xml_text = fetch_news_rss()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        # Same philosophy as fetch_bullion_data.py: a failed fetch leaves
        # yesterday's news.json in place rather than writing an empty or
        # truncated ticker. This is a quality-of-life feature, not
        # load-bearing data -- it is not worth failing the whole daily cron
        # over, but it must not go silently stale either, so this prints
        # loudly to stderr for the workflow log to catch.
        print(f"News fetch failed ({e}); leaving existing {NEWS_OUT_PATH} untouched.",
              file=sys.stderr)
        sys.exit(1)

    items = parse_rss_items(xml_text)
    items = filter_recent(items, now)
    items = filter_listicles(items)
    items = items[:MAX_HEADLINES]

    generated_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = build_news_envelope(items, generated_at)

    with open(NEWS_OUT_PATH, "w") as f:
        json.dump(envelope, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote {NEWS_OUT_PATH} with {len(envelope['headlines'])} headlines "
          f"(of {len(parse_rss_items(xml_text))} fetched, filtered to last "
          f"{MAX_AGE_HOURS}h).")


if __name__ == "__main__":
    main()
