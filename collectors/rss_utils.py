"""
Small, dependency-free RSS/Atom parsing helper.

We deliberately avoid the `feedparser` package so this system has no
third-party dependency beyond `requests` -- fewer moving parts to keep
free and working long-term.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

import config


def fetch_url(url, params=None):
    """GET a URL with a sensible timeout and user-agent. Returns response text.
    Raises requests.RequestException on failure -- callers should catch this
    per-source so one broken feed doesn't stop the whole scan."""
    headers = {"User-Agent": config.USER_AGENT}
    resp = requests.get(url, params=params, headers=headers, timeout=config.REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.text


def parse_rss_datetime(raw):
    """Best-effort parse of an RSS/Atom pubDate/updated string into an
    aware UTC datetime. Returns None if it can't be parsed -- callers
    should treat that as 'unknown date' rather than crash."""
    if not raw:
        return None
    raw = raw.strip()
    # Try RFC 2822 (most common in RSS: "Fri, 10 Jul 2026 09:00:00 GMT")
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass
    # Try ISO 8601 (common in Atom: "2026-07-10T09:00:00Z")
    try:
        cleaned = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def parse_feed(xml_text):
    """
    Parse an RSS 2.0 or Atom feed into a list of dicts:
    {title, url, published_at (datetime or None), summary}

    Handles the two common feed formats; unknown/malformed feeds return
    an empty list rather than raising, so one bad feed doesn't crash a scan.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    items = []

    # RSS 2.0: <rss><channel><item>...
    channel = root.find("channel")
    if channel is not None:
        for item in channel.findall("item"):
            title = _text(item, "title")
            link = _text(item, "link")
            pub_date = parse_rss_datetime(_text(item, "pubDate"))
            summary = _text(item, "description")
            if title and link:
                items.append({"title": title, "url": link, "published_at": pub_date, "summary": summary})
        return items

    # Atom: <feed><entry>...
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns)
    if entries:
        for entry in entries:
            title = _text(entry, "atom:title", ns)
            link_el = entry.find("atom:link", ns)
            link = link_el.get("href") if link_el is not None else None
            pub_date = parse_rss_datetime(_text(entry, "atom:updated", ns) or _text(entry, "atom:published", ns))
            summary = _text(entry, "atom:summary", ns)
            if title and link:
                items.append({"title": title, "url": link, "published_at": pub_date, "summary": summary})
        return items

    return items


def _text(el, tag, ns=None):
    found = el.find(tag, ns) if ns else el.find(tag)
    if found is not None and found.text:
        return found.text.strip()
    return None
