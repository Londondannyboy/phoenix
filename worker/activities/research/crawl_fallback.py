"""
Crawl Fallback Chain

Robust crawling with fallback:
1. Crawl4AI (free, browser automation)
2. Firecrawl (paid, intelligent)
3. Linkup (search-based)
4. httpx (basic fallback)
"""

import os
from typing import Dict, Any, Optional
from temporalio import activity
import httpx
from bs4 import BeautifulSoup

from config import config


# ============================================================================
# CRAWL4AI SERVICE CLIENT
# ============================================================================

@activity.defn
async def crawl4ai_service(url: str) -> Dict[str, Any]:
    """
    Crawl URL using Crawl4AI external service.

    This is the PRIMARY crawler - free and handles JavaScript.

    Args:
        url: URL to crawl

    Returns:
        Crawl result with content
    """
    service_url = config.CRAWL_SERVICE_URL

    if not service_url:
        return {
            "success": False,
            "error": "CRAWL_SERVICE_URL not configured",
            "crawler": "crawl4ai_service"
        }

    activity.logger.info(f"Crawl4AI: {url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{service_url}/crawl",
                json={"url": url},
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()

            return {
                "success": result.get("success", False),
                "url": url,
                "content": result.get("content", ""),
                "title": result.get("title", ""),
                "links": result.get("links", []),
                "crawler": "crawl4ai_service",
                "word_count": len(result.get("content", "").split())
            }

    except Exception as e:
        activity.logger.warning(f"Crawl4AI failed for {url}: {str(e)}")
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "crawler": "crawl4ai_service"
        }


# ============================================================================
# FIRECRAWL CLIENT
# ============================================================================

@activity.defn
async def firecrawl_scrape(url: str) -> Dict[str, Any]:
    """
    Crawl URL using Firecrawl API.

    This is the FIRST FALLBACK - paid but intelligent.

    Args:
        url: URL to crawl

    Returns:
        Crawl result with content
    """
    api_key = config.FIRECRAWL_API_KEY

    if not api_key:
        return {
            "success": False,
            "error": "FIRECRAWL_API_KEY not configured",
            "crawler": "firecrawl"
        }

    activity.logger.info(f"Firecrawl: {url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "onlyMainContent": True
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()

            data = result.get("data", {})

            return {
                "success": result.get("success", False),
                "url": url,
                "content": data.get("markdown", ""),
                "title": data.get("metadata", {}).get("title", ""),
                "crawler": "firecrawl",
                "word_count": len(data.get("markdown", "").split()),
                "cost": 0.01  # Approximate cost per scrape
            }

    except Exception as e:
        activity.logger.warning(f"Firecrawl failed for {url}: {str(e)}")
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "crawler": "firecrawl"
        }


# ============================================================================
# LINKUP CLIENT
# ============================================================================

@activity.defn
async def linkup_fetch(url: str) -> Dict[str, Any]:
    """
    Fetch content using Linkup API.

    This is the SECOND FALLBACK - search-based.

    Args:
        url: URL to fetch

    Returns:
        Fetch result with content
    """
    api_key = config.LINKUP_API_KEY

    if not api_key:
        return {
            "success": False,
            "error": "LINKUP_API_KEY not configured",
            "crawler": "linkup"
        }

    activity.logger.info(f"Linkup: {url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linkup.so/v1/search",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "q": url,
                    "depth": "standard",
                    "outputType": "sourcedAnswer"
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()

            # Extract content from sources
            sources = result.get("sources", [])
            content = ""
            for source in sources:
                if source.get("url") == url:
                    content = source.get("content", "")
                    break

            if not content and sources:
                content = sources[0].get("content", "")

            return {
                "success": bool(content),
                "url": url,
                "content": content,
                "title": "",
                "crawler": "linkup",
                "word_count": len(content.split())
            }

    except Exception as e:
        activity.logger.warning(f"Linkup failed for {url}: {str(e)}")
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "crawler": "linkup"
        }


# ============================================================================
# HTTPX BASIC FALLBACK
# ============================================================================

@activity.defn
async def httpx_basic_crawl(url: str) -> Dict[str, Any]:
    """
    Basic crawl using httpx + BeautifulSoup.

    This is the LAST RESORT - no JavaScript support.

    Args:
        url: URL to crawl

    Returns:
        Crawl result with content
    """
    activity.logger.info(f"httpx basic: {url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                follow_redirects=True,
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; PhoenixBot/1.0)"
                }
            )
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            # Get title
            title = ""
            if soup.title:
                title = soup.title.string or ""

            # Get main content
            content = ""

            # Try to find main content area
            main = soup.find("main") or soup.find("article") or soup.find("body")
            if main:
                content = main.get_text(separator="\n", strip=True)

            return {
                "success": bool(content),
                "url": url,
                "content": content,
                "title": title,
                "crawler": "httpx_basic",
                "word_count": len(content.split())
            }

    except Exception as e:
        activity.logger.warning(f"httpx failed for {url}: {str(e)}")
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "crawler": "httpx_basic"
        }


# ============================================================================
# CRAWL WITH FALLBACK CHAIN
# ============================================================================

@activity.defn
async def crawl_with_fallback(url: str) -> Dict[str, Any]:
    """
    Crawl URL with full fallback chain.

    Priority:
    1. Crawl4AI (free, browser automation)
    2. Firecrawl (paid, intelligent)
    3. Linkup (search-based)
    4. httpx (basic fallback)

    Args:
        url: URL to crawl

    Returns:
        Crawl result from first successful crawler
    """
    # Try Crawl4AI first (free)
    result = await crawl4ai_service(url)
    if result.get("success") and result.get("content"):
        return result

    # Fallback to Firecrawl (paid)
    result = await firecrawl_scrape(url)
    if result.get("success") and result.get("content"):
        return result

    # Fallback to Linkup
    result = await linkup_fetch(url)
    if result.get("success") and result.get("content"):
        return result

    # Last resort: httpx basic
    result = await httpx_basic_crawl(url)
    return result
