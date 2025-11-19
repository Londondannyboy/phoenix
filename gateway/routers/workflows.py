"""
Workflow trigger endpoints for Phoenix Gateway.

Endpoints:
- POST /api/v1/workflows/companies - Trigger CompanyCreationWorkflow
- POST /api/v1/workflows/articles - Trigger ArticleCreationWorkflow
- GET /api/v1/workflows/{workflow_id}/status - Check workflow status
- GET /api/v1/workflows/{workflow_id}/result - Get workflow result (blocking)
"""

import os
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from auth import verify_api_key
from temporal_client import TemporalClientManager

router = APIRouter(
    prefix="/api/v1/workflows",
    tags=["Workflows"],
    dependencies=[Depends(verify_api_key)]
)

# Task queue from environment
TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "phoenix-queue")


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CompanyWorkflowRequest(BaseModel):
    """Request to create a company profile."""
    url: HttpUrl
    category: str = "placement_agent"
    jurisdiction: str = "UK"
    app: str = "placement"
    force_update: bool = False
    research_depth: str = "standard"  # quick, standard, deep
    max_crawl_urls: int = 15
    use_exa: bool = False  # Optional, cost saving


class ArticleWorkflowRequest(BaseModel):
    """Request to create an article."""
    topic: str
    article_type: str = "news"  # news, analysis, deep_dive
    app: str = "placement"
    research_depth: str = "deep"
    max_sources: int = 30
    priority_sources: Optional[List[str]] = None
    exclude_paywalls: bool = True


class WorkflowStartResponse(BaseModel):
    """Response when workflow is started."""
    workflow_id: str
    status: str
    started_at: str
    message: str
    task_queue: str


class WorkflowStatusResponse(BaseModel):
    """Response for workflow status check."""
    workflow_id: str
    status: str  # running, completed, failed, cancelled
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ============================================================================
# COMPANY WORKFLOW ENDPOINTS
# ============================================================================

@router.post("/companies", response_model=WorkflowStartResponse)
async def create_company_profile(request: CompanyWorkflowRequest):
    """
    Trigger CompanyCreationWorkflow.

    Creates a comprehensive company profile through:
    1. Zep check (existing knowledge)
    2. Deep research (Serper pages 1+2 → Crawl4AI)
    3. AI profile generation (Claude Sonnet 4.5)
    4. Image generation (Flux)
    5. Database storage (Neon)
    6. Zep deposit (narrative + entities)

    Timeline: 90-150 seconds
    Cost: ~$0.07
    """
    client = await TemporalClientManager.get_client()

    # Generate workflow ID
    workflow_id = f"company-{request.app}-{uuid.uuid4().hex[:8]}"

    # Prepare input
    workflow_input = {
        "url": str(request.url),
        "category": request.category,
        "jurisdiction": request.jurisdiction,
        "app": request.app,
        "force_update": request.force_update,
        "research_depth": request.research_depth,
        "max_crawl_urls": request.max_crawl_urls,
        "use_exa": request.use_exa
    }

    try:
        # Start workflow
        handle = await client.start_workflow(
            "CompanyCreationWorkflow",
            workflow_input,
            id=workflow_id,
            task_queue=TASK_QUEUE,
        )

        return WorkflowStartResponse(
            workflow_id=workflow_id,
            status="started",
            started_at=datetime.utcnow().isoformat(),
            message="Company profile creation started. Expected completion: 90-150 seconds.",
            task_queue=TASK_QUEUE
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start workflow: {str(e)}"
        )


# ============================================================================
# ARTICLE WORKFLOW ENDPOINTS
# ============================================================================

@router.post("/articles", response_model=WorkflowStartResponse)
async def create_article(request: ArticleWorkflowRequest):
    """
    Trigger ArticleCreationWorkflow.

    Creates a comprehensive article through:
    1. Zep check (existing knowledge)
    2. Deep research (Serper pages 1+2 → Crawl4AI 30+ sources)
    3. AI content generation (Claude Sonnet 4.5)
    4. Image generation (7 contextual images)
    5. Database storage (Neon)
    6. Zep deposit (narrative + entities)

    Timeline: 5-12 minutes
    Cost: ~$0.10
    """
    client = await TemporalClientManager.get_client()

    # Generate workflow ID
    workflow_id = f"article-{request.app}-{uuid.uuid4().hex[:8]}"

    # Prepare input
    workflow_input = {
        "topic": request.topic,
        "article_type": request.article_type,
        "app": request.app,
        "research_depth": request.research_depth,
        "max_sources": request.max_sources,
        "priority_sources": request.priority_sources or [],
        "exclude_paywalls": request.exclude_paywalls
    }

    try:
        # Start workflow
        handle = await client.start_workflow(
            "ArticleCreationWorkflow",
            workflow_input,
            id=workflow_id,
            task_queue=TASK_QUEUE,
        )

        return WorkflowStartResponse(
            workflow_id=workflow_id,
            status="started",
            started_at=datetime.utcnow().isoformat(),
            message="Article creation started. Expected completion: 5-12 minutes.",
            task_queue=TASK_QUEUE
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start workflow: {str(e)}"
        )


# ============================================================================
# WORKFLOW STATUS ENDPOINTS
# ============================================================================

@router.get("/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str):
    """
    Get workflow status (non-blocking).

    Returns current status without waiting for completion.
    """
    client = await TemporalClientManager.get_client()

    try:
        handle = client.get_workflow_handle(workflow_id)
        describe = await handle.describe()

        # Map Temporal status to simple status
        status_map = {
            "RUNNING": "running",
            "COMPLETED": "completed",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
            "TERMINATED": "terminated",
            "CONTINUED_AS_NEW": "running",
            "TIMED_OUT": "failed"
        }

        status = status_map.get(describe.status.name, "unknown")

        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=status,
            started_at=describe.start_time.isoformat() if describe.start_time else None,
            completed_at=describe.close_time.isoformat() if describe.close_time else None
        )

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow not found: {workflow_id}"
        )


@router.get("/{workflow_id}/result")
async def get_workflow_result(workflow_id: str):
    """
    Get workflow result (blocking).

    Waits for workflow to complete and returns the result.
    """
    client = await TemporalClientManager.get_client()

    try:
        handle = client.get_workflow_handle(workflow_id)
        result = await handle.result()

        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Workflow failed or not found: {str(e)}"
        )
