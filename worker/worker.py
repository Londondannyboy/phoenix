"""
Phoenix Unified Worker

Single Temporal worker that runs BOTH:
- CompanyCreationWorkflow
- ArticleCreationWorkflow

This is the heart of Phoenix - one worker, all workflows.
"""

import asyncio
import sys

from temporalio.client import Client
from temporalio.worker import Worker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import configuration
from config import config

# Import workflows
from workflows.company_creation import CompanyCreationWorkflow
from workflows.article_creation import ArticleCreationWorkflow

# Import all activities
# Research
from activities.research.serper import (
    serper_multi_page_news,
    serper_company_news,
    serper_topic_research,
)
from activities.research.url_filter import (
    smart_filter_urls,
    check_url_accessibility,
)
from activities.research.crawl_fallback import (
    crawl4ai_service,
    firecrawl_scrape,
    linkup_fetch,
    httpx_basic_crawl,
    crawl_with_fallback,
)
from activities.research.deep_research import (
    deep_research_company,
    deep_research_article,
)

# Storage
from activities.storage.zep_hybrid import (
    check_zep_for_existing,
    get_zep_context_for_generation,
    deposit_to_zep_hybrid,
    build_zep_context_prompt,
)


async def main():
    """Start the Phoenix unified worker."""

    print("=" * 70)
    print("Phoenix Unified Worker - Starting...")
    print("=" * 70)

    # Display configuration
    print("\nConfiguration:")
    print(f"   Temporal Address: {config.TEMPORAL_ADDRESS}")
    print(f"   Namespace: {config.TEMPORAL_NAMESPACE}")
    print(f"   Task Queue: {config.TEMPORAL_TASK_QUEUE}")
    print(f"   API Key: {'Set' if config.TEMPORAL_API_KEY else 'Not set'}")
    print(f"   Environment: {config.ENVIRONMENT}")

    # Validate required environment variables
    missing = config.validate_required()

    if missing:
        print(f"\nMissing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\n   Please set them in .env file or environment")
        sys.exit(1)

    print("\nAll required environment variables present")

    # Display service status
    print("\nService Status:")
    service_config = config.as_dict()
    for key, value in service_config.items():
        if key.startswith("has_"):
            service_name = key.replace("has_", "").upper()
            status = "YES" if value else "NO"
            print(f"   {service_name}: {status}")

    # Get AI model
    try:
        provider, model = config.get_ai_model()
        print(f"\nAI Model: {provider} / {model}")
    except ValueError as e:
        print(f"\nAI Error: {e}")
        sys.exit(1)

    # Connect to Temporal
    print(f"\nConnecting to Temporal Cloud...")

    try:
        if config.TEMPORAL_API_KEY:
            # Temporal Cloud with TLS
            client = await Client.connect(
                config.TEMPORAL_ADDRESS,
                namespace=config.TEMPORAL_NAMESPACE,
                api_key=config.TEMPORAL_API_KEY,
                tls=True,
            )
        else:
            # Local Temporal (development)
            client = await Client.connect(
                config.TEMPORAL_ADDRESS,
                namespace=config.TEMPORAL_NAMESPACE,
            )

        print("Connected to Temporal successfully")

    except Exception as e:
        print(f"Failed to connect to Temporal: {e}")
        sys.exit(1)

    # Create unified worker with ALL workflows and activities
    worker = Worker(
        client,
        task_queue=config.TEMPORAL_TASK_QUEUE,
        workflows=[
            CompanyCreationWorkflow,
            ArticleCreationWorkflow,
        ],
        activities=[
            # ========== RESEARCH ==========
            # Serper
            serper_multi_page_news,
            serper_company_news,
            serper_topic_research,

            # URL Filtering
            smart_filter_urls,
            check_url_accessibility,

            # Crawling
            crawl4ai_service,
            firecrawl_scrape,
            linkup_fetch,
            httpx_basic_crawl,
            crawl_with_fallback,

            # Deep Research
            deep_research_company,
            deep_research_article,

            # ========== STORAGE ==========
            # Zep Hybrid
            check_zep_for_existing,
            get_zep_context_for_generation,
            deposit_to_zep_hybrid,
            build_zep_context_prompt,

            # TODO: Add these as they're built
            # Database
            # save_company_to_neon,
            # save_article_to_neon,

            # Generation
            # generate_company_profile,
            # generate_article_content,

            # Media
            # generate_images,
            # extract_logo,

            # Validation
            # validate_urls,
        ],
    )

    print("\n" + "=" * 70)
    print("Phoenix Unified Worker Started Successfully!")
    print("=" * 70)
    print(f"   Task Queue: {config.TEMPORAL_TASK_QUEUE}")
    print(f"   Environment: {config.ENVIRONMENT}")
    print("=" * 70)

    print("\nRegistered Workflows:")
    print("   - CompanyCreationWorkflow")
    print("   - ArticleCreationWorkflow")

    print("\nRegistered Activities:")
    activity_groups = [
        ("Research - Serper", [
            "serper_multi_page_news",
            "serper_company_news",
            "serper_topic_research",
        ]),
        ("Research - URL Filter", [
            "smart_filter_urls",
            "check_url_accessibility",
        ]),
        ("Research - Crawling", [
            "crawl4ai_service",
            "firecrawl_scrape",
            "linkup_fetch",
            "httpx_basic_crawl",
            "crawl_with_fallback",
        ]),
        ("Research - Deep", [
            "deep_research_company",
            "deep_research_article",
        ]),
        ("Storage - Zep", [
            "check_zep_for_existing",
            "get_zep_context_for_generation",
            "deposit_to_zep_hybrid",
            "build_zep_context_prompt",
        ]),
    ]

    for group_name, activities in activity_groups:
        print(f"\n   {group_name}:")
        for activity in activities:
            print(f"     - {activity}")

    print("\nWorker is ready to process workflows")
    print("   Press Ctrl+C to stop\n")

    # Run worker (blocks until interrupted)
    await worker.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nPhoenix Worker stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nPhoenix Worker crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
