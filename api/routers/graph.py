"""
Relationship Graph Analytics API.

Provides access to:
- Owner-property relationships
- Tenant rental history
- Co-ownership networks
- Investment clusters
- Influential owner rankings
- Graph visualizations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
import logging

from api.auth import get_current_user, TokenData
from api.rate_limit import rate_limit
from graph_analytics.relationship_graph import RelationshipGraph, sync_postgresql_to_neo4j

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/graph",
    tags=["graph"]
)


class OwnerNode(BaseModel):
    """Owner node model."""
    id: str
    owner_id: str
    name: str
    email: Optional[str]
    properties_count: Optional[int] = 0
    total_portfolio_value: Optional[float] = 0


class PropertyNode(BaseModel):
    """Property node model."""
    id: str
    property_id: str
    address: str
    city: str
    state: str
    value: Optional[float]


class RelationshipModel(BaseModel):
    """Relationship model."""
    from_id: str
    to_id: str
    type: str
    properties: dict = Field(default_factory=dict)


class NetworkResponse(BaseModel):
    """Network graph response."""
    center_id: str
    nodes: List[dict]
    relationships: List[dict]
    node_count: int
    relationship_count: int


class PortfolioMetrics(BaseModel):
    """Owner portfolio metrics."""
    owner_id: str
    total_properties: int
    total_value: float
    cities: List[str]
    avg_ownership_percentage: float
    property_types: Optional[dict] = None


@router.post("/sync", status_code=202)
@rate_limit(requests_per_minute=5)  # Once per hour
async def sync_graph(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Sync PostgreSQL data to Neo4j graph database.

    This operation:
    1. Extracts all ownership, property, and lease data
    2. Creates/updates nodes in Neo4j
    3. Creates/updates relationships
    4. Builds indexes for fast querying

    Requires admin role. Should be run daily or after bulk imports.
    """
    if current_user.role not in ['admin']:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions. Admin role required."
        )

    logger.info(f"Graph sync requested for tenant {current_user.tenant_id}")

    try:
        result = sync_postgresql_to_neo4j(current_user.tenant_id)

        return {
            "message": "Graph sync queued",
            "tenant_id": current_user.tenant_id,
            "status": "processing",
            "result": result
        }

    except Exception as e:
        logger.error(f"Graph sync failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Graph sync failed"
        )


@router.get("/owner/{owner_id}/properties", response_model=List[dict])
@rate_limit(requests_per_minute=100)
async def get_owner_properties(
    owner_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get all properties owned by an owner.

    Returns properties with ownership percentages.
    """
    logger.info(f"Get properties for owner {owner_id}")

    graph = RelationshipGraph()
    properties = graph.find_owner_properties(owner_id)

    return properties


@router.get("/property/{property_id}/owners", response_model=List[dict])
@rate_limit(requests_per_minute=100)
async def get_property_owners(
    property_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get all owners of a property.

    Returns owners with ownership percentages.
    """
    logger.info(f"Get owners for property {property_id}")

    graph = RelationshipGraph()
    owners = graph.find_property_owners(property_id)

    return owners


@router.get("/owner/{owner_id}/coowners", response_model=List[dict])
@rate_limit(requests_per_minute=100)
async def get_coowners(
    owner_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Find co-owners who own properties together with this owner.

    Returns co-owners and shared properties.
    Useful for identifying investment partnerships.
    """
    logger.info(f"Get co-owners for {owner_id}")

    graph = RelationshipGraph()
    coowners = graph.find_co_owners(owner_id)

    return coowners


@router.get("/tenant/{tenant_id}/history", response_model=List[dict])
@rate_limit(requests_per_minute=100)
async def get_tenant_history(
    tenant_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get rental history for a tenant.

    Returns all properties tenant has rented with dates and amounts.
    """
    logger.info(f"Get rental history for tenant {tenant_id}")

    graph = RelationshipGraph()
    history = graph.find_tenant_history(tenant_id)

    return history


@router.get("/property/{property_id}/network", response_model=NetworkResponse)
@rate_limit(requests_per_minute=50)
async def get_property_network(
    property_id: str,
    max_hops: int = Query(2, ge=1, le=5),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get network of related entities around a property.

    Traverses relationships up to max_hops away.
    Returns all connected owners, tenants, locations, etc.

    Useful for understanding property context and relationships.
    """
    logger.info(f"Get network for property {property_id}, hops={max_hops}")

    graph = RelationshipGraph()
    network = graph.find_property_network(property_id, max_hops=max_hops)

    return NetworkResponse(
        center_id=property_id,
        nodes=network.get("nodes", []),
        relationships=network.get("relationships", []),
        node_count=len(network.get("nodes", [])),
        relationship_count=len(network.get("relationships", []))
    )


@router.get("/owner/{owner_id}/metrics", response_model=PortfolioMetrics)
@rate_limit(requests_per_minute=100)
async def get_owner_metrics(
    owner_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Calculate portfolio metrics for an owner.

    Metrics include:
    - Total properties owned
    - Total portfolio value
    - Geographic distribution
    - Property types
    - Average ownership percentage
    """
    logger.info(f"Get metrics for owner {owner_id}")

    graph = RelationshipGraph()
    metrics = graph.calculate_owner_portfolio_metrics(owner_id)

    return PortfolioMetrics(**metrics)


@router.get("/clusters", response_model=List[dict])
@rate_limit(requests_per_minute=20)
async def get_investment_clusters(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Find clusters of interconnected investors.

    Uses community detection algorithms to identify groups of
    investors who frequently co-invest or are otherwise connected.

    Useful for:
    - Identifying investment syndicates
    - Finding potential partners
    - Understanding market networks
    """
    logger.info("Find investment clusters")

    graph = RelationshipGraph()
    clusters = graph.find_investment_clusters()

    return clusters


@router.get("/influential-owners", response_model=List[dict])
@rate_limit(requests_per_minute=20)
async def get_influential_owners(
    limit: int = Query(10, ge=1, le=50),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Find most influential owners using network centrality metrics.

    Influence is calculated based on:
    - Number of properties
    - Co-ownership relationships
    - Portfolio value
    - Network position

    Uses PageRank algorithm.
    """
    logger.info(f"Get top {limit} influential owners")

    graph = RelationshipGraph()
    influential = graph.find_influential_owners(limit=limit)

    return influential


@router.get("/visualize", response_model=dict)
@rate_limit(requests_per_minute=20)
async def get_graph_visualization(
    center_node_id: Optional[str] = None,
    max_nodes: int = Query(100, ge=10, le=500),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Export graph data for visualization.

    Returns data in D3.js-compatible format with nodes and links.

    If center_node_id provided, returns ego network around that node.
    Otherwise returns most connected subgraph.

    Response format:
    {
      "nodes": [{"id": "...", "label": "...", ...}],
      "links": [{"source": "...", "target": "...", "type": "..."}]
    }
    """
    logger.info("Export graph for visualization")

    graph = RelationshipGraph()
    viz_data = graph.export_graph_for_visualization(
        center_node_id=center_node_id,
        max_nodes=max_nodes
    )

    return viz_data
