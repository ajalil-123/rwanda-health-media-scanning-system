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
    {
        "name": "KT Press",
        "url": "https://www.ktpress.rw/feed/",
        "language": "en",
        "category": "local_online",
        "verified": True,  # confirmed: returns application/rss+xml with real content
    },
    {
        "name": "Taarifa",
        "url": "https://taarifa.rw/feed/",
        "language": "en",
        "category": "local_online",
        "verified": True,  # confirmed: returns application/rss+xml with real content
    },
    # -- Found during the source audit but NOT yet confirmed working --
    # extend the audit before trusting these in production:
    #
    # Imvaho Nshya: feed URL below is commonly cited (WordPress-style
    # /feed/), but a direct fetch attempt returned a server error during
    # verification -- could be transient, could be blocking automated
    # requests. Re-check before enabling.
    # {"name": "Imvaho Nshya", "url": "https://imvahonshya.co.rw/feed/",
    #  "language": "rw", "category": "local_online", "verified": False},
    #
    # Rwanda Today (Nation Media Group): feed URL below is cited by
    # FeedSpot's curated list, but the site's robots.txt disallows
    # automated fetching -- adding this would mean ignoring their stated
    # crawling policy. Worth a manual/legal check before enabling, not a
    # technical one.
    # {"name": "Rwanda Today", "url": "https://rwandatoday.africa/service/rss/rwanda/2464348/feed.rss",
    #  "language": "en", "category": "local_online", "verified": False},
    #
    # IGIHE: no reliable feed found. The English subdomain en2.igihe.com
    # exposes a WordPress feed, but its output is corrupted by leaked PHP
    # warnings printed before the XML declaration, which will fail to
    # parse. igihe.com itself (the main Kinyarwanda site) runs on SPIP,
    # which usually exposes a feed via ?page=backend -- unconfirmed, needs
    # a follow-up check.
    #
    # Still to check: Panorama, Kigali Today, Umuseke, Le Canape,
    # La Nouvelle Releve, The Chronicles.
]

# ---------------------------------------------------------------------------
# Web scraping for local outlets with no working RSS feed (see
# collectors/web_scraper.py for how these are used, and read its module
# docstring before adding a new site -- it explains the generic heuristic
# and how to find a precise `link_selector` for a specific site).
#
# `link_selector` is a CSS selector (e.g. "h2.entry-title a") pointing at
# the <a> tags a site uses for its headline links on its homepage/listing
# page. Leave it as None to use the generic heuristic (works out of the
# box but noisier) until someone inspects the real page and fills it in.
# ---------------------------------------------------------------------------
SCRAPE_SITES = [
    {
        "name": "IGIHE",
        "url": "https://en.igihe.com/",
        "language": "en",
        "category": "local_online",
        "link_selector": None,  # not yet inspected -- see collectors/web_scraper.py
    },
    {
        "name": "Panorama",
        "url": "https://panorama.rw/",
        "language": "rw",
        "category": "local_online",
        "link_selector": None,  # not yet inspected
    },
    {
        "name": "Kigali Today",
        "url": "https://www.kigalitoday.com/amakuru/",
        "language": "rw",
        "category": "local_online",
        "link_selector": None,  # not yet inspected
    },
    {
        "name": "The Chronicles",
        "url": "https://www.chronicles.rw/",
        "language": "en",
        "category": "local_online",
        "link_selector": None,  # not yet inspected
    },
]

# ---------------------------------------------------------------------------
# International News Sources covering Rwanda & East Africa
# These are major outlets with broad coverage. Most don't have Rwanda-specific
# RSS feeds, so they're configured for web scraping (to find Rwanda articles).
# ---------------------------------------------------------------------------
INTERNATIONAL_SOURCES = [
    {
        "name": "Reuters",
        "url": "https://www.reuters.com/world/africa/",
        "language": "en",
        "category": "international",
        "link_selector": "h3 a, .heading-article a",  # approximate, needs inspection
    },
    {
        "name": "BBC News Africa",
        "url": "https://www.bbc.com/news/world/africa/",
        "language": "en",
        "category": "international",
        "link_selector": "h3 a, .sc-2bc9a3a-5 a",  # BBC's class names change; will use generic fallback
    },
    {
        "name": "AFP News",
        "url": "https://www.afp.com/",
        "language": "en",
        "category": "international",
        "link_selector": None,  # needs inspection
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/news/longform/longform/",
        "language": "en",
        "category": "international",
        "link_selector": None,  # needs inspection
    },
    {
        "name": "France 24",
        "url": "https://www.france24.com/en/africa/",
        "language": "en",
        "category": "international",
        "link_selector": "h3 a, .article-headline a",
    },
    {
        "name": "DW News",
        "url": "https://www.dw.com/en/africa/s-9077",
        "language": "en",
        "category": "international",
        "link_selector": "h2 a, .teaser-headline a",
    },
    {
        "name": "Africanews",
        "url": "https://www.africanews.com/",
        "language": "en",
        "category": "international",
        "link_selector": None,  # needs inspection
    },
]

# ---------------------------------------------------------------------------
# Official Government & Health Organization Sources
# Rwanda Ministry of Health, RBC, WHO Rwanda -- direct from the source
# ---------------------------------------------------------------------------
OFFICIAL_SOURCES = [
    {
        "name": "Rwanda Ministry of Health",
        "url": "https://www.moh.gov.rw/",
        "language": "en",
        "category": "local_online",
        "link_selector": None,  # needs inspection of actual site structure
    },
    {
        "name": "Rwanda Biomedical Centre",
        "url": "https://www.rbc.gov.rw/",
        "language": "en",
        "category": "local_online",
        "link_selector": None,  # needs inspection
    },
    {
        "name": "WHO Rwanda",
        "url": "https://www.who.int/countries/rwa/",
        "language": "en",
        "category": "international",
        "link_selector": "h3 a, .news-item a",  # WHO's structure varies
    },
]

# ---------------------------------------------------------------------------
# Academic & Research Sources
# Beyond PubMed: Google Scholar, ResearchGate, SSRN, arXiv. All require
# web scraping (browser-like requests) due to blocking; use with respect
# to each site's robots.txt and terms of service.
# ---------------------------------------------------------------------------
RESEARCH_SOURCES = [
    {
        "name": "Google Scholar Rwanda",
        "url": "https://scholar.google.com/scholar",
        "query": "Rwanda health",
        "source": "google_scholar",
    },
    {
        "name": "ResearchGate Rwanda Health",
        "url": "https://www.researchgate.net/",
        "query": "Rwanda health",
        "source": "researchgate",
    },
    {
        "name": "SSRN Rwanda",
        "url": "https://papers.ssrn.com/",
        "query": "Rwanda health policy",
        "source": "ssrn",
    },
    {
        "name": "arXiv Rwanda",
        "url": "https://arxiv.org/",
        "query": "Rwanda health",
        "source": "arxiv",
    },
]

# ---------------------------------------------------------------------------
# Social Media Accounts to Monitor (future collector)
# Currently not automatically collected, but a future enhancement could
# monitor these Twitter accounts and hashtags for health-related tweets.
# ---------------------------------------------------------------------------
SOCIAL_MEDIA_ACCOUNTS = {
    "twitter": [
        "@RwandaHealth",
        "@RBCRwanda",
        "@WHORwanda",
        "@RwandaHRH",
        "@MinofHealthRwanda",
    ],
    "hashtags": [
        "#RBAAmakuru",
        "#RwandaHealth",
        "#ubuzima",
        "#sante_rwanda",
    ],
}

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
