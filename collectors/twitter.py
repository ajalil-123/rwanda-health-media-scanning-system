"""
Social media collector -- Twitter/X posts and hashtags about Rwanda health.

Uses Twikit library (free, browser automation-based) to search for:
- Posts from configured accounts (@RwandaHealth, @RBCRwanda, etc.)
- Posts with health-related hashtags (#RBAAmakuru, #RwandaHealth, etc.)

WARNING: Requires a dedicated (non-personal) X/Twitter account and active internet.
Twikit uses browser automation which can be detected and blocked by Twitter.
Use responsibly and expect occasional rate limiting.

To use:
1. Set TWITTER_EMAIL and TWITTER_PASSWORD in config.py with a dedicated RBC account
2. First run will require TOTP/email verification (interactive)
3. Subsequent runs cache the auth session
"""

import logging
import os
from datetime import datetime, timedelta

import config

logger = logging.getLogger(__name__)

try:
    from twikit import Client
    TWIKIT_AVAILABLE = True
except ImportError:
    TWIKIT_AVAILABLE = False
    logger.warning("Twikit not installed - Twitter collector disabled. Install with: pip install twikit")


def _get_twitter_client():
    """Authenticate and return a Twikit client. Requires config.TWITTER_EMAIL and TWITTER_PASSWORD."""
    if not TWIKIT_AVAILABLE:
        logger.warning("Twikit not available")
        return None

    if not hasattr(config, "TWITTER_EMAIL") or not hasattr(config, "TWITTER_PASSWORD"):
        logger.warning(
            "Twitter collector requires TWITTER_EMAIL and TWITTER_PASSWORD in config.py. "
            "Set these to a dedicated RBC X account (not personal)."
        )
        return None

    try:
        client = Client()
        logger.info("Authenticating with Twitter...")
        client.login(
            email=config.TWITTER_EMAIL,
            password=config.TWITTER_PASSWORD,
            totp_secret=getattr(config, "TWITTER_TOTP_SECRET", None),
        )
        logger.info("Twitter authentication successful")
        return client
    except Exception as exc:
        logger.warning("Twitter authentication failed: %s", exc)
        return None


def _extract_post_metadata(tweet):
    """Extract relevant metadata from a Twikit tweet object."""
    try:
        return {
            "title": tweet.text[:100] if tweet.text else "(no text)",  # first 100 chars as title
            "url": f"https://twitter.com/{tweet.user.username}/status/{tweet.id}",
            "published_at": tweet.created_at_datetime.isoformat() if hasattr(tweet, "created_at_datetime") else None,
            "summary": tweet.text or "",
            "source_name": f"{tweet.user.username} (Twitter)",
            "source_category": "social_media",
            "language": "en",
        }
    except Exception as exc:
        logger.warning("Could not extract tweet metadata: %s", exc)
        return None


def search_twitter_accounts(client):
    """Search posts from configured Twitter accounts."""
    items = []
    if not hasattr(config, "SOCIAL_MEDIA_ACCOUNTS"):
        return items

    twitter_accounts = config.SOCIAL_MEDIA_ACCOUNTS.get("twitter", [])
    if not twitter_accounts:
        return items

    logger.info("Searching tweets from %d accounts", len(twitter_accounts))

    for account in twitter_accounts:
        try:
            logger.info("Fetching posts from %s", account)
            # Twikit search format: "from:username"
            query = f"from:{account.lstrip('@')} lang:en"
            tweets = client.search_tweet(query, product="Latest", count=10)

            for tweet in tweets:
                metadata = _extract_post_metadata(tweet)
                if metadata:
                    items.append(metadata)
        except Exception as exc:
            logger.warning("Failed to search account %s: %s", account, exc)

    logger.info("Twitter account search returned %d tweets", len(items))
    return items


def search_twitter_hashtags(client):
    """Search posts with configured health-related hashtags."""
    items = []
    if not hasattr(config, "SOCIAL_MEDIA_ACCOUNTS"):
        return items

    hashtags = config.SOCIAL_MEDIA_ACCOUNTS.get("hashtags", [])
    if not hashtags:
        return items

    logger.info("Searching tweets with %d hashtags", len(hashtags))

    for hashtag in hashtags:
        try:
            logger.info("Fetching posts with %s", hashtag)
            query = f"{hashtag} lang:en"
            tweets = client.search_tweet(query, product="Latest", count=10)

            for tweet in tweets:
                metadata = _extract_post_metadata(tweet)
                if metadata:
                    items.append(metadata)
        except Exception as exc:
            logger.warning("Failed to search hashtag %s: %s", hashtag, exc)

    logger.info("Twitter hashtag search returned %d tweets", len(items))
    return items


def collect():
    """
    Collect tweets from configured accounts and hashtags.
    Returns empty list if not configured or Twikit unavailable.
    """
    if not TWIKIT_AVAILABLE:
        logger.info("Twitter collector skipped (Twikit not installed)")
        return []

    client = _get_twitter_client()
    if not client:
        logger.info("Twitter collector skipped (not configured)")
        return []

    items = []
    items += search_twitter_accounts(client)
    items += search_twitter_hashtags(client)

    # Deduplicate by URL
    seen_urls = set()
    unique_items = []
    for item in items:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            unique_items.append(item)

    logger.info("Twitter collector returning %d unique items", len(unique_items))
    return unique_items
