"""
Configuration for the RBC Health Media Scanning system.

This is the single place to edit sources and keywords. Nothing in
collectors/ or processing/ should need to change when you add a new
outlet, RSS feed, or keyword -- just edit the lists below.

Scope note (per current build phase): only TEXT-BASED NEWS sources are
covered here (local online news, international media, research/journals
via PubMed, and broad discovery via Google News RSS). Radio/TV and
YouTube collection is intentionally out of scope for this phase and can
be added later as a new collector module without touching this file's
structure.
"""

# ---------------------------------------------------------------------------
# Google News RSS -- broad discovery, catches outlets beyond the fixed list
# below. Free, no API key. See collectors/google_news.py for how these are
# used.
# ---------------------------------------------------------------------------
GOOGLE_NEWS_QUERIES = [
    {"query": "health Rwanda", "hl": "en-RW", "gl": "RW", "ceid": "RW:en"},
    {"query": "Rwanda hospital", "hl": "en-RW", "gl": "RW", "ceid": "RW:en"},
    {"query": "Rwanda disease outbreak", "hl": "en-RW", "gl": "RW", "ceid": "RW:en"},
    {"query": "ubuzima Rwanda", "hl": "rw", "gl": "RW", "ceid": "RW:rw"},
    {"query": "sante Rwanda", "hl": "fr", "gl": "RW", "ceid": "RW:fr"},
]

# ---------------------------------------------------------------------------
# Direct RSS feeds for priority outlets. Verify and expand this list during
# the Phase 1 source audit -- entries marked "unverified" should be checked
# (visit the outlet's site and look for /feed, /rss, or an RSS link in the
# page footer) before relying on them in production.
# ---------------------------------------------------------------------------
DIRECT_RSS_FEEDS = [
    {
        "name": "The New Times",
        "url": "https://www.newtimes.co.rw/rssFeed/14",
        "language": "en",
        "category": "local_online",
        "verified": True,
    },
    # -- Add more as they are confirmed during the source audit, e.g.:
    # {"name": "KT Press", "url": "https://ktpress.rw/feed/", "language": "en",
    #  "category": "local_online", "verified": False},
    # {"name": "IGIHE", "url": "https://en.igihe.com/spip.php?page=backend",
    #  "language": "en", "category": "local_online", "verified": False},
]

# ---------------------------------------------------------------------------
# PubMed E-utilities -- research & journals. Free, no key required for light
# use (an optional free NCBI API key raises the rate limit).
# ---------------------------------------------------------------------------
PUBMED_QUERY = "Rwanda[Title/Abstract] AND (health OR medicine OR disease OR outbreak)"
PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_API_KEY = None  # optional; set to raise rate limits

# ---------------------------------------------------------------------------
# Multilingual keyword list used for relevance filtering (Section 7.1 of the
# technical design guide). Treat this as a living list -- extend it whenever
# a relevant story is missed because it used a term not covered here.
# Matching is case-insensitive and works on whole words/phrases.
# ---------------------------------------------------------------------------
KEYWORDS = {
    "general": {
        "en": ["health", "healthcare", "hospital", "clinic", "medical", "patient", "medicine"],
        "rw": ["ubuzima", "ivuriro", "umuvuzi", "abarwayi"],
        "fr": ["sante", "hopital", "clinique", "medecin", "medical", "patient"],
    },
    "institutions": {
        "en": ["ministry of health", "rwanda biomedical centre", "rbc", "moh rwanda"],
        "rw": ["minisiteri y'ubuzima", "minisiteri yubuzima"],
        "fr": ["ministere de la sante"],
    },
    "diseases_outbreaks": {
        "en": ["malaria", "tuberculosis", "hiv", "aids", "ebola", "marburg", "cholera",
               "mpox", "monkeypox", "covid", "outbreak", "epidemic", "pandemic"],
        "rw": ["malariya", "igituntu", "sida", "icyorezo"],
        "fr": ["paludisme", "tuberculose", "sida", "epidemie"],
    },
    "maternal_child": {
        "en": ["maternal health", "pregnancy", "child mortality", "newborn", "maternal mortality"],
        "rw": ["ubuzima bw'ababyeyi", "uburumbuke", "kubyara"],
        "fr": ["sante maternelle", "grossesse", "mortalite infantile"],
    },
    "health_systems": {
        "en": ["community health worker", "vaccination", "vaccine", "referral hospital",
               "health insurance", "mutuelle de sante", "health center", "health centre"],
        "rw": ["abajyanama b'ubuzima", "urukingo", "kwirinda"],
        "fr": ["agent de sante", "vaccination", "vaccin", "assurance maladie"],
    },
}


def all_keywords():
    """Flatten the KEYWORDS structure into a single lowercase list."""
    flat = []
    for category in KEYWORDS.values():
        for lang_terms in category.values():
            flat.extend(t.lower() for t in lang_terms)
    return flat


# ---------------------------------------------------------------------------
# Scan settings
# ---------------------------------------------------------------------------
DAILY_WINDOW_DAYS = 1
WEEKLY_WINDOW_DAYS = 7

DB_PATH = "media_monitor.db"

# HTTP settings
REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = "RBC-Health-Media-Monitor/0.1 (+internal RBC tool)"
