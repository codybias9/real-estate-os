# Real Estate OS - Machine Learning Module

**Wave 2.1** - Portfolio Twin: User preference learning with contrastive learning

## Overview

The ML module implements the **Portfolio Twin** - a neural network that learns each user's unique investment criteria by observing their behavior:

- Properties viewed
- Deals created
- Outreach sent
- Explicit feedback (thumbs up/down)

The model creates a user-specific embedding space where similar properties cluster together, enabling:
- **Property affinity prediction**: "How well does this property match the user's preferences?"
- **Smart recommendations**: "What are the top 10 properties for this user?"
- **Look-alikes**: "Find properties similar to this one"

## Architecture

### Model Components

```
┌─────────────────────────────────────────────────────┐
│                  Portfolio Twin                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐         ┌──────────────┐         │
│  │   Property   │         │     User     │         │
│  │   Encoder    │         │  Embeddings  │         │
│  │  (NN layers) │         │   (learned)  │         │
│  └──────────────┘         └──────────────┘         │
│         │                         │                 │
│         └────────┬────────────────┘                 │
│                  │                                   │
│         Cosine Similarity                           │
│                  │                                   │
│          Affinity Score [0, 1]                      │
└─────────────────────────────────────────────────────┘
```

**Property Encoder**: Neural network (25 → 128 → 64 → 32 → 16)
- Input: 25-dim property features (price, beds, location, etc.)
- Output: 16-dim embedding
- Architecture: 4 layers with BatchNorm, ReLU, Dropout

**User Embeddings**: Learned 16-dim vector per user
- Initialized randomly (small std=0.01)
- Optimized during training
- Represents user's "ideal property" in embedding space

**Loss Function**: Contrastive loss (InfoNCE)
- Pulls user embedding close to liked properties
- Pushes away from disliked properties
- Temperature-scaled for better gradients

### Training Pipeline

```
User Interactions → Data Loader → Training → Evaluation → Deployment
                                      ↓
                              Contrastive Loss
                                      ↓
                           Update Embeddings
```

1. **Data Loading** (`ml/training/data_loader.py`)
   - Load user interactions from database
   - Create positive samples (deals, likes)
   - Sample negatives (non-interacted properties)
   - Balance batches (50% positive, 50% negative)

2. **Training** (`ml/training/train_portfolio_twin.py`)
   - Initialize model architecture
   - Train with Adam optimizer (lr=0.001)
   - Validate every epoch
   - Save checkpoints every 10 epochs
   - Track metrics (accuracy, precision, recall, F1)

3. **Evaluation** (`ml/utils/evaluation.py`)
   - Classification metrics (accuracy, F1, AUC)
   - Ranking metrics (Precision@K, NDCG@K)
   - Embedding visualization (t-SNE)
   - User embedding statistics

4. **Deployment** (`dags/portfolio_twin_training.py`)
   - Airflow DAG for automated retraining
   - Quality gates (F1 > 0.6, Accuracy > 0.7)
   - Model versioning and metadata
   - Production deployment

## Project Structure

```
ml/
├── models/                      # Model definitions
│   ├── __init__.py
│   └── portfolio_twin.py        # ⭐ Neural network architecture
│
├── training/                    # Training pipeline
│   ├── __init__.py
│   ├── data_loader.py          # Dataset and DataLoader
│   └── train_portfolio_twin.py # Training script
│
├── serving/                     # Model serving
│   ├── __init__.py
│   ├── portfolio_twin_service.py # ⭐ FastAPI service
│   └── models/                  # Deployed models
│       ├── portfolio_twin.pt    # Latest model
│       └── portfolio_twin_metadata.json
│
├── utils/                       # Utilities
│   ├── __init__.py
│   └── evaluation.py           # Metrics and visualization
│
├── embeddings/                  # Embedding management (Wave 2.2)
│   └── __init__.py
│
├── checkpoints/                 # Training checkpoints
│   ├── portfolio_twin_best.pt
│   ├── portfolio_twin_latest.pt
│   ├── training_history.json
│   └── training_curves.png
│
└── README.md                    # This file
```

## Usage

### Training the Model

#### CLI Training

```bash
python ml/training/train_portfolio_twin.py \
  --tenant-id 00000000-0000-0000-0000-000000000001 \
  --epochs 100 \
  --batch-size 32 \
  --learning-rate 0.001 \
  --device cpu \
  --output-dir ml/checkpoints
```

**Parameters**:
- `--tenant-id`: Tenant ID for RLS context (required)
- `--epochs`: Number of training epochs (default: 100)
- `--batch-size`: Batch size (default: 32)
- `--learning-rate`: Learning rate (default: 0.001)
- `--device`: Device (cpu, cuda, mps) (default: cpu)
- `--output-dir`: Directory for checkpoints (default: ml/checkpoints)
- `--lookback-days`: Interaction lookback period (default: 90)
- `--val-split`: Validation split ratio (default: 0.2)

#### Airflow DAG Training

```bash
# Trigger DAG manually
airflow dags trigger portfolio_twin_training \
  --conf '{
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "db_url": "postgresql://user:pass@localhost/realestate",
    "epochs": 100,
    "batch_size": 32,
    "learning_rate": 0.001
  }'
```

**DAG Tasks**:
1. `check_data_threshold` - Verify sufficient interaction data
2. `prepare_training_data` - Create negative samples
3. `train_model` - Train Portfolio Twin model
4. `evaluate_model` - Check quality gates
5. `deploy_model` - Deploy to serving directory

**Schedule**: Weekly (Sunday 2 AM)

### Serving Predictions

#### Start Service

```bash
# Start FastAPI service
python ml/serving/portfolio_twin_service.py

# Or with uvicorn
uvicorn ml.serving.portfolio_twin_service:app --host 0.0.0.0 --port 8001
```

Service runs on `http://localhost:8001`

#### API Endpoints

**1. Predict Affinity**

```bash
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "property_features": {
      "listing_price": 500000,
      "bedrooms": 3,
      "bathrooms": 2.0,
      "square_footage": 2000,
      "lat": 37.7749,
      "lon": -122.4194,
      "property_type": "Single Family"
    }
  }'
```

Response:
```json
{
  "user_id": 1,
  "affinity_score": 0.87,
  "confidence": 0.92
}
```

**2. Get Recommendations**

```bash
curl -X POST http://localhost:8001/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "candidate_property_ids": ["prop-1", "prop-2", "prop-3"],
    "top_k": 10
  }'
```

**3. Get Embedding**

```bash
curl -X POST http://localhost:8001/embedding \
  -H "Content-Type: application/json" \
  -d '{
    "property_features": { ... }
  }'
```

**4. Batch Predict**

```bash
curl -X POST http://localhost:8001/batch_predict \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "properties": [
      {"listing_price": 500000, "bedrooms": 3, ...},
      {"listing_price": 600000, "bedrooms": 4, ...}
    ]
  }'
```

### Python API

```python
from ml.models.portfolio_twin import (
    PortfolioTwinEncoder,
    PortfolioTwin,
    PropertyFeatures
)
from ml.serving.portfolio_twin_service import PortfolioTwinService

# Load model
service = PortfolioTwinService("ml/serving/models/portfolio_twin.pt")

# Create property features
prop_features = PropertyFeatures(
    listing_price=500000,
    bedrooms=3,
    bathrooms=2.0,
    square_footage=2000,
    lat=37.7749,
    lon=-122.4194,
    property_type="Single Family",
    # ... other fields
)

# Predict affinity
score, confidence = service.predict_affinity(
    user_id=1,
    property_features=prop_features
)

print(f"Affinity score: {score:.2f} (confidence: {confidence:.2f})")
```

## Model Features

### Input Features (25 dimensions)

#### Financial (5)
- `listing_price`: Property price (scaled /1M)
- `price_per_sqft`: Price per square foot (scaled /500)
- `estimated_value`: Estimated market value (scaled /1M)
- `cap_rate`: Capitalization rate (optional)
- `cash_on_cash_return`: Cash-on-cash return (optional)

#### Physical (5)
- `bedrooms`: Number of bedrooms (scaled /10)
- `bathrooms`: Number of bathrooms (scaled /10)
- `square_footage`: Interior square footage (scaled /10K)
- `lot_size_sqft`: Lot size (scaled /50K)
- `year_built`: Year built (age scaled /100)

#### Location (3)
- `lat`: Latitude (scaled /90)
- `lon`: Longitude (scaled /180)
- `zipcode`: Zip code (one-hot encoded, not in vector)

#### Market (2)
- `days_on_market`: Days listed (scaled /365)
- `listing_status`: Active/Pending/Sold/Off Market (one-hot, 4-dim)

#### Condition (2)
- `condition_score`: Condition rating [0-1]
- `renovation_needed`: Boolean (0 or 1)

#### Metadata (3)
- `property_type`: Single Family/Condo/Townhouse/Multi-Family/Land (one-hot, 5-dim)
- `source_system`: Data source
- `confidence`: Overall data confidence [0-1]

**Total**: 16 numerical + 9 categorical (one-hot) = **25 features**

### Output

- **Affinity Score**: Float [0, 1]
  - 0.0 = User would not like this property
  - 1.0 = Perfect match for user's criteria
  - Threshold: Typically 0.5 for binary decision

- **Embedding**: 16-dimensional vector
  - Normalized (L2 norm = 1)
  - Used for similarity search
  - Can be indexed in Qdrant (Wave 2.2)

## Training Details

### Data Requirements

**Minimum**:
- 100+ user interactions (deals)
- 50+ unique properties
- 2+ users with interactions

**Recommended**:
- 1,000+ interactions
- 500+ properties
- 10+ users

**Negative Sampling**:
- Create negatives from properties without interactions
- Balance positive/negative ratio in batches
- Sample 1,000 negatives by default

### Hyperparameters

**Model Architecture**:
- Input dim: 25
- Hidden layers: [128, 64, 32]
- Embedding dim: 16
- Dropout: 0.2
- Batch norm: Yes

**Training**:
- Optimizer: Adam
- Learning rate: 0.001
- Batch size: 32
- Epochs: 100
- Loss: Contrastive (InfoNCE)
- Temperature: 0.07
- Device: CPU (GPU supported)

**Validation**:
- Split: 20% users held out
- Metrics: Accuracy, Precision, Recall, F1, AUC
- Early stopping: Not implemented (save best model)

### Quality Gates

Models must meet these criteria before deployment:

- **F1 Score** ≥ 0.6
- **Accuracy** ≥ 0.7
- **No NaN embeddings**
- **Training converged** (loss decreased)

## Monitoring

### Training Metrics

**Logged every epoch**:
- Training loss
- Validation accuracy
- Validation precision/recall/F1
- Validation AUC

**Saved artifacts**:
- `training_history.json` - Full metric history
- `training_curves.png` - Loss/accuracy plots
- `portfolio_twin_best.pt` - Best model by F1
- `portfolio_twin_latest.pt` - Latest checkpoint

### Production Metrics

**TODO (Wave 2.3)**:
- Prediction latency (p50, p95, p99)
- Throughput (requests/sec)
- Model accuracy on recent data
- User feedback correlation
- Embedding drift detection

## Evaluation

### Classification Metrics

```python
from ml.utils.evaluation import evaluate_model

metrics = evaluate_model(model, val_loader, device='cpu')

print(f"Accuracy: {metrics['accuracy']:.4f}")
print(f"Precision: {metrics['precision']:.4f}")
print(f"Recall: {metrics['recall']:.4f}")
print(f"F1: {metrics['f1']:.4f}")
print(f"AUC: {metrics['auc']:.4f}")
```

### Ranking Metrics

```python
print(f"Precision@5: {metrics['precision@5']:.4f}")
print(f"Recall@10: {metrics['recall@10']:.4f}")
print(f"NDCG@20: {metrics['ndcg@20']:.4f}")
```

### Visualization

```python
from ml.utils.evaluation import (
    plot_training_curves,
    plot_confusion_matrix,
    plot_roc_curve,
    analyze_embeddings
)

# Training curves
plot_training_curves(history, "curves.png")

# Confusion matrix
plot_confusion_matrix(predictions, labels, "confusion.png")

# ROC curve
plot_roc_curve(scores, labels, "roc.png")

# Embedding space (t-SNE)
analyze_embeddings(model, properties, property_ids, "embeddings.png")
```

## Troubleshooting

### Training Issues

**Problem**: Loss not decreasing

**Solution**:
- Check data quality (sufficient positives/negatives)
- Reduce learning rate (try 0.0001)
- Increase batch size
- Check for NaN in data

**Problem**: Overfitting (high train accuracy, low val accuracy)

**Solution**:
- Increase dropout (0.3 or 0.4)
- Add L2 regularization
- Reduce model capacity
- Get more training data

**Problem**: "Not enough deals" error

**Solution**:
- Create more sample data in database
- Reduce `lookback_days` parameter
- Lower threshold in `check_data_threshold()`

### Serving Issues

**Problem**: Model not found

**Solution**:
```bash
# Check model exists
ls ml/serving/models/portfolio_twin.pt

# Train and deploy
python ml/training/train_portfolio_twin.py --tenant-id <uuid>
cp ml/checkpoints/portfolio_twin_best.pt ml/serving/models/portfolio_twin.pt
```

**Problem**: Slow predictions

**Solution**:
- Use GPU for inference (`--device cuda`)
- Batch predictions with `/batch_predict`
- Enable model quantization (TODO)
- Cache frequent property embeddings

## Next Steps

### Wave 2.2: Qdrant Integration
- Index property embeddings in Qdrant
- Fast similarity search
- Incremental updates

### Wave 2.3: Advanced Features
- Multi-task learning (price prediction + affinity)
- Attention mechanism for feature importance
- Temporal dynamics (user preferences change over time)
- Cold-start handling (new users)

### Wave 2.4: UI Integration
- Add "Match Score" to property cards
- "Similar Properties" section
- "Why this match?" explanations
- User feedback loop (thumbs up/down)

## References

- **Contrastive Learning**: [SimCLR paper](https://arxiv.org/abs/2002.05709)
- **InfoNCE Loss**: [CPC paper](https://arxiv.org/abs/1807.03748)
- **Recommender Systems**: [Neural Collaborative Filtering](https://arxiv.org/abs/1708.05031)

## License

Proprietary - Real Estate OS

---

**Wave 2.1 Complete** - Portfolio Twin training and serving infrastructure ✅
