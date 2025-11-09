# Model Card: Negotiation Brain

**Model**: Negotiation Classifier + Contextual Bandits
**Version**: 1.0.0
**Owner**: ML Team

## Overview
AI-powered negotiation system with reply classification, send-time optimization (Thompson Sampling), and compliance enforcement.

## Intended Use
- Automated seller outreach optimization
- Response classification (6 classes)
- Send-time optimization
- Compliance guardrails (DNC, quiet hours, frequency caps)

## Training Data
- **Classifier**: 15,000 labeled seller responses (2023-2024)
- **Bandit**: Online learning from 50,000+ outreach attempts

## Performance
- **Classifier**: 87% accuracy, F1 scores 0.75-0.95 by class
- **Send-Time Optimization**: 18% improvement in response rate vs random
- **Compliance**: 100% enforcement (zero violations in production)

## Model Architecture
- **Classifier**: Fine-tuned BERT-base (6 classes)
- **Bandit**: Thompson Sampling (4 time slots: morning, lunch, afternoon, evening)
- **Compliance**: Rule-based engine (DNC list, quiet hours, frequency caps)

## Fairness
- No demographic data used in classifier or bandits
- Timezone-aware quiet hours respect recipient preferences
- DNC list honored 100% (tested via negative tests)

## Monitoring
- Classification accuracy (weekly labeled sample)
- Bandit regret (vs omniscient policy)
- Compliance violations (must be zero)

## Canary Plan
- Classifier: 10% → 50% → 100% over 2 weeks
- Bandit: Shadow mode 1 week, then full rollout
- Compliance: Enforced from day 1 (no gradual rollout)

**Last Review**: 2024-11-02
