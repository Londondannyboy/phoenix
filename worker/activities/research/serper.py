"""
Serper Research Activities

Multi-page news search with Serper.dev API.
Supports pages 1+2 for comprehensive research.
"""

import os
from typing import Dict, Any, List, Optional
from temporalio import activity
import httpx

from config import config


# ============================================================================
# SERPER API CLIENT
# ============================================================================

SERPER_API_URL = "https://google.serper.dev"


async def _serper_request(
    endpoint: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Make request to Serper API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SERPER_API_URL}/{endpoint}",
            headers={
                "X-API-KEY": config.SERPER_API_KEY,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


# ============================================================================
# MULTI-PAGE NEWS SEARCH
# ============================================================================

@activity.defn
async def serper_multi_page_news(
    query: str,
    pages: int = 2,
    results_per_page: int = 10,
    location: Optional[str] = None,
    time_period: str = "y"  # y=year, m=month, w=week, d=day
) -> Dict[str, Any]:
    """
    Search news across multiple pages with Serper.

    This is the foundation of deep research:
    - Page 1: 10 results
    - Page 2: 10 more results
    - Total: 20 URLs to crawl

    Args:
        query: Search query
        pages: Number of pages to fetch (1-3)
        results_per_page: Results per page (default 10)
        location: Geographic location (e.g., "United States", "United Kingdom")
        time_period: Time filter (y/m/w/d)

    Returns:
        Combined results from all pages with metadata
    """
    activity.logger.info(f"Serper multi-page search: '{query}' ({pages} pages)")

    all_articles = []
    total_cost = 0.0

    for page_num in range(1, pages + 1):
        try:
            # Calculate offset
            start = (page_num - 1) * results_per_page

            payload = {
                "q": query,
                "type": "news",
                "num": results_per_page,
                "page": page_num
            }

            # Add location if specified
            if location:
                payload["gl"] = "us" if "united states" in location.lower() else "gb"

            # Add time filter
            if time_period:
                payload["tbs"] = f"qdr:{time_period}"

            # Make request
            result = await _serper_request("news", payload)

            # Extract articles
            news_items = result.get("news", [])

            for item in news_items:
                all_articles.append({
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "source": item.get("source", ""),
                    "date": item.get("date", ""),
                    "page": page_num,
                    "position": item.get("position", 0)
                })

            # Estimate cost ($0.001 per request)
            total_cost += 0.001

            activity.logger.info(f"Page {page_num}: {len(news_items)} results")

        except Exception as e:
            activity.logger.error(f"Serper page {page_num} failed: {str(e)}")
            # Continue to next page

    # Extract all URLs
    urls = [article["url"] for article in all_articles if article.get("url")]

    activity.logger.info(
        f"Serper complete: {len(all_articles)} articles, {len(urls)} URLs, "
        f"cost: ${total_cost:.4f}"
    )

    return {
        "articles": all_articles,
        "urls": urls,
        "total_results": len(all_articles),
        "pages_fetched": pages,
        "query": query,
        "cost": total_cost
    }


@activity.defn
async def serper_company_news(
    domain: str,
    company_name: str,
    category: str,
    jurisdiction: str,
    pages: int = 2
) -> Dict[str, Any]:
    """
    Search for company-specific news.

    Builds optimized query for company research.

    Args:
        domain: Company domain
        company_name: Company name
        category: Company category
        jurisdiction: Geographic jurisdiction
        pages: Number of pages to fetch

    Returns:
        Company news results
    """
    # Build query
    category_clean = category.replace("_", " ")
    query = f"{company_name} {category_clean}"

    # Add geographic context
    if jurisdiction:
        if jurisdiction.upper() == "UK":
            query += " UK"
        elif jurisdiction.upper() == "US":
            query += " United States"
        elif jurisdiction.upper() == "EU":
            query += " Europe"

    # Location for API
    location = None
    if jurisdiction.upper() == "UK":
        location = "United Kingdom"
    elif jurisdiction.upper() == "US":
        location = "United States"

    # Execute search
    result = await serper_multi_page_news(
        query=query,
        pages=pages,
        location=location
    )

    # Add metadata
    result["company_name"] = company_name
    result["domain"] = domain
    result["category"] = category

    return result


@activity.defn
async def serper_topic_research(
    topic: str,
    article_type: str = "news",
    pages: int = 2,
    priority_sources: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Search for topic-based research (for articles).

    Args:
        topic: Article topic
        article_type: Type of article
        pages: Number of pages to fetch
        priority_sources: Sources to prioritize in results

    Returns:
        Topic research results
    """
    # For articles, search more pages by default
    if article_type in ["deep_dive", "analysis"]:
        pages = min(pages + 1, 3)

    result = await serper_multi_page_news(
        query=topic,
        pages=pages,
        time_period="m"  # Month for articles (more recent)
    )

    # If priority sources specified, boost those results
    if priority_sources:
        boosted = []
        regular = []

        for article in result["articles"]:
            source = article.get("source", "").lower()
            if any(ps.lower() in source for ps in priority_sources):
                boosted.append(article)
            else:
                regular.append(article)

        result["articles"] = boosted + regular
        result["urls"] = [a["url"] for a in result["articles"] if a.get("url")]

    result["topic"] = topic
    result["article_type"] = article_type

    return result
