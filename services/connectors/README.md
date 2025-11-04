# Data Connectors Service

External data connectors for Real Estate OS with automatic fallback, cost tracking, and budget management.

## Features

- **Multiple Providers**: ATTOM, Regrid, OpenAddresses
- **Automatic Fallback**: Try providers in order until success
- **Cost Tracking**: Track API costs per request and per tenant
- **Budget Management**: Policy Kernel integration for spending limits
- **Health Monitoring**: Health checks for all connectors
- **Retry Logic**: Automatic retries with exponential backoff
- **Rate Limiting**: Handle rate limits gracefully

## Connectors

### ATTOM ($0.08/call)
- Premium property data provider
- Ownership, valuation, characteristics, transaction history
- API: https://api.developer.attomdata.com

### Regrid ($0.02/call)
- Parcel boundaries and property data
- Nationwide coverage with GeoJSON boundaries
- API: https://regrid.com/api

### OpenAddresses (Free)
- Basic address geocoding via Nominatim
- Limited data, no APN support
- Best as fallback option

## Installation

```bash
cd services/connectors
pip install -e ".[dev]"
```

## Configuration

```bash
# ATTOM
export ATTOM_API_KEY="your-attom-api-key"

# Regrid
export REGRID_API_KEY="your-regrid-api-key"

# OpenAddresses (no key required)
```

## Usage

### Basic Usage

```python
from connectors import get_connector_manager, ConnectorStrategy

# Create manager with balanced strategy
manager = get_connector_manager(strategy=ConnectorStrategy.BALANCED)

# Get property data (automatic fallback)
response = await manager.get_property_data(
    apn="123-456-789",
    state="CA",
    county="Los Angeles"
)

if response.success:
    print(f"Property: {response.data.street}, {response.data.city}")
    print(f"Beds: {response.data.beds}, Baths: {response.data.baths}")
    print(f"Cost: ${response.cost}")
else:
    print(f"Error: {response.error}")
```

### Connector Strategies

```python
# Cost-optimized: Cheapest first (OpenAddresses → Regrid → ATTOM)
manager = ConnectorManager(strategy=ConnectorStrategy.COST_OPTIMIZED)

# Quality-optimized: Best data first (ATTOM → Regrid → OpenAddresses)
manager = ConnectorManager(strategy=ConnectorStrategy.QUALITY_OPTIMIZED)

# Balanced: Balance cost and quality (Regrid → ATTOM → OpenAddresses)
manager = ConnectorManager(strategy=ConnectorStrategy.BALANCED)
```

### Direct Connector Usage

```python
from connectors import get_attom_connector, get_regrid_connector

# Use specific connector directly
attom = get_attom_connector(api_key="your-key")
response = await attom.get_property_data(apn="123", state="CA")

regrid = get_regrid_connector(api_key="your-key")
response = await regrid.get_property_data(apn="123", state="CA")
```

### Budget Management

```python
from connectors import PolicyKernelIntegration

# Set up budget tracking
policy = PolicyKernelIntegration(
    tenant_id="tenant-123",
    monthly_budget=100.0  # $100/month
)

# Check before making request
if policy.can_make_request(estimated_cost=0.08):
    response = await manager.get_property_data(...)
    policy.record_cost(response.cost)

# Get usage stats
stats = policy.get_usage_stats()
print(f"Spent: ${stats['spent_this_month']}")
print(f"Remaining: ${stats['remaining']}")
print(f"Usage: {stats['usage_percentage']}%")
```

### Health Checks

```python
# Check all connectors
health = await manager.health_check_all()
print(health)  # {'attom': True, 'regrid': True, 'openaddresses': True}

# Check specific connector
healthy = await attom.health_check()
```

### Statistics

```python
# Get manager statistics
stats = manager.get_stats()
print(stats)
# {
#   'strategy': 'balanced',
#   'total_cost': 2.50,
#   'successful_requests': 30,
#   'failed_requests': 2,
#   'success_rate': 0.94,
#   'connectors': {...}
# }

# Get connector-specific stats
attom_stats = attom.get_stats()
# {
#   'connector': 'attom',
#   'status': 'available',
#   'request_count': 15,
#   'total_cost': 1.20
# }
```

## API Integration

```python
from fastapi import APIRouter, Depends
from connectors import get_connector_manager

router = APIRouter()

@router.get("/properties/{apn}")
async def get_property(apn: str, state: str):
    """Get property data via connectors"""
    manager = get_connector_manager()

    response = await manager.get_property_data(
        apn=apn,
        state=state
    )

    if response.success:
        return {
            "success": True,
            "data": response.data.dict(),
            "connector": response.connector.value,
            "cost": response.cost,
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=response.error
        )
```

## Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

**Test Results**: 36 tests passing, 81% coverage

## Architecture

### Connector Flow

```
Request → ConnectorManager
           ├─> Try Primary Connector (e.g., Regrid)
           │   └─> Success? Return
           ├─> Try Secondary Connector (e.g., ATTOM)
           │   └─> Success? Return
           └─> Try Fallback Connector (e.g., OpenAddresses)
               └─> Success? Return : Error
```

### Data Model

All connectors return standardized `PropertyData`:

```python
{
  "street": "123 Main St",
  "city": "Los Angeles",
  "state": "CA",
  "zip": "90001",
  "county": "Los Angeles",
  "lat": 34.0522,
  "lng": -118.2437,
  "beds": 3,
  "baths": 2.0,
  "sqft": 1500,
  "lot_sqft": 5000,
  "year_built": 1950,
  "owner_name": "John Doe",
  "assessed_value": 500000,
  "market_value": 550000,
  "zoning": "R1",
  "land_use": "Residential",
  "raw_data": {...}  # Original API response
}
```

## Cost Comparison

| Provider | Cost/Request | Data Quality | Coverage | Best For |
|----------|-------------|--------------|----------|----------|
| ATTOM | $0.08 | Excellent | US-wide | Complete property data |
| Regrid | $0.02 | Good | US-wide | Parcel boundaries, cost-effective |
| OpenAddresses | Free | Basic | Global | Fallback, geocoding only |

## Performance

- **Typical Response Time**: 500-2000ms (network dependent)
- **Retry Logic**: 3 attempts with exponential backoff (2s, 4s, 8s)
- **Rate Limiting**: Automatic handling with status tracking
- **Caching**: Integrate with cache service for optimal performance

## Best Practices

1. **Use Manager**: Always use ConnectorManager for automatic fallback
2. **Set Budgets**: Configure per-tenant budgets via Policy Kernel
3. **Monitor Health**: Regularly check connector health
4. **Cache Results**: Cache property data to minimize API costs
5. **Handle Errors**: Always check `response.success` before using data

## Troubleshooting

### No Data Returned

- **Check API Keys**: Ensure environment variables are set
- **Check Budget**: Verify tenant hasn't exceeded budget
- **Check Health**: Run health checks to verify connector status

### High Costs

- **Enable Caching**: Cache property lookups (10-30 min TTL)
- **Use Cost-Optimized Strategy**: Try cheaper connectors first
- **Set Budget Limits**: Configure Policy Kernel limits

### Rate Limiting

- **Reduce Request Rate**: Add delays between requests
- **Check Limits**: ATTOM (60/min), Regrid (120/min), Nominatim (60/min)
- **Monitor Status**: Connectors automatically track rate limit status

## License

MIT License - Real Estate OS
