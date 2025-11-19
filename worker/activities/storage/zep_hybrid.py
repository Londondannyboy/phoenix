"""
Zep Hybrid Storage

Zep-centric storage that handles:
1. Check-first: Query if entity exists, get relationships
2. Context retrieval: Get related entities for content generation
3. Hybrid deposit: Store as narrative + structured entities + relationships

This is the BRAIN of Phoenix - all content flows through Zep.
"""

import os
from typing import Dict, Any, List, Optional
from temporalio import activity
import httpx

from config import config


# ============================================================================
# ZEP CLIENT
# ============================================================================

class ZepClient:
    """Client for Zep Cloud API."""

    def __init__(self):
        self.api_key = config.ZEP_API_KEY
        self.base_url = config.ZEP_API_URL
        self.headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make request to Zep API."""
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=30.0,
                **kwargs
            )
            response.raise_for_status()
            return response.json() if response.text else {}


# ============================================================================
# CHECK-FIRST: Query Zep for existing entity
# ============================================================================

@activity.defn
async def check_zep_for_existing(
    entity_name: str,
    entity_type: str,
    domain: Optional[str] = None,
    app: str = "placement"
) -> Dict[str, Any]:
    """
    Check if entity exists in Zep graph.

    This is called FIRST in every workflow to:
    - Avoid duplicate research
    - Get existing relationships
    - Enrich with new data instead of recreating

    Args:
        entity_name: Name of company or article topic
        entity_type: "company" or "article"
        domain: Domain for companies (optional)
        app: App identifier

    Returns:
        ZepContext with existing data or empty context
    """
    activity.logger.info(f"Checking Zep for existing {entity_type}: {entity_name}")

    try:
        client = ZepClient()

        # Search for entity in graph
        search_results = await client._request(
            "POST",
            "/v2/graph/search",
            json={
                "query": entity_name,
                "limit": 5,
                "scope": "nodes",
                "filters": {
                    "node_type": entity_type
                }
            }
        )

        # Check if we found a match
        nodes = search_results.get("results", [])

        if not nodes:
            activity.logger.info(f"No existing {entity_type} found in Zep")
            return {
                "exists": False,
                "entity_id": None,
                "relationships": [],
                "deals": [],
                "people": [],
                "related_companies": []
            }

        # Found existing entity
        entity = nodes[0]
        entity_id = entity.get("uuid")

        activity.logger.info(f"Found existing {entity_type} in Zep: {entity_id}")

        # Get relationships for this entity
        edges_response = await client._request(
            "GET",
            f"/v2/graph/nodes/{entity_id}/edges"
        )

        edges = edges_response.get("edges", [])

        # Categorize relationships
        deals = []
        people = []
        related_companies = []

        for edge in edges:
            target_type = edge.get("target_node_type", "")

            if target_type == "deal":
                deals.append({
                    "name": edge.get("target_node_name"),
                    "attributes": edge.get("target_node_attributes", {}),
                    "relationship": edge.get("type")
                })
            elif target_type == "person":
                people.append({
                    "name": edge.get("target_node_name"),
                    "attributes": edge.get("target_node_attributes", {}),
                    "relationship": edge.get("type")
                })
            elif target_type == "company":
                related_companies.append({
                    "name": edge.get("target_node_name"),
                    "attributes": edge.get("target_node_attributes", {}),
                    "relationship": edge.get("type")
                })

        activity.logger.info(
            f"Zep context: {len(deals)} deals, {len(people)} people, "
            f"{len(related_companies)} related companies"
        )

        return {
            "exists": True,
            "entity_id": entity_id,
            "entity_data": entity,
            "relationships": edges,
            "deals": deals,
            "people": people,
            "related_companies": related_companies
        }

    except Exception as e:
        activity.logger.error(f"Error checking Zep: {str(e)}")
        # Return empty context on error (don't block workflow)
        return {
            "exists": False,
            "entity_id": None,
            "relationships": [],
            "deals": [],
            "people": [],
            "related_companies": [],
            "error": str(e)
        }


# ============================================================================
# CONTEXT RETRIEVAL: Get context for content generation
# ============================================================================

@activity.defn
async def get_zep_context_for_generation(
    entity_name: str,
    entity_type: str,
    app: str = "placement"
) -> Dict[str, Any]:
    """
    Get rich context from Zep for content generation.

    This provides the AI with:
    - Related articles about this entity
    - Known deals and transactions
    - Key people and relationships
    - Similar companies

    Args:
        entity_name: Name of company or topic
        entity_type: "company" or "article"
        app: App identifier

    Returns:
        Rich context for AI generation
    """
    activity.logger.info(f"Getting Zep context for {entity_type}: {entity_name}")

    try:
        client = ZepClient()

        # Memory search for related content
        memory_results = await client._request(
            "POST",
            "/v2/memory/search",
            json={
                "text": entity_name,
                "limit": 10,
                "search_scope": "summary",
                "search_type": "mmr"  # Maximal Marginal Relevance
            }
        )

        memories = memory_results.get("results", [])

        # Graph search for entities
        graph_results = await client._request(
            "POST",
            "/v2/graph/search",
            json={
                "query": entity_name,
                "limit": 20,
                "scope": "nodes"
            }
        )

        nodes = graph_results.get("results", [])

        # Categorize nodes
        articles = []
        deals = []
        people = []
        companies = []

        for node in nodes:
            node_type = node.get("type", "")

            if node_type == "article":
                articles.append({
                    "title": node.get("name"),
                    "uuid": node.get("uuid"),
                    "attributes": node.get("attributes", {})
                })
            elif node_type == "deal":
                deals.append({
                    "name": node.get("name"),
                    "uuid": node.get("uuid"),
                    "attributes": node.get("attributes", {})
                })
            elif node_type == "person":
                people.append({
                    "name": node.get("name"),
                    "uuid": node.get("uuid"),
                    "attributes": node.get("attributes", {})
                })
            elif node_type == "company":
                companies.append({
                    "name": node.get("name"),
                    "uuid": node.get("uuid"),
                    "attributes": node.get("attributes", {})
                })

        activity.logger.info(
            f"Zep context retrieved: {len(memories)} memories, {len(articles)} articles, "
            f"{len(deals)} deals, {len(people)} people, {len(companies)} companies"
        )

        return {
            "memories": memories,
            "articles": articles,
            "deals": deals,
            "people": people,
            "companies": companies,
            "total_context_items": len(memories) + len(nodes)
        }

    except Exception as e:
        activity.logger.error(f"Error getting Zep context: {str(e)}")
        return {
            "memories": [],
            "articles": [],
            "deals": [],
            "people": [],
            "companies": [],
            "total_context_items": 0,
            "error": str(e)
        }


# ============================================================================
# HYBRID DEPOSIT: Store as narrative + entities + relationships
# ============================================================================

@activity.defn
async def deposit_to_zep_hybrid(
    entity_id: str,
    entity_name: str,
    entity_type: str,
    domain: Optional[str],
    payload: Dict[str, Any],
    extracted_entities: Dict[str, Any],
    app: str = "placement"
) -> Dict[str, Any]:
    """
    Deposit content to Zep in HYBRID format:

    1. NARRATIVE: Full text for semantic search
    2. ENTITIES: Structured data for graph visualization
    3. RELATIONSHIPS: Connections between entities

    This enables:
    - Semantic search across all content
    - Graph visualization of relationships
    - Context retrieval for future content

    Args:
        entity_id: Database ID of company/article
        entity_name: Name of entity
        entity_type: "company" or "article"
        domain: Domain for companies
        payload: Full payload with sections
        extracted_entities: Deals, people, companies extracted from content
        app: App identifier

    Returns:
        Deposit result with entity IDs and graph data
    """
    activity.logger.info(f"Depositing {entity_type} to Zep (hybrid): {entity_name}")

    try:
        client = ZepClient()

        # ========== 1. NARRATIVE STORAGE ==========
        # Combine all sections into full narrative
        if entity_type == "company":
            sections = payload.get("profile_sections", {})
            narrative_parts = [entity_name, "\n\n"]

            for section_key, section_data in sections.items():
                if isinstance(section_data, dict):
                    content = section_data.get("content", "")
                else:
                    content = str(section_data)

                if content:
                    narrative_parts.append(content)
                    narrative_parts.append("\n\n")

            full_narrative = "".join(narrative_parts)
        else:
            # Article
            full_narrative = f"{entity_name}\n\n{payload.get('content', '')}"

        # Add to Zep memory for semantic search
        session_id = f"{entity_type}-{entity_id}"

        await client._request(
            "POST",
            f"/v2/sessions/{session_id}/memory",
            json={
                "messages": [{
                    "role": "system",
                    "content": full_narrative,
                    "metadata": {
                        "type": f"{entity_type}_profile",
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "domain": domain,
                        "app": app
                    }
                }]
            }
        )

        activity.logger.info(f"Narrative stored: {len(full_narrative)} chars")

        # ========== 2. ENTITY STORAGE ==========
        entities_to_create = []

        # Main entity (company/article)
        main_entity = {
            "name": entity_name,
            "type": entity_type,
            "attributes": {
                "entity_id": entity_id,
                "domain": domain,
                "app": app,
                "category": payload.get("category", ""),
            }
        }
        entities_to_create.append(main_entity)

        # Extract deals
        deals = extracted_entities.get("deals", [])
        for deal in deals:
            entities_to_create.append({
                "name": deal.get("name", "Unknown Deal"),
                "type": "deal",
                "attributes": {
                    "amount": deal.get("amount"),
                    "date": deal.get("date"),
                    "parties": deal.get("parties", []),
                    "sector": deal.get("sector"),
                    "source_entity": entity_name
                }
            })

        # Extract people
        people = extracted_entities.get("people", [])
        for person in people:
            entities_to_create.append({
                "name": person.get("name", "Unknown Person"),
                "type": "person",
                "attributes": {
                    "role": person.get("role"),
                    "company": person.get("company", entity_name),
                    "source_entity": entity_name
                }
            })

        # Create all entities in graph
        entity_ids = []
        for entity in entities_to_create:
            try:
                result = await client._request(
                    "POST",
                    "/v2/graph/nodes",
                    json=entity
                )
                entity_ids.append(result.get("uuid"))
            except Exception as e:
                activity.logger.warning(f"Failed to create entity {entity['name']}: {e}")
                entity_ids.append(None)

        activity.logger.info(f"Entities created: {len([e for e in entity_ids if e])}")

        # ========== 3. RELATIONSHIP STORAGE ==========
        main_entity_id = entity_ids[0] if entity_ids else None
        relationships_created = 0

        if main_entity_id:
            # Link people to company
            people_start_idx = 1 + len(deals)
            for i, person in enumerate(people):
                person_entity_id = entity_ids[people_start_idx + i] if people_start_idx + i < len(entity_ids) else None

                if person_entity_id:
                    try:
                        await client._request(
                            "POST",
                            "/v2/graph/edges",
                            json={
                                "source_node_uuid": person_entity_id,
                                "target_node_uuid": main_entity_id,
                                "type": "works_at"
                            }
                        )
                        relationships_created += 1
                    except Exception as e:
                        activity.logger.warning(f"Failed to create relationship: {e}")

            # Link deals to company
            for i, deal in enumerate(deals):
                deal_entity_id = entity_ids[1 + i] if 1 + i < len(entity_ids) else None

                if deal_entity_id:
                    try:
                        await client._request(
                            "POST",
                            "/v2/graph/edges",
                            json={
                                "source_node_uuid": main_entity_id,
                                "target_node_uuid": deal_entity_id,
                                "type": "advised_on"
                            }
                        )
                        relationships_created += 1
                    except Exception as e:
                        activity.logger.warning(f"Failed to create relationship: {e}")

        activity.logger.info(f"Relationships created: {relationships_created}")

        # ========== 4. FETCH GRAPH DATA ==========
        graph_data = {"nodes": [], "edges": []}

        if main_entity_id:
            try:
                # Get entity with edges for visualization
                edges_response = await client._request(
                    "GET",
                    f"/v2/graph/nodes/{main_entity_id}/edges"
                )

                graph_data = {
                    "nodes": [{"id": main_entity_id, "name": entity_name, "type": entity_type}],
                    "edges": edges_response.get("edges", [])
                }

                # Add connected nodes
                for edge in graph_data["edges"]:
                    graph_data["nodes"].append({
                        "id": edge.get("target_node_uuid"),
                        "name": edge.get("target_node_name"),
                        "type": edge.get("target_node_type")
                    })

            except Exception as e:
                activity.logger.warning(f"Failed to fetch graph data: {e}")

        activity.logger.info(
            f"Zep deposit complete: narrative={len(full_narrative)} chars, "
            f"entities={len(entity_ids)}, relationships={relationships_created}"
        )

        return {
            "success": True,
            "session_id": session_id,
            "main_entity_id": main_entity_id,
            "entities_created": len([e for e in entity_ids if e]),
            "relationships_created": relationships_created,
            "narrative_length": len(full_narrative),
            "graph_data": graph_data,
            "deals_count": len(deals),
            "people_count": len(people)
        }

    except Exception as e:
        activity.logger.error(f"Error depositing to Zep: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "entities_created": 0,
            "relationships_created": 0
        }


# ============================================================================
# UTILITY: Build context prompt for AI
# ============================================================================

@activity.defn
async def build_zep_context_prompt(zep_context: Dict[str, Any]) -> str:
    """
    Build a context prompt from Zep data for AI generation.

    This formats the Zep context into a prompt that the AI
    can use to generate richer, more connected content.

    Args:
        zep_context: Context from get_zep_context_for_generation

    Returns:
        Formatted context prompt string
    """
    if not zep_context.get("exists", False) and zep_context.get("total_context_items", 0) == 0:
        return ""

    parts = ["\n\nEXISTING KNOWLEDGE FROM ZEP GRAPH:\n"]

    # Deals
    deals = zep_context.get("deals", [])
    if deals:
        parts.append(f"\nKnown Deals ({len(deals)}):\n")
        for deal in deals[:10]:  # Limit to 10
            name = deal.get("name", "Unknown")
            amount = deal.get("attributes", {}).get("amount", "undisclosed")
            date = deal.get("attributes", {}).get("date", "")
            parts.append(f"- {name}: {amount}")
            if date:
                parts.append(f" ({date})")
            parts.append("\n")

    # People
    people = zep_context.get("people", [])
    if people:
        parts.append(f"\nKnown People ({len(people)}):\n")
        for person in people[:10]:
            name = person.get("name", "Unknown")
            role = person.get("attributes", {}).get("role", "")
            parts.append(f"- {name}")
            if role:
                parts.append(f": {role}")
            parts.append("\n")

    # Related companies
    companies = zep_context.get("related_companies", []) or zep_context.get("companies", [])
    if companies:
        parts.append(f"\nRelated Companies ({len(companies)}):\n")
        for company in companies[:10]:
            name = company.get("name", "Unknown")
            parts.append(f"- {name}\n")

    # Articles
    articles = zep_context.get("articles", [])
    if articles:
        parts.append(f"\nRelated Articles ({len(articles)}):\n")
        for article in articles[:5]:
            title = article.get("title", "Unknown")
            parts.append(f"- {title}\n")

    return "".join(parts)
