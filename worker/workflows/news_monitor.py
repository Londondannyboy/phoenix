"""
News Monitor Workflow

SCHEDULED workflow that runs daily to find and create news articles.

Uses Pydantic AI to assess relevance with Zep + Neon context.

Pipeline:
1. Fetch news for app-specific keywords (Serper)
2. Get Zep context (existing coverage)
3. Get Neon recent (recently published)
4. AI assessment: relevance, new vs saga, priority
5. Spawn ArticleCreationWorkflow for relevant stories

Each app has its own scheduled instance:
- placement: "placement agent", "fund placement", "capital raising"
- relocation: "corporate relocation", "employee mobility", "global mobility"
- rainmaker: "rainmaker", "dealmaker", "investment banking"
"""

from temporalio import workflow
from datetime import timedelta
from typing import Dict, Any, List

with workflow.unsafe.imports_passed_through():
    pass


# ============================================================================
# APP CONFIGURATIONS
# ============================================================================

APP_KEYWORDS = {
    "placement": [
        "placement agent",
        "fund placement",
        "capital raising",
        "private equity fundraising",
        "LP commitment",
        "fund distribution"
    ],
    "relocation": [
        "corporate relocation",
        "employee mobility",
        "global mobility",
        "expat relocation",
        "talent mobility",
        "international assignment"
    ],
    "rainmaker": [
        "rainmaker",
        "dealmaker",
        "investment banking",
        "M&A advisor",
        "deal origination",
        "client acquisition"
    ],
    "chief-of-staff": [
        "chief of staff",
        "executive operations",
        "CEO office",
        "strategic operations",
        "executive assistant"
    ]
}


@workflow.defn
class NewsMonitorWorkflow:
    """
    Scheduled workflow that monitors news and creates articles.

    Runs daily (or on schedule) to:
    1. Find relevant news for the app
    2. Use AI to assess if we should cover it
    3. Automatically create articles for high-priority stories
    """

    @workflow.run
    async def run(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute news monitoring workflow.

        Args:
            input_dict: {
                "app": "placement",
                "keywords": [...] (optional, uses defaults)
                "min_relevance_score": 0.7,
                "auto_create_articles": True,
                "max_articles_to_create": 5
            }

        Returns:
            Summary of monitoring results
        """
        app = input_dict.get("app", "placement")
        keywords = input_dict.get("keywords", APP_KEYWORDS.get(app, []))
        min_relevance = input_dict.get("min_relevance_score", 0.7)
        auto_create = input_dict.get("auto_create_articles", True)
        max_articles = input_dict.get("max_articles_to_create", 5)

        workflow.logger.info(f"News Monitor starting for app: {app}")
        workflow.logger.info(f"Keywords: {keywords}")

        # ===== PHASE 1: FETCH NEWS =====
        workflow.logger.info("Phase 1: Fetching news from Serper")

        # Build query from keywords
        query = " OR ".join(keywords[:3])  # Use top 3 keywords

        news_result = await workflow.execute_activity(
            "serper_multi_page_news",
            args=[query, 2, 10, None, "d"],  # 2 pages, 10 per page, last day
            start_to_close_timeout=timedelta(minutes=2)
        )

        stories = news_result.get("articles", [])
        workflow.logger.info(f"Found {len(stories)} news stories")

        if not stories:
            return {
                "app": app,
                "stories_found": 0,
                "stories_relevant": 0,
                "articles_created": 0,
                "message": "No news stories found for today"
            }

        # ===== PHASE 2: GET ZEP CONTEXT =====
        workflow.logger.info("Phase 2: Getting Zep context for existing coverage")

        zep_context = await workflow.execute_activity(
            "get_zep_context_for_generation",
            args=[query, "article", app],
            start_to_close_timeout=timedelta(seconds=30)
        )

        workflow.logger.info(
            f"Zep context: {len(zep_context.get('articles', []))} existing articles, "
            f"{len(zep_context.get('companies', []))} known companies"
        )

        # ===== PHASE 3: GET NEON RECENT =====
        workflow.logger.info("Phase 3: Getting recently published from Neon")

        neon_recent = await workflow.execute_activity(
            "get_recent_articles_from_neon",
            args=[app, 7, 50],  # Last 7 days, max 50
            start_to_close_timeout=timedelta(seconds=30)
        )

        workflow.logger.info(f"Neon recent: {len(neon_recent)} articles in last 7 days")

        # ===== PHASE 4: AI ASSESSMENT =====
        workflow.logger.info("Phase 4: AI assessment of story relevance")

        assessment_result = await workflow.execute_activity(
            "assess_news_batch",
            args=[
                stories,
                app,
                keywords,
                zep_context,
                neon_recent,
                min_relevance
            ],
            start_to_close_timeout=timedelta(minutes=5)
        )

        relevant_stories = assessment_result.get("relevant_stories", [])

        workflow.logger.info(
            f"Assessment complete: {len(relevant_stories)} relevant stories "
            f"(high={assessment_result.get('total_high_priority', 0)}, "
            f"medium={assessment_result.get('total_medium_priority', 0)}, "
            f"low={assessment_result.get('total_low_priority', 0)})"
        )

        # ===== PHASE 5: CREATE ARTICLES =====
        articles_created = []

        if auto_create and relevant_stories:
            workflow.logger.info(f"Phase 5: Creating articles for top {max_articles} stories")

            # Sort by priority (high first) and relevance score
            sorted_stories = sorted(
                relevant_stories,
                key=lambda x: (
                    0 if x.get("priority") == "high" else (1 if x.get("priority") == "medium" else 2),
                    -x.get("relevance_score", 0)
                )
            )

            # Create articles for top stories
            for story_assessment in sorted_stories[:max_articles]:
                story = story_assessment.get("story", {})

                workflow.logger.info(f"Creating article: {story.get('title', '')[:50]}...")

                # Build article input
                article_input = {
                    "topic": story.get("title", ""),
                    "article_type": "news",
                    "app": app,
                    "research_depth": "standard",
                    "max_sources": 20,
                    "exclude_paywalls": True,
                    # Pass assessment context
                    "source_url": story.get("url"),
                    "story_type": story_assessment.get("story_type", "new"),
                    "suggested_angle": story_assessment.get("suggested_angle"),
                    "related_entities": story_assessment.get("related_entities", [])
                }

                # Spawn child workflow
                try:
                    result = await workflow.execute_child_workflow(
                        "ArticleCreationWorkflow",
                        article_input,
                        id=f"article-{app}-{workflow.uuid4().hex[:8]}",
                        task_queue=workflow.info().task_queue
                    )

                    articles_created.append({
                        "title": story.get("title"),
                        "article_id": result.get("article_id"),
                        "slug": result.get("slug"),
                        "priority": story_assessment.get("priority"),
                        "story_type": story_assessment.get("story_type")
                    })

                    workflow.logger.info(f"Article created: {result.get('slug')}")

                except Exception as e:
                    workflow.logger.error(f"Failed to create article: {str(e)}")

        # ===== COMPLETE =====
        workflow.logger.info(
            f"News Monitor complete for {app}: "
            f"{len(stories)} found, {len(relevant_stories)} relevant, "
            f"{len(articles_created)} created"
        )

        return {
            "app": app,
            "keywords": keywords,
            "stories_found": len(stories),
            "stories_assessed": assessment_result.get("stories_assessed", 0),
            "stories_relevant": len(relevant_stories),
            "articles_created": len(articles_created),
            "articles": articles_created,
            "high_priority_count": assessment_result.get("total_high_priority", 0),
            "medium_priority_count": assessment_result.get("total_medium_priority", 0),
            "low_priority_count": assessment_result.get("total_low_priority", 0),
            "cost": news_result.get("cost", 0.0)
        }


@workflow.defn
class NewsMonitorAllAppsWorkflow:
    """
    Master workflow that runs NewsMonitorWorkflow for all apps.

    Schedule this once daily to monitor all apps.
    """

    @workflow.run
    async def run(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor news for all configured apps.

        Args:
            input_dict: {
                "apps": ["placement", "relocation", "rainmaker"],
                "min_relevance_score": 0.7,
                "max_articles_per_app": 3
            }
        """
        apps = input_dict.get("apps", list(APP_KEYWORDS.keys()))
        min_relevance = input_dict.get("min_relevance_score", 0.7)
        max_per_app = input_dict.get("max_articles_per_app", 3)

        workflow.logger.info(f"News Monitor All Apps: {apps}")

        results = []
        total_created = 0

        for app in apps:
            workflow.logger.info(f"Monitoring {app}...")

            result = await workflow.execute_child_workflow(
                "NewsMonitorWorkflow",
                {
                    "app": app,
                    "min_relevance_score": min_relevance,
                    "auto_create_articles": True,
                    "max_articles_to_create": max_per_app
                },
                id=f"news-monitor-{app}-{workflow.uuid4().hex[:8]}",
                task_queue=workflow.info().task_queue
            )

            results.append(result)
            total_created += result.get("articles_created", 0)

        workflow.logger.info(
            f"News Monitor All Apps complete: {total_created} articles created"
        )

        return {
            "apps_monitored": len(apps),
            "total_articles_created": total_created,
            "results_by_app": results
        }
