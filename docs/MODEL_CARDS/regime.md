# Model Card: Market Regime Monitoring

**Model Name**: Regime Detector
**Version**: 1.0.0
**Last Updated**: 2025-11-01
**Owner**: Data Science / Market Intelligence Team
**Status**: ⚠️ PRE-PRODUCTION (Requires DAG execution and validation)

---

## Model Details

### Model Type
Composite index with rule-based classification and Bayesian change-point detection

### Components
1. **Composite Index Calculator**: 4-component scoring system (0-100 scale)
2. **Regime Classifier**: Threshold-based with hysteresis
3. **BOCPD (Bayesian Online Change-Point Detection)**: Adams & MacKay (2007) algorithm
4. **Policy Engine**: Regime-specific acquisition policy recommendations

### Framework & Dependencies
- **Scoring**: NumPy for composite calculations
- **Change-Point**: SciPy (stats, logsumexp)
- **Orchestration**: Airflow DAG for daily market monitoring
- **Storage**: Postgres for regime history

### Model Location
- **Code**:
  - `ml/regime/market_regime_detector.py` (600+ LOC)
  - `ml/regime/changepoint_detection.py` (400+ LOC)
- **DAG**: `dags/regime/regime_monitoring_dag.py`
- **API**: `/regime/detect`, `/regime/policy/{regime}`

---

## Intended Use

### Primary Use Cases
- **Market Monitoring**: Daily classification of top 100 markets
- **Policy Adjustment**: Automatically adjust acquisition parameters by regime
- **Alerting**: Notify team of regime changes (especially transitions to HOT or COLD)
- **Strategic Planning**: Identify optimal markets for expansion/contraction

### Users
- Acquisitions team for market selection
- Portfolio managers for risk assessment
- Executive leadership for strategic planning
- Data science team for market research

### Geographic Scope
- **Coverage**: All US markets (ZIP code level)
- **Minimum Data**: ≥10 properties with activity in last 180 days
- **Optimal Data**: ≥50 properties for stable estimates
- **Excluded**: Rural ZIP codes with <10 properties

---

## Model Inputs

### Market Signals Required

**Inventory Metrics**:
- `active_listings`: Current active + pending listings
- `months_of_inventory`: Active listings / avg monthly sales
- `new_listings_mom`: Month-over-month change in new listings

**Price Metrics**:
- `median_list_price`: Median asking price
- `median_sale_price`: Median closed price
- `list_to_sale_ratio`: Sale price / list price (e.g., 1.02 = 2% over list)
- `price_yoy_change`: Year-over-year price change (%)

**Velocity Metrics**:
- `avg_days_on_market`: Average time to sale/contract
- `dom_yoy_change`: YoY change in DOM (positive = slower)
- `sell_through_rate`: Sales / (Sales + Expireds)

**Financial Metrics**:
- `avg_cap_rate`: Average cap rate for income properties
- `avg_price_per_sf`: Average $/SF
- `mortgage_rate`: Current 30-year fixed rate

**Volume Metrics**:
- `sales_volume_mom`: Month-over-month sales volume change

### Data Sources
- Property database (MLS feeds, internal data)
- County recorder (sales transactions)
- External: Mortgage rate APIs (e.g., Freddie Mac)

---

## Model Outputs

### Regime Classification

**4 Regime Categories**:
1. **HOT** (index ≥75): Seller's market, fierce competition
2. **WARM** (50-75): Balanced market, moderate competition
3. **COOL** (25-50): Buyer's market, more negotiating power
4. **COLD** (<25): Distressed market, abundant inventory

### Composite Index Components

Each component scored 0-100 (higher = hotter):

**1. Inventory Tightness (25% weight)**:
- <2 months supply → 100 (very hot)
- 6 months → 50 (balanced)
- >24 months → 0 (cold)

**2. Price Strength (25% weight)**:
- List-to-sale ≥1.00 → 75-100 (bidding wars)
- Price YoY >10% → 100
- Price YoY <-10% → 0

**3. Market Velocity (25% weight)**:
- DOM <14 days → 100
- DOM 60 days → 50 (balanced)
- Sell-through >90% → 100

**4. Financial Metrics (25% weight)**:
- Cap rate <4% → 100 (high competition)
- Cap rate 6% → 50 (balanced)
- Mortgage rate <3% → 100 (low rates)

### Change-Point Detection

**BOCPD Outputs**:
- `run_length_distribution`: Probability distribution over time since last changepoint
- `changepoint_probability`: P(changepoint at current time)
- `is_change_point`: Boolean flag (probability >0.5)
- `segment_statistics`: Mean/std of index within each segment

### Policy Recommendations

**Per Regime**:
| Regime | Max Offer % | DD Days | Target Margin | Followup Freq |
|--------|-------------|---------|---------------|---------------|
| HOT | 85% ARV | 7 | 12% | 2 days |
| WARM | 80% ARV | 14 | 15% | 3 days |
| COOL | 75% ARV | 21 | 18% | 5 days |
| COLD | 65% ARV | 30 | 22% | 7 days |

---

## Calculations & Formulas

### Composite Index

```python
composite_index = (
    0.25 * inventory_score(months_of_inventory) +
    0.25 * price_score(list_to_sale_ratio, price_yoy_change) +
    0.25 * velocity_score(avg_dom, sell_through_rate) +
    0.25 * financial_score(avg_cap_rate, mortgage_rate)
)
```

### Inventory Score Example

```python
def score_inventory(months_of_inventory):
    if months < 2:
        return 100
    elif months < 3:
        return 75 + 25 * (3 - months)
    elif months < 6:
        return 50 + 25 * (6 - months) / 3
    elif months < 12:
        return 25 + 25 * (12 - months) / 6
    elif months < 24:
        return 25 * (24 - months) / 12
    else:
        return 0
```

### Regime Classification with Hysteresis

```python
# Base thresholds
HOT = 75, WARM = 50, COOL = 25

# Apply ±5 point hysteresis based on previous regime
if previous_regime == HOT:
    hot_threshold = 70  # Easier to stay hot
else:
    hot_threshold = 75  # Harder to become hot

# Prevents rapid flip-flopping between regimes
```

### BOCPD Algorithm

**Update Step**:
```python
# Predictive probability (Student's t distribution)
pred_log_probs = student_t_log_prob(observation, alpha, beta, kappa, mu)

# Growth probabilities (no changepoint)
growth_log_probs = run_length_log_probs + pred_log_probs + log(1 - hazard)

# Changepoint probability
cp_log_prob = logsumexp(run_length_log_probs + pred_log_probs + log(hazard))

# Combine and normalize
new_run_length_log_probs = concatenate([cp_log_prob, growth_log_probs])
new_run_length_log_probs -= logsumexp(new_run_length_log_probs)

# Update sufficient statistics (Gaussian-Gamma posterior)
```

---

## Performance

### Classification Accuracy

⚠️ **Requires validation** - Expected performance:

**Precision/Recall by Regime**:
| Regime | Precision Target | Recall Target | Notes |
|--------|------------------|---------------|-------|
| HOT | ≥0.85 | ≥0.80 | High stakes, prefer precision |
| WARM | ≥0.75 | ≥0.75 | Most common |
| COOL | ≥0.75 | ≥0.75 | Balanced |
| COLD | ≥0.85 | ≥0.70 | Rare, critical to detect |

**Change-Point Detection**:
- **Precision**: ≥0.70 (70% of flagged changepoints are real)
- **Recall**: ≥0.60 (detect 60% of true changepoints)
- **Latency**: Detect within 30 days of actual change

### Hysteresis Effectiveness

**Goal**: Prevent flip-flopping between regimes

**Metric**: Regime stability duration
- Target: ≥90% of regimes last ≥30 days
- Alert: If >10% of regimes flip-flop (change back within 14 days)

### Market Coverage

**Daily Monitoring**:
- Top 100 markets by activity
- Target: Complete processing in <5 minutes
- Alert if any market fails to process

---

## Uncertainty & Confidence

### Sources of Uncertainty

**Data Quality**:
- MLS feeds incomplete or delayed
- County recorder lag (sales reported weeks later)
- Self-reported attributes (sqft, condition)

**Market Heterogeneity**:
- ZIP code may contain diverse neighborhoods
- Luxury vs entry-level have different dynamics
- New construction vs resale

**External Shocks**:
- Sudden interest rate changes
- Economic events (recession, pandemic)
- Local events (factory closing, tech company arrival)

### Confidence Scoring

**Composite Index Confidence**:
```python
confidence = (
    0.4 * data_completeness +  # % of expected signals present
    0.3 * sample_size_weight +  # More sales = higher confidence
    0.3 * consistency_weight    # Low variance across components
)
```

**Low Confidence Warnings**:
- <30 sales in last 90 days → Show ⚠️
- Missing >20% of signals → Flag data issue
- High variance across components → "Mixed signals"

---

## Limitations & Caveats

### Model Limitations

**Rule-Based Thresholds**:
- Thresholds (e.g., 6 months = balanced) not market-specific
- Phoenix in summer ≠ Detroit in winter
- Should eventually train market-specific thresholds

**Equal Weighting**:
- All 4 components weighted 25%
- Some markets more inventory-driven, others price-driven
- Future: Learn optimal weights per market

**Lagging Indicators**:
- Sales data lags by weeks
- By time regime detected, may have shifted
- Leading indicators (pending sales) could improve

**BOCPD Assumptions**:
- Assumes Gaussian-Gamma prior (may not fit data)
- Constant hazard function (real changepoints non-uniform)
- Doesn't model seasonality (spring/fall cycles)

### Known Failure Modes

**Sparse Markets**:
- <20 sales in 90 days → Noisy estimates
- Solution: Aggregate to larger geography (county)

**Seasonal Fluctuations**:
- Spring: Higher inventory, faster sales
- Winter: Lower inventory, slower sales
- Risk: Classify as regime change when it's seasonality
- Solution: Year-over-year comparisons help

**Outlier Sales**:
- One $10M sale in $500K market → Skews median
- Solution: Use robust statistics (median, not mean)

**New Development**:
- Large subdivision opening → Inventory spike
- Looks like market cooling, but it's supply increase
- Solution: Flag markets with >20% new construction

**Distressed Events**:
- Foreclosure wave → Price collapse
- Model may be slow to detect COLD regime
- Solution: Add foreclosure rate signal

---

## Monitoring

### Real-Time Metrics

**Per Market Per Day**:
- `composite_index`: 0-100 score
- `regime`: HOT/WARM/COOL/COLD
- `regime_confidence`: 0-1
- `changepoint_probability`: 0-1
- `data_completeness`: % of signals present

### Aggregated Metrics (Daily)

- `markets_monitored`: Count of markets processed
- `markets_hot`: Count in HOT regime
- `markets_cold`: Count in COLD regime
- `regime_changes_detected`: Count of transitions
- `avg_composite_index`: National average
- `processing_time_seconds`: DAG runtime

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Markets hot | >30% | >50% |
| Markets cold | >10% | >20% |
| Regime changes | >20/day | >50/day |
| Processing time | >300s | >600s |
| Data completeness | <80% | <60% |

### Drift Detection

**Input Drift**:
- Monitor distribution of raw signals over time
- Alert if median list price shifts >20% in 30 days
- Alert if months of inventory shifts >50%

**Output Drift**:
- Track regime distribution over time
- Historical baseline: 20% HOT, 50% WARM, 25% COOL, 5% COLD
- Alert if deviates >10 percentage points

**Market Regime Stability**:
- Track average regime duration
- Alert if median duration <30 days (too much flipping)

---

## Deployment

### Canary Plan

**Phase 1: Shadow Mode (2 weeks)**
- Run regime detection, don't change policies
- Compare with manual market assessments
- Success: ≥80% agreement with acquisitions team

**Phase 2: Pilot Markets (1 month)**
- Apply policies in 10 test markets
- Monitor offer acceptance rates, deal flow
- Success: No statistical difference in outcomes

**Phase 3: Rollout (1 month)**
- 10% markets → 50% → 100%
- Pause at each stage for review
- Success: Improved acquisition efficiency

**Phase 4: Full Automation**
- Daily regime detection with auto-policy updates
- Manual override capability maintained

### Rollback Triggers

**Automatic**:
- DAG failure rate >10%
- Processing time >10 minutes
- >50% of markets with low confidence

**Manual**:
- Acquisitions team disputes classifications
- Systematic policy errors (too aggressive/conservative)
- Regulatory concerns

### Feature Flags

**Flag**: `regime_monitoring.enabled`
- Default: False
- Gradual rollout per market

**Flag**: `regime_monitoring.auto_policy_update`
- Default: False (manual review required)
- Enable after validation period

**Flag**: `regime_monitoring.alert_on_change`
- Default: True
- Send Slack alerts on regime transitions

---

## Future Improvements

### Short-term (3 months)
1. **DAG Execution**: Deploy and validate daily runs
2. **Market-Specific Thresholds**: Tune thresholds per market tier
3. **Backtest**: Validate changepoint detection on historical data
4. **Seasonality Adjustment**: Deseasonalize signals before scoring

### Medium-term (6 months)
1. **Learned Weights**: Optimize component weights per market
2. **Leading Indicators**: Add pending sales, mortgage applications
3. **Granular Scoring**: Neighborhood-level within large markets
4. **Regime Prediction**: Forecast regime 30-60 days ahead

### Long-term (12 months)
1. **ML Classifier**: Replace rules with gradient boosting
2. **Multi-Market Model**: Model inter-market dependencies
3. **Causal Inference**: Identify regime drivers (rates vs inventory)
4. **Real-Time Updates**: Intraday regime scoring

---

## References

- **BOCPD Paper**: Adams & MacKay (2007) "Bayesian Online Changepoint Detection"
- **Implementation**: `ml/regime/` directory
- **Market Cycles**: Case-Shiller methodology
- **Real Estate Economics**: "Real Estate Cycles" by Pyhrr et al.

---

## Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-11-01 | Initial regime monitoring system | Platform Engineering |

---

## Approval Status

- [ ] **Data Science Lead**: Methodology validated
- [ ] **Acquisitions Lead**: Policies reviewed
- [ ] **Product**: Use cases confirmed
- [ ] **Compliance**: Fair housing review (no demographic proxies)

**Status**: ⚠️ DRAFT - Pending DAG deployment and validation
