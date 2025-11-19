"""
Phoenix Crawl Service

FastAPI microservice for web crawling using Crawl4AI and Playwright.
Provides intelligent content extraction with multiple crawling strategies.
"""

import asyncio
import re
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import httpx
from bs4 import BeautifulSoup

# Crawl4AI imports
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    print("Warning: crawl4ai not installed, using fallback crawler only")


# ============================================================================
# APP SETUP
# ============================================================================

app = FastAPI(
    title="Phoenix Crawl Service",
    description="Web crawling microservice for Phoenix content engine",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# MODELS
# ============================================================================

class CrawlRequest(BaseModel):
    """Request to crawl a URL."""
    url: str
    timeout: int = 30
    wait_for_selector: Optional[str] = None
    extract_images: bool = False
    use_js: bool = True


class CrawlResponse(BaseModel):
    """Response from crawling."""
    url: str
    success: bool
    content: Optional[str] = None
    title: Optional[str] = None
    word_count: int = 0
    images: List[str] = []
    crawler_used: str = "unknown"
    error: Optional[str] = None
    crawl_time_ms: int = 0


class BatchCrawlRequest(BaseModel):
    """Request to crawl multiple URLs."""
    urls: List[str]
    timeout: int = 30
    max_concurrent: int = 5
    use_js: bool = True


class BatchCrawlResponse(BaseModel):
    """Response from batch crawling."""
    total: int
    successful: int
    failed: int
    results: List[CrawlResponse]
    total_time_ms: int = 0


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    crawl4ai_available: bool
    timestamp: str


# ============================================================================
# CRAWLING FUNCTIONS
# ============================================================================

async def crawl_with_crawl4ai(url: str, timeout: int = 30, use_js: bool = True) -> CrawlResponse:
    """
    Crawl URL using Crawl4AI with Playwright.

    This is the primary crawler with full JS rendering support.
    """
    if not CRAWL4AI_AVAILABLE:
        raise Exception("Crawl4AI not available")

    start_time = datetime.now()

    try:
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
        )

        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="networkidle" if use_js else "domcontentloaded",
            page_timeout=timeout * 1000,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=url,
                config=crawler_config
            )

            if not result.success:
                raise Exception(f"Crawl failed: {result.error_message}")

            # Extract content
            content = result.markdown_v2.raw_markdown if hasattr(result, 'markdown_v2') else result.markdown
            title = result.metadata.get("title", "") if result.metadata else ""

            # Clean content
            content = clean_markdown(content)
            word_count = len(content.split()) if content else 0

            # Extract images if present
            images = []
            if result.media and "images" in result.media:
                images = [img.get("src", "") for img in result.media["images"][:10]]

            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return CrawlResponse(
                url=url,
                success=True,
                content=content,
                title=title,
                word_count=word_count,
                images=images,
                crawler_used="crawl4ai",
                crawl_time_ms=elapsed_ms
            )

    except Exception as e:
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return CrawlResponse(
            url=url,
            success=False,
            crawler_used="crawl4ai",
            error=str(e),
            crawl_time_ms=elapsed_ms
        )


async def crawl_with_httpx(url: str, timeout: int = 30) -> CrawlResponse:
    """
    Fallback crawler using httpx + BeautifulSoup.

    No JS rendering, but fast and reliable for static pages.
    """
    start_time = datetime.now()

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers=headers
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text().strip()

            # Remove unwanted elements
            for element in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()

            # Extract main content
            main_content = soup.find("main") or soup.find("article") or soup.find("body")
            if main_content:
                content = main_content.get_text(separator="\n", strip=True)
            else:
                content = soup.get_text(separator="\n", strip=True)

            # Clean content
            content = clean_text(content)
            word_count = len(content.split()) if content else 0

            # Extract images
            images = []
            for img in soup.find_all("img", src=True)[:10]:
                src = img["src"]
                if src.startswith("http"):
                    images.append(src)

            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return CrawlResponse(
                url=url,
                success=True,
                content=content,
                title=title,
                word_count=word_count,
                images=images,
                crawler_used="httpx",
                crawl_time_ms=elapsed_ms
            )

    except Exception as e:
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return CrawlResponse(
            url=url,
            success=False,
            crawler_used="httpx",
            error=str(e),
            crawl_time_ms=elapsed_ms
        )


def clean_markdown(text: str) -> str:
    """Clean markdown content."""
    if not text:
        return ""

    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def clean_text(text: str) -> str:
    """Clean plain text content."""
    if not text:
        return ""

    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        crawl4ai_available=CRAWL4AI_AVAILABLE,
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Alternative health check endpoint."""
    return await health_check()


@app.post("/crawl", response_model=CrawlResponse)
async def crawl_url(request: CrawlRequest):
    """
    Crawl a single URL.

    Uses Crawl4AI (with Playwright) as primary crawler,
    falls back to httpx for simpler pages or when Crawl4AI fails.
    """
    # Try Crawl4AI first if JS rendering is needed
    if CRAWL4AI_AVAILABLE and request.use_js:
        result = await crawl_with_crawl4ai(
            url=request.url,
            timeout=request.timeout,
            use_js=request.use_js
        )

        if result.success:
            return result

        # Fall back to httpx
        print(f"Crawl4AI failed for {request.url}, trying httpx: {result.error}")

    # Use httpx as fallback or primary for non-JS pages
    return await crawl_with_httpx(
        url=request.url,
        timeout=request.timeout
    )


@app.post("/crawl/batch", response_model=BatchCrawlResponse)
async def crawl_batch(request: BatchCrawlRequest):
    """
    Crawl multiple URLs concurrently.

    Respects max_concurrent limit to avoid overwhelming the service.
    """
    start_time = datetime.now()

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(request.max_concurrent)

    async def crawl_with_limit(url: str) -> CrawlResponse:
        async with semaphore:
            crawl_request = CrawlRequest(
                url=url,
                timeout=request.timeout,
                use_js=request.use_js
            )

            # Try Crawl4AI first
            if CRAWL4AI_AVAILABLE and request.use_js:
                result = await crawl_with_crawl4ai(
                    url=url,
                    timeout=request.timeout,
                    use_js=request.use_js
                )
                if result.success:
                    return result

            # Fall back to httpx
            return await crawl_with_httpx(
                url=url,
                timeout=request.timeout
            )

    # Crawl all URLs concurrently
    tasks = [crawl_with_limit(url) for url in request.urls]
    results = await asyncio.gather(*tasks)

    elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    return BatchCrawlResponse(
        total=len(results),
        successful=successful,
        failed=failed,
        results=results,
        total_time_ms=elapsed_ms
    )


@app.post("/extract-text")
async def extract_text(request: CrawlRequest):
    """
    Extract plain text from a URL.

    Returns only the text content without formatting.
    """
    result = await crawl_url(request)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    # Convert to plain text if needed
    content = result.content or ""

    # Remove markdown formatting
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)  # Links
    content = re.sub(r'[#*_`]', '', content)  # Formatting chars
    content = clean_text(content)

    return {
        "url": result.url,
        "text": content,
        "word_count": len(content.split()),
        "title": result.title
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
