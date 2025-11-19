"""
Company Creation Workflow

Zep-first workflow for comprehensive company profiling.

Pipeline:
1. Check Zep for existing (avoid duplicate research)
2. Get Zep context (enrich with existing knowledge)
3. Deep research (Serper pages 1+2 → Crawl4AI)
4. Generate profile (Claude Sonnet 4.5)
5. Extract entities (deals, people)
6. Generate images (Flux)
7. Save to database (Neon)
8. Deposit to Zep (hybrid: narrative + entities)

Timeline: 90-150 seconds
Cost: ~$0.07
"""

from temporalio import workflow
from datetime import timedelta
import asyncio
from typing import Dict, Any

# Import models (passed through)
with workflow.unsafe.imports_passed_through():
    pass


@workflow.defn
class CompanyCreationWorkflow:
    """
    Zep-first company creation workflow.

    This workflow puts Zep at the center:
    - Check first (don't duplicate)
    - Enrich with context (better content)
    - Deposit back (grow the graph)
    """

    @workflow.run
    async def run(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute company creation workflow.

        Args:
            input_dict: CompanyInput as dict

        Returns:
            Dict with company_id, slug, metrics
        """
        workflow.logger.info(f"Creating company: {input_dict.get('url')}")

        # Extract input
        url = input_dict.get("url")
        category = input_dict.get("category", "placement_agent")
        jurisdiction = input_dict.get("jurisdiction", "UK")
        app = input_dict.get("app", "placement")
        force_update = input_dict.get("force_update", False)
        max_crawl_urls = input_dict.get("max_crawl_urls", 15)
        use_exa = input_dict.get("use_exa", False)

        # ===== PHASE 1: NORMALIZE URL =====
        workflow.logger.info("Phase 1: Normalizing URL")

        # Extract domain and company name from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        company_name_guess = domain.split(".")[0].replace("-", " ").title()

        workflow.logger.info(f"Domain: {domain}, Company guess: {company_name_guess}")

        # ===== PHASE 2: CHECK ZEP FIRST =====
        workflow.logger.info("Phase 2: Checking Zep for existing company")

        zep_existing = await workflow.execute_activity(
            "check_zep_for_existing",
            args=[company_name_guess, "company", domain, app],
            start_to_close_timeout=timedelta(seconds=30)
        )

        if zep_existing.get("exists") and not force_update:
            workflow.logger.info(f"Company exists in Zep: {zep_existing.get('entity_id')}")
            # Could return existing or continue to enrich

        # ===== PHASE 3: GET ZEP CONTEXT =====
        workflow.logger.info("Phase 3: Getting Zep context for generation")

        zep_context = await workflow.execute_activity(
            "get_zep_context_for_generation",
            args=[company_name_guess, "company", app],
            start_to_close_timeout=timedelta(seconds=30)
        )

        workflow.logger.info(
            f"Zep context: {zep_context.get('total_context_items', 0)} items, "
            f"{len(zep_context.get('deals', []))} deals, "
            f"{len(zep_context.get('people', []))} people"
        )

        # Build context prompt for AI
        context_prompt = await workflow.execute_activity(
            "build_zep_context_prompt",
            args=[zep_context],
            start_to_close_timeout=timedelta(seconds=10)
        )

        # ===== PHASE 4: DEEP RESEARCH =====
        workflow.logger.info("Phase 4: Deep research (Serper pages 1+2 → Crawl4AI)")

        research_data = await workflow.execute_activity(
            "deep_research_company",
            args=[
                company_name_guess,
                domain,
                category,
                jurisdiction,
                max_crawl_urls,
                use_exa
            ],
            start_to_close_timeout=timedelta(minutes=5)
        )

        workflow.logger.info(
            f"Research complete: {research_data.get('total_sources', 0)} sources, "
            f"{research_data.get('total_words', 0):,} words, "
            f"cost: ${research_data.get('cost', 0):.4f}"
        )

        # ===== PHASE 5: GENERATE PROFILE =====
        workflow.logger.info("Phase 5: Generating company profile (Claude Sonnet 4.5)")

        # TODO: Implement generate_company_profile activity
        # This will use the research_data + context_prompt to generate profile
        # profile = await workflow.execute_activity(
        #     "generate_company_profile",
        #     args=[research_data, context_prompt],
        #     start_to_close_timeout=timedelta(seconds=120)
        # )

        # Placeholder profile
        profile = {
            "name": company_name_guess,
            "slug": domain.replace(".", "-"),
            "domain": domain,
            "category": category,
            "app": app,
            "profile_sections": {
                "overview": {
                    "title": "Overview",
                    "content": f"Company profile for {company_name_guess}"
                }
            },
            "deals": [],
            "key_people": [],
            "data_completeness_score": 0.0
        }

        # ===== PHASE 6: EXTRACT ENTITIES =====
        workflow.logger.info("Phase 6: Extracting entities for Zep graph")

        # TODO: Implement entity extraction
        extracted_entities = {
            "deals": [],
            "people": [],
            "companies": []
        }

        # ===== PHASE 7: GENERATE IMAGES =====
        workflow.logger.info("Phase 7: Generating images (Flux)")

        # TODO: Implement image generation
        images = {
            "logo_url": None,
            "featured_image_url": None,
            "hero_image_url": None
        }

        # ===== PHASE 8: SAVE TO DATABASE =====
        workflow.logger.info("Phase 8: Saving to Neon database")

        # TODO: Implement database save
        company_id = "temp-id-" + domain

        # ===== PHASE 9: DEPOSIT TO ZEP =====
        workflow.logger.info("Phase 9: Depositing to Zep (hybrid storage)")

        zep_result = await workflow.execute_activity(
            "deposit_to_zep_hybrid",
            args=[
                company_id,
                company_name_guess,
                "company",
                domain,
                profile,
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
            0.01  # Profile generation cost placeholder
        )

        workflow.logger.info(
            f"Company creation complete: {profile.get('slug')} "
            f"(cost: ${total_cost:.4f})"
        )

        return {
            "status": "created",
            "company_id": company_id,
            "slug": profile.get("slug"),
            "name": company_name_guess,
            "domain": domain,
            "logo_url": images.get("logo_url"),
            "featured_image_url": images.get("featured_image_url"),
            "research_cost": total_cost,
            "research_sources": research_data.get("total_sources", 0),
            "research_words": research_data.get("total_words", 0),
            "data_completeness": profile.get("data_completeness_score", 0),
            "zep_entities_created": zep_result.get("entities_created", 0),
            "zep_relationships_created": zep_result.get("relationships_created", 0)
        }
