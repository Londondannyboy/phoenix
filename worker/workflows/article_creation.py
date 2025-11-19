"""
Article Creation Workflow

Zep-first workflow for comprehensive article generation.

Pipeline:
1. Check Zep for existing (avoid duplicate content)
2. Get Zep context (related entities)
3. Deep research (Serper pages 1-3 → Crawl4AI 30+ sources)
4. Generate article (Claude Sonnet 4.5)
5. Extract entities (companies, people, deals)
6. Generate images (7 contextual)
7. Save to database (Neon)
8. Deposit to Zep (hybrid: narrative + entities)

Timeline: 5-12 minutes
Cost: ~$0.10
"""

from temporalio import workflow
from datetime import timedelta
import asyncio
from typing import Dict, Any

with workflow.unsafe.imports_passed_through():
    pass


@workflow.defn
class ArticleCreationWorkflow:
    """
    Zep-first article creation workflow.

    Articles use MORE research than company profiles:
    - More pages (2-3)
    - More sources (30+)
    - More images (7)
    """

    @workflow.run
    async def run(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute article creation workflow.

        Args:
            input_dict: ArticleInput as dict

        Returns:
            Dict with article_id, slug, metrics
        """
        workflow.logger.info(f"Creating article: {input_dict.get('topic')}")

        # Extract input
        topic = input_dict.get("topic")
        article_type = input_dict.get("article_type", "news")
        app = input_dict.get("app", "placement")
        research_depth = input_dict.get("research_depth", "deep")
        max_sources = input_dict.get("max_sources", 30)
        priority_sources = input_dict.get("priority_sources", [])
        exclude_paywalls = input_dict.get("exclude_paywalls", True)

        # ===== PHASE 1: CHECK ZEP FIRST =====
        workflow.logger.info("Phase 1: Checking Zep for existing article")

        zep_existing = await workflow.execute_activity(
            "check_zep_for_existing",
            args=[topic, "article", None, app],
            start_to_close_timeout=timedelta(seconds=30)
        )

        if zep_existing.get("exists"):
            workflow.logger.info(f"Similar article exists in Zep: {zep_existing.get('entity_id')}")

        # ===== PHASE 2: GET ZEP CONTEXT =====
        workflow.logger.info("Phase 2: Getting Zep context for generation")

        zep_context = await workflow.execute_activity(
            "get_zep_context_for_generation",
            args=[topic, "article", app],
            start_to_close_timeout=timedelta(seconds=30)
        )

        workflow.logger.info(
            f"Zep context: {zep_context.get('total_context_items', 0)} items"
        )

        # Build context prompt
        context_prompt = await workflow.execute_activity(
            "build_zep_context_prompt",
            args=[zep_context],
            start_to_close_timeout=timedelta(seconds=10)
        )

        # ===== PHASE 3: DEEP RESEARCH =====
        workflow.logger.info("Phase 3: Deep research (Serper pages 1-3 → Crawl4AI)")

        research_data = await workflow.execute_activity(
            "deep_research_article",
            args=[
                topic,
                article_type,
                max_sources,
                priority_sources,
                exclude_paywalls
            ],
            start_to_close_timeout=timedelta(minutes=8)
        )

        workflow.logger.info(
            f"Research complete: {research_data.get('total_sources', 0)} sources, "
            f"{research_data.get('total_words', 0):,} words, "
            f"cost: ${research_data.get('cost', 0):.4f}"
        )

        # ===== PHASE 4: GENERATE ARTICLE =====
        workflow.logger.info("Phase 4: Generating article content (Claude Sonnet 4.5)")

        article = await workflow.execute_activity(
            "generate_article_content",
            args=[topic, article_type, research_data, context_prompt, app],
            start_to_close_timeout=timedelta(seconds=180)
        )

        workflow.logger.info(
            f"Article generated: '{article.get('title')}', "
            f"completeness={article.get('data_completeness_score', 0):.2f}"
        )

        slug = article.get("slug", topic.lower().replace(" ", "-")[:50])

        # ===== PHASE 5: EXTRACT ENTITIES =====
        workflow.logger.info("Phase 5: Extracting entities for Zep graph")

        # Use entities from article generation
        extracted_entities = {
            "deals": article.get("deals_mentioned", []),
            "people": [{"name": p} for p in article.get("people_mentioned", [])],
            "companies": [{"name": c} for c in article.get("companies_mentioned", [])]
        }

        workflow.logger.info(
            f"Entities: {len(extracted_entities['deals'])} deals, "
            f"{len(extracted_entities['people'])} people, "
            f"{len(extracted_entities['companies'])} companies"
        )

        # ===== PHASE 6: GENERATE IMAGES =====
        workflow.logger.info("Phase 6: Generating 7 contextual images (Flux)")

        # TODO: Implement image generation
        images = {
            "featured_image_url": None,
            "images": []  # 7 images for different sections
        }

        # ===== PHASE 7: SAVE TO DATABASE =====
        workflow.logger.info("Phase 7: Saving to Neon database")

        db_result = await workflow.execute_activity(
            "save_article_to_neon",
            args=[article, "draft", False],
            start_to_close_timeout=timedelta(seconds=30)
        )

        article_id = db_result.get("article_id", "temp-article-" + slug)

        workflow.logger.info(
            f"Saved to database: {db_result.get('operation')} {db_result.get('slug')}"
        )

        # ===== PHASE 8: DEPOSIT TO ZEP =====
        workflow.logger.info("Phase 8: Depositing to Zep (hybrid storage)")

        zep_result = await workflow.execute_activity(
            "deposit_to_zep_hybrid",
            args=[
                article_id,
                topic,
                "article",
                None,  # No domain for articles
                article,
                extracted_entities,
                app
            ],
            start_to_close_timeout=timedelta(minutes=2)
        )

        workflow.logger.info(
            f"Zep deposit: {zep_result.get('entities_created', 0)} entities, "
            f"{zep_result.get('relationships_created', 0)} relationships"
        )

        # ===== COMPLETE =====
        total_cost = (
            research_data.get("cost", 0.0) +
            0.02  # Article generation cost placeholder
        )

        workflow.logger.info(
            f"Article creation complete: {slug} "
            f"(cost: ${total_cost:.4f})"
        )

        return {
            "status": "created",
            "article_id": article_id,
            "slug": slug,
            "title": topic,
            "article_type": article_type,
            "featured_image_url": images.get("featured_image_url"),
            "research_cost": total_cost,
            "research_sources": research_data.get("total_sources", 0),
            "research_words": research_data.get("total_words", 0),
            "data_completeness": article.get("data_completeness_score", 0),
            "zep_entities_created": zep_result.get("entities_created", 0),
            "zep_relationships_created": zep_result.get("relationships_created", 0)
        }
