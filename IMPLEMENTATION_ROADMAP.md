# Real Estate OS - Production Enhancement Roadmap

**Status**: Foundation Complete (12 PRs), Now Enhancing to Full Production Spec

---

## Phase 1: Foundation Verification ✅

### Completed (PRs 1-12)
- [x] JWT authentication (~500 LOC)
- [x] Basic testing infrastructure
- [x] Docker/Kubernetes foundation
- [x] OpenTelemetry/Prometheus/Grafana/Sentry
- [x] Redis caching layer
- [x] PostGIS geographic search (basic)
- [x] Splink owner deduplication (basic)
- [x] SHAP/DiCE explainability (basic)
- [x] Temporal workflows (basic)
- [x] DocuSign integration (basic)
- [x] Lease parsing (basic)
- [x] Hazard layers (basic)

### Code Stats
- Total files: ~65
- Total LOC: ~15,000
- Routers: 1,896 LOC (auth, properties, outreach)
- Auth system: 487 LOC
- Observability: 515 LOC
- Tests: ~70,000 LOC

---

## Phase 2: Production Hardening (In Progress)

### PR#13: Data Trust & Lineage Pack
**Objective**: Add Great Expectations, OpenLineage, Marquez

**Implementation**:
```
libs/data_quality/gx/
├── expectations/
│   ├── properties_suite.json
│   ├── ownership_suite.json
│   └── outreach_suite.json
├── checkpoints/
│   └── daily_validation.py
└── great_expectations.yml

services/lineage/
├── docker-compose.marquez.yml
├── marquez/
│   ├── manifests/
│   └── config/
└── openlineage_integration.py
```

**Acceptance**:
- [ ] GX coverage ≥90% of datasets
- [ ] Data Docs accessible from admin UI
- [ ] Marquez UI shows full DAG lineage
- [ ] OpenLineage events emitted for all Airflow tasks

---

### PR#14: Keycloak OIDC Integration
**Objective**: Replace/augment JWT with enterprise SSO

**Implementation**:
```
auth/keycloak/
├── realm-export.json
├── clients/
│   ├── api-client.json
│   └── web-client.json
└── docker-compose.keycloak.yml

api/app/auth/
├── oidc.py          # OIDC provider integration
├── keycloak.py      # Keycloak-specific logic
└── middleware.py    # Updated auth middleware
```

**Key Changes**:
- FastAPI middleware checks OIDC tokens OR JWT (backward compat)
- React app uses Code Flow with PKCE
- Role mappings from Keycloak → app roles
- API keys remain for service-to-service

**Acceptance**:
- [ ] User can login via Keycloak
- [ ] Roles sync correctly
- [ ] Existing JWT auth still works
- [ ] RBAC enforced

---

### PR#15: Feast Feature Store
**Objective**: Replace bespoke feature joins with Feast

**Implementation**:
```
ml/feature_repo/
├── feature_store.yaml
├── features/
│   ├── property_features.py
│   ├── market_features.py
│   ├── owner_features.py
│   └── hazard_features.py
├── data_sources.py
└── registry.db

api/app/ml/
└── feast_client.py
```

**Feature Views**:
1. **PropertyFeatures**: sqft, lot_size, year_built, condition, renovation_date
2. **MarketFeatures**: median_price, DOM, inventory, price_cut_rate, by submarket
3. **OwnerFeatures**: portfolio_size, avg_hold_period, response_rate
4. **HazardFeatures**: flood_zone, wildfire_risk, heat_island_intensity

**Integration**:
- Scoring service calls `feast.get_online_features()`
- Redis for online store
- Postgres for offline store
- Materializations via Airflow

**Acceptance**:
- [ ] All features in Feast registry
- [ ] Scoring service uses `get_online_features()`
- [ ] Online features <50ms p95
- [ ] Offline features work for training

---

### PR#16: libpostal + Enhanced PostGIS
**Objective**: Production-grade geocoding and search

**Implementation**:
```
services/normalization/
├── Dockerfile (with libpostal compiled)
├── address_normalizer.py
└── api.py

db/migrations/
└── 0010_add_postgis_extensions.sql

api/app/geo/
├── search.py (enhanced)
├── geocoding.py
└── nominatim.py (self-hosted option)
```

**Address Normalization Flow**:
```python
raw_address → libpostal.parse() → {
    "house_number": "123",
    "road": "main st",
    "city": "las vegas",
    "state": "nv",
    "postcode": "89101"
} → canonical_address + confidence
```

**PostGIS Enhancements**:
- `ALTER TABLE property ADD COLUMN geom geography(Point, 4326)`
- `CREATE INDEX idx_property_geom ON property USING GIST(geom)`
- Add `geom_confidence` field
- Snap to parcel centroids when available

**Acceptance**:
- [ ] libpostal normalizes addresses
- [ ] PostGIS queries use spatial index
- [ ] Self-hosted Nominatim option available
- [ ] Geocoding confidence tracked in provenance

---

### PR#17: Enhanced ML Explainability + UI
**Objective**: Production UI for SHAP/DiCE

**Implementation**:
```
web/src/features/explainability/
├── components/
│   ├── SHAPDrivers.tsx
│   ├── CounterfactualSliders.tsx
│   ├── WhatIfPanel.tsx
│   └── ForceePlot.tsx
├── hooks/
│   ├── useExplainability.ts
│   └── useCounterfactuals.ts
└── api/
    └── explainabilityApi.ts

api/app/ml/
├── shap_service.py (enhanced)
└── dice_service.py (enhanced)
```

**UI Components**:
1. **SHAP Drivers Panel**:
   - Top-k features with signed impacts
   - Waterfall chart
   - Feature importance bar chart

2. **What-If Sliders**:
   - Interactive sliders for key features
   - Real-time prediction updates
   - Policy constraints enforced

3. **Counterfactual Suggestions**:
   - "To reach grade A, you need..."
   - Minimal changes highlighted
   - Feasibility indicators

**Acceptance**:
- [ ] Property drawer shows SHAP panel
- [ ] Sliders update predictions in real-time
- [ ] Counterfactuals suggest actionable changes
- [ ] Force plots render correctly

---

### PR#18: Qdrant Vector Search
**Objective**: Add vector search for portfolio twins

**Implementation**:
```
services/qdrant/
└── docker-compose.qdrant.yml

api/app/vector/
├── qdrant_client.py
├── embeddings.py
└── search.py

ml/embeddings/
├── property_encoder.py  # Supervised metric learning
└── train_encoder.py     # Triplet loss on won/passed pairs
```

**Qdrant Collections**:
```python
{
  "name": "properties",
  "vectors": {"size": 128, "distance": "Cosine"},
  "payload_schema": {
    "tenant_id": "keyword",  # INDEXED
    "market": "keyword",     # INDEXED
    "asset_type": "keyword", # INDEXED
    "price_band": "keyword", # INDEXED
    "sqft_band": "keyword"   # INDEXED
  }
}
```

**Search Flow**:
```python
# Encode query property
embedding = encoder.encode(property_features)

# Search with tenant isolation
results = qdrant.search(
    collection_name="properties",
    query_vector=embedding,
    query_filter={
        "must": [
            {"key": "tenant_id", "match": {"value": tenant_id}},
            {"key": "market", "match": {"value": market}}
        ]
    },
    limit=20
)
```

**Acceptance**:
- [ ] Qdrant running in docker-compose
- [ ] Property embeddings created
- [ ] tenant_id filter ALWAYS enforced
- [ ] p95 < 80ms @ 10M vectors (filtered)
- [ ] Payload indexes created

---

### PR#19: Evidently Drift Detection
**Objective**: Monitor feature and model drift

**Implementation**:
```
ml/monitoring/
├── evidently_config.py
├── drift_detection.py
└── reports/

dags/
└── drift_monitoring_dag.py  # Nightly

observability/grafana/dashboards/
└── ml_drift_dashboard.json
```

**Drift Reports**:
1. **Feature Drift**:
   - PSI (Population Stability Index)
   - JS Divergence
   - Per-feature drift scores

2. **Model Drift**:
   - R² degradation
   - MAE/RMSE increase
   - Prediction distribution shift

3. **Data Quality**:
   - Missing values %
   - Outlier detection
   - Schema changes

**Alert Thresholds**:
- Warning: PSI > 0.1
- Critical: PSI > 0.25
- Block deployments: PSI > 0.4

**Acceptance**:
- [ ] Nightly drift jobs run
- [ ] HTML reports generated
- [ ] Alerts fire when drift exceeds thresholds
- [ ] Grafana dashboard shows drift metrics

---

### PR#20: Comp-Critic Valuation Logic
**Objective**: 3-stage comp selection and adjustment

**Implementation**:
```
ml/valuation/
├── comp_retrieval.py
├── comp_ranking.py
├── comp_adjustment.py
└── valuation_service.py

api/app/routers/
└── valuation.py  # New endpoints
```

**3-Stage Comp-Critic**:

**Stage 1: Retrieval**
```python
def retrieve_comps(subject, k=50):
    """Broad retrieval with basic filters"""
    comps = db.query(Property).filter(
        ST_DWithin(Property.geom, subject.geom, radius=1609*2),  # 2 miles
        Property.asset_type == subject.asset_type,
        Property.sqft.between(subject.sqft*0.7, subject.sqft*1.3),
        Property.sale_date >= now() - timedelta(days=180)
    ).all()

    # Weight by distance and recency
    for comp in comps:
        d_spatial = haversine(subject, comp)
        d_temporal = (now() - comp.sale_date).days
        comp.weight = exp(-(d_spatial/sigma_d)**2) * exp(-(d_temporal/sigma_t)**2)

    return sorted(comps, key=lambda c: c.weight, reverse=True)[:k]
```

**Stage 2: Ranking (LambdaMART)**
```python
def rank_comps(subject, comps):
    """Learn-to-rank with structural features"""
    features = []
    for comp in comps:
        features.append({
            'distance_m': haversine(subject, comp),
            'recency_days': (now() - comp.sale_date).days,
            'size_delta': abs(comp.sqft - subject.sqft) / subject.sqft,
            'vintage_delta': abs(comp.year_built - subject.year_built),
            'renovation_match': int(comp.renovated == subject.renovated),
            'micro_market_match': int(comp.micro_market == subject.micro_market)
        })

    # LightGBM ranker trained on historical appraisals
    scores = ranker_model.predict(features)
    return sorted(zip(comps, scores), key=lambda x: x[1], reverse=True)
```

**Stage 3: Hedonic Adjustment**
```python
def adjust_comps(subject, ranked_comps):
    """Apply hedonic adjustments"""
    model = QuantileRegressor(quantile=0.5, alpha=0.01)  # L1 regularization

    # Train on comp delta features
    X = [comp_features(c) - subject_features(subject) for c, _ in ranked_comps]
    y = [c.price_per_sf for c, _ in ranked_comps]

    model.fit(X, y)

    # Adjust each comp
    adjusted = []
    for comp, rank_score in ranked_comps:
        delta_features = comp_features(comp) - subject_features(subject)
        delta_price_per_sf = model.predict([delta_features])[0]

        adjusted_price = comp.price - (delta_price_per_sf * comp.sqft)

        adjusted.append({
            'comp': comp,
            'rank_score': rank_score,
            'unadjusted_price': comp.price,
            'adjusted_price': adjusted_price,
            'adjustments': explain_adjustments(delta_features, model.coef_)
        })

    return adjusted
```

**Valuation Output**:
```json
{
  "subject_property_id": "...",
  "estimated_value": 425000,
  "confidence_interval": [405000, 445000],
  "comps": [
    {
      "property_id": "...",
      "address": "456 Main St",
      "distance_m": 320,
      "sale_date": "2024-09-15",
      "sale_price": 430000,
      "adjusted_price": 423500,
      "adjustments": {
        "size": -3000,
        "condition": +2500,
        "location": -1000
      },
      "weight": 0.25
    }
  ],
  "drivers": [
    {"feature": "location", "impact": +15000},
    {"feature": "size", "impact": +8000}
  ]
}
```

**Acceptance**:
- [ ] 3-stage comp logic implemented
- [ ] LambdaMART ranker trained
- [ ] Hedonic adjustments work
- [ ] Waterfall charts show adjustments
- [ ] Backtesting: MAE < 5% of sale price

---

### PR#21: MF/CRE DCF Valuation
**Objective**: Income approach for multi-family and commercial

**Implementation**:
```
ml/valuation/
├── mf_valuation.py
├── cre_valuation.py
└── dcf_engine.py
```

**MF Valuation**:
```python
def value_mf_property(property_id, rent_roll, market_data):
    """Multi-family valuation via direct cap and DCF"""

    # 1. Calculate Effective Gross Income
    GPR = sum(unit.base_rent * 12 for unit in rent_roll)
    vacancy_rate = market_data.submarket_vacancy or 0.05
    EGI = GPR * (1 - vacancy_rate)

    # 2. Operating Expenses
    opex_per_unit = market_data.opex_per_unit or 5000
    opex = opex_per_unit * len(rent_roll)
    reserves = EGI * 0.03  # 3% for CapEx reserves

    # 3. Net Operating Income
    NOI = EGI - opex - reserves

    # 4. Direct Capitalization
    cap_rate = market_data.submarket_cap_rate or 0.055
    cap_rate_bayesian = bayesian_shrink(cap_rate, market_data.county_cap_rate)
    value_direct_cap = NOI / cap_rate_bayesian

    # 5. DCF (10-year hold)
    cash_flows = []
    for year in range(1, 11):
        # Rent growth
        rent_growth = market_data.rent_growth_rate or 0.025
        gpr_year = GPR * (1 + rent_growth) ** year
        egi_year = gpr_year * (1 - vacancy_rate)

        # Expense growth
        expense_growth = 0.03
        opex_year = opex * (1 + expense_growth) ** year
        reserves_year = egi_year * 0.03

        noi_year = egi_year - opex_year - reserves_year
        cash_flows.append(noi_year)

    # Exit value (year 10)
    exit_cap_rate = cap_rate_bayesian + 0.005  # 50bps premium
    exit_value = cash_flows[-1] / exit_cap_rate
    cash_flows[-1] += exit_value

    # Discount to present
    discount_rate = 0.08  # 8% IRR target
    npv = sum(cf / (1 + discount_rate)**i for i, cf in enumerate(cash_flows, 1))

    # Debt service coverage ratio
    loan_amount = npv * 0.75  # 75% LTV
    interest_rate = 0.05
    debt_service = loan_amount * (interest_rate / 12) * 12 / (1 - (1 + interest_rate/12)**(-30*12))
    dscr = NOI / debt_service

    return {
        'value_direct_cap': value_direct_cap,
        'value_dcf': npv,
        'NOI': NOI,
        'cap_rate': cap_rate_bayesian,
        'dscr': dscr,
        'cash_flows': cash_flows,
        'assumptions': {
            'vacancy_rate': vacancy_rate,
            'rent_growth': rent_growth,
            'exit_cap_rate': exit_cap_rate
        }
    }
```

**CRE Valuation** (similar but suite-level):
- Per-suite cash flows
- Lease rollover modeling
- TI/LC reserves per SF
- Credit-weighted vacancy

**Acceptance**:
- [ ] MF valuation works
- [ ] CRE valuation works
- [ ] DCF with scenario analysis
- [ ] DSCR and yield metrics
- [ ] UI shows waterfall and fan chart

---

### PR#22: Regime Monitoring
**Objective**: Detect market regime changes

**Implementation**:
```
ml/regime/
├── regime_detector.py
├── bayesian_changepoint.py
└── regime_service.py

dags/
└── regime_monitoring_dag.py  # Weekly
```

**Regime Composite Index**:
```python
def calculate_regime_index(market, week):
    """Composite index from multiple signals"""

    # 1. New listings (normalized)
    new_listings_z = (week.new_listings - market.mean_new_listings) / market.std_new_listings

    # 2. Days on market (inverted)
    dom_z = -(week.median_dom - market.mean_dom) / market.std_dom

    # 3. Price cuts
    price_cut_pct = week.price_cuts / week.active_listings
    price_cut_z = (price_cut_pct - market.mean_price_cut_pct) / market.std_price_cut_pct

    # 4. Rent growth
    rent_growth = (week.median_rent - week_52ago.median_rent) / week_52ago.median_rent
    rent_z = (rent_growth - market.mean_rent_growth) / market.std_rent_growth

    # 5. Interest rates (external)
    rate_delta = week.mortgage_rate - week_52ago.mortgage_rate
    rate_z = -rate_delta / market.std_rate_delta  # Negative = stimulative

    # Composite
    regime_index = (
        0.25 * new_listings_z +
        0.20 * dom_z +
        0.20 * price_cut_z +
        0.20 * rent_z +
        0.15 * rate_z
    )

    return regime_index
```

**Bayesian Change-Point Detection**:
```python
from rpy2.robjects.packages import importr
bcp = importr('bcp')

# Detect regime shifts
regime_series = [calculate_regime_index(market, w) for w in weeks]
changepoints = bcp.bcp(regime_series, burnin=100, mcmc=1000)

# Classify current regime
current_index = regime_series[-1]
if current_index > 0.75:
    regime = "hot"
elif current_index > 0.25:
    regime = "warm"
elif current_index > -0.25:
    regime = "cool"
else:
    regime = "cold"
```

**Policy Adjustments**:
```python
regime_policies = {
    "hot": {
        "max_offer_pct": 0.98,  # Aggressive
        "earnest_pct": 0.02,
        "dd_days": 7,
        "close_days": 21
    },
    "warm": {
        "max_offer_pct": 0.95,
        "earnest_pct": 0.01,
        "dd_days": 14,
        "close_days": 30
    },
    "cool": {
        "max_offer_pct": 0.90,
        "earnest_pct": 0.01,
        "dd_days": 21,
        "close_days": 45
    },
    "cold": {
        "max_offer_pct": 0.85,  # Conservative
        "earnest_pct": 0.005,
        "dd_days": 30,
        "close_days": 60
    }
}
```

**Acceptance**:
- [ ] Regime index calculated weekly
- [ ] Change-point detection works
- [ ] Regime classification: hot/warm/cool/cold
- [ ] Policy knobs auto-adjust
- [ ] Dashboard shows regime history
- [ ] Alerts on regime transitions

---

### PR#23: Offer Optimization
**Objective**: MIP-based offer optimization

**Implementation**:
```
ml/optimization/
├── offer_optimizer.py
├── constraints.py
└── objectives.py
```

**MIP Formulation**:
```python
from ortools.linear_solver import pywraplp

def optimize_offer(property, tenant_policy, market_regime):
    """Mixed-integer programming for offer optimization"""

    solver = pywraplp.Solver.CreateSolver('SCIP')

    # Decision variables
    price = solver.NumVar(
        property.arv * 0.70,  # Min 70% of ARV
        property.arv * 0.98,  # Max 98% of ARV
        'price'
    )

    earnest = solver.NumVar(
        property.arv * 0.005,
        property.arv * 0.03,
        'earnest'
    )

    dd_days = solver.IntVar(7, 30, 'dd_days')
    close_days = solver.IntVar(14, 60, 'close_days')

    # Binary: include contingencies
    inspection_contingency = solver.BoolVar('inspection')
    financing_contingency = solver.BoolVar('financing')
    appraisal_contingency = solver.BoolVar('appraisal')

    repair_credit = solver.NumVar(0, 10000, 'repair_credit')
    escalation_clause = solver.BoolVar('escalation')

    # Constraints

    # 1. Profit margin
    total_cost = price + tenant_policy.rehab_budget + tenant_policy.carry_costs + tenant_policy.fees
    profit = property.arv - total_cost
    solver.Add(profit >= property.arv * tenant_policy.min_margin)  # e.g., 15%

    # 2. DSCR (for rental properties)
    if property.strategy == 'buy_and_hold':
        noi = property.projected_rent * 12 * 0.65  # 65% after opex
        debt_service = price * 0.75 * 0.05  # 75% LTV, 5% rate
        dscr = noi / debt_service
        solver.Add(dscr >= 1.25)

    # 3. Cash constraints
    down_payment = price * (1 - tenant_policy.max_ltv)
    solver.Add(down_payment + earnest <= tenant_policy.available_cash)

    # 4. Hazard caps
    if property.flood_zone in ['A', 'AE', 'V']:
        solver.Add(price <= property.arv * 0.90)  # 10% discount for flood

    # 5. Regime constraints
    regime_policy = regime_policies[market_regime]
    solver.Add(price <= property.list_price * regime_policy['max_offer_pct'])

    # Objective: Maximize utility

    # P(accept) model (logistic regression)
    p_accept = logistic_model.predict_proba([[
        price / property.list_price,
        earnest / price,
        dd_days,
        close_days,
        inspection_contingency,
        financing_contingency,
        appraisal_contingency,
        repair_credit,
        escalation_clause,
        property.dom,
        market_regime_idx
    ]])[0][1]

    expected_profit = profit * p_accept
    time_penalty = close_days * tenant_policy.time_penalty
    risk_penalty = property.risk_score * tenant_policy.risk_aversion

    utility = (
        tenant_policy.alpha * p_accept +
        tenant_policy.beta * expected_profit -
        tenant_policy.gamma * time_penalty -
        tenant_policy.delta * risk_penalty
    )

    solver.Maximize(utility)

    # Solve
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        return {
            'price': price.solution_value(),
            'earnest': earnest.solution_value(),
            'dd_days': int(dd_days.solution_value()),
            'close_days': int(close_days.solution_value()),
            'contingencies': {
                'inspection': bool(inspection_contingency.solution_value()),
                'financing': bool(financing_contingency.solution_value()),
                'appraisal': bool(appraisal_contingency.solution_value())
            },
            'repair_credit': repair_credit.solution_value(),
            'escalation_clause': bool(escalation_clause.solution_value()),
            'expected_utility': solver.Objective().Value(),
            'p_accept': p_accept,
            'expected_profit': expected_profit
        }
    else:
        raise Exception("No feasible offer found")
```

**Pareto Frontier (NSGA-II)**:
```python
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

def generate_pareto_offers(property, tenant_policy):
    """Multi-objective optimization for Pareto frontier"""

    problem = OfferProblem(property, tenant_policy)

    algorithm = NSGA2(pop_size=100)

    res = minimize(
        problem,
        algorithm,
        ('n_gen', 200),
        verbose=False
    )

    # Return Pareto-optimal offers
    pareto_offers = []
    for x, f in zip(res.X, res.F):
        offer = decode_offer(x)
        offer['objectives'] = {
            'p_accept': -f[0],  # Negated because we minimized
            'expected_profit': -f[1],
            'time_to_close': f[2],
            'risk': f[3]
        }
        pareto_offers.append(offer)

    return pareto_offers
```

**Acceptance**:
- [ ] MIP optimizer works
- [ ] Constraints enforced (profit, DSCR, cash, hazard)
- [ ] Utility function maximized
- [ ] Pareto frontier generated
- [ ] UI shows optimal offer + alternatives
- [ ] What-if sliders respect constraints

---

### PR#24: Negotiation Brain
**Objective**: Email classification + policy engine + send-time optimization

**Implementation**:
```
ml/negotiation/
├── reply_classifier.py
├── policy_engine.py
├── send_time_optimizer.py
└── sequence_selector.py

api/app/routers/
└── negotiation.py
```

**Reply Classification**:
```python
from transformers import pipeline

classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")

def classify_reply(email_body):
    """Classify seller reply intent"""

    result = classifier(email_body)[0]

    # Custom rules for RE-specific intents
    if 'interested' in email_body.lower() or 'tell me more' in email_body.lower():
        return 'positive'
    elif 'not interested' in email_body.lower() or 'remove me' in email_body.lower():
        return 'negative'
    elif 'counter' in email_body.lower() or '$' in email_body:
        return 'counter_offer'
    elif '?' in email_body:
        return 'question'
    else:
        return result['label'].lower()
```

**Policy Engine**:
```python
def check_send_policy(contact, template, tenant):
    """Policy checks before sending"""

    violations = []

    # 1. Suppression list
    if contact.suppressed:
        violations.append("contact_suppressed")

    # 2. Quiet hours
    recipient_tz = contact.timezone or 'America/Los_Angeles'
    local_time = datetime.now(pytz.timezone(recipient_tz))
    if local_time.hour < 9 or local_time.hour >= 21:
        violations.append("quiet_hours")

    # 3. Frequency cap
    recent_sends = db.query(OutreachEvent).filter(
        OutreachEvent.contact_id == contact.id,
        OutreachEvent.sent_at >= now() - timedelta(days=7)
    ).count()

    if recent_sends >= tenant.max_emails_per_week:
        violations.append("frequency_cap")

    # 4. Deliverability health
    if contact.bounce_count >= 3:
        violations.append("high_bounce_rate")

    if contact.complaint_count >= 1:
        violations.append("spam_complaint")

    # 5. Template lint
    spam_score = calculate_spam_score(template.body)
    if spam_score > 0.7:
        violations.append("high_spam_score")

    # 6. DMARC/SPF
    if not verify_dmarc(tenant.sending_domain):
        violations.append("dmarc_failure")

    return {
        'allowed': len(violations) == 0,
        'violations': violations
    }
```

**Send-Time Optimization (Thompson Sampling)**:
```python
class SendTimeOptimizer:
    def __init__(self):
        # Beta distributions for each hour
        self.hour_alphas = [1] * 24
        self.hour_betas = [1] * 24

    def select_send_hour(self):
        """Thompson Sampling to find best send hour"""
        samples = [
            np.random.beta(self.hour_alphas[h], self.hour_betas[h])
            for h in range(9, 21)  # 9am - 9pm
        ]
        return 9 + np.argmax(samples)

    def update(self, hour, reply_received):
        """Update beliefs based on outcome"""
        if reply_received:
            self.hour_alphas[hour] += 1
        else:
            self.hour_betas[hour] += 1
```

**Sequence Selection (Contextual Bandits)**:
```python
from vowpalwabbit import pywrapper as vw

class SequenceSelector:
    def __init__(self):
        self.vw_model = vw.vw("--cb_explore_adf --epsilon 0.1")

    def select_sequence(self, contact, property):
        """Select email sequence variant"""

        # Context features
        context = {
            'contact_age': contact.age or 50,
            'property_price': property.list_price,
            'market': property.market,
            'asset_type': property.asset_type,
            'dom': property.dom
        }

        # Available sequences (arms)
        sequences = [
            'soft_intro',  # Friendly, low-pressure
            'data_driven',  # Market insights, charts
            'urgency',      # Time-sensitive, scarcity
            'social_proof'  # Testimonials, case studies
        ]

        # Select via contextual bandit
        chosen_sequence = self.vw_model.predict(context, sequences)

        return chosen_sequence

    def update(self, context, sequence, reward):
        """Update model with outcome"""
        # reward = 1 if positive reply, 0 otherwise
        self.vw_model.learn(context, sequence, reward)
```

**Acceptance**:
- [ ] Reply classification works
- [ ] Policy engine blocks violations
- [ ] Send-time optimization learns from data
- [ ] Sequence selection improves over time
- [ ] Dashboard shows send metrics
- [ ] Trust ledger logs all sends

---

## Phase 3: UI & Advanced Features

### PR#25-30: UI Performance Pack
- deck.gl map layers
- TanStack virtualized tables
- React Flow pipeline visualizer
- Stacking plans UI
- Hazard overlay toggles
- Explainability panels (already in PR#17)

### PR#31-35: Advanced API Surfaces
- `/properties/search` with facets + polygon + vector
- `/ownership/{id}` with entity graph
- `/offer/optimize` endpoint
- `/regime/current` endpoint
- `/trust_ledger/export`

### PR#36-40: SaaS & Ops
- Stripe usage meters
- Quota enforcement
- Cost dashboards
- DR drills
- Chaos testing

---

## Acceptance Criteria (Global)

### Security
- [x] 100% endpoints gated (JWT)
- [ ] OIDC SSO via Keycloak
- [ ] DSAR/export/delete e2e tests
- [ ] SBOM + signed images
- [ ] Vault/SOPS for secrets

### Quality
- [ ] GX coverage ≥90%
- [ ] Lineage coverage 100%
- [ ] Drift monitoring live
- [ ] Model cards for all models

### Reliability
- [ ] SLOs met 30 days staging
- [ ] 2 DR drills/quarter
- [ ] 1 chaos scenario/month

### Performance
- [ ] Provenance cache hit ≥80%
- [ ] Filtered ANN p95 <80ms @ 10M
- [ ] API p95 <250ms

### Actionability
- [ ] Select→offer <5min
- [ ] Counterfactual usefulness ≥80%
- [ ] Reply rate +30% with negotiation brain

### Parity
- [x] MF/CRE stacking (basic)
- [ ] Lease search live
- [x] Hazard overlays (basic)
- [x] Ownership alternates (basic)

---

## Next Steps

**Immediate (This Session)**:
1. PR#13: Great Expectations integration
2. PR#14: Keycloak OIDC
3. PR#15: Feast feature store
4. PR#16: libpostal + enhanced PostGIS

**Short-term (Next Session)**:
5. PR#17-19: ML enhancements
6. PR#20-21: Valuation logic
7. PR#22-24: Optimization & negotiation

**Long-term**:
- UI performance pack
- Stripe billing
- Full SaaS readiness
- Production deployment

---

**Status**: Starting PR#13 (Great Expectations)
**Branch**: `claude/systematic-phase-work-011CUhTfsuprpo5BVihNuVQj`
