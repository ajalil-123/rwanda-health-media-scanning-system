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
            source_el = item.find("source")  # Google News RSS: <source url="...">Publisher Name</source>
            source_name = source_el.text.strip() if source_el is not None and source_el.text else None
            if title and link:
                items.append({
                    "title": title,
                    "url": link,
                    "published_at": pub_date,
                    "summary": summary,
                    "source_name": source_name,  # None for feeds that don't provide this (e.g. most direct outlet feeds)
                })
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


def extract_date_from_html(element_text):
    """
    Try to parse a date from HTML text.
    Handles various common formats: "July 14, 2026", "2026-07-14", "14/07/2026", etc.
    Returns datetime object or None.
    """
    import re

    if not element_text:
        return None

    text = str(element_text).strip()
    if not text or len(text) > 200:  # Skip very long strings
        return None

    # Common date patterns (most specific first)
    patterns = [
        # ISO format: 2026-07-14 or 2026-07-14 10:30 or 2026-07-14T10:30
        (r"(\d{4}-\d{2}-\d{2})[\sT]?(\d{2}:\d{2}(?::\d{2})?)?", "%Y-%m-%d"),
        # US format: July 14, 2026 or Jul 14, 2026
        (r"([A-Z][a-z]{2,8}\.?\s+\d{1,2},?\s+\d{4})", "%B %d, %Y"),
        # European format: 14/07/2026 or 14.07.2026 or 14-07-2026
        (r"(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4})", "%d/%m/%Y"),
        # Short format: 14 Jul 2026
        (r"(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})", "%d %b %Y"),
        # "Posted Jul 14" or "Published July 14, 2026"
        (r"(?:Posted|Published|Updated)?\s+([A-Z][a-z]{2,8}\.?\s+\d{1,2},?\s+\d{4})", "%B %d, %Y"),
    ]

    for pattern, date_fmt in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            try:
                parsed = datetime.strptime(date_str, date_fmt)
                # Add UTC timezone
                parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                pass

    return None


def extract_date_from_element(soup_element):
    """
    Try to extract a date from a BeautifulSoup element.
    Checks common date indicator classes, attributes, and meta tags.
    Returns datetime object or None.
    """
    from bs4 import BeautifulSoup

    if not soup_element:
        return None

    # If it's a string, parse it
    if isinstance(soup_element, str):
        soup_element = BeautifulSoup(soup_element, "html.parser")

    # Try <time> element first (most reliable, HTML5 standard)
    time_elem = soup_element.find("time")
    if time_elem:
        # Check datetime attribute first
        if time_elem.get("datetime"):
            date_obj = parse_rss_datetime(time_elem.get("datetime"))
            if date_obj:
                return date_obj
        # Try text content
        text = time_elem.get_text(strip=True)
        if text:
            date_obj = extract_date_from_html(text)
            if date_obj:
                return date_obj

    # Try common class/id patterns for date elements
    date_class_names = [
        "published-date",
        "publish-date",
        "posted-date",
        "post-date",
        "article-date",
        "entry-date",
        "date-posted",
        "dateline",
        "timestamp",
        "meta-date",
    ]

    for class_name in date_class_names:
        elem = soup_element.find(class_=class_name)
        if elem:
            # Try datetime attribute first
            if elem.get("datetime"):
                date_obj = parse_rss_datetime(elem.get("datetime"))
                if date_obj:
                    return date_obj
            # Try text content
            text = elem.get_text(strip=True)
            if text:
                date_obj = extract_date_from_html(text)
                if date_obj:
                    return date_obj

    # Try meta tags (Open Graph, Twitter Card, schema.org, etc.)
    meta_patterns = [
        ("property", "article:published_time"),
        ("property", "article:modified_time"),
        ("name", "publish_date"),
        ("name", "article.published"),
        ("name", "dc.date"),
        ("name", "date"),
    ]

    for attr_name, attr_value in meta_patterns:
        meta = soup_element.find("meta", {attr_name: attr_value})
        if meta and meta.get("content"):
            date_obj = parse_rss_datetime(meta.get("content"))
            if date_obj:
                return date_obj

    # Last resort: look for text patterns in common locations
    for elem in soup_element.find_all(["span", "p", "div", "small"], limit=10):
        text = elem.get_text(strip=True)
        if text and len(text) < 50:  # Date text is usually short
            date_obj = extract_date_from_html(text)
            if date_obj:
                return date_obj

    return None
