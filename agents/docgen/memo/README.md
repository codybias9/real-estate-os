# Docgen.Memo

**Single-Writer Agent**: Generates PDF memos for property reports.

## Purpose

Docgen.Memo is responsible for generating professional PDF memos that combine:
- Property details (address, attributes, owner information)
- Investment score and explanation
- Provenance summary (data sources)
- Map visualization

## Architecture

**Input Contract**: `PropertyRecord` + `ScoreResult` (from contracts package)
**Output**: PDF stored in MinIO/S3
**Event Published**: `event.docgen.memo` (single producer)

## Usage

```python
from memo import DocgenMemo
from contracts.property_record import PropertyRecord
from contracts.score_result import ScoreResult

# Initialize memo generator
memo_gen = DocgenMemo(
    s3_bucket="property-memos",
    s3_endpoint="http://localhost:9000",  # MinIO
    s3_access_key="minioadmin",
    s3_secret_key="minioadmin"
)

# Generate memo
pdf_url = memo_gen.generate_memo(
    property_record=property_record,
    score_result=score_result,
    tenant_id="tenant-uuid"
)

print(f"Memo generated: {pdf_url}")
```

## Features

- **Single Writer Pattern**: Only Docgen.Memo publishes `event.docgen.memo`
- **PDF Generation**: Uses WeasyPrint for HTML-to-PDF conversion
- **S3 Storage**: Stores PDFs in MinIO/S3 with tenant isolation
- **Templating**: Jinja2 templates for flexible memo layouts
- **Idempotency**: Same property + score → same PDF URL (hash-based naming)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=memo --cov-report=html

# Run golden snapshot test
pytest tests/test_memo.py::test_golden_pdf_snapshot -v
```

## Template Customization

Templates are located in `templates/` directory:
- `memo_template.html` - Main memo HTML structure
- `memo_styles.css` - Styling for PDF output

## Dependencies

- **weasyprint**: HTML-to-PDF conversion
- **jinja2**: Template rendering
- **boto3**: S3/MinIO storage
- **contracts**: Shared data contracts
