# libpostal Address Normalization Service

## Overview

This service provides address parsing and normalization using the [libpostal](https://github.com/openvenues/libpostal) library. libpostal is a C library for parsing/normalizing street addresses around the world using statistical NLP and open data.

## Features

- **Address Parsing**: Breaks down addresses into components (house number, street, city, state, postal code, etc.)
- **Address Expansion**: Generates normalized variations of an address
- **International Support**: Handles addresses from 249+ countries and territories
- **High Accuracy**: Trained on OpenStreetMap, OpenAddresses, and other open datasets

## Deployment

### Using Docker Compose

```bash
# Start the libpostal service
cd infra/address-normalization
docker-compose -f docker-compose-libpostal.yml up -d

# Check service health
curl http://localhost:8181/health

# Stop the service
docker-compose -f docker-compose-libpostal.yml down
```

### Configuration

- **Port**: 8181 (mapped to container port 8080)
- **Memory**: 2-4GB (libpostal models are large)
- **CPU**: 1-2 cores
- **Data Volume**: libpostal-data (persistent storage for models)

## API Usage

### Parse Address

Breaks an address into labeled components.

```bash
curl -X POST http://localhost:8181/parser \
  -H "Content-Type: application/json" \
  -d '{"query": "123 Main St, Austin, TX 78701"}'
```

Response:
```json
[
  {"label": "house_number", "value": "123"},
  {"label": "road", "value": "main st"},
  {"label": "city", "value": "austin"},
  {"label": "state", "value": "tx"},
  {"label": "postcode", "value": "78701"}
]
```

### Expand Address

Generates normalized variations of an address for fuzzy matching.

```bash
curl -X POST http://localhost:8181/expand \
  -H "Content-Type: application/json" \
  -d '{"query": "123 Main Street"}'
```

Response:
```json
[
  "123 main street",
  "123 main st",
  "123 main str"
]
```

## Python Integration

See `address_normalization/libpostal_client.py` for Python client library.

```python
from address_normalization.libpostal_client import LibpostalClient

client = LibpostalClient(base_url="http://localhost:8181")

# Parse address
result = client.parse_address("123 Main St, Austin, TX 78701")
# Returns: {"house_number": "123", "road": "main st", ...}

# Expand address for fuzzy matching
variations = client.expand_address("123 Main Street")
# Returns: ["123 main street", "123 main st", ...]
```

## Performance

- **Parsing Latency**: 10-30ms per address
- **Throughput**: 100-300 requests/second (single instance)
- **Accuracy**: 95%+ on US addresses, 90%+ globally

## Troubleshooting

### Service won't start

Check memory allocation. libpostal requires at least 2GB RAM:
```bash
docker stats real-estate-os-libpostal
```

### Data directory issues

If models fail to load, clear the volume and restart:
```bash
docker-compose -f docker-compose-libpostal.yml down -v
docker-compose -f docker-compose-libpostal.yml up -d
```

### Health check failing

Wait 60 seconds for initial model loading:
```bash
docker-compose -f docker-compose-libpostal.yml logs -f libpostal
```

## References

- [libpostal GitHub](https://github.com/openvenues/libpostal)
- [libpostal REST API Docker Image](https://github.com/openvenues/libpostal-rest-docker)
- [Address Parser Documentation](https://github.com/openvenues/libpostal#parser-api)
