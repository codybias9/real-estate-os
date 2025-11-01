# Wave 3 Implementation Plan
## Comp-Critic + Negotiation Brain + Outreach Automation

**Goal**: Build intelligent systems for comp analysis, negotiation strategies, and automated outreach

---

## Wave 3.1: Comp-Critic - Adversarial Comp Analysis ⏳

### Overview
Comp-Critic uses adversarial analysis to identify over/undervalued properties by:
1. Finding similar properties (comps) using Qdrant
2. Analyzing price differentials
3. Computing negotiation leverage scores
4. Identifying market anomalies

### Components to Build

#### 1. Comp Analysis ML Model
**File**: `ml/models/comp_critic.py`
- **CompCriticAnalyzer** class:
  - Load similar properties from Qdrant
  - Compute price per sqft differentials
  - Identify overvalued (priced above comps)
  - Identify undervalued (priced below comps)
  - Calculate negotiation leverage score

**Features**:
- Price deviation analysis
- Market position scoring
- Negotiation leverage calculation
- Confidence intervals

#### 2. Comp Analysis Service
**File**: `ml/serving/comp_critic_service.py`
- FastAPI endpoints:
  - `POST /analyze/comp-critic` - Analyze property vs comps
  - `GET /analyze/{property_id}/leverage` - Get negotiation leverage
  - `GET /analyze/{property_id}/comps` - Get comparable properties

**Response**:
```json
{
  "property_id": "...",
  "market_position": "overvalued",
  "price_deviation_percent": 15.2,
  "negotiation_leverage": 0.85,
  "comps": [
    {
      "property_id": "...",
      "similarity_score": 0.92,
      "price_diff_percent": 12.5,
      "leverage_contribution": 0.3
    }
  ],
  "recommendations": [
    "Property is 15.2% overvalued based on 10 comparable properties",
    "Strong negotiation position - aim for 10-15% price reduction"
  ]
}
```

#### 3. Database Schema Updates
**File**: `db/migrations/XXX_add_comp_analysis_tables.py`

**New Tables**:
- `comp_analysis`:
  - id, property_id, tenant_id
  - market_position (overvalued/fairly_valued/undervalued)
  - price_deviation_percent
  - negotiation_leverage
  - num_comps_analyzed
  - analyzed_at, created_at

- `property_comp`:
  - id, property_id, comp_property_id, tenant_id
  - similarity_score
  - price_diff_percent
  - leverage_contribution
  - created_at

#### 4. API Integration
**File**: `api/app/routers/properties.py` (update)
- Add endpoints for comp analysis results
- `GET /properties/{id}/comp-analysis`
- `GET /properties/{id}/negotiation-leverage`

---

## Wave 3.2: Negotiation Brain - Recommendation Engine ⏳

### Overview
Negotiation Brain provides AI-powered recommendations for:
1. When to reach out
2. What messaging to use
3. Optimal offer strategies
4. Follow-up timing

### Components to Build

#### 1. Negotiation Strategy Model
**File**: `ml/models/negotiation_brain.py`
- **NegotiationBrain** class:
  - Input: Property data, comp analysis, owner info, market conditions
  - Output: Recommended strategy (aggressive/moderate/cautious)
  - Optimal offer range
  - Messaging tone recommendation
  - Timing recommendation

**Strategies**:
- **Aggressive**: High leverage, motivated seller
- **Moderate**: Balanced approach, typical market
- **Cautious**: Low leverage, competitive situation

#### 2. Offer Recommendation System
**File**: `ml/models/offer_recommendations.py`
- Calculate optimal offer range based on:
  - Comp analysis
  - Days on market
  - Owner motivation signals
  - Market conditions
  - User investment criteria

#### 3. Messaging Template Engine
**File**: `ml/utils/messaging_templates.py`
- Template categories:
  - Initial outreach
  - Follow-up
  - Offer presentation
  - Negotiation counter
- Personalization variables:
  - Owner name
  - Property address
  - Offer amount
  - Unique property features

#### 4. Negotiation Brain Service
**File**: `ml/serving/negotiation_brain_service.py`
- Endpoints:
  - `POST /negotiate/strategy` - Get negotiation strategy
  - `POST /negotiate/offer-range` - Calculate optimal offer
  - `POST /negotiate/messaging` - Generate personalized message

---

## Wave 3.3: Outreach Automation ⏳

### Overview
Automate email outreach with:
1. Sequence builder
2. Personalized messaging
3. Follow-up scheduling
4. Tracking and analytics

### Components to Build

#### 1. Email Outreach System
**File**: `outreach/email_service.py`
- Integration with email provider (SendGrid, Mailgun, etc.)
- Template rendering
- Personalization
- Sending queue

#### 2. Sequence Builder
**File**: `outreach/sequence_builder.py`
- Define multi-step sequences:
  - Day 0: Initial outreach
  - Day 3: Follow-up #1
  - Day 7: Follow-up #2
  - Day 14: Final follow-up
- Conditional logic (if replied, stop sequence)
- A/B testing support

#### 3. Database Schema
**File**: `db/migrations/XXX_add_outreach_tables.py`

**New Tables**:
- `outreach_sequence`:
  - id, name, description, tenant_id
  - steps (JSONB array)
  - active, created_at

- `outreach_campaign`:
  - id, property_id, owner_id, sequence_id, tenant_id
  - status (active/paused/completed)
  - current_step
  - started_at, completed_at

- `outreach_email`:
  - id, campaign_id, property_id, owner_id, tenant_id
  - subject, body, sent_at
  - opened_at, clicked_at, replied_at
  - status (pending/sent/delivered/opened/clicked/replied/bounced)

- `outreach_template`:
  - id, name, category, tenant_id
  - subject_template, body_template
  - variables (JSONB array)
  - created_at

#### 4. Outreach API
**File**: `api/app/routers/outreach.py`
- Endpoints:
  - `POST /outreach/sequences` - Create sequence
  - `GET /outreach/sequences` - List sequences
  - `POST /outreach/campaigns` - Start campaign
  - `GET /outreach/campaigns/{id}` - Campaign status
  - `POST /outreach/campaigns/{id}/pause` - Pause campaign
  - `GET /outreach/analytics` - Outreach analytics

#### 5. Outreach UI
**File**: `web/src/components/OutreachTab.tsx`
- Display outreach status for property
- Show email sequence progress
- Analytics dashboard (open rate, reply rate)
- Manual outreach trigger

---

## Implementation Priority

### Phase 1: Comp-Critic (Wave 3.1)
1. ✅ Create comp analysis model
2. ✅ Build comp analysis service
3. ✅ Add database tables
4. ✅ Integrate with API
5. ✅ Create UI component

### Phase 2: Negotiation Brain (Wave 3.2)
1. ✅ Build strategy model
2. ✅ Implement offer calculator
3. ✅ Create messaging templates
4. ✅ Build negotiation service
5. ✅ Integrate with UI

### Phase 3: Outreach Automation (Wave 3.3)
1. ✅ Set up email service
2. ✅ Build sequence builder
3. ✅ Add database tables
4. ✅ Create outreach API
5. ✅ Build outreach UI

---

## Success Metrics

### Comp-Critic
- Accuracy: 80%+ correct market position identification
- Coverage: Comp analysis for 95%+ of properties
- Performance: <500ms analysis time

### Negotiation Brain
- Adoption: 60%+ of users use recommendations
- Success rate: 40%+ recommended strategies lead to deal
- Satisfaction: 4.0+ average rating

### Outreach Automation
- Volume: 1000+ emails sent per week
- Engagement: 30%+ open rate, 5%+ reply rate
- Efficiency: 10x more outreach vs manual

---

## Next Steps

Start with Wave 3.1 - Comp-Critic adversarial comp analysis.
