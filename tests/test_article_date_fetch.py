"""
Tests for the optional article-page date-fetch enrichment in
collectors/web_scraper.py (see DATE_FILTER_FIX.md).

These verify the guardrails that keep it safe on Render's 30s worker timeout:
  - a date already found in the URL is never re-fetched
  - a request is only spent on headlines that match the health keyword filter
  - the per-run fetch cap is respected
  - the feature can be switched off via config
  - scrape_site() on its own does no article fetching (the enrichment runs
    once, in collect())

All network access is mocked -- no live requests.

Run with:  python -m unittest discover tests
"""

import os
import sys
import unittest
import unittest.mock
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from collectors import web_scraper  # noqa: E402


SITE = {
    "name": "Test Site", "url": "https://fakesite.rw/", "language": "en",
    "category": "local_online", "link_selector": "h2.entry-title a",
}

HOMEPAGE = """
<html><body>
  <article><h2 class="entry-title"><a href="/story/malaria-treatment-rolled-out-in-rwanda-hospitals">Malaria treatment rolled out in Rwanda hospitals</a></h2></article>
  <article><h2 class="entry-title"><a href="/story/football-club-wins-a-big-tournament-in-kigali">Football club wins a big tournament in Kigali</a></h2></article>
  <article><h2 class="entry-title"><a href="/2026/07/14/health-ministry-launches-vaccination-campaign">Health ministry launches vaccination campaign</a></h2></article>
</body></html>
"""

# Article page that states a real publish date (both a <time> tag and an OG
# meta tag, which extract_date_from_element knows how to read).
ARTICLE_WITH_DATE = """<html><head>
<meta property="article:published_time" content="2026-07-08T09:00:00Z">
</head><body>
<time datetime="2026-07-08T09:00:00Z">8 July 2026</time>
<p>Article body.</p>
</body></html>"""


def _find(items, needle):
    return next(i for i in items if needle in i["title"].lower())


class TestArticleDateFetch(unittest.TestCase):
    def setUp(self):
        self._orig_sites = config.SCRAPE_SITES

    def tearDown(self):
        config.SCRAPE_SITES = self._orig_sites
        for attr in ("ARTICLE_DATE_FETCH_MAX", "ARTICLE_DATE_FETCH_ENABLED",
                     "ARTICLE_DATE_FETCH_BUDGET_SECONDS", "ARTICLE_DATE_FETCH_TIMEOUT_SECONDS"):
            if hasattr(config, attr):
                delattr(config, attr)

    def test_ordering_and_date_sources(self):
        """URL date is free; article fetch happens only for keyword-matching
        undated headlines; non-health and already-dated ones are not fetched."""
        config.SCRAPE_SITES = [SITE]
        fetched = []

        def fake_fetch(url, params=None, timeout=None):
            fetched.append(url)
            return HOMEPAGE if url == SITE["url"] else ARTICLE_WITH_DATE

        with unittest.mock.patch("collectors.web_scraper.fetch_url", side_effect=fake_fetch):
            items = web_scraper.collect()

        malaria = _find(items, "malaria")
        football = _find(items, "football")
        vaccination = _find(items, "vaccination")

        self.assertEqual(len(items), 3)
        # Recovered from the article page:
        self.assertIsNotNone(malaria["published_at"])
        self.assertEqual(malaria["published_at"].date(), date(2026, 7, 8))
        # Left undated (not health-relevant, so no request was spent):
        self.assertIsNone(football["published_at"])
        # Dated straight from the URL, no fetch:
        self.assertIsNotNone(vaccination["published_at"])
        self.assertEqual(vaccination["published_at"].date(), date(2026, 7, 14))

        self.assertIn(malaria["url"], fetched)
        self.assertNotIn(football["url"], fetched)
        self.assertNotIn(vaccination["url"], fetched)
        self.assertEqual([u for u in fetched if u != SITE["url"]], [malaria["url"]])

    def test_fetch_cap_is_respected(self):
        config.SCRAPE_SITES = [SITE]
        config.ARTICLE_DATE_FETCH_MAX = 2
        many = "<html><body>" + "".join(
            f'<article><h2 class="entry-title"><a href="/story/malaria-outbreak-update-number-{n}-in-rwanda">'
            f'Malaria outbreak update number {n} in Rwanda</a></h2></article>'
            for n in range(6)
        ) + "</body></html>"
        fetched = []

        def fake_fetch(url, params=None, timeout=None):
            fetched.append(url)
            return many if url == SITE["url"] else ARTICLE_WITH_DATE

        with unittest.mock.patch("collectors.web_scraper.fetch_url", side_effect=fake_fetch):
            items = web_scraper.collect()

        article_fetches = [u for u in fetched if u != SITE["url"]]
        dated = [i for i in items if i["published_at"] is not None]
        self.assertEqual(len(items), 6)
        self.assertEqual(len(article_fetches), 2)
        self.assertEqual(len(dated), 2)

    def test_can_be_disabled(self):
        config.SCRAPE_SITES = [SITE]
        config.ARTICLE_DATE_FETCH_ENABLED = False
        fetched = []

        def fake_fetch(url, params=None, timeout=None):
            fetched.append(url)
            return HOMEPAGE if url == SITE["url"] else ARTICLE_WITH_DATE

        with unittest.mock.patch("collectors.web_scraper.fetch_url", side_effect=fake_fetch):
            items = web_scraper.collect()

        self.assertEqual([u for u in fetched if u != SITE["url"]], [])
        self.assertIsNone(_find(items, "malaria")["published_at"])

    def test_scrape_site_alone_does_no_article_fetching(self):
        """The enrichment runs once in collect(); a direct scrape_site() call
        must only hit the homepage -- this is what keeps
        test_scrape_site_sets_published_at_none in test_pipeline.py valid."""
        fetched = []

        def fake_fetch(url, params=None, timeout=None):
            fetched.append(url)
            return HOMEPAGE

        with unittest.mock.patch("collectors.web_scraper.fetch_url", side_effect=fake_fetch):
            items = web_scraper.scrape_site(SITE)

        self.assertEqual(fetched, [SITE["url"]])
        self.assertIsNone(_find(items, "malaria")["published_at"])
        # The URL-dated one still gets its date without any article fetch:
        self.assertEqual(_find(items, "vaccination")["published_at"].date(), date(2026, 7, 14))


if __name__ == "__main__":
    unittest.main()
