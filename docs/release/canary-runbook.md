# Canary Deployment Runbook

## Overview
Canary deployments allow gradual rollout of new model versions with automatic rollback on failure.

## General Canary Process

### Phase 1: 10% Cohort (Week 1)
1. Deploy new model version alongside old version
2. Configure feature flag: `model_name_v2.rollout_percentage = 10`
3. Monitor for 7 days:
   - Model quality metrics (MAE, accuracy, etc.)
   - Latency (p95, p99)
   - Error rate
   - User feedback

**Success Criteria**:
- Quality degradation <5%
- Latency within SLO
- Error rate <0.1%
- No critical user complaints

**Rollback Triggers**:
- Quality degradation >15%
- Latency p95 exceeds SLO by 50%
- Error rate >0.5%
- Critical bug detected

### Phase 2: 50% Cohort (Week 2)
1. Increase feature flag: `model_name_v2.rollout_percentage = 50`
2. Monitor for 7 days
3. Same success criteria as Phase 1

### Phase 3: 100% Rollout (Week 3)
1. Set feature flag: `model_name_v2.rollout_percentage = 100`
2. Monitor for 14 days
3. Keep old model as fallback
4. After 14 days of stability, retire old model

## Rollback Procedure

### Immediate Rollback (P0 Issue)
```bash
# 1. Set feature flag to 0%
feature_flags.set("model_name_v2", rollout_percentage=0)

# 2. Verify traffic routing to old model
curl http://api/internal/model-version
# Should return: {"model": "model_name_v1"}

# 3. Monitor for 15 minutes
# Check: Error rate drops, latency improves, quality stable

# 4. Post in #incidents
# "Rolled back model_name to v1 due to [reason]. Investigating."

# 5. Create incident ticket
```

### Gradual Rollback (Non-Critical Issue)
```bash
# Reduce gradually: 50% → 25% → 10% → 0%
# Monitor at each step (30 min)
```

## Feature Flag Management

### LaunchDarkly (or similar)
```python
import launchdarkly as ld

client = ld.Client(sdk_key=os.getenv("LD_SDK_KEY"))
user = {"key": request_id}

rollout_pct = client.variation("model_name_v2_rollout", user, default=0)

if random.random() * 100 < rollout_pct:
    model = load_model("model_name_v2")
else:
    model = load_model("model_name_v1")
```

## Model-Specific Canary Plans

See individual Model Cards for specific rollout criteria and rollback triggers:
- [Comp-Critic](../MODEL_CARDS/comp-critic.md)
- [DCF Engine](../MODEL_CARDS/dcf-engine.md)
- [Regime Monitor](../MODEL_CARDS/regime-monitor.md)
- [Negotiation Brain](../MODEL_CARDS/negotiation-brain.md)

## Post-Rollout Tasks
- [ ] Document lessons learned
- [ ] Update model card with production metrics
- [ ] Remove old model after 30 days of stability
- [ ] Archive old model artifacts
