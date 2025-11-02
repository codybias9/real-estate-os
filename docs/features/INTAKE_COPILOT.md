# Intake Copilot (PR-P2.7)

**Status**: ✅ Specification Complete
**Type**: AI-Assisted Data Entry

## Overview

The Intake Copilot is an AI-powered assistant that helps users quickly enter property data by:
- Accepting natural language descriptions
- Parsing addresses and property details
- Auto-filling form fields
- Validating data completeness
- Suggesting corrections

## Key Features

### 1. Natural Language Input
```
User: "3-bed, 2-bath house in Austin TX, built 1985, asking $450k"
Copilot:
  ✓ Property Type: Residential (Single Family)
  ✓ Bedrooms: 3
  ✓ Bathrooms: 2
  ✓ Location: Austin, TX
  ✓ Year Built: 1985
  ✓ List Price: $450,000
```

### 2. Address Parsing
- Extract street address, city, state, ZIP
- Validate against USPS database
- Geocode to lat/lon
- Identify MSA/market

### 3. Auto-Complete
- Pre-fill known fields from public records
- Suggest typical values based on location
- Import data from MLS listings
- Pull tax assessor data

### 4. Data Validation
- Check required fields
- Validate ranges (e.g., 1-100 bedrooms)
- Flag inconsistencies
- Suggest corrections

### 5. Smart Suggestions
- "Similar properties in this area typically have..."
- "Based on the year built, estimated roof age is..."
- "Tax rate for this ZIP code is typically..."

## Implementation

### Backend
```python
# /api/routers/copilot.py
@router.post("/parse-description")
async def parse_property_description(
    description: str
) -> ParsedPropertyData:
    """
    Parse natural language property description.

    Uses LLM to extract structured data from unstructured text.
    """
    # Use Claude/GPT to parse description
    # Extract: address, bedrooms, bathrooms, sqft, price, etc.
    # Return structured JSON
```

### Frontend
```typescript
// PropertyIntakeForm.tsx
<IntakeCopilot
  onPropertyParsed={(data) => form.prefill(data)}
  onSuggestion={(field, value) => form.suggest(field, value)}
/>
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/copilot/parse-description` | Parse natural language |
| POST | `/api/v1/copilot/parse-address` | Parse and validate address |
| GET | `/api/v1/copilot/suggestions/{field}` | Get field suggestions |
| POST | `/api/v1/copilot/validate` | Validate property data |

## User Experience

1. User enters free-form description
2. Copilot parses and highlights extracted fields
3. User confirms or corrects
4. Form auto-fills with confirmed data
5. Copilot suggests missing fields
6. User completes remaining fields
7. Final validation before save

## Benefits

- **10x faster data entry**: Seconds vs minutes
- **Fewer errors**: AI validation catches mistakes
- **Better completion**: Suggests fields users might miss
- **Lower friction**: Natural language is easier than forms

## Status

- ✅ Specification complete
- ⏸ Implementation pending (requires LLM integration)
- 📝 API structure defined
- 🎯 Ready for frontend development
