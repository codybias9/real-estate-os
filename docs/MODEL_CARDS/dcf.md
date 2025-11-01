# Model Card: DCF Valuation Engine

**Model Name**: DCF (Discounted Cash Flow) Valuation
**Version**: 1.0.0
**Last Updated**: 2025-11-01
**Owner**: Finance/Analytics Team
**Status**: ⚠️ PRE-PRODUCTION (Requires golden test validation)

---

## Model Details

### Model Type
Deterministic financial model with optional Monte Carlo simulation

### Components
1. **DCF Core Engine**: NPV, IRR, DSCR calculations for 1-30 year projections
2. **Multi-Family (MF) Valuation**: Unit-mix modeling with rent roll analysis
3. **Commercial (CRE) Valuation**: Lease-by-lease modeling with TI/LC reserves
4. **Scenario Analysis**: Monte Carlo simulation with 10,000+ runs

### Framework & Dependencies
- **Core**: NumPy, SciPy (newton for IRR)
- **Data**: Pandas for cash flow tables
- **Optimization**: None (deterministic calculations)

### Model Location
- **Code**:
  - `ml/valuation/dcf_engine.py` (700+ LOC)
  - `ml/valuation/mf_valuation.py` (500+ LOC)
  - `ml/valuation/cre_valuation.py` (600+ LOC)
  - `ml/valuation/scenario_analysis.py` (500+ LOC)
- **Serving**: FastAPI endpoints `/valuation/mf/value`, `/valuation/cre/value`

---

## Intended Use

### Primary Use Cases

**Multi-Family (MF)**:
- Underwriting apartment acquisitions
- Portfolio valuation for lenders
- Investment committee approval

**Commercial (CRE)**:
- Office, retail, industrial property analysis
- Lease rollover risk assessment
- Tenant concentration analysis

### Users
- Acquisitions team evaluating deals
- Asset managers monitoring portfolio performance
- Lenders underwriting commercial loans
- Investors conducting due diligence

### Geographic Scope
- **US Markets**: All markets
- **International**: Formula-based, market parameters must be adjusted

### Asset Types

**Supported**:
- Multi-family (5+ units)
- Office (Class A, B, C)
- Retail (anchored, strip, lifestyle centers)
- Industrial (warehouse, distribution, flex)

**Out of Scope**:
- Single-family residential (use Comp-Critic instead)
- Land (no income stream)
- Development projects (different cash flow pattern)

---

## Model Inputs

### Multi-Family Required Inputs

**Property Attributes**:
- `total_units`: Number of units
- `total_sf`: Total rentable square feet
- `year_built`: Construction year
- `unit_mix`: List of {unit_type, count, avg_sf, market_rent, current_rent}

**Financial Assumptions**:
- `gross_potential_rent`: Annual GPR at market rents
- `vacancy_rate`: Physical + economic vacancy (default: 5%)
- `other_income`: Parking, laundry, pet fees
- `annual_opex`: Operating expenses per SF or % of EGI
- `replacement_reserve_per_unit`: CapEx reserve (default: $250/unit/year)

**Market/Scenario**:
- `rent_growth_annual`: Expected rent growth (default: 3%)
- `expense_growth_annual`: Expense inflation (default: 2.5%)
- `holding_period_years`: Investment horizon (default: 10)
- `exit_cap_rate`: Terminal cap rate (default: 5.5%)

**Financing**:
- `loan_to_value`: LTV ratio (default: 70%)
- `interest_rate`: Annual loan rate (default: 5.5%)
- `amortization_years`: Loan term (default: 30)
- `interest_only_years`: IO period (default: 0)

### Commercial Required Inputs

**Property Attributes**:
- `property_type`: Office, retail, industrial, flex
- `total_sf`: Total rentable SF
- `leases`: List of lease contracts with:
  - Tenant name, credit rating
  - Leased SF, lease term, expiration date
  - Base rent per SF, escalations
  - Renewal probability

**Financial Assumptions**:
- `annual_opex_psf`: Operating expenses per SF
- `ti_reserve_per_sf`: Tenant improvement reserve (varies by type)
- `lc_reserve_per_sf`: Leasing commission reserve

**Default TI/LC by Property Type**:
| Type | TI ($/SF) | LC (% of 1st year rent) |
|------|-----------|-------------------------|
| Office | $40 | 6% |
| Retail | $25 | 8% |
| Industrial | $10 | 4% |
| Flex | $15 | 5% |

---

## Model Outputs

### DCF Result Object

**Valuation Metrics**:
- `npv`: Net Present Value of equity cash flows
- `irr`: Internal Rate of Return (equity IRR)
- `equity_multiple`: Total distributed / total invested
- `direct_cap_value`: Stabilized NOI / market cap rate

**Debt Metrics**:
- `avg_dscr`: Average Debt Service Coverage Ratio
- `min_dscr`: Minimum DSCR (typically Year 1)
- `loan_amount`: Total debt

**Cash Flows**:
- `cash_flows`: List of annual CashFlowPeriod objects with:
  - Revenue (GPR, vacancy, concessions, other income, EGI)
  - Expenses (OpEx, taxes, insurance, management, reserves)
  - NOI
  - Debt service (interest, principal)
  - Cash flow before tax (CFBT)
  - Exit proceeds (final year only)
  - DSCR, DCCR

**Scenario Analysis** (if enabled):
- `npv_distribution`: Array of NPV values from Monte Carlo
- `irr_distribution`: Array of IRR values
- `npv_percentiles`: {5th, 25th, 50th, 75th, 95th}
- `npv_var_95`: Value at Risk (5th percentile)
- `npv_cvar_95`: Conditional VaR (expected loss beyond VaR)
- `sensitivity_analysis`: DataFrame ranking variable importance

---

## Calculations & Formulas

### NPV (Net Present Value)

```
NPV = Σ[t=1 to n] (CFBT_t + ExitProceeds_t) / (1 + r)^t - InitialEquity
```

Where:
- `CFBT_t` = Cash flow before tax in year t
- `r` = Discount rate (required equity return)
- `InitialEquity` = Purchase price × (1 - LTV)

### IRR (Internal Rate of Return)

Solve for `r` where NPV = 0:
```
0 = Σ[t=0 to n] CashFlow_t / (1 + r)^t
```

Uses Newton's method with fallback to bisection search.

### DSCR (Debt Service Coverage Ratio)

```
DSCR = NOI / DebtService

Where:
- NOI = EGI - OpEx - Reserves
- DebtService = Annual loan payment (P&I)

Lender requirement: DSCR ≥ 1.25 (often required)
```

### Debt Service Calculation

**Fully Amortizing**:
```
Payment = Principal × [r(1+r)^n] / [(1+r)^n - 1]

Where:
- r = Annual interest rate
- n = Amortization period (years)
```

**Interest-Only**:
```
Payment = Principal × r  (for IO period)
Then switches to amortizing payment
```

### Exit Value

```
ExitValue = NOI_final / ExitCapRate
ExitProceeds = ExitValue - SellingCosts - RemainingLoanBalance
```

---

## Performance

### Accuracy Validation

⚠️ **Requires golden test suite** - Planned validations:

**Deterministic Tests**:
1. Known property inputs → Expected NPV/IRR (within 0.1% tolerance)
2. Zero NPV case → IRR should equal discount rate
3. Interest-only loan → Principal balance unchanged during IO period
4. No debt case → CFBT should equal NOI

**Edge Cases**:
1. Very high LTV (95%) → DSCR should be low
2. Negative NOI → IRR should be negative
3. Short holding period (1 year) → Limited compounding
4. Long holding period (30 years) → Full amortization

### Performance Benchmarks

| Operation | Target | Notes |
|-----------|--------|-------|
| MF DCF (10 years) | <100ms | Deterministic calculation |
| CRE DCF (10 years) | <150ms | Lease-by-lease complexity |
| Monte Carlo (10K runs) | <5s | Async pathway |
| API Mode (p95) | <500ms | Deterministic only |

### Comparison with Industry Tools

**vs. ARGUS Enterprise**:
- Faster for standard cases
- Fewer customization options
- Transparent formulas (no black box)

**vs. Excel Pro Formas**:
- More consistent (no formula errors)
- Automated scenario analysis
- API-driven (programmatic access)

---

## Uncertainty & Confidence

### Sources of Uncertainty

**Input Uncertainty**:
1. **Rent Growth**: Market-dependent, cyclical (±2% variance typical)
2. **Expense Growth**: Inflation-linked (±1% variance)
3. **Vacancy**: Market-specific, tenant quality (±3% variance)
4. **Exit Cap Rate**: Most sensitive variable (±0.5% = ±10% value change)

**Model Uncertainty**:
1. **Discount Rate**: Subjective (risk-adjusted required return)
2. **Holding Period**: Actual hold may differ from plan
3. **Lease Renewals**: Actual renewal rates vary from assumptions
4. **CapEx**: Replacement reserves may be insufficient

### Sensitivity Analysis

**Tornado Chart Variables** (rank ordered by impact):
1. Exit cap rate (highest impact)
2. Rent growth rate
3. Vacancy rate
4. Discount rate
5. Expense growth rate

**Rule of Thumb Sensitivities** (10-year hold, 70% LTV):
- 0.5% exit cap rate change → ±8-12% NPV change
- 1% rent growth change → ±5-8% NPV change
- 2% vacancy change → ±3-5% NPV change

### Monte Carlo Confidence Intervals

With 10,000 simulations:
- **95% CI for NPV**: [5th percentile, 95th percentile]
- **Probability of Positive NPV**: % of simulations with NPV > 0
- **Downside Risk (CVaR)**: Expected loss in worst 5% of scenarios

---

## Limitations & Caveats

### Assumptions & Simplifications

1. **No Taxes**: Model calculates before-tax cash flows
   - Actual returns depend on investor tax situation
   - Should add tax module for after-tax analysis

2. **No Disposition Costs**: Only selling costs (2%) modeled
   - Actual: legal, environmental reports, prepayment penalties

3. **Straight-Line Growth**: Rent/expense grow at constant rates
   - Reality: Lumpy, market-driven, non-linear

4. **Perfect Foresight**: Exit cap rate known in advance
   - Reality: High uncertainty 10 years out

5. **No Operational Events**: Assumes smooth operations
   - Reality: Major repairs, tenant bankruptcies, disasters

6. **CRE Simplifications**:
   - Fixed renewal probability (reality: tenant-specific)
   - Average TI/LC (reality: lease-specific negotiations)
   - No free rent periods modeled explicitly

### Known Failure Modes

1. **High Leverage (LTV >85%)**: DSCR warnings may not be severe enough
2. **Distressed Assets**: Turnaround CapEx not modeled
3. **Development**: Cannot model construction period cash flows
4. **Value-Add**: Renovation costs/timing not explicitly modeled
5. **Negative Leverage**: If cap rate > interest rate, debt hurts returns

### Scenario Analysis Limitations

1. **Correlation Not Modeled**: Rent growth and cap rates are correlated (boom/bust)
2. **Fat Tails**: Monte Carlo assumes normal distributions (reality: Black Swans)
3. **Regime Changes**: Cannot model structural market shifts
4. **Seed Dependency**: Results vary slightly with random seed

---

## Monitoring

### Real-Time Metrics

**Per Request**:
- `dcf_calculation_latency_ms`: Total time for DCF
- `monte_carlo_runs_completed`: For MC mode
- `irr_convergence_iterations`: Newton's method iterations

### Daily Aggregates

- `avg_irr_calculated`: Track typical IRR range
- `pct_negative_npv`: % of valuations with NPV < 0
- `pct_dscr_violations`: % with min DSCR < 1.25
- `avg_monte_carlo_latency`: MC performance tracking

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| API latency p95 | >500ms | >1000ms |
| MC latency p95 | >5s | >10s |
| IRR non-convergence | >1% | >5% |
| Negative NPV rate | >50% | >80% |

### Drift Detection

**Input Drift**:
- Monitor distribution of input parameters
- Alert if median exit cap rate shifts >0.5%
- Alert if median LTV shifts >10%

**Output Drift**:
- Track IRR distribution over time
- Detect if median shifts (market regime change)
- Cross-check with market indices

---

## Deployment

### Canary Plan

**Phase 1: Shadow Mode (1 week)**
- Run DCF alongside legacy Excel models
- Compare outputs for sample properties
- Success: <5% difference in NPV for 95% of cases

**Phase 2: Parallel Validation (2 weeks)**
- Acquisitions team uses both systems
- Flag large discrepancies for review
- Success: Team confident in DCF accuracy

**Phase 3: Primary System (ongoing)**
- DCF becomes primary, Excel for cross-check
- Excel deprecated after 3 months of parallel use

### Rollback Triggers

**Automatic**:
- Error rate >1% (should be near-zero for deterministic)
- p95 latency >1000ms

**Manual**:
- Systematic differences vs validated Excel models
- Regulatory/audit concerns
- Team discomfort with outputs

### Golden Test Suite

**Required Before Production**:
```python
def test_mf_dcf_golden():
    """100-unit property, known inputs → expected outputs"""
    result = value_mf_property(GOLDEN_MF_INPUT)
    assert abs(result.npv - EXPECTED_NPV) < 0.001 * EXPECTED_NPV
    assert abs(result.irr - EXPECTED_IRR) < 0.0001
    assert abs(result.min_dscr - EXPECTED_DSCR) < 0.01

def test_cre_dcf_golden():
    """Office building, 5 leases → expected cash flows"""
    result = value_cre_property(GOLDEN_CRE_INPUT)
    # Validate every year's cash flow
    for year, expected in EXPECTED_CASHFLOWS:
        assert abs(result.cash_flows[year].noi - expected.noi) < 100

def test_dcf_zero_npv():
    """IRR should equal discount rate when NPV = 0"""
    # Construct inputs where NPV ≈ 0
    result = value_mf_property(...)
    assert abs(result.irr - result.assumptions.discount_rate) < 0.001
```

---

## Future Improvements

### Short-term (3 months)
1. **Golden Test Suite**: Create 20+ validated test cases
2. **Tax Module**: Add federal/state tax calculations
3. **Waterfall Output**: Visual breakdown of cash flow components
4. **Sensitivity UI**: Interactive tornado charts

### Medium-term (6 months)
1. **Value-Add Modeling**: Renovation costs and staging
2. **Refinance Analysis**: Optimal refi timing
3. **Lease-Specific TI/LC**: CRE model per-lease costs
4. **Stochastic Cap Rates**: Exit cap rate distribution

### Long-term (12 months)
1. **Portfolio DCF**: Aggregate 100+ properties
2. **Real Options**: Flexibility to change strategy
3. **Market Integration**: Auto-pull rent growth from regime model
4. **Comparison API**: Side-by-side scenario comparison

---

## References

- **Implementation**: See `/ml/valuation/` directory
- **Textbooks**:
  - "Real Estate Finance & Investments" by Brueggeman & Fisher
  - "Valuing Real Estate Investments Using Discounted Cash Flow" by Greer & Kolbe
- **Industry Standards**:
  - Appraisal Institute: "The Appraisal of Real Estate"
  - NCREIF Property Index methodology

---

## Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-11-01 | Initial DCF engine and model card | Platform Engineering |

---

## Approval Status

- [ ] **Finance Lead**: Formula validation complete
- [ ] **Product**: Use cases confirmed
- [ ] **Legal**: Disclaimer language approved
- [ ] **Security**: Data privacy review
- [ ] **Acquisitions Team**: Parallel testing passed

**Status**: ⚠️ DRAFT - Pending golden test validation
