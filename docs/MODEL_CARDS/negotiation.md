# Model Card: Negotiation Brain

**Model Name**: Negotiation Brain
**Version**: 1.0.0
**Last Updated**: 2025-11-01
**Owner**: Outreach / ML Team
**Status**: ⚠️ PRE-PRODUCTION (Requires evaluation and compliance audit)

---

## Model Details

### Model Type
Composite system with rule-based NLP, Thompson Sampling bandits, and policy enforcement

### Components
1. **Reply Classifier**: Rule-based NLP for intent detection (8 intent classes)
2. **Contact Policy Engine**: Compliance rules enforcement (TCPA, quiet hours, frequency caps)
3. **Send-Time Optimizer**: Thompson Sampling bandit (24 arms = hours of day)
4. **Template Selector**: Thompson Sampling bandit (N arms = N templates)
5. **Sequence Selector**: Contextual bandit with linear models (3 sequences)

### Framework & Dependencies
- **NLP**: Regex-based pattern matching (no external dependencies)
- **Bandits**: NumPy, SciPy (Beta distributions, multivariate normal sampling)
- **Policy**: pytz for timezone handling
- **Orchestration**: Airflow DAG for hourly processing
- **Storage**: Postgres for conversation state, Redis for real-time lookups

### Model Location
- **Code**:
  - `ml/negotiation/reply_classifier.py` (425 LOC)
  - `ml/negotiation/contact_policy.py` (519 LOC)
  - `ml/negotiation/bandits.py` (562 LOC)
- **DAG**: `dags/negotiation/intelligent_outreach_dag.py`
- **API**: `/negotiation/classify-reply`, `/negotiation/select-send-time`, `/negotiation/select-template`, `/negotiation/select-sequence`

---

## Intended Use

### Primary Use Cases
- **Reply Classification**: Automatically classify seller replies (interested, not interested, counter offer, etc.)
- **Send-Time Optimization**: Learn optimal hours to send messages (maximize reply rates)
- **Message Selection**: Select best-performing templates and sequences
- **Compliance**: Enforce TCPA, quiet hours, frequency caps, DNC lists

### Users
- Outreach team for lead nurturing
- Acquisitions team for seller engagement
- Compliance team for policy enforcement
- Marketing team for campaign optimization

### Geographic Scope
- **Coverage**: All US markets (timezone-aware)
- **Timezones**: Respects lead's local timezone for quiet hours
- **Compliance**: TCPA-compliant for SMS/phone (opt-in required)

---

## Model Inputs

### Reply Classifier Inputs

**Message Text** (string):
- Seller's reply message
- Length: 1-5000 characters
- Language: English (primary)

**Context** (optional):
- `lead_id`: Lead identifier
- `property_id`: Property identifier
- Previous conversation history

### Send-Time Optimizer Inputs

**Historical Outcomes**:
- `send_hour`: Hour when message was sent (0-23)
- `replied`: Boolean (did lead reply?)
- Minimum 100+ sends per hour for stable estimates

### Template Selector Inputs

**Template Pool**:
- List of template IDs
- Minimum 3 templates recommended
- Historical reply rates per template

### Sequence Selector Inputs

**Context Features** (12 dimensions):
- `lead_responded_before`: Boolean
- `lead_interest_score`: 0-1 (engagement level)
- `days_since_last_contact`: Integer
- `property_type`: String (sfr, mf, cre, land)
- `price_range`: String (low, medium, high)
- `market_regime`: String (hot, warm, cool, cold)
- `day_of_week`: 0-6 (Monday=0)
- `is_weekend`: Boolean

### Contact Policy Inputs

**Lead Profile**:
- `lead_id`: Identifier
- `timezone`: IANA timezone (e.g., "America/New_York")
- `opted_out`: Boolean
- `on_dnc_registry`: Boolean
- Contact history (last contact time, total contacts)

**Channel**:
- EMAIL, SMS, PHONE, DIRECT_MAIL

---

## Model Outputs

### Reply Classification

**8 Intent Classes**:
1. **INTERESTED** (confidence ≥0.85): "yes", "interested", "tell me more"
2. **NOT_INTERESTED** (confidence ≥0.90): "no thanks", "stop", "not selling"
3. **COUNTER_OFFER** (confidence ≥0.85): "$XXX", "what's your best offer"
4. **REQUEST_INFO** (confidence ≥0.75): "what", "tell me about", "more details"
5. **CALLBACK_LATER** (confidence ≥0.80): "call back later", "busy", "thinking about it"
6. **AUTO_REPLY** (confidence ≥0.95): "out of office", "automatic reply"
7. **IRRELEVANT** (confidence ≥0.70): Spam, wrong number
8. **UNKNOWN** (confidence ≤0.50): Cannot classify

**Extracted Entities**:
- Price amounts (e.g., "$250,000", "250k")
- Sentiment: positive, negative, neutral
- Urgency: high, medium, low
- Next action: schedule_call, send_info, archive, manual_review

### Send-Time Optimization

**Selected Hour**: 8-20 (8 AM - 8 PM)
**Best Hours** (top 3 with expected reply rates):
```json
[
  {"hour": 10, "expected_reply_rate": 0.15},
  {"hour": 14, "expected_reply_rate": 0.14},
  {"hour": 18, "expected_reply_rate": 0.13}
]
```

### Template Selection

**Selected Template ID**: String
**Template Performance**:
```json
[
  {
    "template_id": "T1",
    "pulls": 150,
    "successes": 20,
    "mean": 0.133,
    "confidence_interval_95": [0.08, 0.19]
  },
  ...
]
```

### Sequence Selection

**3 Sequence Types**:
- **aggressive**: 3 messages over 5 days (high interest leads)
- **standard**: 4 messages over 14 days (normal leads)
- **patient**: 5 messages over 30 days (low interest, high value)

**Expected Performance** (context-dependent):
```json
{
  "aggressive": 0.12,
  "standard": 0.18,
  "patient": 0.15
}
```

### Contact Policy Decision

**Outcome Codes**:
- `ALLOWED`: Contact permitted
- `BLOCKED_QUIET_HOURS`: 9 PM - 8 AM local time
- `BLOCKED_FREQUENCY_CAP`: <48 hours since last contact
- `BLOCKED_DNC`: On do-not-contact list
- `BLOCKED_OPT_OUT`: Lead opted out
- `BLOCKED_DAILY_LIMIT`: Max 100 contacts/day/user
- `BLOCKED_COMPLIANCE`: SMS/phone without opt-in

**Next Allowed Time**: ISO timestamp when contact becomes allowed

---

## Algorithms & Formulas

### Thompson Sampling (Send-Time & Templates)

**Beta-Bernoulli Conjugate Prior**:
```python
# Each arm has Beta distribution
alpha = successes + 1  # Prior: 1
beta = failures + 1    # Prior: 1

# Selection: Sample from each arm's posterior
sample_i = Beta(alpha_i, beta_i).sample()
selected_arm = argmax_i(sample_i)

# Update: Observed reward
if reward == 1:
    alpha += 1  # Success
else:
    beta += 1   # Failure

# Expected reward
E[reward] = alpha / (alpha + beta)
```

### Contextual Bandit (Sequence Selection)

**Bayesian Linear Regression**:
```python
# Each arm has linear model: E[reward | context] = context · theta
# Prior: theta ~ N(0, v * I)

# Precision matrix (inverse covariance)
A = I + Σ(x_i · x_i^T)  # Updated with each observation

# Weighted sum of rewards
b = Σ(reward_i · x_i)

# Posterior mean
theta_mean = A^(-1) · b

# Posterior covariance
theta_cov = v · A^(-1)

# Selection: Sample theta from posterior
theta_sample ~ N(theta_mean, theta_cov)
expected_reward = context · theta_sample
selected_arm = argmax(expected_reward)

# Update: Add new observation (x, reward)
A += x · x^T
b += reward · x
```

### Quiet Hours Check

**Timezone-Aware Enforcement**:
```python
# Convert to lead's local time
local_time = current_time.astimezone(pytz.timezone(lead_timezone))

# Check overnight quiet hours (21:00 - 08:00)
if quiet_start > quiet_end:  # Spans midnight
    blocked = (local_time.time() >= quiet_start) or (local_time.time() < quiet_end)
else:
    blocked = quiet_start <= local_time.time() < quiet_end

# If blocked, next allowed time = quiet_end
```

### Frequency Cap Check

**Minimum Hours Between Contacts**:
```python
hours_since_last = (now - last_contact_at).total_seconds() / 3600
blocked = hours_since_last < min_hours_between_contacts  # Default: 48h
```

---

## Performance

### Reply Classifier Accuracy

⚠️ **Requires Validation** - Expected performance:

**Precision/Recall by Intent** (on 1000+ manually labeled replies):
| Intent | Precision Target | Recall Target | Notes |
|--------|------------------|---------------|-------|
| INTERESTED | ≥0.80 | ≥0.85 | High recall critical (don't miss hot leads) |
| NOT_INTERESTED | ≥0.90 | ≥0.80 | High precision (don't false-reject) |
| COUNTER_OFFER | ≥0.85 | ≥0.80 | Price extraction accuracy ≥90% |
| REQUEST_INFO | ≥0.70 | ≥0.75 | Broader category |
| CALLBACK_LATER | ≥0.75 | ≥0.70 | Temporal entities |
| AUTO_REPLY | ≥0.95 | ≥0.90 | Easy to detect |

**Overall Accuracy**: ≥0.80

### Thompson Sampling Performance

**Send-Time Optimizer**:
- **Regret**: Sublinear O(log T) cumulative regret
- **Convergence**: ≥200 pulls per arm for stable estimates
- **Exploration**: First 50 pulls = uniform exploration
- **Expected Lift**: 15-30% reply rate improvement vs. random

**Template Selector**:
- **Convergence**: ≥100 pulls per template
- **Best Template Identification**: ≥90% probability after 500 total pulls
- **Expected Lift**: 10-20% reply rate improvement

### Contextual Bandit Performance

**Sequence Selector**:
- **Context Features**: 12-dimensional feature vector
- **Sample Efficiency**: ≥50 pulls per sequence for learning
- **Personalization Lift**: 5-15% conversion improvement vs. non-contextual
- **Regret**: O(√T) cumulative regret with high probability

### Contact Policy Compliance

**Enforcement Metrics**:
- **Quiet Hours Violations**: 0 (hard block)
- **Frequency Cap Violations**: 0 (hard block)
- **TCPA Compliance**: 100% (SMS/phone require explicit opt-in)
- **DNC Respect**: 100% (hard block)
- **Opt-Out Latency**: <1 second (real-time enforcement)

---

## Uncertainty & Confidence

### Sources of Uncertainty

**Reply Classifier**:
- **Pattern Coverage**: New slang, abbreviations, emojis
- **Context Sensitivity**: Same text, different meaning with context
- **Sarcasm**: "Oh great, another lowball offer"
- **Multi-Intent**: "Interested but need to talk to spouse" (interested + callback)

**Thompson Sampling**:
- **Cold Start**: First 50-100 pulls per arm have high uncertainty
- **Non-Stationarity**: Reply rates change over time (holidays, market shifts)
- **Sample Size**: Arms with <20 pulls have wide confidence intervals

**Contextual Bandit**:
- **Feature Engineering**: Missing important context (e.g., lead's FICO score)
- **Linear Model**: Assumes linear relationship (may not hold)
- **Exploration-Exploitation**: May over-explore early, missing short-term gains

### Confidence Indicators

**Classification Confidence**:
```python
# Confidence based on pattern matches
confidence = 0.95 if len(matched_patterns) >= 3 else 0.85
confidence = 0.70 if len(matched_patterns) == 1 else confidence
confidence = 0.50 if len(matched_patterns) == 0 else confidence

# Low confidence warning
if confidence < 0.70:
    next_action = "manual_review"
```

**Bandit Confidence Intervals**:
```python
# 95% CI for Beta distribution
lower, upper = stats.beta.ppf([0.025, 0.975], alpha, beta)

# CI width (uncertainty)
uncertainty = upper - lower

# Low confidence warning
if pulls < 50 or uncertainty > 0.3:
    log_warning("High uncertainty - needs more data")
```

---

## Limitations & Caveats

### Reply Classifier Limitations

**Rule-Based Approach**:
- No machine learning (no training on labeled data)
- Fixed patterns (doesn't adapt to new language)
- English-only (no multi-language support)
- No semantic understanding (misses paraphrases)

**Known Failure Modes**:
- **Ambiguity**: "Maybe" classified as UNKNOWN
- **Negation**: "Not not interested" (double negative)
- **Complex Sentences**: Long replies with multiple topics
- **Abbreviations**: "NFS" (not for sale) may miss
- **Emojis**: "👍" not recognized

**Mitigation**:
- Manual review queue for UNKNOWN intents
- Periodic pattern updates based on review queue
- Future: Train supervised classifier on labeled data

### Thompson Sampling Limitations

**Non-Stationarity**:
- Reply rates change over time
- Holidays, seasons affect send-time performance
- Market regime shifts (hot → cold)
- Solution: Add discount factor or sliding window

**Cold Start**:
- New templates need 50-100 pulls to converge
- Early performance may be suboptimal
- Solution: Warm-start with prior from similar templates

**Correlation Ignored**:
- Treats each arm independently
- Misses correlations (e.g., hour 9 similar to hour 10)
- Solution: Use Gaussian Process bandits for smooth functions

### Contextual Bandit Limitations

**Linear Model Assumption**:
- Assumes E[reward | x] = x · θ
- May miss non-linear interactions
- Solution: Add polynomial features or use neural bandits

**Feature Engineering**:
- Only 12 features (may miss important signals)
- Categorical features one-hot encoded (sparse)
- No automatic feature learning

**Sample Efficiency**:
- Requires ≥50 pulls per sequence for learning
- Context distribution must be diverse

### Contact Policy Limitations

**Timezone Accuracy**:
- Assumes timezone is correct
- No automatic timezone detection
- Daylight saving time transitions

**Compliance Gaps**:
- No integration with external DNC registries (manual)
- No real-time opt-out webhook
- No attorney/lawyer detection ("cease and desist")

**Rate Limiting**:
- Daily limits per user (no global limit)
- No rate limiting per campaign
- No burst protection

---

## Monitoring

### Real-Time Metrics

**Reply Classifier** (per intent, per hour):
- `classification_count`: Count of classifications
- `intent_distribution`: % of each intent
- `avg_confidence`: Average confidence score
- `manual_review_rate`: % sent to manual review

**Thompson Sampling** (per arm, per day):
- `arm_pulls`: Count of arm selections
- `arm_successes`: Count of successes (replies)
- `arm_mean_reward`: Expected reward (alpha / (alpha + beta))
- `arm_confidence_interval`: 95% CI width
- `regret`: Cumulative regret vs. best arm

**Contact Policy** (per day):
- `contact_attempts`: Total contact attempts
- `contact_allowed`: Allowed contacts
- `blocked_by_reason`: Count per blocking reason
- `opt_outs`: New opt-outs
- `policy_violations`: Count of violations (should be 0)

### Aggregated Metrics (Daily)

- `total_replies_classified`: Total count
- `reply_rate_by_hour`: Reply rate by hour (for send-time analysis)
- `reply_rate_by_template`: Reply rate by template
- `conversion_rate_by_sequence`: Conversion rate by sequence
- `policy_compliance_rate`: % of allowed contacts (should be 100% compliant)

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Classification confidence | <0.70 avg | <0.60 avg |
| Manual review rate | >30% | >50% |
| Reply rate drop | -20% vs. baseline | -40% vs. baseline |
| Thompson regret | >200 after 1000 pulls | >500 after 1000 pulls |
| Policy violations | >0 per day | >10 per day |
| Opt-out rate | >5% per campaign | >10% per campaign |

### Drift Detection

**Input Drift**:
- Monitor reply text statistics (length, vocabulary)
- Alert if median reply length shifts >50%
- Alert if new patterns emerge (>10% UNKNOWN)

**Output Drift**:
- Track intent distribution over time
- Baseline: 30% interested, 20% not interested, 15% counter, 20% info, 15% other
- Alert if deviates >10 percentage points

**Performance Drift**:
- Track reply rates by hour over 30-day rolling window
- Alert if best hour drops >20%
- Alert if worst hour becomes new best (regime shift)

---

## Deployment

### Canary Plan

**Phase 1: Shadow Mode (2 weeks)**
- Run classifier, don't change outreach
- Compare with manual classifications (sample 500 replies)
- Success: ≥80% agreement, <5% critical misclassifications

**Phase 2: Pilot Send-Time Optimization (2 weeks)**
- Apply send-time optimization to 10% of leads
- Compare reply rates vs. control (random times)
- Success: ≥10% lift in reply rate, no policy violations

**Phase 3: Full Rollout (1 month)**
- 10% → 25% → 50% → 100% of leads
- Enable template selection and sequence selection
- Monitor opt-out rates closely

**Phase 4: Continuous Learning**
- Daily updates to bandit models
- Weekly review of manual review queue
- Monthly retraining of pattern updates

### Rollback Triggers

**Automatic**:
- Reply rate drops >30% vs. baseline
- Policy violations >10 per day
- Opt-out rate >10% per campaign
- DAG failure rate >10%

**Manual**:
- Compliance team flags TCPA violations
- Outreach team disputes classifications
- Leads report spam/harassment

### Feature Flags

**Flag**: `negotiation.classifier.enabled`
- Default: False
- Gradual rollout by tenant

**Flag**: `negotiation.send_time_optimizer.enabled`
- Default: False
- Enable after 200+ sends per hour

**Flag**: `negotiation.contact_policy.strict_mode`
- Default: True (block all violations)
- False = log violations but allow (testing only)

---

## Future Improvements

### Short-term (3 months)
1. **Supervised Classifier**: Train BERT/RoBERTa on 5000+ labeled replies
2. **Price Extraction**: Improve counter-offer price extraction (regex → NER)
3. **Multi-Intent**: Support multiple intents per reply
4. **Evaluation Suite**: Create confusion matrix on 1000+ test set

### Medium-term (6 months)
1. **Contextual Send-Time**: Incorporate lead features (not just time)
2. **Neural Bandits**: Replace linear contextual bandits with neural networks
3. **Real-Time DNC**: Integrate with external DNC registries (API)
4. **Multi-Language**: Extend to Spanish (second most common)

### Long-term (12 months)
1. **Conversational AI**: Generate personalized reply content
2. **Sentiment Analysis**: Track sentiment trajectory across conversation
3. **Predictive Lead Scoring**: Forecast conversion probability
4. **Reinforcement Learning**: End-to-end RL for outreach strategy

---

## References

- **Thompson Sampling**: Russo et al. (2018) "Tutorial on Thompson Sampling"
- **Contextual Bandits**: Li et al. (2010) "Contextual-Bandit Approach to Personalized News Article Recommendation"
- **TCPA Compliance**: FCC TCPA Guidelines (47 CFR § 64.1200)
- **Implementation**: `ml/negotiation/` directory

---

## Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-11-01 | Initial negotiation brain system | Platform Engineering |

---

## Approval Status

- [ ] **Data Science Lead**: Classifier evaluation validated
- [ ] **Compliance Lead**: TCPA compliance confirmed
- [ ] **Outreach Lead**: Reply patterns reviewed
- [ ] **Product**: Use cases confirmed
- [ ] **Legal**: Opt-out mechanisms approved

**Status**: ⚠️ DRAFT - Pending classifier evaluation and compliance audit
