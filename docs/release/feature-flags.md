# Feature Flag Strategy

## Overview
Feature flags enable safe, gradual rollouts and instant rollbacks.

## Flag Types

### 1. Release Flags
- **Purpose**: Gradual rollout of new features
- **Lifetime**: Temporary (removed after full rollout)
- **Example**: `comp_critic_v2_rollout`

### 2. Operational Flags
- **Purpose**: Emergency kill switches
- **Lifetime**: Permanent
- **Example**: `enable_ml_predictions` (fallback to simple heuristics)

### 3. Permission Flags
- **Purpose**: Access control for beta features
- **Lifetime**: Permanent
- **Example**: `enable_advanced_analytics` (for enterprise tier)

## Rollout Strategy

### Cohort-Based Rollout
- **10% cohort**: Internal users + friendly customers (1 week)
- **50% cohort**: Expanded user base (1 week)
- **100% rollout**: All users

### Ring-Based Rollout
- **Ring 0**: Dev/staging environments
- **Ring 1**: Internal production (employees only)
- **Ring 2**: Early adopter customers
- **Ring 3**: General availability

## Flag Naming Convention
- Format: `[component]_[feature]_[version]`
- Examples:
  - `comp_critic_v2_rollout`
  - `regime_monitor_enable`
  - `dcf_monte_carlo_available`

## Implementation
```python
from feature_flags import FeatureFlags

flags = FeatureFlags()

if flags.is_enabled("comp_critic_v2", user_id=user_id):
    result = comp_critic_v2.value_property(property_data)
else:
    result = comp_critic_v1.value_property(property_data)
```

## Monitoring
- Track flag evaluation counts (by flag, by value)
- Alert on unusual patterns (sudden drop to 0% or spike to 100%)
- Dashboard: Flag usage, rollout progress

## Cleanup
- Review all release flags quarterly
- Remove flags after successful 100% rollout (30 days stable)
- Archive flag history for auditing
