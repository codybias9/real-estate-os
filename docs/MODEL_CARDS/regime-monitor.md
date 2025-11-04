# Model Card: Regime Monitoring System

**Model**: Regime Monitor (BOCPD)
**Version**: 1.0.0
**Owner**: ML Team

## Overview
Bayesian Online Changepoint Detection for market regime classification (COLD/COOL/WARM/HOT) with policy generation.

## Intended Use
- Daily market regime classification for 100+ markets
- Investment policy adjustment
- Risk management

## Training Data
- Historical market data (2020-2024)
- 4 composite indicators: inventory, price trends, sales velocity, mortgage rates

## Performance
- **Regime Accuracy**: 82% on holdout (vs 68% baseline)
- **Changepoint Detection**: 78% precision, 71% recall
- **False Alarm Rate**: 12% (hysteresis reduces flapping)

## Model Architecture
- Composite index calculation (weighted 4 indicators)
- BOCPD with hazard rate = 0.05
- Hysteresis threshold = 0.15 to prevent rapid switching

## Monitoring
- Daily regime updates for top 100 markets
- Slack alerts on regime changes
- Quarterly backtest against actual market conditions

## Canary Plan
- Shadow mode for 2 weeks (compare to manual classification)
- 50% markets → 100% over 1 week

**Last Review**: 2024-11-02
