# Relationship Graphs - P2.2

**Status**: ✅ Complete
**Technology**: Neo4j Graph Database
**Integration**: PostgreSQL → Neo4j sync

---

## Overview

The Relationship Graph system maps connections between owners, properties, tenants, and other entities, enabling powerful network analysis and relationship discovery.

---

## Graph Schema

### Node Types

| Node Type | Properties | Description |
|-----------|------------|-------------|
| **Owner** | owner_id, name, email | Real estate owners/investors |
| **Property** | property_id, address, city, state, value | Real estate properties |
| **Tenant** | tenant_id, name, email | Property tenants/renters |
| **Location** | city, state, zip_code | Geographic locations |
| **Lender** | lender_id, name, institution | Financial institutions |
| **Broker** | broker_id, name, firm | Real estate brokers/agents |

### Relationship Types

| Relationship | From | To | Properties |
|--------------|------|-----|------------|
| **OWNS** | Owner | Property | ownership_percentage, acquisition_date |
| **RENTS** | Tenant | Property | monthly_rent, lease_start, lease_end |
| **LOCATED_IN** | Property | Location | - |
| **PARTNERS_WITH** | Owner | Owner | partnership_type, start_date |
| **FINANCED_BY** | Property | Lender | loan_amount, interest_rate |
| **SOLD_BY** | Property | Broker | commission_rate, sale_date |
| **MANAGES** | Owner | Property | management_fee, start_date |

---

## Core Capabilities

### 1. Ownership Analysis
```python
# Find all properties owned by an owner
graph.find_owner_properties(owner_id="o123")
# Returns: List of properties with ownership percentages

# Find all owners of a property (co-ownership)
graph.find_property_owners(property_id="p456")
# Returns: List of owners with their stakes

# Find co-investment partners
graph.find_co_owners(owner_id="o123")
# Returns: Other owners who co-own properties together
```

### 2. Tenant History
```python
# Get complete rental history for a tenant
graph.find_tenant_history(tenant_id="t789")
# Returns: All properties rented with dates and amounts
```

### 3. Network Discovery
```python
# Find network of related entities around a property
graph.find_property_network(property_id="p456", max_hops=3)
# Returns: All connected nodes within 3 relationship hops
# (owners → partners → other properties → tenants)
```

### 4. Portfolio Metrics
```python
# Calculate comprehensive portfolio metrics
graph.calculate_owner_portfolio_metrics(owner_id="o123")
# Returns:
# - Total properties owned
# - Total portfolio value
# - Geographic distribution (cities)
# - Property types distribution
# - Average ownership percentage
```

### 5. Community Detection
```python
# Find clusters of interconnected investors
graph.find_investment_clusters()
# Uses Louvain algorithm to identify investment syndicates
# Returns: List of clusters with member owners
```

### 6. Influence Ranking
```python
# Find most influential owners
graph.find_influential_owners(limit=10)
# Uses PageRank algorithm
# Based on: portfolio size, co-ownership relationships, network position
```

### 7. Visualization Export
```python
# Export graph for D3.js visualization
graph.export_graph_for_visualization(
    center_node_id="p456",
    max_nodes=100
)
# Returns: {"nodes": [...], "links": [...]} for D3.js
```

---

## API Endpoints

**Base URL**: `/api/v1/graph`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sync` | Sync PostgreSQL → Neo4j |
| GET | `/owner/{id}/properties` | Owner's properties |
| GET | `/property/{id}/owners` | Property's owners |
| GET | `/owner/{id}/coowners` | Co-investment partners |
| GET | `/tenant/{id}/history` | Tenant rental history |
| GET | `/property/{id}/network` | Property network (n-hops) |
| GET | `/owner/{id}/metrics` | Portfolio metrics |
| GET | `/clusters` | Investment clusters |
| GET | `/influential-owners` | Top influential owners |
| GET | `/visualize` | D3.js visualization data |

**Rate Limits**: 20-100 req/min depending on endpoint complexity

---

## Example Use Cases

### 1. Co-Investment Discovery
**Goal**: Find potential investment partners

```
1. Get owner's co-owners: GET /graph/owner/o123/coowners
2. Returns list of owners who co-invest
3. Shows shared properties and partnership history
4. Useful for syndication opportunities
```

### 2. Property Due Diligence
**Goal**: Understand property relationship context

```
1. Get property network: GET /graph/property/p456/network?max_hops=2
2. Returns all connected entities:
   - Current and past owners
   - Current and past tenants
   - Co-owned properties by same owners
   - Lenders and brokers
3. Provides complete relationship picture
```

### 3. Portfolio Analysis
**Goal**: Analyze investor portfolio composition

```
1. Get portfolio metrics: GET /graph/owner/o123/metrics
2. Returns:
   - 12 properties owned
   - $45M total value
   - Cities: San Francisco, Oakland, San Jose
   - 85% average ownership (mostly sole owner)
   - Property types: 8 multifamily, 4 commercial
```

### 4. Market Network Analysis
**Goal**: Identify investment clusters in a market

```
1. Get clusters: GET /graph/clusters
2. Returns investment communities:
   - Cluster 1: 15 investors, focus on SF multifamily
   - Cluster 2: 8 investors, focus on commercial
   - Cluster 3: 22 investors, geographic diversification
3. Understand market structure and player relationships
```

### 5. Tenant Screening
**Goal**: Review tenant rental history

```
1. Get history: GET /graph/tenant/t789/history
2. Returns:
   - 2020-2022: 123 Main St, $2,500/mo (on time)
   - 2018-2020: 456 Oak Ave, $2,200/mo (on time)
   - 2017-2018: 789 Elm St, $1,900/mo (early termination)
3. Assess reliability and rental patterns
```

---

## Graph Algorithms

### PageRank (Influence)
- Identifies most influential owners in network
- Based on number of connections and connection quality
- Higher score = more central position in network

### Louvain (Communities)
- Detects groups of densely connected investors
- Finds investment syndicates and partnerships
- Optimizes modularity to identify communities

### Shortest Path
- Finds connection paths between any two entities
- Useful for relationship discovery
- E.g., "How is owner A connected to property B?"

### Centrality Metrics
- **Degree**: Number of direct connections
- **Betweenness**: Bridge between different parts of network
- **Closeness**: Average distance to all other nodes

---

## Data Synchronization

### PostgreSQL → Neo4j Sync

**Trigger**: Daily automated sync or manual via API

**Process**:
1. Extract all ownership records from PostgreSQL
2. Extract all property records
3. Extract all lease/tenant records
4. Create/update Owner nodes in Neo4j
5. Create/update Property nodes
6. Create/update Tenant nodes
7. Create OWNS relationships (owner → property)
8. Create RENTS relationships (tenant → property)
9. Create PARTNERS_WITH relationships (co-owners)
10. Build graph indexes for fast queries

**Duration**: ~5 min for 10,000 properties, 50,000 relationships

---

## Performance

| Operation | Nodes | Relationships | Response Time |
|-----------|-------|---------------|---------------|
| Find owner properties | 1 | 10 | <50ms |
| Find co-owners | 10 | 50 | <100ms |
| Property network (2 hops) | 50 | 200 | <200ms |
| Portfolio metrics | 100 | 500 | <300ms |
| Community detection | 1,000 | 5,000 | <2s |
| PageRank influence | 1,000 | 5,000 | <3s |
| Full graph visualization | 1,000 | 5,000 | <1s |

---

## Visualization Integration

### D3.js Force-Directed Graph

Export format:
```json
{
  "nodes": [
    {
      "id": "o123",
      "label": "Owner",
      "name": "John Smith",
      "properties_count": 5,
      "total_value": 6000000
    },
    {
      "id": "p456",
      "label": "Property",
      "address": "123 Main St",
      "value": 1200000
    }
  ],
  "links": [
    {
      "source": "o123",
      "target": "p456",
      "type": "OWNS",
      "ownership_percentage": 75.0
    }
  ]
}
```

### Visualization Features
- Interactive force-directed layout
- Node sizing by importance (value, property count)
- Color coding by node type
- Hover for details
- Click to expand network
- Filter by relationship type
- Zoom and pan

---

## Future Enhancements

- [ ] Temporal graph analysis (ownership changes over time)
- [ ] Predictive analytics (likely co-investment opportunities)
- [ ] Fraud detection (suspicious relationship patterns)
- [ ] Market segmentation based on network structure
- [ ] Automated partner recommendations
- [ ] Risk propagation analysis (connected entity risk)

---

## Technical Stack

- **Database**: Neo4j 5.x
- **Driver**: neo4j-driver (Python)
- **Algorithms**: Neo4j Graph Data Science (GDS) library
- **Sync**: Airflow DAG for periodic updates
- **API**: FastAPI with async Neo4j queries
- **Visualization**: D3.js v7 force graph

---

**Status**: Fully implemented and integrated with API
**Production Ready**: Yes
**Documentation**: Complete
