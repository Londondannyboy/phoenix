"""
Deep Research Orchestration

Orchestrates the full deep research pipeline:
1. Serper multi-page search (pages 1+2)
2. Smart URL filtering
3. Parallel crawling with fallback chain
4. Result aggregation

This is the SECRET WEAPON - 53% cost savings vs Exa.
"""

import asyncio
from typing import Dict, Any, List, Optional
from temporalio import activity

from .serper import serper_multi_page_news, serper_company_news, serper_topic_research
from .url_filter import smart_filter_urls
from .crawl_fallback import crawl_with_fallback


# ============================================================================
# DEEP RESEARCH FOR COMPANIES
# ============================================================================

@activity.defn
async def deep_research_company(
    company_name: str,
    domain: str,
    category: str,
    jurisdiction: str = "UK",
    max_urls: int = 15,
    use_exa: bool = False
) -> Dict[str, Any]:
    """
    Deep research for company profile generation.

    Pipeline:
    1. Serper pages 1+2 → 20 URLs
    2. Smart filter → 15 high-quality URLs
    3. Parallel crawl all 15 with fallback chain
    4. Aggregate 50,000+ words of research

    Cost: ~$0.07 (vs $0.15 with Exa)

    Args:
        company_name: Company name
        domain: Company domain
        category: Company category
        jurisdiction: Geographic jurisdiction
        max_urls: Maximum URLs to crawl
        use_exa: Whether to use Exa as supplement

    Returns:
        Aggregated research data
    """
    activity.logger.info(f"Deep research for company: {company_name}")

    # ========== STEP 1: SERPER MULTI-PAGE ==========
    serper_result = await serper_company_news(
        domain=domain,
        company_name=company_name,
        category=category,
        jurisdiction=jurisdiction,
        pages=2  # Pages 1 and 2
    )

    all_urls = serper_result.get("urls", [])
    activity.logger.info(f"Serper found {len(all_urls)} URLs")

    # ========== STEP 2: SMART FILTERING ==========
    filtered_urls = await smart_filter_urls(
        urls=all_urls,
        max_urls=max_urls,
        exclude_paywalls=True,
        exclude_social=True,
        prefer_authoritative=True
    )

    activity.logger.info(f"Filtered to {len(filtered_urls)} URLs for crawling")

    # ========== STEP 3: PARALLEL DEEP CRAWL ==========
    # Use asyncio.gather to crawl all URLs in parallel
    crawl_tasks = [crawl_with_fallback(url) for url in filtered_urls]

    crawl_results = await asyncio.gather(
        *crawl_tasks,
        return_exceptions=True
    )

    # Process results
    successful_crawls = []
    crawler_stats = {
        "crawl4ai_service": 0,
        "firecrawl": 0,
        "linkup": 0,
        "httpx_basic": 0
    }

    for result in crawl_results:
        if isinstance(result, Exception):
            continue

        if result.get("success"):
            successful_crawls.append(result)
            crawler = result.get("crawler", "unknown")
            if crawler in crawler_stats:
                crawler_stats[crawler] += 1

    activity.logger.info(
        f"Crawled {len(successful_crawls)}/{len(filtered_urls)} URLs successfully"
    )

    # ========== STEP 4: BUILD ARTICLES ==========
    articles = []
    total_words = 0
    total_cost = serper_result.get("cost", 0.0)

    for i, crawl in enumerate(successful_crawls):
        # Get original Serper metadata
        original_article = None
        for article in serper_result.get("articles", []):
            if article.get("url") == crawl.get("url"):
                original_article = article
                break

        word_count = crawl.get("word_count", 0)
        total_words += word_count

        # Add cost for paid crawlers
        if crawl.get("crawler") == "firecrawl":
            total_cost += crawl.get("cost", 0.01)

        articles.append({
            "url": crawl.get("url"),
            "title": crawl.get("title") or (original_article.get("title") if original_article else ""),
            "content": crawl.get("content", ""),
            "source": original_article.get("source", "") if original_article else "",
            "date": original_article.get("date", "") if original_article else "",
            "snippet": original_article.get("snippet", "") if original_article else "",
            "crawler_used": crawl.get("crawler", "unknown"),
            "word_count": word_count
        })

    activity.logger.info(
        f"Deep research complete: {len(articles)} articles, "
        f"{total_words:,} words, cost: ${total_cost:.4f}"
    )

    return {
        "articles": articles,
        "total_sources": len(articles),
        "total_words": total_words,
        "crawlers_used": crawler_stats,
        "cost": total_cost,
        "company_name": company_name,
        "domain": domain,
        "category": category,
        "urls_found": len(all_urls),
        "urls_filtered": len(filtered_urls),
        "urls_crawled": len(successful_crawls)
    }


# ============================================================================
# DEEP RESEARCH FOR ARTICLES
# ============================================================================

@activity.defn
async def deep_research_article(
    topic: str,
    article_type: str = "news",
    max_sources: int = 30,
    priority_sources: Optional[List[str]] = None,
    exclude_paywalls: bool = True
) -> Dict[str, Any]:
    """
    Deep research for article generation.

    Articles need MORE research than company profiles:
    - More pages (2-3)
    - More URLs to crawl (30)
    - More content depth

    Args:
        topic: Article topic
        article_type: Type of article
        max_sources: Maximum sources to crawl
        priority_sources: Sources to prioritize
        exclude_paywalls: Skip paywalled content

    Returns:
        Aggregated research data
    """
    activity.logger.info(f"Deep research for article: {topic}")

    # More pages for articles
    pages = 3 if article_type in ["deep_dive", "analysis"] else 2

    # ========== STEP 1: SERPER MULTI-PAGE ==========
    serper_result = await serper_topic_research(
        topic=topic,
        article_type=article_type,
        pages=pages,
        priority_sources=priority_sources
    )

    all_urls = serper_result.get("urls", [])
    activity.logger.info(f"Serper found {len(all_urls)} URLs")

    # ========== STEP 2: SMART FILTERING ==========
    filtered_urls = await smart_filter_urls(
        urls=all_urls,
        max_urls=max_sources,
        exclude_paywalls=exclude_paywalls,
        exclude_social=True,
        prefer_authoritative=True
    )

    activity.logger.info(f"Filtered to {len(filtered_urls)} URLs for crawling")

    # ========== STEP 3: PARALLEL DEEP CRAWL ==========
    crawl_tasks = [crawl_with_fallback(url) for url in filtered_urls]

    crawl_results = await asyncio.gather(
        *crawl_tasks,
        return_exceptions=True
    )

    # Process results
    successful_crawls = []
    crawler_stats = {
        "crawl4ai_service": 0,
        "firecrawl": 0,
        "linkup": 0,
        "httpx_basic": 0
    }

    for result in crawl_results:
        if isinstance(result, Exception):
            continue

        if result.get("success"):
            successful_crawls.append(result)
            crawler = result.get("crawler", "unknown")
            if crawler in crawler_stats:
                crawler_stats[crawler] += 1

    activity.logger.info(
        f"Crawled {len(successful_crawls)}/{len(filtered_urls)} URLs successfully"
    )

    # ========== STEP 4: BUILD SOURCES ==========
    sources = []
    total_words = 0
    total_cost = serper_result.get("cost", 0.0)

    for crawl in successful_crawls:
        # Get original Serper metadata
        original_article = None
        for article in serper_result.get("articles", []):
            if article.get("url") == crawl.get("url"):
                original_article = article
                break

        word_count = crawl.get("word_count", 0)
        total_words += word_count

        if crawl.get("crawler") == "firecrawl":
            total_cost += crawl.get("cost", 0.01)

        sources.append({
            "url": crawl.get("url"),
            "title": crawl.get("title") or (original_article.get("title") if original_article else ""),
            "content": crawl.get("content", ""),
            "source": original_article.get("source", "") if original_article else "",
            "date": original_article.get("date", "") if original_article else "",
            "crawler_used": crawl.get("crawler", "unknown"),
            "word_count": word_count
        })

    activity.logger.info(
        f"Deep research complete: {len(sources)} sources, "
        f"{total_words:,} words, cost: ${total_cost:.4f}"
    )

    return {
        "sources": sources,
        "total_sources": len(sources),
        "total_words": total_words,
        "crawlers_used": crawler_stats,
        "cost": total_cost,
        "topic": topic,
        "article_type": article_type,
        "urls_found": len(all_urls),
        "urls_filtered": len(filtered_urls),
        "urls_crawled": len(successful_crawls)
    }
