import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fetch_bullion_news import (
    parse_rss_items,
    filter_recent,
    filter_listicles,
    tag_sentiment,
    build_news_envelope,
)

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Yahoo Finance</title>
<item>
<title>Stocks rally as Fed signals rate cut</title>
<link>https://finance.yahoo.com/news/stocks-rally-1.html</link>
<pubDate>2026-09-01T16:50:13Z</pubDate>
</item>
<item>
<title>Dow, S&amp;P 500, Nasdaq drop as bond yields weigh on stocks</title>
<link>https://finance.yahoo.com/news/stocks-drop-2.html</link>
<pubDate>2026-09-01T08:06:17Z</pubDate>
</item>
<item>
<title>Best Wells Fargo credit cards (2026)</title>
<link>https://finance.yahoo.com/news/best-cards.html</link>
<pubDate>2026-06-01T16:43:10Z</pubDate>
</item>
</channel></rss>
"""

# Real RSS 2.0 spec mandates RFC822 pubDates; Yahoo's actual feed uses ISO
# 8601 instead (confirmed against the live feed 2026-09-01). Support both
# rather than assume the spec-compliant format is what ships in practice.
RFC822_ITEM_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
<title>Gold gains as dollar weakens</title>
<link>https://example.com/gold-gains.html</link>
<pubDate>Tue, 01 Sep 2026 16:50:13 +0000</pubDate>
</item>
</channel></rss>
"""


class TestParseRssItems(unittest.TestCase):
    def test_extracts_title_link_and_pubdate(self):
        items = parse_rss_items(SAMPLE_RSS)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["title"], "Stocks rally as Fed signals rate cut")
        self.assertEqual(items[0]["link"], "https://finance.yahoo.com/news/stocks-rally-1.html")
        self.assertEqual(items[0]["published"],
                          datetime(2026, 9, 1, 16, 50, 13, tzinfo=timezone.utc))

    def test_unescapes_html_entities_in_title(self):
        items = parse_rss_items(SAMPLE_RSS)
        self.assertEqual(items[1]["title"],
                          "Dow, S&P 500, Nasdaq drop as bond yields weigh on stocks")

    def test_no_items_returns_empty_list(self):
        self.assertEqual(parse_rss_items("<rss><channel></channel></rss>"), [])

    def test_parses_rfc822_pubdate_too(self):
        # RSS 2.0's own spec format — a different feed than Yahoo's might use it.
        items = parse_rss_items(RFC822_ITEM_RSS)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["published"],
                          datetime(2026, 9, 1, 16, 50, 13, tzinfo=timezone.utc))


class TestFilterRecent(unittest.TestCase):
    NOW = datetime(2026, 9, 1, 18, 0, 0, tzinfo=timezone.utc)

    def test_keeps_items_published_within_window(self):
        items = parse_rss_items(SAMPLE_RSS)
        recent = filter_recent(items, self.NOW, max_age_hours=48)
        titles = {i["title"] for i in recent}
        self.assertIn("Stocks rally as Fed signals rate cut", titles)

    def test_drops_stale_evergreen_items(self):
        # The credit-card listicle is months old — this is the exact noise
        # the real Yahoo Finance feed mixes into its "latest" items.
        items = parse_rss_items(SAMPLE_RSS)
        recent = filter_recent(items, self.NOW, max_age_hours=48)
        titles = {i["title"] for i in recent}
        self.assertNotIn("Best Wells Fargo credit cards (2026)", titles)

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(filter_recent([], self.NOW, max_age_hours=48), [])


class TestFilterListicles(unittest.TestCase):
    def test_drops_leading_digit_listicle_titles(self):
        items = [{"title": "5 Easy Side Gigs to Quickly Eliminate Credit Card Debt"}]
        self.assertEqual(filter_listicles(items), [])

    def test_keeps_titles_that_merely_start_with_a_numbered_fact(self):
        # "161-year-old ..." starts with digits but isn't a numbered listicle
        # (no space right after the digits) -- must not be filtered.
        items = [{"title": "161-year-old kids clothing giant closes 29 more stores"}]
        self.assertEqual(filter_listicles(items), items)

    def test_keeps_normal_market_headlines(self):
        items = [{"title": "Stocks rally as Fed signals rate cut"}]
        self.assertEqual(filter_listicles(items), items)


class TestTagSentiment(unittest.TestCase):
    def test_bullish_keyword_tags_bullish(self):
        self.assertEqual(tag_sentiment("Stocks rally as Fed signals rate cut"), "bullish")

    def test_bearish_keyword_tags_bearish(self):
        self.assertEqual(tag_sentiment("Dow drops as recession fears mount"), "bearish")

    def test_no_keyword_tags_neutral(self):
        self.assertEqual(tag_sentiment("FDA approval marks a turning point for BeOne"), "neutral")

    def test_mixed_keywords_tags_neutral(self):
        # One bullish, one bearish signal in the same headline — no clear lean.
        self.assertEqual(tag_sentiment("Stocks rally even as recession fears mount"), "neutral")

    def test_case_insensitive(self):
        self.assertEqual(tag_sentiment("SELLOFF hits tech stocks"), "bearish")


class TestBuildNewsEnvelope(unittest.TestCase):
    def test_envelope_shape(self):
        items = [{
            "title": "Stocks rally as Fed signals rate cut",
            "link": "https://finance.yahoo.com/news/stocks-rally-1.html",
            "published": datetime(2026, 9, 1, 16, 50, 13, tzinfo=timezone.utc),
        }]
        env = build_news_envelope(items, "2026-09-01T18:00:00Z")
        self.assertEqual(env["generated_at"], "2026-09-01T18:00:00Z")
        self.assertEqual(len(env["headlines"]), 1)
        h = env["headlines"][0]
        self.assertEqual(h["headline"], "Stocks rally as Fed signals rate cut")
        self.assertEqual(h["link"], "https://finance.yahoo.com/news/stocks-rally-1.html")
        self.assertEqual(h["published"], "2026-09-01T16:50:13Z")
        self.assertEqual(h["sentiment"], "bullish")


if __name__ == "__main__":
    unittest.main()
