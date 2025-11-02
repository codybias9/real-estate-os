# Property Dossier Generation (PR-P2.8)

**Status**: ✅ Specification Complete
**Type**: Comprehensive Property Report

## Overview

The Property Dossier is a comprehensive PDF report that consolidates all property data,
analysis, and due diligence into a single document for sharing with partners, lenders,
and stakeholders.

## Report Sections

### 1. Executive Summary (1 page)
- Property overview
- Key metrics (price, sqft, cap rate)
- Investment thesis
- Recommendation

### 2. Property Details (2-3 pages)
- Full address and photos
- Physical characteristics
- Condition assessment
- Year built, last renovated
- Zoning and land use

### 3. Financial Analysis (3-4 pages)
- Purchase price and terms
- DCF analysis (5-10 year projection)
- Comp-Critic valuation
- Cap rate and cash-on-cash return
- IRR and NPV

### 4. Market Analysis (2 pages)
- MSA overview
- Neighborhood demographics
- Supply and demand
- Rent trends
- Comparable properties

### 5. Hazard Assessment (1-2 pages)
- Flood risk
- Wildfire risk
- Heat risk
- Composite hazard score
- Risk mitigation costs

### 6. Property Twins (1 page)
- Similar properties
- Comparative analysis
- Market positioning

### 7. Financing Options (1-2 pages)
- Lender matches (top 3)
- Terms comparison
- Estimated payments

### 8. Renovation Analysis (if applicable) (2 pages)
- Current condition
- Renovation scope
- Budget breakdown
- ARV estimate
- ROI calculation

### 9. Due Diligence (2 pages)
- Document checklist
- Inspection items
- Title issues
- Lease abstracts
- Outstanding items

### 10. Appendices
- Rent roll
- Lease summaries
- Inspection reports
- Comparable sale details
- Full DCF model

## Report Formats

- **PDF**: Professional layout with charts/graphs
- **Excel**: Editable financial model
- **PowerPoint**: Presentation deck for meetings

## Generation API

```python
# /api/routers/dossiers.py
@router.post("/properties/{property_id}/dossier")
async def generate_property_dossier(
    property_id: UUID,
    sections: List[str] = None,  # Optional: select specific sections
    format: str = "pdf"
) -> DossierResponse:
    """
    Generate comprehensive property dossier.

    Aggregates all property data, runs all analyses,
    and produces professional report.
    """
```

## Implementation

### Report Builder
```python
class DossierBuilder:
    def __init__(self, property_id: UUID):
        self.property = fetch_property(property_id)

    def add_section(self, section: Section):
        # Fetch data for section
        # Run analysis if needed
        # Format for PDF

    def generate_pdf(self) -> bytes:
        # Use ReportLab or WeasyPrint
        # Apply professional template
        # Include charts and tables
        # Return PDF bytes
```

### Chart Generation
- matplotlib for financial charts
- plotly for interactive visualizations
- Pillow for image processing
- Charts embedded in PDF

## Templates

### Professional Template
- Clean layout
- Company branding
- Color scheme
- Chart styles
- Table formats

### Investor Template
- Focus on returns
- Emphasized financial sections
- Risk assessment
- Exit strategies

### Lender Template
- Focus on creditworthiness
- DSCR and LTV prominently displayed
- Appraisal details
- Insurance and tax documentation

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/dossiers/{property_id}/generate` | Generate dossier |
| GET | `/api/v1/dossiers/{id}` | Get generated dossier |
| GET | `/api/v1/dossiers/{id}/download` | Download PDF |
| GET | `/api/v1/dossiers/templates` | List templates |

## Use Cases

### 1. Partnership Review
Generate dossier before partner call:
- All data in one place
- Professional presentation
- Easy to share

### 2. Lender Submission
Submit with loan application:
- Complete property details
- Financial analysis
- Due diligence documentation

### 3. Investment Committee
Present to investment committee:
- Executive summary
- Risk analysis
- Recommendation

### 4. Property Disposition
Marketing package for sale:
- Property highlights
- Cash flow history
- Market opportunity

## Performance

- Generation time: 30-60 seconds
- Async processing for large reports
- Cached sections for quick regeneration
- PDF size: 2-5 MB typical

## Status

- ✅ Specification complete
- ✅ Report structure defined
- ✅ Integration with offer packet generator
- ⏸ Full implementation pending
- 📝 Templates designed
- 🎯 Ready for production build
