# UI Decision Aids - User Guide

This document describes the AI-powered decision aids in the Real Estate OS interface.

---

## 1. Score Panel with SHAP Explanations

**Location**: Property Detail Page → Score Tab

### Features
- **Score Visualization**: 0-1 scale with confidence level
- **Top Influencing Factors**: Top 10 SHAP values with:
  - Direction (🟢 positive / 🔴 negative)
  - Magnitude (bar chart)
  - Feature value
  - Impact explanation

### What-If Scenarios
- **Interactive Sliders**: Adjust property features to see score impact
- **Counterfactual Suggestions**: 5 actionable scenarios with:
  - Expected score change
  - Feasibility assessment
  - Estimated cost (if applicable)

### Use Cases
- Understand why a property scored high/low
- Identify value-add opportunities
- Estimate ROI of improvements

**Evidence**: [artifacts/ui/score-panel-shap.png.txt](../artifacts/ui/score-panel-shap.png.txt)

---

## 2. Comps Waterfall Visualization

**Location**: Property Detail Page → Valuation Tab

### Features
- **Waterfall Chart**: Visual breakdown of adjustments
- **Comparable Properties List**: Top 10 comps with:
  - Distance and days since sale
  - Relevance score and weight
  - Adjustment breakdown (sqft, lot, condition, etc.)
- **Confidence Interval**: 95% CI displayed as range

### Interactive Elements
- Hover over comps to see full details
- Click comp to view on map
- Filter comps by distance/recency

### Use Cases
- Validate AVM estimate
- Understand market comparables
- Adjust offer price based on comps

**Evidence**: [artifacts/ui/comps-waterfall.png.txt](../artifacts/ui/comps-waterfall.png.txt)

---

## 3. Regime Monitoring Badge

**Location**: Market Dashboard

### Features
- **Regime Badge**: Color-coded (🥶 COLD / 🌤️ COOL / ☀️ WARM / 🔥 HOT)
- **Confidence Percentage**: How confident the system is
- **Market Indicators**: 4 key metrics with trend arrows
- **Investment Policy**: Auto-generated guidelines:
  - Max offer percentage
  - Min profit margin
  - Due diligence period
  - Recommended pace

### "Why?" Explanation
- Composite index breakdown
- Historical regime changes
- Policy rationale

### Use Cases
- Understand current market conditions
- Adjust investment strategy per market
- Track regime changes over time

**Evidence**: [artifacts/ui/regime-badge.png.txt](../artifacts/ui/regime-badge.png.txt)

---

## 4. Negotiation Compliance Badges

**Location**: Outreach Campaign Manager

### Features
- **Real-Time Compliance Checking**:
  - ✅ DNC list status
  - ⏰ Quiet hours enforcement
  - 📊 Frequency cap tracking
  - ⏳ Cool-down period remaining

- **Recommended Send Time**: AI-optimized time slot with:
  - Expected response rate
  - Recipient timezone
  - Historical performance

- **Blocked Sends**: Clear explanation of why a send is blocked

### Compliance Dashboard
- Total leads
- Eligible now
- Blocked reasons (breakdown)

### Use Cases
- Ensure legal compliance (TCPA, DNC)
- Optimize outreach timing
- Manage contact frequency

**Evidence**: [artifacts/ui/negotiation-badges.png.txt](../artifacts/ui/negotiation-badges.png.txt)

---

## Design Principles

### Transparency
- Show confidence scores and uncertainty
- Explain AI decisions in plain language
- Provide evidence (e.g., source comps)

### Actionability
- Suggest concrete next steps
- Estimate costs/benefits
- Enable what-if exploration

### Compliance
- Enforce rules transparently
- Explain why actions are blocked
- Provide remediation guidance

---

## Accessibility

- **Keyboard Navigation**: All interactive elements keyboard-accessible
- **Screen Readers**: ARIA labels on all charts and badges
- **Color Blindness**: Don't rely solely on color (use icons + text)
- **Mobile Responsive**: All decision aids work on mobile devices

---

## Future Enhancements

- [ ] Export decision aids as PDF reports
- [ ] Historical tracking (score changes over time)
- [ ] Comparative analysis (compare multiple properties side-by-side)
- [ ] Voice annotations for busy investors
- [ ] Collaborative decision-making (comments, approvals)

---

**Last Updated**: 2024-11-02
**Owner**: Product + ML Teams
