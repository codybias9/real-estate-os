# Vector Database Service

Qdrant integration for vector similarity search. Smoke test implementation for future semantic search capabilities.

## Features

- **Property Similarity**: Find similar properties based on characteristics
- **Semantic Search**: Search memos and documents by meaning
- **Recommendations**: Property recommendation system
- **Vector Storage**: Store and retrieve high-dimensional embeddings

## Installation

```bash
cd services/vector
pip install -e ".[dev]"
```

## Quick Start

### 1. Start Qdrant

```bash
# Docker
docker run -p 6333:6333 qdrant/qdrant

# Or use Qdrant Cloud
export QDRANT_URL="https://your-cluster.qdrant.io"
export QDRANT_API_KEY="your-api-key"
```

### 2. Basic Usage

```python
from vector import VectorClient, create_dummy_embedding

# Create client
client = VectorClient(collection_name="properties", vector_size=384)

# Create collection
client.create_collection(distance="Cosine")

# Insert property with embedding
embedding = create_dummy_embedding(384)  # In production, use real embeddings
client.upsert_property(
    property_id="prop-123",
    embedding=embedding,
    metadata={
        "street": "123 Main St",
        "city": "Los Angeles",
        "beds": 3,
        "baths": 2.0,
    }
)

# Search for similar properties
query_embedding = create_dummy_embedding(384)
results = client.search_similar(query_embedding, limit=10)

for result in results:
    print(f"Property {result['property_id']}: score={result['score']}")
    print(f"Metadata: {result['metadata']}")
```

## Use Cases

### Property Similarity Search

```python
# Find properties similar to a given property
property = get_property("prop-123")
property_embedding = generate_embedding(property)

similar_properties = client.search_similar(
    query_vector=property_embedding,
    limit=10,
    score_threshold=0.8  # Only return highly similar (>0.8)
)
```

### Semantic Memo Search

```python
# Search memos by semantic meaning
query = "properties with renovation potential in downtown"
query_embedding = generate_text_embedding(query)

relevant_memos = client.search_similar(
    query_vector=query_embedding,
    limit=5
)
```

### Property Recommendations

```python
# Recommend properties based on user preferences
user_preferences = {
    "preferred_areas": ["Downtown", "Midtown"],
    "beds": 3,
    "style": "Modern"
}

preference_embedding = generate_preference_embedding(user_preferences)
recommendations = client.search_similar(
    query_vector=preference_embedding,
    limit=20
)
```

## Embedding Models

For production use, integrate a real embedding model:

### Option 1: Sentence Transformers (Local)

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dim

def generate_property_embedding(property):
    text = f"{property['street']} {property['city']} {property['beds']}bed {property['baths']}bath"
    embedding = model.encode(text)
    return embedding.tolist()
```

### Option 2: OpenAI Embeddings (Cloud)

```python
import openai

def generate_property_embedding(property):
    text = f"{property['street']} {property['city']} {property['beds']}bed {property['baths']}bath"
    response = openai.Embedding.create(
        model="text-embedding-ada-002",  # 1536 dim
        input=text
    )
    return response['data'][0]['embedding']
```

### Option 3: Cohere Embeddings (Cloud)

```python
import cohere

co = cohere.Client('your-api-key')

def generate_property_embedding(property):
    text = f"{property['street']} {property['city']}"
    response = co.embed(
        texts=[text],
        model='embed-english-v3.0'
    )
    return response.embeddings[0]
```

## Testing

```bash
# Run smoke tests (requires Qdrant running)
pytest tests/test_vector_smoke.py -v

# Tests will skip if Qdrant not available
```

## Architecture

### Vector Storage

```
Property → Text → Embedding Model → Vector (384-dim) → Qdrant
```

### Similarity Search

```
Query → Embedding Model → Query Vector → Qdrant Search → Results
```

### Distance Metrics

- **Cosine**: Best for normalized vectors (default)
- **Euclidean**: L2 distance
- **Dot Product**: For pre-normalized vectors

## Performance

- **Insert**: ~1ms per vector
- **Search**: ~10ms for 1M vectors (HNSW index)
- **Memory**: ~4KB per 384-dim vector
- **Scalability**: Millions of vectors per collection

## Configuration

```python
# Local Qdrant
client = VectorClient(
    url="http://localhost:6333",
    collection_name="properties",
    vector_size=384
)

# Qdrant Cloud
client = VectorClient(
    url="https://your-cluster.qdrant.io",
    api_key="your-api-key",
    collection_name="properties",
    vector_size=1536  # For OpenAI ada-002
)
```

## Best Practices

1. **Normalize Vectors**: Use cosine distance with normalized vectors
2. **Batch Operations**: Upsert in batches for better performance
3. **Index Tuning**: Adjust HNSW parameters for speed vs accuracy
4. **Metadata Filtering**: Use filters to narrow search space
5. **Monitor Performance**: Track search latency and accuracy

## Limitations

- **Dummy Embeddings**: Current implementation uses random vectors
- **No Embedding Model**: Integrate sentence-transformers or OpenAI
- **Basic Operations**: No batch operations or advanced filtering
- **No Persistence**: Collections deleted after tests

## Future Enhancements

1. **Embedding Integration**: Add sentence-transformers support
2. **Batch Operations**: Bulk upsert/delete
3. **Hybrid Search**: Combine vector and metadata filters
4. **Quantization**: Reduce memory with quantized vectors
5. **Multi-tenancy**: Tenant-specific collections

## License

MIT License - Real Estate OS
