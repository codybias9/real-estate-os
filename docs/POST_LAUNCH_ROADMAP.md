# Real Estate OS - Post-Launch Feature Roadmap

**Created**: 2025-11-03
**Status**: Strategic Plan (Post Full Go Approval)
**Horizon**: 6 months (Q1-Q2 2026)

---

## Vision

Transform Real Estate OS from a solid technical platform into the **best-in-class operational tool** that makes real estate professionals say *"this is better than my spreadsheets + CRM + email."*

**Core Principles**:
1. **Decision speed, not just data** - Surface the ONE thing to do next
2. **Fewer tabs** - Bring email, calls, docs into the pipeline
3. **Explainable confidence** - Probabilities the team can trust and challenge
4. **Zero-friction collaboration** - Secure sharing without logins
5. **Operational guardrails** - Automate "don't forgets"

---

## Quick Wins (Month 1) 🚀

*Low effort → High impact. Ship these immediately after launch.*

### 1. Generate & Send Memo Combo ⚡
**Impact**: Reduce friction in critical workflow
**Effort**: 2 days

**Current**: Generate memo → Download → Go to outreach → Upload → Send
**New**: "Generate & Send" button → PDF ready → Auto-open sequence modal with memo link pre-inserted

**Implementation**:
```typescript
// After PDF generation completes
const memoUrl = `${MINIO_URL}/memos/${propertyId}/memo.pdf`;
// Auto-open outreach modal with pre-filled template
openOutreachModal({
  propertyId,
  template: "investor_intro",
  attachments: [{ type: "memo", url: memoUrl }]
});
```

**KPI**: Time from "generate" to "sent" reduced from 3 min → 30 sec

---

### 2. Auto-Assign on Reply ⚡
**Impact**: Eliminate manual assignment busywork
**Effort**: 1 day

**Logic**:
```python
# When reply event received
if property.assigned_to is None:
    # Find last person who sent outreach to this property
    last_sender = get_last_outreach_sender(property_id)
    property.assigned_to = last_sender
    timeline.add_event("auto_assigned", user=last_sender)
```

**KPI**: 100% of engaged leads have owners

---

### 3. Stage-Aware Template Filtering ⚡
**Impact**: Prevent embarrassing template misfires
**Effort**: 4 hours

**Current**: Show all 50 templates regardless of stage
**New**:
- Stage=New → "Initial Contact" templates only
- Stage=Qualified → "Follow-up" templates
- Stage=Negotiating → "Offer" templates

**Implementation**: Add `stage_filter` field to templates table

**KPI**: Template selection errors eliminated

---

### 4. One-Click "Flag Data Issue" ⚡
**Impact**: Surface and fix bad data faster
**Effort**: 1 day

**UI**: Hover any field → "🚩 Flag" button → Creates task:
```json
{
  "type": "data_quality",
  "property_id": "...",
  "field": "assessed_value",
  "current_value": "$0",
  "reason": "Seems incorrect",
  "action": "refresh_from_attom"
}
```

**Auto-action**: If >5 flags on same field → Auto-trigger enrichment refresh

**KPI**: Data quality issues resolved <24h

---

### 5. CSV Import Wizard ⚡
**Impact**: Onboard seller lists 10x faster
**Effort**: 3 days

**Flow**:
1. Upload CSV
2. Map columns (APN, Address, Owner) with preview
3. Validate (show errors inline: "Row 23: Invalid APN format")
4. Import → Auto-create properties + trigger enrichment

**KPI**: Time to import 1000 leads: 2 hours → 10 minutes

---

## A) Workflow Accelerators (Quarter 1)

### A1. Next Best Action (NBA) Panel 🎯
**Impact**: HIGH | **Effort**: 2 weeks | **Priority**: P0

**What**: Smart panel on property detail showing the ONE thing to do next

**Examples**:
- *New lead, high score, no memo*: **"Generate investor memo"** [1-click]
- *Memo sent, 72h no open*: **"Send SMS follow-up"** [1-click]
- *Email opened 3x, no reply*: **"Call now"** [Click-to-dial]
- *In negotiation, missing comps*: **"Update comparables"** [Auto-refresh]

**Logic**:
```python
def next_best_action(property: Property) -> Action:
    # Rule-based + light ML
    if property.stage == "new" and property.score > 70 and not property.memo_generated:
        return Action("generate_memo", priority=1)

    if property.last_outreach_sent > 72h and property.last_email_opened and not property.last_reply:
        return Action("call_owner", priority=1, phone=property.owner_phone)

    if property.stage == "negotiating" and property.comps_age > 30d:
        return Action("refresh_comps", priority=2)

    # ML model: predict next action based on historical outcomes
    return ml_model.predict_next_action(property)
```

**UI Mockup**:
```
┌─────────────────────────────────────────────┐
│ 📌 Next Best Action                         │
├─────────────────────────────────────────────┤
│ Call owner about offer                      │
│ [📞 Call (555) 123-4567]  [⏭️ Skip]          │
│                                             │
│ Why: Opened email 3x, no reply yet          │
│ Expected impact: +45% reply rate            │
└─────────────────────────────────────────────┘
```

**KPIs**:
- Time New→Qualified: -30%
- Reply rate: +45%
- Weekly touches per property: +2.5x

---

### A2. Smart Lists (Saved Queries with Intent) 🎯
**Impact**: HIGH | **Effort**: 1 week | **Priority**: P0

**What**: Pre-built + custom saved searches that surface work to be done

**Default Smart Lists**:
1. **"Hot & Ready"** - High score, no memo, added <7d
2. **"Warm Replies"** - Replied in last 48h, needs follow-up
3. **"Stuck Negotiations"** - In negotiating stage >14d, no activity
4. **"Missing Packets"** - In pitched stage, no investor memo
5. **"Cold Reactivation"** - Score >70, last touch >90d

**Implementation**:
```typescript
interface SmartList {
  id: string;
  name: string;
  description: string;
  filters: PropertyFilter[];
  sort: SortConfig;
  badge_count: number; // Real-time count
  suggested_action: string; // "Generate memos for these 12 properties"
}

const HOT_AND_READY: SmartList = {
  id: "hot_ready",
  name: "Hot & Ready",
  description: "High-potential leads that need memos",
  filters: [
    { field: "score", operator: ">=", value: 70 },
    { field: "memo_generated", operator: "=", value: false },
    { field: "created_at", operator: ">=", value: "now-7d" }
  ],
  sort: { field: "score", order: "desc" },
  suggested_action: "Generate memos"
};
```

**UI**: Left sidebar, always visible, with badge counts
```
┌──────────────────────┐
│ 📋 Smart Lists       │
├──────────────────────┤
│ 🔥 Hot & Ready  (12) │
│ 💬 Warm Replies  (5) │
│ ⏸️  Stuck Deals   (3) │
│ 📄 Missing Packet(8) │
│ ❄️  Cold Leads  (47) │
│                      │
│ ➕ Create Custom     │
└──────────────────────┘
```

**KPIs**:
- Percent of pipeline touched weekly: 60% → 95%
- Time to find "what to work on": 5 min → 10 sec

---

### A3. One-Click Tasking from Timeline 🎯
**Impact**: MEDIUM | **Effort**: 3 days | **Priority**: P1

**What**: Convert any timeline event into a task

**Interactions**:
- Reply received → "Create follow-up task" → Auto-fill: Due in 24h, assigned to you
- Email opened 3x → "Create call task" → Auto-fill: "Call within 2h"
- Property viewed by investor → "Create check-in task"

**Implementation**:
```typescript
// On timeline event
<TimelineEvent event={event}>
  <ContextMenu>
    <MenuItem onClick={() => createTaskFromEvent(event)}>
      📌 Create Task
    </MenuItem>
  </ContextMenu>
</TimelineEvent>

function createTaskFromEvent(event: TimelineEvent): Task {
  const defaultSLA = {
    "reply_received": 24, // hours
    "email_opened_3x": 2,
    "investor_viewed": 48
  }[event.type] || 48;

  return {
    title: `Follow up on ${event.type}`,
    property_id: event.property_id,
    assigned_to: getCurrentUser(),
    due_at: addHours(now(), defaultSLA),
    context: event
  };
}
```

**KPIs**:
- Overdue task rate: 25% → <5%
- Follow-up completion within SLA: 40% → 90%

---

## B) Communication Inside Pipeline (Quarter 1-2)

### B1. Email Threading → Auto-Ingest 📧
**Impact**: HIGH | **Effort**: 2 weeks | **Priority**: P0

**What**: Connect Gmail/Outlook, auto-import all emails related to properties

**Flow**:
1. User connects Gmail via OAuth
2. Background job: Scan inbox for property-related emails (match by address, APN, owner name)
3. Import as timeline events with full thread context
4. Link to property automatically

**Detection**:
```python
def match_email_to_property(email: Email) -> Optional[Property]:
    # Extract potential property identifiers
    addresses = extract_addresses(email.body + email.subject)
    apns = extract_apns(email.body)

    # Match against properties
    if addresses:
        return Property.query.filter(Property.address.in_(addresses)).first()
    if apns:
        return Property.query.filter(Property.apn.in_(apns)).first()

    # Use sender/recipient matching
    if email.from_email in property_contacts:
        return get_property_by_contact(email.from_email)

    return None
```

**UI**: Timeline shows email threads with "Reply" button inline

**KPIs**:
- Manual log entries: 100% → 0%
- Time to find "what did we last say": 2 min → 5 sec

---

### B2. Call Capture + Transcription 📞
**Impact**: HIGH | **Effort**: 2 weeks | **Priority**: P1

**What**: Click-to-dial with automatic recording, transcription, and key points

**Integration**: Twilio Voice API + AssemblyAI for transcription

**Features**:
- Click phone number anywhere → Initiates call via browser
- Auto-record (with consent prompt)
- Real-time transcription
- Sentiment analysis (positive, neutral, negative)
- Key point extraction ("Owner mentioned: wants $150k, needs 30-day close")

**Implementation**:
```python
# After call ends
transcription = assemblyai.transcribe(call_recording_url)
sentiment = transcription.sentiment_analysis
key_points = extract_key_points(transcription.text)

timeline.add_event(
    type="call_completed",
    property_id=property_id,
    duration_sec=call.duration,
    transcript=transcription.text,
    sentiment=sentiment.overall,
    key_points=key_points,
    recording_url=call_recording_url
)
```

**UI**: Call button on property card, transcript view in timeline

**KPIs**:
- Contact attempts per lead: +50%
- Note quality score (has specific details): 30% → 85%

---

### B3. AI Reply Drafting + Objection Handling 🤖
**Impact**: MEDIUM | **Effort**: 1 week | **Priority**: P2

**What**: Draft context-aware replies with objection templates

**Context Used**:
- Property score + reasons
- Memo summary
- Last 3 interactions
- Objection type (price, timing, tenant, etc.)

**Objection Templates**:
1. **"Price too low"** → Emphasize market data, recent comps, quick close value
2. **"Bad timing"** → Offer flexible close date, present value of selling now
3. **"Tenant in place"** → Show cash-flow analysis, tenant-in-place buyer options
4. **"Not interested"** → Ask permission to stay in touch, pivot to referral

**Implementation**:
```python
def draft_reply(property: Property, objection_type: str) -> str:
    context = {
        "score_reasons": property.score_explanation[:3],
        "memo_summary": property.memo_summary,
        "last_interaction": property.timeline[-1],
        "owner_name": property.owner_name
    }

    prompt = f"""
    Draft a professional reply to an owner who said: "{objection_type}"

    Property context:
    - Address: {property.address}
    - Score: {property.score}/100 because {context['score_reasons']}
    - Recent activity: {context['last_interaction']}

    Tone: Professional, empathetic, data-driven
    Goal: Keep conversation open, address objection with facts
    """

    return openai.complete(prompt, max_tokens=200)
```

**UI**: "✨ Draft Reply" button when composing email

**KPIs**:
- Time to send reply: -60%
- Reply→meeting conversion: +25%

---

## C) Portfolio & Outcomes (Quarter 2)

### C1. Deal Economics Panel 💰
**Impact**: HIGH | **Effort**: 2 weeks | **Priority**: P0

**What**: Show expected value (EV) with top drivers and what-if scenarios

**Calculation**:
```python
def calculate_ev(property: Property) -> DealEconomics:
    # Base calculation
    arv = property.after_repair_value or property.market_value
    acquisition_cost = property.offer_price or property.assessed_value * 0.75
    rehab_cost = property.estimated_rehab or 0

    # Expected margin
    if property.strategy == "wholesale":
        expected_fee = 5000  # Assignment fee
    elif property.strategy == "flip":
        expected_margin = arv - acquisition_cost - rehab_cost
        expected_fee = expected_margin * 0.7  # After holding costs

    # Probability of close (from ML model)
    prob_close = property.close_probability or 0.3

    # Expected Value
    ev = expected_fee * prob_close

    # Top drivers (SHAP-like)
    drivers = [
        ("Probability of close", prob_close, "+$" + str(int(expected_fee * prob_close))),
        ("Owner tenure (14y)", 0.15, "+$750"),
        ("Motivated seller signals", 0.10, "+$500"),
        ("Quick close premium", 0.05, "+$250")
    ]

    return DealEconomics(
        ev=ev,
        expected_fee=expected_fee,
        prob_close=prob_close,
        drivers=drivers
    )
```

**UI Mockup**:
```
┌─────────────────────────────────────────────┐
│ 💰 Deal Economics                           │
├─────────────────────────────────────────────┤
│ Expected Value: $1,500                      │
│ (If close: $5,000 × 30% probability)        │
│                                             │
│ Top Drivers:                                │
│ 1. Probability of close (30%)    +$1,500   │
│ 2. Owner tenure (14y)            +$750     │
│ 3. Motivated seller signals      +$500     │
│                                             │
│ What-if:                                    │
│ Offer: $75k [────■──] $100k                │
│ Close days: 30 [──■────] 90                │
│                                             │
│ Updated EV: $1,875 (+25%)                   │
└─────────────────────────────────────────────┘
```

**KPIs**:
- Prioritization accuracy: Top 20% of EV gets 80% of touches
- Portfolio EV: Visible and trending upward

---

### C2. Investor Readiness Score 📊
**Impact**: MEDIUM | **Effort**: 1 week | **Priority**: P1

**What**: Checklist-based score that unlocks "Share Packet" when Green

**Checklist**:
- ✅ Memo generated (<30 days old)
- ✅ Comparables updated (<30 days)
- ✅ Photos uploaded (min 5)
- ✅ Disclosure checklist complete
- ✅ Title search ordered
- ✅ Activity in last 7 days

**Scoring**:
```python
def investor_readiness_score(property: Property) -> ReadinessScore:
    checks = {
        "memo_fresh": property.memo_age_days < 30,
        "comps_fresh": property.comps_age_days < 30,
        "has_photos": len(property.photos) >= 5,
        "disclosure_complete": property.disclosure_checklist_pct == 100,
        "title_ordered": property.title_status == "ordered",
        "recent_activity": property.last_activity_days < 7
    }

    score = sum(checks.values()) / len(checks) * 100
    status = "green" if score >= 80 else "yellow" if score >= 60 else "red"

    return ReadinessScore(
        score=score,
        status=status,
        checks=checks,
        missing=[k for k, v in checks.items() if not v]
    )
```

**UI**: Traffic light badge on property card + detailed checklist in drawer

**KPIs**:
- Properties ready to share: 25% → 70%
- Time to first investor share: -50%

---

### C3. Template Leaderboard 🏆
**Impact**: MEDIUM | **Effort**: 3 days | **Priority**: P2

**What**: Rank outreach templates by reply rate with champion/challenger testing

**Metrics per Template**:
- Sends: 1,247
- Opens: 623 (49.9%)
- Clicks: 156 (12.5%)
- Replies: 87 (7.0%)
- Meetings: 23 (1.8%)

**Champion/Challenger**:
- Current champion: "Direct & Urgent"
- New challenger: "Empathetic & Personal"
- Auto A/B test: 80% champion, 20% challenger
- Auto-promote when challenger wins with statistical significance

**UI**: Admin dashboard with sortable table

**KPIs**:
- Reply rate uplift: +15% from continuous optimization
- Template experimentation velocity: 1 test/month → 4 tests/month

---

## D) Sharing & Deal Rooms (Quarter 2)

### D1. Secure Share Links (No Login) 🔗
**Impact**: HIGH | **Effort**: 1 week | **Priority**: P0

**What**: Share memos or full deal rooms via secure link without requiring investor login

**Features**:
- Watermark with viewer name/email
- Link expiry (24h, 7d, 30d)
- Per-viewer tracking (views, time spent, downloads)
- Optional Q&A thread that writes back to Timeline

**Implementation**:
```python
def create_share_link(property_id: str, viewer_email: str, expiry_days: int = 7) -> ShareLink:
    token = generate_secure_token()
    watermark = f"Shared with {viewer_email} on {date.today()}"

    return ShareLink(
        token=token,
        property_id=property_id,
        viewer_email=viewer_email,
        expires_at=now() + timedelta(days=expiry_days),
        watermark=watermark,
        tracking={
            "views": 0,
            "time_spent_sec": 0,
            "downloads": 0,
            "questions": []
        }
    )

@app.get("/share/{token}")
def view_shared_property(token: str):
    link = ShareLink.get_by_token(token)

    if not link or link.is_expired():
        raise HTTPException(404, "Link expired or not found")

    # Track view
    link.tracking["views"] += 1

    # Return watermarked memo + property details
    return render_shared_view(link)
```

**UI**: Share modal with options
```
┌─────────────────────────────────────────────┐
│ Share with Investor                         │
├─────────────────────────────────────────────┤
│ Email: investor@fund.com                    │
│ Expiry: [7 days ▼]                          │
│ Include: [x] Memo  [x] Photos  [ ] Comps   │
│ Allow Q&A: [x]                              │
│                                             │
│ [Generate Link]                             │
└─────────────────────────────────────────────┘
```

**KPIs**:
- Investor engagement: Views per share +3x
- Time to investor offer: -40%

---

### D2. Deal Room Artifacts 📁
**Impact**: MEDIUM | **Effort**: 1 week | **Priority**: P1

**What**: Organize all deal documents in one place with export

**Artifacts**:
- Investor memo (PDF)
- Comparables analysis
- Photos (organized: exterior, interior, issues)
- Inspection reports
- Title search
- Disclosure documents
- Offer template (pre-filled)

**Export**: ZIP file "Offer Pack" with all artifacts organized

**Implementation**:
```python
def create_deal_room(property_id: str) -> DealRoom:
    return DealRoom(
        property_id=property_id,
        artifacts={
            "memo": property.memo_url,
            "comps": generate_comps_pdf(property),
            "photos": organize_photos(property.photos),
            "inspection": property.inspection_report_url,
            "title": property.title_search_url,
            "disclosures": property.disclosure_docs,
            "offer_template": generate_offer_template(property)
        }
    )

def export_offer_pack(property_id: str) -> bytes:
    room = get_deal_room(property_id)
    zip_buffer = BytesIO()

    with ZipFile(zip_buffer, 'w') as zip_file:
        zip_file.writestr("README.txt", "Deal Pack for {property.address}")
        zip_file.writestr("memo.pdf", download_file(room.artifacts["memo"]))
        zip_file.writestr("comps.pdf", room.artifacts["comps"])
        # ... add all artifacts

    return zip_buffer.getvalue()
```

**UI**: "Deal Room" tab on property detail + "📦 Export Offer Pack" button

**KPIs**:
- Time to prepare investor packet: 2 hours → 5 minutes
- Investor questions about missing docs: -90%

---

## E) Data & Trust Upgrades (Quarter 2)

### E1. Owner Propensity Signals 🎯
**Impact**: HIGH | **Effort**: 2 weeks | **Priority**: P1

**What**: "Likely to entertain offer" probability with explainable reasons

**Signals (Public Data)**:
- Tenure: How long owner has owned (14y = higher motivation)
- Last sale: Recent purchase = less likely to sell
- Tax status: Delinquent/liens = higher motivation
- Vacancy proxies: Utilities disconnected, mail returned
- Absentee owner: Mailing address ≠ property address
- Recent price cuts: Zillow/Redfin price reductions
- Distress signals: Pre-foreclosure, probate, divorce filings

**Model**:
```python
def calculate_propensity(property: Property) -> PropensityScore:
    signals = {
        "tenure_years": property.owner_tenure_years,
        "tax_delinquent": property.tax_status == "delinquent",
        "absentee_owner": property.owner_address != property.address,
        "vacancy_indicators": property.vacancy_score,
        "price_cuts": property.recent_price_cuts,
        "distress_flags": property.distress_signals
    }

    # Logistic regression trained on historical closes
    probability = propensity_model.predict_proba(signals)[1]

    # Explainable reasons
    feature_importance = get_shap_values(signals)
    top_reasons = sorted(feature_importance, key=lambda x: abs(x[1]), reverse=True)[:3]

    return PropensityScore(
        probability=probability,
        confidence="high" if probability > 0.7 else "medium",
        reasons=top_reasons
    )
```

**UI Mockup**:
```
┌─────────────────────────────────────────────┐
│ 🎯 Seller Propensity                        │
├─────────────────────────────────────────────┤
│ Likely to entertain offer: 73%              │
│ Confidence: High                            │
│                                             │
│ Top Reasons:                                │
│ • Owner tenure 14y (+18%)                   │
│ • Tax lien active (+12%)                    │
│ • Absentee owner (+8%)                      │
│                                             │
│ [View All Signals →]                        │
└─────────────────────────────────────────────┘
```

**KPIs**:
- Contact-to-reply rate: +35%
- Marketing cost efficiency: +25% (focus on high propensity)

---

### E2. Provenance Inspector UI 🔍
**Impact**: MEDIUM | **Effort**: 3 days | **Priority**: P2

**What**: Hover any field to see source, cost, freshness, and prefer source

**Tooltip on Hover**:
```
┌─────────────────────────────────────────────┐
│ Assessed Value: $175,000                    │
├─────────────────────────────────────────────┤
│ Source: ATTOM (Premium)                     │
│ Cost: $0.08                                 │
│ Fetched: 2 days ago                         │
│ Confidence: High                            │
│                                             │
│ Also available from:                        │
│ • Regrid: $165,000 ($0.02) 5 days ago       │
│ • Public Record: $170,000 (Free) 30 days ago│
│                                             │
│ [⭐ Prefer ATTOM for this property]         │
│ [🔄 Refresh from all sources]               │
└─────────────────────────────────────────────┘
```

**Implementation**:
```typescript
interface FieldProvenance {
  field: string;
  value: any;
  source: "attom" | "regrid" | "public" | "user";
  cost_usd: number;
  fetched_at: Date;
  confidence: "high" | "medium" | "low";
  alternatives: Array<{
    source: string;
    value: any;
    cost_usd: number;
    fetched_at: Date;
  }>;
}

function ProvenanceTooltip({ field, property }: Props) {
  const provenance = getFieldProvenance(property.id, field);

  return (
    <Tooltip>
      <div>Source: {provenance.source}</div>
      <div>Cost: ${provenance.cost_usd}</div>
      <div>Fetched: {formatRelativeTime(provenance.fetched_at)}</div>

      {provenance.alternatives.map(alt => (
        <div>• {alt.source}: {alt.value} (${alt.cost_usd})</div>
      ))}

      <Button onClick={() => preferSource(property.id, field, provenance.source)}>
        Prefer {provenance.source}
      </Button>
    </Tooltip>
  );
}
```

**KPIs**:
- Data disputes: -80%
- User confidence in data: Survey score 6.2 → 8.5

---

### E3. Deliverability Hygiene Dashboard 📈
**Impact**: MEDIUM | **Effort**: 1 week | **Priority**: P2

**What**: Domain warmup, bounce trends, and list health suggestions

**Metrics**:
- Domain reputation score (0-100)
- Daily send volume vs warmup schedule
- Bounce rate trend (last 30d)
- Suppression list size
- Spam complaint rate
- Top bounce reasons

**Suggestions**:
- "Remove these 27 hard-bounced addresses"
- "Reduce daily volume by 20% (warmup phase)"
- "Add these 3 seed addresses to improve reputation"

**Implementation**:
```python
def deliverability_health(tenant_id: UUID) -> DeliverabilityReport:
    # Domain reputation (from SendGrid)
    reputation = sendgrid.get_reputation_score(tenant_id)

    # Bounce analysis
    bounces = get_bounces(tenant_id, days=30)
    bounce_rate = len(bounces) / get_total_sends(tenant_id, days=30)

    # Suppression list
    suppressed = get_suppression_list(tenant_id)

    # Suggestions
    suggestions = []
    if bounce_rate > 0.05:
        hard_bounces = [b for b in bounces if b.type == "hard"]
        suggestions.append(f"Remove {len(hard_bounces)} hard-bounced addresses")

    if reputation < 80 and daily_send_volume > warmup_limit:
        suggestions.append(f"Reduce daily volume to {warmup_limit} (warmup)")

    return DeliverabilityReport(
        reputation=reputation,
        bounce_rate=bounce_rate,
        suppressed_count=len(suppressed),
        suggestions=suggestions
    )
```

**UI**: Health dashboard with traffic lights and action buttons

**KPIs**:
- Bounce rate: <3% maintained
- Open rate: +8% from better deliverability

---

## F) Automation & Guardrails (Quarter 2)

### F1. Cadence Governor ⏱️
**Impact**: HIGH | **Effort**: 1 week | **Priority**: P1

**What**: Smart auto-pause/switch based on engagement

**Rules**:
1. Reply detected → Pause sequence for 48h
2. 3 unopened emails → Switch to SMS or postcard
3. 7+ days no engagement → Move to "Cold" smart list
4. Unsubscribe/complaint → Immediate suppress + stop all

**Implementation**:
```python
def cadence_governor(property_id: str, event: Event):
    sequence = get_active_sequence(property_id)

    if not sequence:
        return

    if event.type == "reply_received":
        sequence.pause(duration_hours=48, reason="Reply received")
        create_task("Follow up on reply", property_id, due_in_hours=4)

    elif count_unopened_emails(property_id) >= 3:
        sequence.pause()
        suggest_channel_switch(property_id, to="sms", reason="Low email engagement")

    elif days_since_last_engagement(property_id) > 7:
        sequence.pause()
        move_to_smart_list(property_id, "cold_leads")

    elif event.type in ["unsubscribe", "complaint"]:
        sequence.stop()
        suppress_contact(property_id, reason=event.type)
```

**KPIs**:
- Unsubscribe rate: -60%
- Reply rate: +20% from better timing

---

### F2. Compliance Pack ✅
**Impact**: MEDIUM | **Effort**: 1 week | **Priority**: P1

**What**: DNC checks, opt-out enforcement, state disclaimers

**Features**:
- DNC list check before every call/SMS
- State-specific mail disclaimers auto-inserted
- Opt-out enforcement (email List-Unsubscribe + SMS STOP)
- Compliance badge on outreach: "✅ Compliant"

**Implementation**:
```python
def compliance_check(property: Property, channel: str) -> ComplianceResult:
    checks = {
        "dnc": not is_on_dnc_list(property.owner_phone),
        "suppression": not is_suppressed(property.owner_email),
        "opt_out": has_explicit_consent(property.id),
        "disclaimer": has_state_disclaimer(property.state, channel)
    }

    compliant = all(checks.values())

    if not compliant:
        blocking_issues = [k for k, v in checks.items() if not v]
        return ComplianceResult(
            compliant=False,
            issues=blocking_issues,
            action="blocked"
        )

    return ComplianceResult(compliant=True)
```

**UI**: Badge on outreach button + pre-send validation

**KPIs**:
- Compliance incidents: 0 (zero tolerance)
- Legal complaints: 0

---

### F3. Budget & Provider Dashboard 💵
**Impact**: MEDIUM | **Effort**: 3 days | **Priority**: P2

**What**: Real-time spend vs caps with forecasting

**Metrics**:
- ATTOM: $45 / $100 daily cap (45%)
- Regrid: $23 / $500 daily cap (4.6%)
- Total spend (30d): $1,247 / $5,000

**Forecast**: "At current rate: $1,850 this month"

**Auto-Actions**:
- At 80% of cap: Alert to Slack
- At 90%: Auto-switch to cheaper provider
- At 100%: Block expensive calls, use free sources only

**Implementation**:
```python
def budget_monitor(tenant_id: UUID):
    usage = get_provider_usage(tenant_id, period="today")
    caps = get_budget_caps(tenant_id)

    for provider, spent in usage.items():
        cap = caps[provider]
        pct = spent / cap

        if pct >= 1.0:
            policy_kernel.block_provider(tenant_id, provider)
            alert(f"🚫 {provider} budget exhausted")
        elif pct >= 0.9:
            policy_kernel.set_fallback_mode(tenant_id, provider)
            alert(f"⚠️ {provider} at 90% budget")
        elif pct >= 0.8:
            alert(f"📊 {provider} at 80% budget")
```

**UI**: Dashboard with burn rate charts and projected spend

**KPIs**:
- Cost predictability: Zero surprise overages
- Average cost per property: Tracked and optimized

---

## G) Mobile-First (Quarter 2)

### G1. Mobile Web Quick Actions 📱
**Impact**: HIGH | **Effort**: 1 week | **Priority**: P0

**What**: Thumb-optimized actions for field work

**Quick Actions** (Big buttons):
- 📞 Call Owner
- 💬 Send SMS
- ✅ Change Stage
- 🎤 Record Note (voice-to-text)
- 📷 Add Photos
- 📄 Share Memo

**Voice Notes**:
```typescript
function VoiceNoteRecorder({ propertyId }: Props) {
  const [recording, setRecording] = useState(false);

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);

    recorder.ondataavailable = async (e) => {
      const audioBlob = e.data;

      // Transcribe with Whisper API
      const transcription = await transcribeAudio(audioBlob);

      // Add as timeline note
      await addTimelineNote(propertyId, transcription);
    };

    recorder.start();
    setRecording(true);
  }

  return (
    <Button onTouchStart={startRecording} size="lg">
      {recording ? "🔴 Recording..." : "🎤 Record Note"}
    </Button>
  );
}
```

**Mobile-Optimized Layout**: Large touch targets (44px min), simplified nav

**KPIs**:
- Updates same-day as visit: 35% → 90%
- Mobile usage: 15% → 45% of total

---

## Priority Matrix

**Impact vs Effort**:

```
High Impact
│
│  A1. NBA Panel        │  C1. Deal Economics
│  A2. Smart Lists      │  D1. Share Links
│  E1. Propensity       │  B1. Email Threading
│  QW. Generate&Send    │  F1. Cadence Governor
│  G1. Mobile Actions   │  B2. Call Capture
│
├──────────────────────┼──────────────────────
│  A3. One-Click Tasks  │  C2. Investor Score
│  E2. Provenance UI    │  D2. Deal Rooms
│  F2. Compliance       │  E3. Deliverability
│  QW. Auto-Assign      │  C3. Template Leaderboard
│  QW. Stage Templates  │  B3. AI Reply Drafting
│
Low Impact                                High Effort
```

---

## Implementation Roadmap

### Month 1 (Immediate Post-Launch)
**Focus**: Quick wins + stability

**Week 1-2**:
- ✅ Generate & Send combo
- ✅ Auto-assign on reply
- ✅ Stage-aware templates
- ✅ Flag data issue
- ✅ CSV import wizard
- Monitor production metrics

**Week 3-4**:
- Next Best Action panel (A1)
- Smart Lists (A2)
- Start email threading integration (B1)

---

### Month 2-3 (Quarter 1)
**Focus**: Workflow acceleration + communication

**Month 2**:
- Complete email threading (B1)
- One-click tasking (A3)
- Call capture + transcription (B2)
- Mobile quick actions (G1)

**Month 3**:
- AI reply drafting (B3)
- Secure share links (D1)
- Owner propensity signals (E1)

---

### Month 4-6 (Quarter 2)
**Focus**: Portfolio intelligence + automation

**Month 4**:
- Deal economics panel (C1)
- Investor readiness score (C2)
- Template leaderboard (C3)

**Month 5**:
- Deal room artifacts (D2)
- Cadence governor (F1)
- Compliance pack (F2)

**Month 6**:
- Provenance inspector (E2)
- Deliverability dashboard (E3)
- Budget monitor (F3)

---

## Success Metrics

**User Delight**:
- Time New→Qualified: -30%
- Reply rate: +45%
- Weekly pipeline touches: +2.5x

**Operational Excellence**:
- Overdue tasks: <5%
- Compliance incidents: 0
- Data disputes: -80%

**Business Outcomes**:
- Portfolio EV: Visible and growing
- Cost per property: Optimized
- Time to investor offer: -40%

---

## Differentiators (Long-term Bets)

### 1. Explainable Probability of Close
Not just a score - a calibrated probability with SHAP-style explanations showing exactly what drives the number and how actions change it.

### 2. Scenario Planning
"What if we offer $X?" instantly updates memo, EV, probability, and suggested next action across the entire deal.

### 3. Investor Network Effects
Private investor directory with asset class preferences, past engagement history, and AI-suggested matches per property.

---

**Document Owner**: Product Team
**Last Updated**: 2025-11-03
**Review Cycle**: Monthly
**Status**: Draft for approval
