"""
Offline tests for the Rwanda Health Media Scanning System pipeline.

These use synthetic RSS XML and item dicts -- no network access needed --
so the collection/filtering/dedup/scoring/windowing/storage logic can be
verified without hitting live feeds. Run with:

    python -m unittest discover tests
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db  # noqa: E402
from collectors.rss_utils import parse_feed, parse_rss_datetime  # noqa: E402
from processing import filter_relevance, dedup, highlight_score  # noqa: E402
import scan  # noqa: E402


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Sample Feed</title>
  <item>
    <title>New malaria treatment rolled out in Rwanda hospitals</title>
    <link>https://example.com/malaria-treatment</link>
    <pubDate>Fri, 10 Jul 2026 09:00:00 GMT</pubDate>
    <description>The Ministry of Health announced a new malaria protocol.</description>
  </item>
  <item>
    <title>Kigali football club wins regional tournament</title>
    <link>https://example.com/football</link>
    <pubDate>Fri, 10 Jul 2026 08:00:00 GMT</pubDate>
    <description>A sports story with no health relevance.</description>
  </item>
</channel>
</rss>
"""

SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Sample Atom Feed</title>
  <entry>
    <title>Rwanda Biomedical Centre launches vaccination drive</title>
    <link href="https://example.com/vaccination"/>
    <updated>2026-07-09T12:00:00Z</updated>
    <summary>RBC announced a new vaccination campaign this week.</summary>
  </entry>
</feed>
"""


class TestFeedParsing(unittest.TestCase):
    def test_parses_rss2_items(self):
        items = parse_feed(SAMPLE_RSS)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "New malaria treatment rolled out in Rwanda hospitals")
        self.assertIsNotNone(items[0]["published_at"])

    def test_parses_atom_entries(self):
        items = parse_feed(SAMPLE_ATOM)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], "https://example.com/vaccination")

    def test_malformed_xml_returns_empty_list_not_crash(self):
        items = parse_feed("<not valid xml")
        self.assertEqual(items, [])

    def test_rfc2822_date_parses(self):
        dt = parse_rss_datetime("Fri, 10 Jul 2026 09:00:00 GMT")
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 7)
        self.assertEqual(dt.day, 10)

    def test_iso_date_parses(self):
        dt = parse_rss_datetime("2026-07-09T12:00:00Z")
        self.assertEqual(dt.day, 9)

    def test_unparseable_date_returns_none(self):
        self.assertIsNone(parse_rss_datetime("not a date"))
        self.assertIsNone(parse_rss_datetime(None))


class TestRelevanceFilter(unittest.TestCase):
    def test_health_item_is_relevant(self):
        item = {"title": "New malaria treatment rolled out in Rwanda hospitals", "summary": ""}
        is_rel, matches = filter_relevance.is_relevant(item)
        self.assertTrue(is_rel)
        self.assertIn("malaria", matches)
        self.assertIn("hospital", matches)

    def test_non_health_item_is_not_relevant(self):
        item = {"title": "Kigali football club wins regional tournament", "summary": "A sports story."}
        is_rel, matches = filter_relevance.is_relevant(item)
        self.assertFalse(is_rel)
        self.assertEqual(matches, [])

    def test_kinyarwanda_keyword_matches(self):
        item = {"title": "Ubuzima bw'ababyeyi butera impungenge", "summary": ""}
        is_rel, matches = filter_relevance.is_relevant(item)
        self.assertTrue(is_rel)

    def test_french_keyword_matches(self):
        item = {"title": "Le ministere de la sante annonce une nouvelle campagne", "summary": ""}
        is_rel, matches = filter_relevance.is_relevant(item)
        self.assertTrue(is_rel)

    def test_filter_items_annotates_matched_keywords(self):
        items = [
            {"title": "Malaria cases rise", "summary": "", "source_name": "A"},
            {"title": "Football scores", "summary": "", "source_name": "B"},
        ]
        result = filter_relevance.filter_items(items)
        self.assertEqual(len(result), 1)
        self.assertIn("matched_keywords", result[0])

    def test_filter_does_not_mutate_input(self):
        items = [{"title": "Malaria cases rise", "summary": "", "source_name": "A"}]
        filter_relevance.filter_items(items)
        self.assertNotIn("matched_keywords", items[0])


class TestDedup(unittest.TestCase):
    def test_near_duplicate_titles_are_folded(self):
        items = [
            {"title": "New malaria treatment rolled out in Rwanda hospitals", "source_name": "Outlet A", "matched_keywords": ["malaria"]},
            {"title": "New malaria treatment rolled out in Rwanda's hospitals", "source_name": "Outlet B", "matched_keywords": ["malaria"]},
        ]
        unique_items, duplicates = dedup.deduplicate(items)
        self.assertEqual(len(unique_items), 1)
        self.assertEqual(len(duplicates), 1)
        self.assertIn("Outlet B", unique_items[0]["covered_by"])

    def test_distinct_stories_are_not_folded(self):
        items = [
            {"title": "New malaria treatment rolled out in hospitals", "source_name": "Outlet A", "matched_keywords": []},
            {"title": "Cholera outbreak reported in Western Province", "source_name": "Outlet B", "matched_keywords": []},
        ]
        unique_items, duplicates = dedup.deduplicate(items)
        self.assertEqual(len(unique_items), 2)
        self.assertEqual(len(duplicates), 0)


class TestHighlightScoring(unittest.TestCase):
    def test_more_outlets_scores_higher(self):
        now = datetime(2026, 7, 10, tzinfo=timezone.utc)
        item_wide = {"source_name": "A", "covered_by": ["A", "B", "C"], "matched_keywords": ["malaria"], "published_at": now}
        item_single = {"source_name": "D", "covered_by": ["D"], "matched_keywords": ["malaria"], "published_at": now}
        self.assertGreater(highlight_score.score_item(item_wide, now=now), highlight_score.score_item(item_single, now=now))

    def test_older_item_scores_lower(self):
        now = datetime(2026, 7, 10, tzinfo=timezone.utc)
        fresh = {"source_name": "A", "matched_keywords": [], "published_at": now}
        old = {"source_name": "B", "matched_keywords": [], "published_at": now - timedelta(days=6)}
        self.assertGreater(highlight_score.score_item(fresh, now=now), highlight_score.score_item(old, now=now))

    def test_rank_items_sorted_descending(self):
        now = datetime(2026, 7, 10, tzinfo=timezone.utc)
        items = [
            {"source_name": "A", "matched_keywords": [], "published_at": now - timedelta(days=5)},
            {"source_name": "B", "covered_by": ["B", "C"], "matched_keywords": ["malaria"], "published_at": now},
        ]
        ranked = highlight_score.rank_items(items, now=now)
        self.assertEqual(ranked[0]["source_name"], "B")


class TestScanWindow(unittest.TestCase):
    def test_daily_window_is_one_day(self):
        end = datetime(2026, 7, 10, tzinfo=timezone.utc)
        start, computed_end = scan.compute_window("daily", end_date=end)
        self.assertEqual((computed_end - start).days, 1)

    def test_weekly_window_is_seven_days(self):
        end = datetime(2026, 7, 10, tzinfo=timezone.utc)
        start, computed_end = scan.compute_window("weekly", end_date=end)
        self.assertEqual((computed_end - start).days, 7)

    def test_item_inside_window_is_kept(self):
        start = datetime(2026, 7, 3, tzinfo=timezone.utc)
        end = datetime(2026, 7, 10, tzinfo=timezone.utc)
        item = {"published_at": datetime(2026, 7, 5, tzinfo=timezone.utc)}
        self.assertTrue(scan.within_window(item, start, end))

    def test_item_outside_window_is_dropped(self):
        start = datetime(2026, 7, 3, tzinfo=timezone.utc)
        end = datetime(2026, 7, 10, tzinfo=timezone.utc)
        item = {"published_at": datetime(2026, 6, 1, tzinfo=timezone.utc)}
        self.assertFalse(scan.within_window(item, start, end))

    def test_item_with_unknown_date_is_kept_not_dropped(self):
        start = datetime(2026, 7, 3, tzinfo=timezone.utc)
        end = datetime(2026, 7, 10, tzinfo=timezone.utc)
        item = {"published_at": None}
        self.assertTrue(scan.within_window(item, start, end))


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        db.init_db(self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_insert_and_retrieve_item(self):
        scan_id = db.start_scan("daily", "2026-07-09T00:00:00", "2026-07-10T00:00:00", "2026-07-10T00:00:00", db_path=self.db_path)
        item = {
            "source_name": "The New Times", "source_category": "local_online",
            "title": "Test story", "url": "https://example.com/1",
            "language": "en", "published_at": "2026-07-10T00:00:00",
            "fetched_at": "2026-07-10T00:00:00", "matched_keywords": ["health"], "snippet": "",
        }
        item_id = db.insert_item(item, scan_id, db_path=self.db_path)
        self.assertIsNotNone(item_id)

        items = db.get_items_for_scan(scan_id, db_path=self.db_path)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Test story")

    def test_duplicate_url_is_not_inserted_twice(self):
        scan_id = db.start_scan("daily", "2026-07-09T00:00:00", "2026-07-10T00:00:00", "2026-07-10T00:00:00", db_path=self.db_path)
        item = {
            "source_name": "A", "source_category": "local_online", "title": "T",
            "url": "https://example.com/dup", "language": "en", "published_at": None,
            "fetched_at": "2026-07-10T00:00:00", "matched_keywords": [], "snippet": "",
        }
        first_id = db.insert_item(item, scan_id, db_path=self.db_path)
        second_id = db.insert_item(item, scan_id, db_path=self.db_path)
        self.assertIsNotNone(first_id)
        self.assertIsNone(second_id)

    def test_finish_scan_records_counts(self):
        scan_id = db.start_scan("weekly", "2026-07-03T00:00:00", "2026-07-10T00:00:00", "2026-07-10T00:00:00", db_path=self.db_path)
        db.finish_scan(scan_id, "2026-07-10T00:05:00", raw_items=50, relevant_items=12, unique_items=9, db_path=self.db_path)
        row = db.get_scan(scan_id, db_path=self.db_path)
        self.assertEqual(row["raw_items_collected"], 50)
        self.assertEqual(row["unique_items"], 9)


if __name__ == "__main__":
    unittest.main()
