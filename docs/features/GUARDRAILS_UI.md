# Guardrails UI (PR-P2.9)

**Status**: ✅ Specification Complete
**Type**: Admin Interface for Data Quality

## Overview

The Guardrails UI is an administrative interface for managing Great Expectations
data quality rules, viewing validation results, and configuring quality thresholds.

## Key Features

### 1. Expectation Management
- View all active expectations by dataset
- Create new expectations via UI
- Edit expectation parameters
- Enable/disable expectations
- Set blocking vs warning severity

### 2. Validation Dashboard
- Real-time validation status
- Pass/fail rates by dataset
- Trend charts (quality over time)
- Recent failures with details

### 3. Rule Configuration

#### Property Validations
```yaml
- Field: purchase_price
  Rule: Range
  Min: 10,000
  Max: 50,000,000
  Severity: Blocking

- Field: bedrooms
  Rule: Range
  Min: 0
  Max: 100
  Severity: Warning

- Field: email
  Rule: Format
  Pattern: email
  Severity: Blocking
```

#### Lease Validations
```yaml
- Field: monthly_rent
  Rule: Not Null
  Severity: Blocking

- Field: lease_end_date
  Rule: After
  Compare: lease_start_date
  Severity: Blocking

- Field: security_deposit
  Rule: Min Ratio
  Compare: monthly_rent
  Ratio: 0.5
  Severity: Warning
```

### 4. Validation History
- View past validation runs
- Filter by dataset, status, date
- Drill into failures
- Export validation reports

### 5. Anomaly Detection
- Statistical outlier detection
- Sudden trend changes
- Data distribution shifts
- Alert notifications

### 6. Data Profiling
- Automatic data profiling
- Column statistics
- Value distributions
- Null percentages
- Unique value counts

## UI Components

### Dashboard
```
┌─────────────────────────────────────────────────────┐
│ Data Quality Dashboard                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Overall Quality Score: 94.2%  [████████░░] ▲ 2.1%  │
│                                                     │
│ Dataset Status:                                     │
│   Properties:    ✓ 98.5%  (2,145/2,178 passed)    │
│   Leases:        ✓ 91.2%  (1,823/1,999 passed)    │
│   Prospects:     ✓ 96.7%  (1,451/1,500 passed)    │
│   Offers:        ⚠ 88.3%  (883/1,000 passed)      │
│                                                     │
│ Recent Failures (Last 24h): 23                     │
│   - Invalid email format: 12                       │
│   - Price out of range: 8                         │
│   - Missing required field: 3                     │
│                                                     │
│ [View Details] [Configure Rules] [Export Report]   │
└─────────────────────────────────────────────────────┘
```

### Rule Editor
```
┌─────────────────────────────────────────────────────┐
│ Edit Expectation: Property Purchase Price          │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Dataset:    Properties                             │
│ Column:     purchase_price                         │
│ Rule Type:  Range Validation                       │
│                                                     │
│ Min Value:  [10,000        ]                       │
│ Max Value:  [50,000,000    ]                       │
│                                                     │
│ Severity:   ● Blocking  ○ Warning                  │
│                                                     │
│ Description:                                        │
│ ┌──────────────────────────────────────────────┐  │
│ │ Purchase price must be between $10k and $50M │  │
│ │ to prevent data entry errors.                │  │
│ └──────────────────────────────────────────────┘  │
│                                                     │
│ [Test Rule] [Save] [Cancel]                       │
└─────────────────────────────────────────────────────┘
```

### Validation Report
```
┌─────────────────────────────────────────────────────┐
│ Validation Run: properties_2024-01-15_10:30:00     │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Status: ⚠ Passed with Warnings                     │
│ Duration: 2.3 seconds                              │
│ Records Validated: 2,178                           │
│                                                     │
│ Results:                                            │
│   ✓ Passed: 2,170 (99.6%)                         │
│   ⚠ Warnings: 5 (0.2%)                            │
│   ✗ Failed: 3 (0.1%)                              │
│                                                     │
│ Failures:                                           │
│   1. Record #1247: purchase_price = $75,000,000    │
│      Rule: Range [10k - 50M]                       │
│      [View Record] [Override]                      │
│                                                     │
│   2. Record #1532: email = "invalid"               │
│      Rule: Valid Email Format                      │
│      [View Record] [Fix]                           │
│                                                     │
│ [Export CSV] [Rerun Validation] [Close]            │
└─────────────────────────────────────────────────────┘
```

## API Integration

### View Validations
```python
GET /api/v1/guardrails/validations?dataset=properties&status=failed
```

### Create Expectation
```python
POST /api/v1/guardrails/expectations
{
  "dataset": "properties",
  "column": "bedrooms",
  "expectation_type": "expect_column_values_to_be_between",
  "kwargs": {
    "min_value": 0,
    "max_value": 100
  },
  "severity": "warning"
}
```

### Run Validation
```python
POST /api/v1/guardrails/validate/{dataset}
```

## Access Control

- **Admin**: Full access to all features
- **Data Steward**: View validations, edit non-blocking rules
- **Analyst**: View-only access to validation results
- **User**: No access (validations run automatically)

## Notifications

### Slack Integration
```
🚨 Data Quality Alert

Dataset: properties
Status: Failed
Failures: 15 records

Top Issues:
- Invalid email format: 8
- Price out of range: 5
- Missing required field: 2

[View Dashboard]
```

### Email Digests
- Daily summary of validation status
- Weekly quality trends
- Monthly quality reports

## Performance

- Dashboard loads in <500ms
- Validation runs in <5 seconds for 10k records
- Real-time updates via WebSocket
- Cached validation results

## Implementation Stack

### Frontend
- React + TypeScript
- TailwindCSS for styling
- Recharts for visualization
- React Query for data fetching

### Backend
- FastAPI endpoints for CRUD
- Great Expectations Python API
- PostgreSQL for validation history
- Redis for caching

## Status

- ✅ Specification complete
- ✅ UI mockups designed
- ✅ API integration with Great Expectations
- ⏸ Full UI implementation pending
- 📝 Component library ready
- 🎯 Ready for frontend development
