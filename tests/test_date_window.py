"""
Focused tests for the strict date-window behaviour introduced by the
date-filter fix (see DATE_FILTER_FIX.md).

IMPORTANT: these REPLACE the single obsolete assertion
`TestScanWindow.test_item_with_unknown_date_is_kept_not_dropped` in
tests/test_pipeline.py. Delete that one method -- it asserts the OLD
behaviour of keeping every undated item, which is exactly what this fix
removes, so it will now fail by design. Everything else in test_pipeline.py
still passes unchanged.

Run with:  python -m unittest discover tests
"""

import os
import sys
import unittest
import unittest.mock
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import scan  # noqa: E402
from collectors.rss_utils import extract_date_from_url  # noqa: E402


WINDOW_START = datetime(2026, 7, 3, 0, 0, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 7, 10, 23, 59, 59, tzinfo=timezone.utc)


class TestStrictWindow(unittest.TestCase):
    def test_dated_item_inside_window_is_kept(self):
        item = {"published_at": datetime(2026, 7, 5, tzinfo=timezone.utc)}
        self.assertTrue(scan.within_window(item, WINDOW_START, WINDOW_END))

    def test_dated_item_on_exact_boundary_is_kept(self):
        item = {"published_at": WINDOW_END}
        self.assertTrue(scan.within_window(item, WINDOW_START, WINDOW_END))

    def test_dated_item_outside_window_is_dropped(self):
        item = {"published_at": datetime(2026, 6, 1, tzinfo=timezone.utc)}
        self.assertFalse(scan.within_window(item, WINDOW_START, WINDOW_END))

    def test_undated_item_is_dropped_by_default(self):
        """The core of the fix: an item whose date we cannot determine can
        no longer slip into a date-scoped scan."""
        self.assertFalse(scan.within_window({"published_at": None}, WINDOW_START, WINDOW_END))

    def test_item_missing_published_at_key_is_dropped_by_default(self):
        self.assertFalse(scan.within_window({}, WINDOW_START, WINDOW_END))

    def test_upstream_date_filtered_item_is_kept_without_a_date(self):
        """PubMed constrains dates at the source, so its undated items are
        trusted as in-window."""
        item = {"published_at": None, "date_filtered_upstream": True}
        self.assertTrue(scan.within_window(item, WINDOW_START, WINDOW_END))

    def test_undated_item_kept_when_lenient_flag_enabled(self):
        with unittest.mock.patch.object(config, "KEEP_UNDATED_ITEMS", True, create=True):
            self.assertTrue(scan.within_window({"published_at": None}, WINDOW_START, WINDOW_END))


class TestExtractDateFromUrl(unittest.TestCase):
    def test_slash_ymd_permalink(self):
        dt = extract_date_from_url("https://site.rw/2026/07/14/some-health-story")
        self.assertEqual((dt.year, dt.month, dt.day), (2026, 7, 14))

    def test_slash_ymd_permalink_at_end_of_url(self):
        dt = extract_date_from_url("https://site.rw/2026/07/14")
        self.assertEqual((dt.year, dt.month, dt.day), (2026, 7, 14))

    def test_dashed_ymd_permalink(self):
        dt = extract_date_from_url("https://site.rw/news/2026-07-14-some-health-story")
        self.assertEqual((dt.year, dt.month, dt.day), (2026, 7, 14))

    def test_month_only_permalink_is_not_a_date(self):
        """A /YYYY/MM/ path is too imprecise to place inside a specific day,
        so it counts as 'no date' (and is then dropped under strict mode)."""
        self.assertIsNone(extract_date_from_url("https://site.rw/2026/07/some-health-story"))

    def test_url_without_any_date_returns_none(self):
        self.assertIsNone(extract_date_from_url("https://site.rw/articles/some-health-story"))

    def test_impossible_date_is_rejected(self):
        self.assertIsNone(extract_date_from_url("https://site.rw/2026/13/40/nope"))

    def test_none_url_returns_none(self):
        self.assertIsNone(extract_date_from_url(None))

    def test_returned_datetime_is_utc_aware(self):
        dt = extract_date_from_url("https://site.rw/2026/07/14/story")
        self.assertIsNotNone(dt.tzinfo)


if __name__ == "__main__":
    unittest.main()
