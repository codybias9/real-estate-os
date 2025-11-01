# Model Card: ARV Predictor

**Model Name**: ARV Predictor (After Repair Value)
**Version**: 0.0.0
**Last Updated**: 2025-11-01
**Owner**: Data Science / Valuation Team
**Status**: ❌ NOT IMPLEMENTED (Planned for future development)

---

## Model Details

### Model Type
Regression model for predicting post-renovation property value

### Planned Components
1. **Base Value Estimator**: Current as-is market value (leverage Comp-Critic)
2. **Repair Impact Model**: Value lift from specific repairs/renovations
3. **Market Adjustment**: Local market conditions and buyer preferences
4. **Ensemble Predictor**: Combine multiple estimation approaches

### Framework & Dependencies (Planned)
- **ML Framework**: scikit-learn (Gradient Boosting), XGBoost, or LightGBM
- **Feature Engineering**: Pandas, NumPy
- **Geospatial**: PostGIS for market-level features
- **Integration**: Comp-Critic API for base valuations
- **Storage**: Postgres for training data, Redis for fast lookups

### Model Location (Planned)
- **Code**: `ml/valuation/arv_predictor.py` (NOT YET CREATED)
- **API**: `/valuation/arv` (NOT YET CREATED)
- **Training Pipeline**: `dags/ml/arv_training_dag.py` (NOT YET CREATED)

---

## Intended Use

### Primary Use Cases
- **Offer Calculation**: Estimate property value after planned repairs for max offer calculation
- **Deal Analysis**: Evaluate profit potential (ARV - Purchase Price - Repair Cost)
- **Renovation Planning**: Identify highest-value improvements (value lift per $1 spent)
- **Portfolio Prioritization**: Rank properties by potential value-add opportunity

### Users
- Acquisitions team for offer pricing
- Renovations team for scope planning
- Portfolio managers for investment prioritization
- Finance team for underwriting

### Property Types
- **Primary**: Single-family residential (SFR)
- **Secondary**: Small multifamily (2-4 units)
- **Future**: Condos, townhomes

### Geographic Scope
- **Coverage**: All US markets where Comp-Critic operates
- **Minimum Data**: ≥20 renovated comps in market (last 2 years)
- **Optimal Data**: ≥100 renovated comps per market

---

## Model Inputs

### Property Characteristics

**As-Is Condition**:
- `property_id`: Identifier
- `address`: Full address
- `sqft`: Square footage
- `bedrooms`: Bedroom count
- `bathrooms`: Bathroom count
- `year_built`: Construction year
- `lot_size`: Lot size (sqft)
- `garage_spaces`: Garage count
- `stories`: Number of stories
- `foundation_type`: Slab, crawl, basement

**Current Condition Assessment**:
- `overall_condition`: Scale 1-10 (1=tear-down, 10=pristine)
- `roof_condition`: Years remaining, material
- `hvac_condition`: Years old, type
- `kitchen_condition`: Scale 1-10
- `bathroom_condition`: Scale 1-10
- `flooring_condition`: Carpet/hardwood/tile percentages
- `foundation_issues`: Boolean flags (cracks, settling, water)
- `systems_functional`: Electrical, plumbing, HVAC status

### Planned Renovation Scope

**Major Systems**:
- `roof_replacement`: Boolean + cost estimate
- `hvac_replacement`: Boolean + cost estimate
- `electrical_upgrade`: Boolean + cost estimate
- `plumbing_upgrade`: Boolean + cost estimate

**Interior Upgrades**:
- `kitchen_remodel`: None, light, moderate, full
- `bathroom_remodel`: Count + level (light/moderate/full)
- `flooring_upgrade`: Sqft + material (carpet/laminate/hardwood/tile)
- `paint_interior`: Boolean
- `fixtures_upgrade`: Boolean (lights, fans, hardware)

**Exterior Upgrades**:
- `siding_replacement`: Boolean + material
- `windows_replacement`: Count + type (vinyl/wood/fiberglass)
- `landscaping`: Level (basic/moderate/premium)
- `driveway_repair`: Boolean
- `deck_patio_addition`: Boolean + sqft

**Structural**:
- `addition_sqft`: Square feet added (bedroom, bathroom, etc.)
- `garage_addition`: Boolean
- `basement_finish`: Sqft finished

**Total Repair Budget**:
- `total_repair_cost`: Total estimated cost ($)
- `repair_timeline`: Weeks to complete
- `holding_costs`: Carrying costs during renovation

### Market Context

**Local Market Data**:
- `median_sale_price`: Market median
- `price_per_sqft`: Market average $/sqft
- `days_on_market`: Average DOM
- `market_regime`: Hot/warm/cool/cold
- `inventory_months`: Months of supply
- `price_appreciation_yoy`: YoY price change

**Comparable Sales**:
- Recent renovated sales (within 1 mile, last 12 months)
- Renovation level comparison (light/moderate/heavy)
- Value lift observed (sale price vs. pre-renovation assessed value)

---

## Model Outputs

### ARV Estimate

**Point Estimate**:
- `arv_estimate`: After Repair Value ($)
- `arv_per_sqft`: ARV / sqft ($)
- `value_lift`: ARV - Current As-Is Value ($)
- `value_lift_pct`: (ARV - As-Is) / As-Is (%)

**Confidence Interval**:
- `arv_lower_80`: 10th percentile ($)
- `arv_upper_80`: 90th percentile ($)
- `arv_lower_95`: 2.5th percentile ($)
- `arv_upper_95`: 97.5th percentile ($)

**Breakdown by Category**:
```json
{
  "base_value": 250000,
  "repair_impact": {
    "kitchen_remodel": 15000,
    "bathroom_remodel": 8000,
    "flooring_upgrade": 5000,
    "paint_interior": 3000,
    "roof_replacement": 7000,
    "total_value_add": 38000
  },
  "market_adjustment": 12000,
  "arv_estimate": 300000
}
```

### Deal Metrics

**Profit Analysis**:
```python
arv_estimate = 300000
purchase_price = 200000
repair_cost = 40000
holding_costs = 5000 (6 months @ $1000/mo + utilities)
closing_costs = 8000 (selling costs @ 4%)

# Net profit
profit = arv_estimate - purchase_price - repair_cost - holding_costs - closing_costs
profit = 300000 - 200000 - 40000 - 5000 - 8000 = 47000

# ROI
roi = profit / (purchase_price + repair_cost)
roi = 47000 / 240000 = 19.6%
```

**Renovation ROI by Category**:
```json
{
  "kitchen_remodel": {"cost": 12000, "value_add": 15000, "roi": 1.25},
  "bathroom_remodel": {"cost": 6000, "value_add": 8000, "roi": 1.33},
  "flooring_upgrade": {"cost": 4000, "value_add": 5000, "roi": 1.25},
  "roof_replacement": {"cost": 10000, "value_add": 7000, "roi": 0.70}
}
```

### Recommendations

**High-ROI Improvements** (value add > 1.2x cost):
- Kitchen remodel (light/moderate)
- Bathroom updates
- Fresh paint + flooring
- Curb appeal (landscaping, door/shutters)

**Low-ROI Improvements** (value add < 1.0x cost):
- Swimming pools (rarely recover cost)
- Over-improved kitchens (gold fixtures, custom cabinets)
- High-end finishes in low-price-point markets

**Market-Specific Adjustments**:
- Hot markets: Focus on speed (light rehab, flip fast)
- Cool markets: Focus on value-add (moderate rehab, differentiate)

---

## Calculations & Formulas (Planned)

### Base Value Estimation

**Approach 1: Comp-Critic Integration**
```python
# Get current as-is value from Comp-Critic
as_is_value = comp_critic_api.estimate_value(
    property_id=property_id,
    condition="as-is"
)

# Use as baseline
base_value = as_is_value.median_estimate
```

**Approach 2: Comparative Sales Analysis**
```python
# Find renovated comps in market
renovated_comps = get_renovated_comps(
    location=property.location,
    sqft_range=(property.sqft * 0.8, property.sqft * 1.2),
    sold_date_range=(now - 24_months, now)
)

# Calculate value lift from renovations
for comp in renovated_comps:
    value_lift = comp.sale_price - comp.pre_renovation_assessed_value
    value_lift_per_sqft = value_lift / comp.sqft
    value_lift_pct = value_lift / comp.pre_renovation_assessed_value
```

### Repair Impact Model

**Feature Engineering**:
```python
# Renovation features (binary + categorical)
features = [
    # Major systems (0/1)
    'roof_replaced', 'hvac_replaced', 'electrical_upgraded', 'plumbing_upgraded',

    # Interior (0/1/2/3 for none/light/moderate/full)
    'kitchen_remodel_level', 'bathroom_remodel_level',

    # Flooring (sqft renovated × material quality score)
    'flooring_sqft_hardwood', 'flooring_sqft_tile', 'flooring_sqft_laminate',

    # Structural additions (sqft)
    'addition_sqft', 'garage_added', 'basement_finished_sqft',

    # Exterior (0/1)
    'siding_replaced', 'windows_replaced', 'landscaping_upgraded'
]

# Target
target = arv - as_is_value  # Value lift from repairs
```

**Model Training** (Gradient Boosting):
```python
from sklearn.ensemble import GradientBoostingRegressor

model = GradientBoostingRegressor(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    loss='huber',  # Robust to outliers
    subsample=0.8
)

model.fit(X_train, y_train)  # X=renovation features, y=value lift

# Predict value lift for new property
value_lift_pred = model.predict(X_new)
arv_estimate = as_is_value + value_lift_pred
```

### Market Adjustment

**Local Market Multiplier**:
```python
# Adjust for local market strength
market_multiplier = 1.0

if market_regime == "hot":
    market_multiplier = 1.10  # Buyers pay premium
elif market_regime == "cold":
    market_multiplier = 0.90  # Buyers demand discount

# Apply to value lift
adjusted_value_lift = value_lift_pred * market_multiplier
arv_estimate = as_is_value + adjusted_value_lift
```

### Uncertainty Quantification

**Quantile Regression** (for confidence intervals):
```python
from sklearn.ensemble import GradientBoostingRegressor

# Train models for different quantiles
model_q10 = GradientBoostingRegressor(loss='quantile', alpha=0.10)
model_q50 = GradientBoostingRegressor(loss='quantile', alpha=0.50)
model_q90 = GradientBoostingRegressor(loss='quantile', alpha=0.90)

model_q10.fit(X_train, y_train)
model_q50.fit(X_train, y_train)
model_q90.fit(X_train, y_train)

# Predict with uncertainty
value_lift_q10 = model_q10.predict(X_new)
value_lift_q50 = model_q50.predict(X_new)
value_lift_q90 = model_q90.predict(X_new)

arv_lower_80 = as_is_value + value_lift_q10
arv_median = as_is_value + value_lift_q50
arv_upper_80 = as_is_value + value_lift_q90
```

---

## Performance (Target Metrics)

### Accuracy Targets

**Prediction Error** (on test set, 20% holdout):
- **MAE**: ≤7% of ARV (e.g., $21k on $300k property)
- **MAPE**: ≤8%
- **RMSE**: ≤10% of ARV
- **R²**: ≥0.85

**By Property Value Range**:
| Price Range | MAE Target | MAPE Target |
|-------------|------------|-------------|
| <$200k | ≤$15k | ≤10% |
| $200k-$400k | ≤$20k | ≤7% |
| $400k-$600k | ≤$30k | ≤6% |
| >$600k | ≤$40k | ≤5% |

**By Renovation Level**:
| Renovation Level | MAE Target | Notes |
|------------------|------------|-------|
| Light (<$20k) | ≤$10k | High confidence |
| Moderate ($20k-$50k) | ≤$20k | Most common |
| Heavy (>$50k) | ≤$30k | Higher uncertainty |

### Calibration

**Confidence Interval Coverage**:
- 80% CI should contain true ARV in ≥78% of cases
- 95% CI should contain true ARV in ≥93% of cases
- Track coverage by market, property type

### Business Impact

**Offer Accuracy**:
- Properties purchased using ARV estimates should achieve ≥90% of predicted profit
- Offer acceptance rate ≥15% (not over-paying)
- Average profit margin ≥12% of ARV

**Renovation ROI**:
- Recommended improvements should achieve ≥1.2x ROI in ≥80% of cases
- Discouraged improvements (low ROI) avoided in ≥90% of cases

---

## Training Data Requirements

### Data Sources

**Historical Renovated Sales**:
- Source: MLS, county recorder, internal portfolio
- Required: Before/after values, renovation details, costs
- Volume: 5000+ renovated properties across markets
- Timeframe: Last 3 years (recent trends)

**Property Assessments**:
- Source: County assessors
- Required: Pre-renovation assessed value, post-renovation assessed value
- Volume: 10,000+ properties

**Cost Data**:
- Source: Contractor bids, internal renovation logs
- Required: Itemized costs by renovation type
- Volume: 1000+ completed projects

### Data Quality Requirements

**Completeness**:
- ≥90% of properties have renovation scope details
- ≥80% have before/after photos
- ≥70% have itemized cost breakdowns

**Accuracy**:
- Sale prices verified against county records
- Renovation dates within ±30 days
- Cost estimates within ±20% of actuals

**Labeling**:
- Renovation level (light/moderate/heavy) manually labeled
- Quality checks by experienced acquisitions team

---

## Limitations & Caveats

### Model Limitations

**Data Sparsity**:
- Sparse markets (<20 renovated comps) → High uncertainty
- Rare renovation types (e.g., basement addition in hot markets)
- Solution: Fall back to national averages, widen CI

**Cost Variability**:
- Contractor costs vary widely by market and season
- Model assumes typical contractor rates
- User should input actual bid costs

**Market Timing**:
- ARV assumes property sells immediately after renovation
- Holding time affects value (market may shift)
- Solution: Add market trend forecast (appreciate/depreciate)

**Over-Improvement Risk**:
- Model may not penalize over-improving for neighborhood
- $100k kitchen in $200k neighborhood = bad ROI
- Solution: Add neighborhood comps ceiling check

### Known Failure Modes

**Unique Properties**:
- Historical homes (restoration vs. renovation)
- Properties on large lots (land value dominates)
- Luxury properties (few comps)

**Market Shocks**:
- Rapid market appreciation during renovation → ARV understated
- Market crash during renovation → ARV overstated
- Solution: Update ARV monthly based on market trends

**Scope Creep**:
- Actual renovation costs exceed estimates (common!)
- Model predicts value lift, not cost overruns
- Solution: Add 10-20% contingency buffer

---

## Monitoring (Planned)

### Real-Time Metrics

**Per Prediction**:
- `arv_estimate`: Predicted ARV
- `confidence_interval_width`: Upper - Lower (uncertainty)
- `comp_count`: Number of renovated comps used
- `market_data_age`: Days since last market data update

### Aggregated Metrics (Monthly)

**Prediction Accuracy** (on realized ARV):
- `mae`: Mean Absolute Error
- `mape`: Mean Absolute Percentage Error
- `calibration_error`: CI coverage deviation
- Broken down by: market, property type, renovation level

**Business Outcomes**:
- `offer_acceptance_rate`: % of offers accepted
- `realized_profit_pct`: Actual profit / predicted profit
- `renovation_roi_accuracy`: Predicted ROI vs. actual ROI

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| MAE | >10% of ARV | >15% of ARV |
| Calibration error | CI coverage <75% | CI coverage <70% |
| Comp count | <10 per market | <5 per market |
| Data freshness | >30 days | >60 days |

---

## Integration Points

### Comp-Critic Integration
```python
# Step 1: Get as-is value from Comp-Critic
as_is_value = comp_critic_api.estimate_value(
    property_id=property_id,
    condition="as-is",
    include_comps=True
)

# Step 2: Predict value lift from renovations
value_lift = arv_model.predict_value_lift(
    property_features=property,
    renovation_scope=renovation_plan
)

# Step 3: Combine
arv_estimate = as_is_value.median + value_lift
```

### Offer Optimizer Integration
```python
# Offer optimizer needs ARV for max offer calculation
max_offer = arv_estimate * 0.85 - repair_cost - holding_cost

# Pass ARV to optimizer
offer_optimizer.optimize_offer(
    property_id=property_id,
    arv=arv_estimate,
    arv_confidence_interval=(arv_lower_80, arv_upper_80),
    repair_cost=repair_cost,
    holding_cost=holding_cost,
    target_margin=0.15
)
```

### DCF Integration
```python
# For rental properties, ARV affects exit value
dcf_engine.calculate_npv(
    property_id=property_id,
    initial_investment=purchase_price + repair_cost,
    rental_income_projection=[...],
    exit_year=5,
    exit_value=arv_estimate  # ARV used as exit valuation
)
```

---

## Future Improvements

### Short-term (3 months)
1. **Data Collection**: Partner with contractors for cost data
2. **Baseline Model**: Train initial model on 1000+ properties
3. **API Endpoint**: Create `/valuation/arv` endpoint
4. **Validation**: Backtest on 6 months of closed deals

### Medium-term (6 months)
1. **Computer Vision**: Estimate condition from photos (roof, kitchen, etc.)
2. **Cost Estimator**: Automated repair cost estimation by scope
3. **Market Trends**: Incorporate forward-looking market forecasts
4. **Renovation Planner**: Recommend optimal scope for max ROI

### Long-term (12 months)
1. **Causal Inference**: Isolate causal effect of each renovation type
2. **Personalization**: Per-tenant models (risk appetite, budget)
3. **Real-Time Updates**: Update ARV as renovation progresses
4. **Multi-Property**: Portfolio-level optimization (which properties to renovate)

---

## References

- **Real Estate Appraisal**: "The Appraisal of Real Estate" (Appraisal Institute)
- **Renovation ROI**: Remodeling Magazine "Cost vs. Value Report" (annual)
- **ML Methods**: "Gradient Boosting" (Hastie, Tibshirani, Friedman)
- **Related Models**: Comp-Critic (base value), DCF (exit value), Offer Optimizer (max offer)

---

## Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.0.0 | 2025-11-01 | Initial model card (NOT IMPLEMENTED) | Platform Engineering |

---

## Approval Status

- [ ] **Data Science Lead**: Model architecture approved
- [ ] **Acquisitions Lead**: Use cases validated
- [ ] **Renovations Lead**: Scope categories confirmed
- [ ] **Finance**: Profit calculations reviewed
- [ ] **Product**: Integration points confirmed

**Status**: ❌ NOT IMPLEMENTED - Pending data collection and model development

---

## Implementation Roadmap

### Phase 1: Data Foundation (Month 1-2)
- Collect historical renovation data (before/after values, costs)
- Build ETL pipeline for contractor cost data
- Label renovation levels (light/moderate/heavy)
- Create training dataset (target: 1000+ properties)

### Phase 2: Baseline Model (Month 3-4)
- Train Gradient Boosting model on collected data
- Implement quantile regression for confidence intervals
- Create `/valuation/arv` API endpoint
- Backtest on last 6 months of deals

### Phase 3: Integration (Month 5-6)
- Integrate with Comp-Critic for as-is valuations
- Connect to Offer Optimizer for max offer calculations
- Build UI for renovation scope input
- Deploy to staging environment

### Phase 4: Validation & Launch (Month 7-8)
- Run shadow mode for 1 month (predict, don't use)
- Compare predictions to realized ARVs
- Tune model based on feedback
- GA launch with monitoring

**Total Timeline**: 8 months from start to GA
