# Model Card: DCF Engine (MF/CRE)

**Model**: DCF Engine
**Version**: 1.0.0
**Owner**: ML Team

## Overview
Discounted Cash Flow engine for multifamily and commercial real estate valuation with unit-mix modeling, lease-by-lease analysis, and Monte Carlo simulation.

## Intended Use
- Investment underwriting for MF/CRE properties
- Hold period analysis (5-30 years)
- Sensitivity analysis via Monte Carlo

## Model Architecture
- **Multifamily**: Unit-mix based, vacancy modeling, operating expense ratios
- **Commercial**: Lease-by-lease, renewal probabilities, TI/LC reserves
- **Financial**: IO periods, amortization, exit cap scenarios

## Performance
- **API Mode**: p95 < 500ms (target: 500ms) ✅
- **Monte Carlo (1000 scenarios)**: ~15-20 seconds
- **Accuracy**: Validated against 50 real deals, IRR within ±2pp

## Monitoring
- Latency alerts (p95 > 750ms)
- Error rate (<0.1%)
- Input validation failures

## Canary Plan
- 10% → 50% → 100% over 3 weeks
- Rollback if calculation errors detected

**Last Review**: 2024-11-02
