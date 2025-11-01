# Model Card: Comp-Critic Valuation

**Model Name**: Comp-Critic
**Version**: 1.0.0
**Last Updated**: 2025-11-01
**Owner**: ML Engineering Team
**Status**: ⚠️ PRE-PRODUCTION (Requires backtest validation)

---

## Model Details

### Model Type
Three-stage comparable property selection and adjustment pipeline

### Components
1. **Stage 1 - Retrieval**: Spatial + temporal + structural filtering with Gaussian weighting
2. **Stage 2 - Ranking**: LambdaMART learning-to-rank model
3. **Stage 3 - Adjustment**: Quantile regression for hedonic price adjustments

### Framework & Dependencies
- **Spatial**: PostGIS (ST_DWithin, geography type)
- **Ranking**: LightGBM (LambdaMART)
- **Regression**: scikit-learn (QuantileRegressor)
- **Database**: PostgreSQL with PostGIS extension

### Model Location
- **Code**: `ml/valuation/comp_critic.py`
- **Training Pipeline**: (Not yet implemented - future work)
- **Serving**: FastAPI endpoint `/valuation/comp-critic`

---

## Intended Use

### Primary Use Case
Select and adjust comparable properties ("comps") for residential real estate valuation. Provides 3-10 high-quality comps with transparent adjustments for differences in features.

### Users
- Real estate investors evaluating acquisition opportunities
- Underwriters determining property value for loan approval
- Portfolio managers monitoring asset values

### Geographic Scope
- **Trained Markets**: (Not yet trained - requires backtest)
- **Target Markets**: All US metros with ≥100 sales in last 180 days
- **Excluded**: Rural areas with sparse sales data (<50 sales/year)

### Asset Types
- Single-family residential
- Condominiums
- Townhomes

**Out of Scope**: Multi-family, commercial, land

---

## Training Data

### Data Sources
⚠️ **Not yet trained** - Specifications only

**Planned Sources**:
- Public MLS listings (RETS/RESO feeds)
- County recorder sales data
- Property attribute databases (e.g., CoreLogic, ATTOM)

### Data Window
**Planned**:
- Training: Jan 2020 - Dec 2023 (4 years)
- Validation: Jan 2024 - Jun 2024 (6 months)
- Test: Jul 2024 - Present (out-of-time holdout)

### Sample Size
**Estimated Requirements**:
- Minimum: 10,000 sales per market
- Target: 50,000+ sales per market for major metros
- Total: 2-5 million sales across all markets

### Geographic Coverage
**Planned Coverage**:
- Tier 1: Top 20 metros (NYC, LA, SF, etc.)
- Tier 2: Next 50 metros
- Tier 3: Additional 100 markets with sufficient data

### Feature Set

**Subject Property Features**:
- Location: Latitude, longitude, zip code
- Physical: sqft, lot size, bedrooms, bathrooms, year built
- Quality: Condition score, renovation status
- Structural: Stories, garage, basement, pool

**Comp Features (for ranking)**:
- `distance_m`: Haversine distance to subject
- `recency_days`: Days since comp sale
- `size_delta_pct`: Absolute % difference in sqft
- `vintage_delta`: Absolute year difference
- `renovation_match`: Binary (both renovated or both not)
- `structural_similarity`: Composite score

**Adjustment Features** (for hedonic model):
- `delta_sqft`: Comp sqft - subject sqft
- `delta_condition`: Condition score difference
- `delta_lot_size`: Lot size difference
- `delta_age`: Age difference
- Indicator variables for categorical features

---

## Performance

### Metrics

**Stage 1 - Retrieval** (⚠️ Not yet measured):
- Recall@50: Target ≥95% (at least one truly comparable property in top 50)

**Stage 2 - Ranking** (⚠️ Not yet measured):
- NDCG@5: Target ≥0.85 (top 5 comps are highly relevant)
- NDCG@10: Target ≥0.90
- Comparison: Should exceed simple recency-based ranking by ≥10% NDCG

**Stage 3 - Adjustment** (⚠️ Not yet measured):
- MAE (Mean Absolute Error): Target <5% of property value
- Baseline Comparison: Should beat simple average by ≥20% MAE reduction

### Performance by Market Segment

⚠️ **Requires backtest** - Expected performance ranges:

| Market Tier | NDCG@5 Target | MAE Target | Data Availability |
|-------------|---------------|------------|-------------------|
| Tier 1 (Top 20) | ≥0.90 | <3% | Excellent |
| Tier 2 (Next 50) | ≥0.85 | <5% | Good |
| Tier 3 (Others) | ≥0.80 | <7% | Moderate |

| Price Range | NDCG@5 Target | Notes |
|-------------|---------------|-------|
| <$200K | ≥0.80 | More inventory, higher variance |
| $200K-$500K | ≥0.88 | Sweet spot with best data |
| $500K-$1M | ≥0.85 | Good comparables available |
| >$1M | ≥0.75 | Sparse data, unique features |

---

## Uncertainty & Confidence

### Confidence Intervals
Each comp receives an adjustment confidence score based on:
- Number of comps available (more = higher confidence)
- Variance in adjusted prices (lower variance = higher confidence)
- Distance from subject (closer = higher confidence)

**Formula**:
```python
confidence = (
    0.4 * (1 - distance / max_distance) +  # Proximity weight
    0.3 * (1 - cv_adjusted_prices) +        # Consistency weight
    0.3 * min(1, n_comps / 10)              # Sample size weight
)
```

### Uncertainty Sources
1. **Data Quality**: Missing attributes, incorrect sqft, outdated condition
2. **Market Conditions**: Rapid appreciation/depreciation not captured
3. **Uniqueness**: High-end or unusual properties with few comparables
4. **Timing**: Recent sales may not reflect current market
5. **Structural Differences**: Difficult to quantify features (view, location micro-factors)

### Known Failure Modes
- **Sparse Markets**: Rural areas with <5 sales in 180 days → Return empty or low-confidence
- **Luxury Segment**: >$5M properties often unique → Adjustments unreliable
- **Distressed Sales**: Foreclosures/short sales may contaminate comps → Filter needed
- **New Construction**: Lack of historical comps → Fallback to cost approach
- **Rapid Appreciation**: 20%+ YoY growth → Temporal weighting insufficient

---

## Limitations & Caveats

### Technical Limitations
1. **Spatial Dependency**: Requires PostGIS with geography support and GiST indexes
2. **Computational Cost**: Spatial queries can be slow without proper indexing
3. **Ranking Model Size**: LambdaMART model requires ~50MB memory per market if separately trained
4. **Hedonic Assumption**: Assumes linear/quantile-linear relationship between feature deltas and price deltas

### Bias Considerations
1. **Historical Bias**: Training on past sales may perpetuate historical discrimination in pricing
2. **Geographic Bias**: Better performance in data-rich urban markets vs rural
3. **Price Tier Bias**: Mid-range properties overrepresented in training data
4. **Temporal Bias**: Recent boom/bust cycles may not generalize to future

### Data Limitations
1. **MLS Coverage**: Not all sales reported to MLS (FSBOs, off-market)
2. **Attribute Accuracy**: Sqft, bedrooms often user-reported, not verified
3. **Condition Subjectivity**: "Excellent" condition not standardized across markets
4. **Renovation Recency**: "Renovated" doesn't capture when or quality

### Ethical Considerations
1. **Redlining Risk**: Must ensure similar properties receive similar valuations regardless of neighborhood demographics
2. **Fair Housing**: Cannot use protected class proxies (zip code alone is risky)
3. **Transparency**: Users must understand adjustments, not treat as black box
4. **Appeal Mechanism**: Property owners should be able to contest automated valuations

---

## Monitoring

### Metrics to Track

**Real-Time (Per Request)**:
- `comp_selection_latency_ms`: Time to retrieve and rank comps
- `comp_count_returned`: Number of comps found
- `avg_confidence_score`: Average confidence across returned comps

**Daily Aggregates**:
- `avg_ndcg_degradation`: NDCG vs baseline (detect model drift)
- `pct_low_comp_count`: % of requests returning <5 comps
- `pct_low_confidence`: % of results with confidence <0.7

**Weekly Backtests**:
- Re-evaluate last week's valuations against actual sales
- MAE of adjusted comp prices vs actual sale prices
- Segment-level performance degradation

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Latency p95 | >400ms | >800ms | Investigate query plan, check indexes |
| Low comp count | >10% | >25% | Expand radius, relax filters |
| Low confidence | >15% | >30% | Review feature quality, add more comps |
| MAE degradation | >20% vs baseline | >50% vs baseline | Retrain model |
| NDCG drop | -0.05 | -0.10 | Investigate ranking model drift |

### Drift Detection

**Feature Drift**:
- Monitor distribution of input features (sqft, price, age)
- Use Evidently AI to detect statistical drift (PSI, KL divergence)
- Alert if >30% of features show drift

**Prediction Drift**:
- Compare valuation distribution over time
- Detect sudden shifts in median/variance
- Cross-check with market indices (Case-Shiller)

**Market Regime Changes**:
- Integrate with Regime Monitoring system
- Hot market → comps may underprice (recent appreciation)
- Cold market → comps may overprice (recent decline)

---

## Deployment

### Canary Plan

**Phase 1: Shadow Mode (2 weeks)**
- Run Comp-Critic alongside legacy comp selection
- Log both results, compare
- No user-facing impact
- Success: <10% latency increase, NDCG ≥0.80

**Phase 2: Canary (10% traffic, 1 week)**
- Serve Comp-Critic to 10% of requests
- Monitor error rates, latency, user feedback
- A/B test: Compare offer acceptance rates
- Success: No stat sig difference in acceptance, latency OK

**Phase 3: Ramp Up (1 week)**
- 10% → 50% → 100%
- Pause at 50% for 3 days to verify
- Automated rollback if error rate >2% or latency >500ms

**Phase 4: Full Deployment**
- 100% traffic to Comp-Critic
- Legacy system on standby for rollback

### Rollback Triggers

**Automatic Rollback**:
- Error rate >5% for 5 minutes
- p95 latency >800ms for 10 minutes
- >30% of requests returning <3 comps
- Confidence score <0.5 for >40% of requests

**Manual Rollback**:
- User complaints about comp quality
- Regulatory concerns raised
- Model unexpectedly biased in certain markets

### Feature Flags

**Flag**: `comp_critic.enabled`
- **Type**: Boolean
- **Default**: False (legacy system)
- **Rollout**: Gradual percentage-based
- **Override**: Can disable per market if issues detected

**Flag**: `comp_critic.min_confidence`
- **Type**: Float (0-1)
- **Default**: 0.6
- **Purpose**: Fallback to legacy if confidence below threshold

### Version Control

- **Model Artifacts**: Store in S3/GCS with version tags
- **Training Code**: Git SHA linked to model version
- **Training Data**: Snapshot ID for reproducibility
- **A/B Tests**: Record which model version in request logs

---

## Future Improvements

### Short-term (Next 3 months)
1. **Backtest on Historical Data**: Validate NDCG and MAE targets
2. **Training Pipeline**: Automated retraining monthly
3. **Expand Markets**: Train on top 50 metros
4. **Explainability**: Waterfall chart showing adjustment breakdown

### Medium-term (6-12 months)
1. **Deep Learning Ranker**: Replace LambdaMART with neural ranker
2. **Multimodal Features**: Include property images in similarity
3. **Market-Specific Models**: Separate models per market tier
4. **Temporal Weighting**: More sophisticated recency decay

### Long-term (12+ months)
1. **Real-Time Learning**: Update model with new sales immediately
2. **Counterfactual Comps**: "If this property had a pool, comps would be..."
3. **Confidence Calibration**: Ensure 80% confidence = 80% accuracy
4. **Interactive Refinement**: Let users adjust comp selection criteria

---

## References

- Implementation: `ml/valuation/comp_critic.py`
- API Documentation: `/docs` endpoint (FastAPI auto-docs)
- Research: "Learning to Rank" by Li (2011)
- Hedonic Pricing: Rosen (1974), "Hedonic Prices and Implicit Markets"

---

## Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-11-01 | Initial model card creation | Platform Engineering |

---

## Approval Status

- [ ] **Model Owner**: Reviewed and approved
- [ ] **Data Science Lead**: Validated methodology
- [ ] **Legal/Compliance**: Fair housing review completed
- [ ] **Security**: Privacy review completed
- [ ] **Product**: Use case alignment confirmed

**Status**: ⚠️ DRAFT - Pending backtest validation and approvals
