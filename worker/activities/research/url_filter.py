"""
Smart URL Filtering

Filters and ranks URLs for optimal crawling:
- Excludes paywalled content (WSJ, FT, etc.)
- Excludes social media
- Prioritizes authoritative sources
- Ranks by relevance score
"""

from typing import List, Dict, Any
from temporalio import activity


# ============================================================================
# DOMAIN LISTS
# ============================================================================

# Paywalled domains to skip
PAYWALLED_DOMAINS = [
    "wsj.com",
    "ft.com",
    "economist.com",
    "bloomberg.com/professional",
    "barrons.com",
    "nytimes.com",
    "washingtonpost.com",
    "thetimes.co.uk",
    "telegraph.co.uk",
    "hbr.org",
    "seekingalpha.com",
]

# Authoritative sources (high priority)
AUTHORITATIVE_SOURCES = [
    # News
    "reuters.com",
    "bloomberg.com",
    "cnbc.com",
    "bbc.com",
    "theguardian.com",
    "forbes.com",
    "axios.com",
    "businessinsider.com",

    # Tech
    "techcrunch.com",
    "wired.com",
    "theverge.com",
    "arstechnica.com",

    # Finance/PE
    "privateequitywire.co.uk",
    "pehub.com",
    "pitchbook.com",
    "dealroom.co",
    "preqin.com",
    "privateequityinternational.com",

    # Business
    "inc.com",
    "entrepreneur.com",
    "fastcompany.com",
]

# Social/aggregator domains (low priority or skip)
SOCIAL_DOMAINS = [
    "twitter.com",
    "x.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "reddit.com",
    "youtube.com",
    "tiktok.com",
    "pinterest.com",
    "medium.com",  # Often aggregated content
]

# Relevant keywords that boost score
RELEVANT_KEYWORDS = [
    "acquisition",
    "funding",
    "deal",
    "investment",
    "placement",
    "relocation",
    "advisory",
    "capital",
    "merger",
    "partnership",
    "expansion",
    "launch",
    "raises",
    "series",
    "valuation",
]


# ============================================================================
# URL FILTERING
# ============================================================================

@activity.defn
async def smart_filter_urls(
    urls: List[str],
    max_urls: int = 15,
    exclude_paywalls: bool = True,
    exclude_social: bool = True,
    prefer_authoritative: bool = True
) -> List[str]:
    """
    Filter and rank URLs for crawling.

    Args:
        urls: List of URLs to filter
        max_urls: Maximum URLs to return
        exclude_paywalls: Skip paywalled domains
        exclude_social: Skip social media
        prefer_authoritative: Boost authoritative sources

    Returns:
        Filtered and ranked list of URLs (top N by score)
    """
    activity.logger.info(f"Filtering {len(urls)} URLs (max: {max_urls})")

    scored_urls = []

    for url in urls:
        url_lower = url.lower()

        # Skip paywalls
        if exclude_paywalls:
            if any(pw in url_lower for pw in PAYWALLED_DOMAINS):
                continue

        # Skip social
        if exclude_social:
            if any(s in url_lower for s in SOCIAL_DOMAINS):
                continue

        # Calculate relevance score
        score = 0

        # Authoritative source bonus (+10)
        if prefer_authoritative:
            if any(auth in url_lower for auth in AUTHORITATIVE_SOURCES):
                score += 10

        # Relevant keywords in URL (+5)
        if any(kw in url_lower for kw in RELEVANT_KEYWORDS):
            score += 5

        # Deep article bonus (not homepage) (+3)
        if url.count("/") > 4:
            score += 3

        # HTTPS bonus (+1)
        if url.startswith("https://"):
            score += 1

        # Recent year in URL bonus (+2)
        if any(year in url for year in ["2025", "2024", "2023"]):
            score += 2

        scored_urls.append((url, score))

    # Sort by score descending
    scored_urls.sort(key=lambda x: x[1], reverse=True)

    # Return top N
    filtered = [url for url, score in scored_urls[:max_urls]]

    activity.logger.info(
        f"Filtered to {len(filtered)} URLs "
        f"(removed {len(urls) - len(filtered)} paywalls/social/low-relevance)"
    )

    return filtered


@activity.defn
async def check_url_accessibility(url: str) -> Dict[str, Any]:
    """
    Quick check if URL is accessible.

    Args:
        url: URL to check

    Returns:
        Accessibility status
    """
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(
                url,
                follow_redirects=True,
                timeout=5.0
            )

            return {
                "url": url,
                "accessible": response.status_code < 400,
                "status_code": response.status_code,
                "final_url": str(response.url)
            }

    except Exception as e:
        return {
            "url": url,
            "accessible": False,
            "error": str(e)
        }
