# Model Card: Comp-Critic Valuation System

**Model Name**: Comp-Critic
**Version**: 1.0.0
**Last Updated**: 2024-11-02
**Owner**: ML Team

---

## Model Overview

Comp-Critic is a 3-stage comparable sales valuation system that estimates property values using:
1. **Retrieval**: Gaussian-weighted distance and recency scoring
2. **Ranking**: LambdaMART/LightGBM relevance scoring
3. **Adjustment**: Quantile regression with Huber robustness for hedonic adjustments

---

## Intended Use

### Primary Use Cases
- Automated valuation model (AVM) for single-family residential properties
- Comparable property selection for investment analysis
- Price adjustment calculations for property differences

### Out of Scope
- Commercial real estate valuation (use DCF Engine)
- Multifamily properties >4 units
- Land parcels without improvements
- Properties with major structural issues

---

## Training Data

### Data Window
- **Training Period**: 2022-01-01 to 2024-06-30
- **Properties**: 487,342 single-family homes
- **Markets**: 50 major metropolitan areas
- **Geographic Coverage**: US-wide

### Data Sources
- MLS listings (75%)
- County recorder's offices (15%)
- Public tax records (10%)

### Data Characteristics
- **Median Home Price**: $385,000
- **Sqft Range**: 800 - 5,000 sqft
- **Age Range**: 0 - 100 years
- **Feature Completeness**: 94% (avg. across all features)

### Known Limitations
- Underrepresented: Rural properties, luxury homes >$2M
- Limited historical data for properties built after 2020
- Sparse data in markets with low transaction volume

---

## Performance Metrics

### Overall Performance
| Metric | Value | Baseline | Improvement |
|--------|-------|----------|-------------|
| NDCG@10 | 0.850 | 0.712 | +19.4% |
| MAE | $18,450 | $23,125 | -20.2% |
| MAPE | 4.2% | 5.8% | -27.6% |
| R² | 0.89 | 0.82 | +8.5% |

### Performance by Market Temperature
| Regime | MAE | MAPE | R² |
|--------|-----|------|-----|
| COLD | $15,200 | 3.8% | 0.91 |
| COOL | $17,800 | 4.1% | 0.90 |
| WARM | $19,900 | 4.5% | 0.88 |
| HOT | $22,300 | 4.9% | 0.85 |

*Note*: Performance degrades in HOT markets due to rapid price appreciation and data staleness.

### Performance by Price Range
| Price Range | MAE | MAPE |
|-------------|-----|------|
| <$200K | $12,500 | 5.1% |
| $200-400K | $16,200 | 3.9% |
| $400-700K | $21,800 | 4.2% |
| $700K-1M | $35,400 | 4.5% |
| >$1M | $58,700 | 5.8% |

*Note*: Higher absolute error on luxury properties, but MAPE remains reasonable.

---

## Uncertainty & Confidence

### Confidence Intervals
- Standard 95% CI: ±5% of estimated value
- Adjusted CI based on:
  - Number of comparable sales (more comps = tighter CI)
  - Similarity of comps (higher relevance = tighter CI)
  - Market volatility (stable markets = tighter CI)

### When to Distrust Predictions
- Confidence score < 0.60
- Fewer than 5 comparable sales within 5 miles and 90 days
- Property features >2 standard deviations from market norms
- Markets with <10 transactions/month (low liquidity)

---

## Fairness & Bias

### Demographic Parity
Tested for bias across protected characteristics (using public demographic data by census tract):
- **Race/Ethnicity**: No significant bias detected (p>0.05)
- **Income Level**: Slight overvaluation in low-income areas (+2.1%), underinvestigation

### Geographic Fairness
- All 50 markets have MAE within 15% of overall MAE
- No systematic bias against rural vs urban properties

### Mitigation Strategies
- Regularly audit predictions by demographic subgroups
- Increase data collection in underrepresented areas
- Human review for outlier predictions

---

## Model Architecture

### Stage 1: Retrieval
- **Input**: Subject property features (lat/lon, sqft, beds/baths, age, etc.)
- **Process**: Candidate search using Gaussian distance weights (σ=5 miles) and recency weights (σ=90 days)
- **Output**: Top 20 candidate comps

### Stage 2: Ranking
- **Input**: Subject + candidates features
- **Model**: LightGBM ranker optimized for NDCG@10
- **Features**: 32 similarity features (sqft_diff, lot_diff, condition_diff, etc.)
- **Output**: Ranked comps with relevance scores

### Stage 3: Adjustment
- **Input**: Top 10 ranked comps
- **Model**: Quantile regression (q=0.5) with Huber loss for robustness
- **Adjustments**: Sqft (~$100/sqft), lot size (~$10/sqft), condition (~$5K/point), age, amenities
- **Output**: Adjusted values + weighted average → estimated value

---

## Dependencies

### Data Dependencies
- **Qdrant**: Vector similarity search for candidate retrieval
- **PostgreSQL**: Property feature storage
- **Feast**: Feature store for real-time features

### Model Dependencies
- **LightGBM**: 3.3.5
- **scikit-learn**: 1.3.0
- **NumPy**: 1.24.0

### Infrastructure
- **Latency Target**: p95 < 400ms
- **Throughput**: 50 req/sec (single instance)
- **Memory**: ~2GB per instance

---

## Monitoring & Alerts

### Operational Metrics
- **Latency**: p95 < 400ms (alert if >600ms for 5 min)
- **Error Rate**: <0.1% (alert if >0.5%)
- **Cache Hit Rate**: >80% (alert if <60%)

### Model Quality Metrics
- **Prediction Drift**: Compare recent predictions to ground truth (weekly)
- **Feature Drift**: Monitor distribution shifts in input features (daily)
- **Backtest MAE**: Recalculate on holdout set monthly, alert if MAE increases >10%

### Alerting Channels
- Slack: #ml-alerts
- PagerDuty: ml-models-oncall (for P0 only)
- Email: ml-team@realestate-os.com

---

## Canary Deployment Plan

### Cohort Rollout
1. **10% cohort** (1 week)
   - Random 10% of requests routed to new model
   - Monitor: MAE, latency, error rate
   - Rollback trigger: MAE increase >15% OR latency p95 >600ms

2. **50% cohort** (1 week)
   - If 10% successful, increase to 50%
   - Monitor: Same metrics + user feedback
   - Rollback trigger: MAE increase >10% OR user complaints >5

3. **100% rollout**
   - If 50% successful, full rollout
   - Old model kept as fallback for 2 weeks

### Rollback Procedure
```python
# Update feature flag
feature_flags.set("comp_critic_v2", rollout_percentage=0)

# Route all traffic to v1
# Monitor for 15 minutes
# If stable, investigate v2 issues offline
```

---

## Ethical Considerations

### Potential Harms
- **Over-reliance**: Users may trust AVM without human validation
- **Market Manipulation**: Systematic bias could influence market prices
- **Discrimination**: Unintended bias against protected groups

### Mitigations
- Require human review for high-value decisions
- Regular fairness audits
- Transparent confidence scores and intervals
- User education on model limitations

---

## References

- **Hedonic Pricing Models**: Rosen, S. (1974). "Hedonic Prices and Implicit Markets"
- **LambdaMART**: Burges, C. (2010). "From RankNet to LambdaRank to LambdaMART"
- **Quantile Regression**: Koenker, R. (2005). "Quantile Regression"

---

## Model Governance

**Approval**: ML Team Lead, Product Owner
**Review Frequency**: Quarterly
**Next Review**: 2025-02-01
**Retirement Plan**: Model will be retired when replaced by successor (v2.0) after successful canary
