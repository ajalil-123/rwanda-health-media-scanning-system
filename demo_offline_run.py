"""
Offline demonstration of the full scan pipeline using synthetic collector
output (standing in for what google_news/direct_rss/pubmed would return
over the network). This proves filter -> dedup -> score -> store -> export
works end-to-end without needing live internet access.

This is a demo/dev tool, not part of the production system -- in real
operation, scan.py calls the real collectors instead of this fixture.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db
import export
from processing import filter_relevance, dedup, highlight_score
import scan


def fake_raw_items(now):
    return [
        # Same story, three outlets -- should collapse to one item with covered_by = 3
        {"title": "Rwanda rolls out new malaria treatment protocol in hospitals",
         "url": "https://newtimes.co.rw/malaria-protocol", "published_at": now - timedelta(hours=3),
         "summary": "The Ministry of Health announced a new malaria treatment protocol.",
         "source_name": "The New Times", "source_category": "local_online", "language": "en"},
        {"title": "Rwanda rolls out new malaria treatment protocol for hospitals",
         "url": "https://ktpress.rw/malaria-protocol", "published_at": now - timedelta(hours=5),
         "summary": "RBC confirmed the new malaria protocol nationwide.",
         "source_name": "KT Press", "source_category": "local_online", "language": "en"},
        {"title": "New malaria treatment protocol rolled out across Rwandan hospitals",
         "url": "https://news.google.com/rss/articles/xyz1", "published_at": now - timedelta(hours=8),
         "summary": "Health officials confirm new malaria treatment guidance.",
         "source_name": "Google News", "source_category": "local_online", "language": "en"},

        # Distinct story, Kinyarwanda
        {"title": "Ubuzima bw'ababyeyi bwongerewe imbaraga mu Rwanda",
         "url": "https://igihe.com/ubuzima-ababyeyi", "published_at": now - timedelta(hours=10),
         "summary": "Minisiteri y'Ubuzima yatangaje gahunda nshya.",
         "source_name": "IGIHE", "source_category": "local_online", "language": "rw"},

        # Distinct story, French, international
        {"title": "Le ministere de la sante du Rwanda annonce une campagne de vaccination",
         "url": "https://rfi.fr/rwanda-vaccination", "published_at": now - timedelta(hours=20),
         "summary": "Une nouvelle campagne de vaccination contre la rougeole.",
         "source_name": "RFI", "source_category": "international", "language": "fr"},

        # Research item (would come from PubMed -- no published_at, as in real esummary responses)
        {"title": "Outcomes of a community health worker malaria intervention in Rwanda",
         "url": "https://pubmed.ncbi.nlm.nih.gov/99999999/", "published_at": None,
         "summary": "Published in The Lancet Global Health.",
         "source_name": "The Lancet Global Health", "source_category": "research", "language": "en"},

        # Irrelevant item -- should be dropped by the keyword filter
        {"title": "Rwanda national football team wins away fixture",
         "url": "https://newtimes.co.rw/football-win", "published_at": now - timedelta(hours=2),
         "summary": "APR FC secured a 2-0 win on Saturday.",
         "source_name": "The New Times", "source_category": "local_online", "language": "en"},

        # Old item -- outside a daily window, should be dropped by within_window for --mode daily
        {"title": "Cholera outbreak update from three weeks ago in Rwanda",
         "url": "https://newtimes.co.rw/cholera-old", "published_at": now - timedelta(days=20),
         "summary": "An older cholera outbreak update.",
         "source_name": "The New Times", "source_category": "local_online", "language": "en"},
    ]


def main():
    now = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
    db_path = "demo_output/demo.db"
    os.makedirs("demo_output", exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    fixture_items = fake_raw_items(now)

    with patch("collectors.google_news.collect", return_value=[]), \
         patch("collectors.direct_rss.collect", return_value=fixture_items), \
         patch("collectors.pubmed.collect", return_value=[]):

        result = scan.run_scan("daily", end_date=now, db_path=db_path)

    print("\n=== DAILY SCAN RESULT (offline demo) ===")
    print(f"Window: {result['window_start'].isoformat()} to {result['window_end'].isoformat()}")
    print(f"Shortlist size: {len(result['ranked_items'])}")
    print(f"CSV: {result['csv_path']}")
    print(f"Markdown: {result['md_path']}")
    print("\n--- Shortlist (ranked) ---")
    for item in result["ranked_items"]:
        covered = item.get("covered_by", [item["source_name"]])
        print(f"[{item['highlight_score']:>5}] ({item['source_category']}) {item['title']}  "
              f"-- {item['source_name']}" + (f" +{len(covered)-1} more outlet(s)" if len(covered) > 1 else ""))

    print("\n--- Sanity checks ---")
    titles = [i["title"] for i in result["ranked_items"]]
    assert not any("football" in t.lower() for t in titles), "Irrelevant item leaked through filter!"
    assert not any("three weeks ago" in t.lower() for t in titles), "Out-of-window item leaked through!"
    malaria_items = [i for i in result["ranked_items"] if "malaria treatment" in i["title"].lower()]
    assert len(malaria_items) == 1, "Duplicate malaria stories were not merged!"
    assert len(malaria_items[0].get("covered_by", [])) == 3, "Expected 3 outlets folded into one story!"
    print("All sanity checks passed: irrelevant item dropped, out-of-window item dropped, "
          "3-outlet duplicate merged into 1 story.")


if __name__ == "__main__":
    main()
