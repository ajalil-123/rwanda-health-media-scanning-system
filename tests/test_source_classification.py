"""
Tests for Google News outlet -> report-section classification
(collectors/google_news._classify_category). See CLASSIFICATION_FIX.md.

The bug these guard against: Rwandan outlets whose Google News name contains
a space or accent (KT Press, Kigali Today, Le Canapé) were being labelled
International because the old check compared raw substrings ("ktpress" is not
inside "kt press").

Run with:  python -m unittest discover tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors import google_news  # noqa: E402


class TestSourceClassification(unittest.TestCase):
    def test_kt_press_with_space_is_local(self):
        self.assertEqual(google_news._classify_category("KT Press"), "local_online")

    def test_kt_press_all_caps_is_local(self):
        self.assertEqual(google_news._classify_category("KT PRESS"), "local_online")

    def test_the_new_times_is_local(self):
        self.assertEqual(google_news._classify_category("The New Times"), "local_online")

    def test_igihe_is_local(self):
        self.assertEqual(google_news._classify_category("IGIHE"), "local_online")

    def test_kigali_today_with_space_is_local(self):
        self.assertEqual(google_news._classify_category("Kigali Today"), "local_online")

    def test_the_chronicles_is_local(self):
        self.assertEqual(google_news._classify_category("The Chronicles"), "local_online")

    def test_taarifa_is_local(self):
        self.assertEqual(google_news._classify_category("Taarifa"), "local_online")

    def test_accented_le_canape_is_local(self):
        self.assertEqual(google_news._classify_category("Le Canapé"), "local_online")

    def test_accented_nouvelle_releve_is_local(self):
        self.assertEqual(google_news._classify_category("La Nouvelle Relève"), "local_online")

    def test_imvaho_nshya_is_local(self):
        self.assertEqual(google_news._classify_category("Imvaho Nshya"), "local_online")

    def test_inyarwanda_is_local(self):
        self.assertEqual(google_news._classify_category("Inyarwanda"), "local_online")

    def test_bbc_is_international(self):
        self.assertEqual(google_news._classify_category("BBC News"), "international")

    def test_reuters_is_international(self):
        self.assertEqual(google_news._classify_category("Reuters"), "international")

    def test_al_jazeera_is_international(self):
        self.assertEqual(google_news._classify_category("Al Jazeera"), "international")

    def test_unattributed_defaults_to_local(self):
        self.assertEqual(google_news._classify_category(None), "local_online")

    def test_empty_string_defaults_to_local(self):
        self.assertEqual(google_news._classify_category(""), "local_online")

    def test_normalize_collapses_spacing_and_accents(self):
        self.assertEqual(google_news._normalize("KT Press"), "ktpress")
        self.assertEqual(google_news._normalize("Le Canapé"), "lecanape")
        self.assertEqual(google_news._normalize("The New Times"), "thenewtimes")


if __name__ == "__main__":
    unittest.main()
