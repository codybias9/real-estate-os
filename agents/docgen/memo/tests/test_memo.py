"""
Tests for Docgen.Memo PDF generation
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from memo import DocgenMemo
from contracts.property_record import PropertyRecord
from contracts.score_result import ScoreResult


class TestDocgenMemo:
    """Test DocgenMemo PDF generation"""

    @pytest.fixture
    def mock_s3(self):
        """Mock S3 client for testing"""
        with patch("boto3.client") as mock_client:
            s3_mock = MagicMock()
            mock_client.return_value = s3_mock

            # Mock head_bucket to simulate bucket exists
            s3_mock.head_bucket.return_value = {}

            # Mock head_object to simulate PDF doesn't exist (first call)
            s3_mock.head_object.side_effect = ClientError(
                {"Error": {"Code": "404"}}, "head_object"
            )

            # Mock put_object
            s3_mock.put_object.return_value = {}

            yield s3_mock

    @pytest.fixture
    def memo_gen(self, mock_s3):
        """DocgenMemo instance with mocked S3"""
        return DocgenMemo(
            s3_bucket="test-bucket",
            s3_endpoint="http://localhost:9000",
            s3_access_key="test-key",
            s3_secret_key="test-secret",
        )

    def test_initialization(self, mock_s3):
        """Test DocgenMemo initialization"""
        memo_gen = DocgenMemo(
            s3_bucket="test-bucket",
            s3_endpoint="http://localhost:9000",
            s3_access_key="test-key",
            s3_secret_key="test-secret",
        )

        assert memo_gen.s3_bucket == "test-bucket"
        assert memo_gen.s3_region == "us-east-1"
        assert memo_gen.jinja_env is not None

    def test_compute_memo_hash_deterministic(
        self, memo_gen, sample_property, sample_score
    ):
        """Test that memo hash is deterministic for same inputs"""
        hash1 = memo_gen._compute_memo_hash(sample_property, sample_score)
        hash2 = memo_gen._compute_memo_hash(sample_property, sample_score)

        assert hash1 == hash2
        assert len(hash1) == 16  # 16-character hex hash

    def test_compute_memo_hash_different_scores(
        self, memo_gen, sample_property, sample_score
    ):
        """Test that different scores produce different hashes"""
        hash1 = memo_gen._compute_memo_hash(sample_property, sample_score)

        # Change score
        sample_score.score = 85
        hash2 = memo_gen._compute_memo_hash(sample_property, sample_score)

        assert hash1 != hash2

    def test_render_template(self, memo_gen, sample_property, sample_score, tenant_id):
        """Test HTML template rendering"""
        html = memo_gen._render_template(sample_property, sample_score, tenant_id)

        # Check that key elements are in HTML
        assert "123 Main St" in html
        assert "Springfield, CA 90210" in html
        assert "78" in html  # Score
        assert "Price per sqft" in html  # Score reason
        assert "John Doe" in html  # Owner name
        assert "123-456-789" in html  # APN

    def test_html_to_pdf(self, memo_gen):
        """Test PDF generation from HTML"""
        simple_html = "<html><body><h1>Test PDF</h1></body></html>"

        pdf_bytes = memo_gen._html_to_pdf(simple_html)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b"%PDF"  # PDF magic number

    @pytest.mark.timeout(30)  # PDF generation can take a while
    def test_generate_memo_creates_pdf(
        self, memo_gen, mock_s3, sample_property, sample_score, tenant_id
    ):
        """Test full memo generation flow"""
        pdf_url, envelope = memo_gen.generate_memo(
            property_record=sample_property,
            score_result=sample_score,
            tenant_id=tenant_id,
        )

        # Check PDF was uploaded to S3
        assert mock_s3.put_object.called
        put_call = mock_s3.put_object.call_args

        # Check S3 key structure
        s3_key = put_call.kwargs["Key"]
        assert s3_key.startswith(f"tenants/{tenant_id}/memos/")
        assert s3_key.endswith(".pdf")

        # Check PDF content type
        assert put_call.kwargs["ContentType"] == "application/pdf"

        # Check metadata
        metadata = put_call.kwargs["Metadata"]
        assert metadata["tenant_id"] == tenant_id
        assert "generated_at" in metadata

        # Check PDF URL
        assert pdf_url.startswith("s3://test-bucket/")
        assert tenant_id in pdf_url

        # Check envelope
        assert envelope.subject == "event.docgen.memo"
        assert str(envelope.tenant_id) == tenant_id
        assert envelope.payload["property_id"] == sample_property.apn
        assert envelope.payload["pdf_url"] == pdf_url
        assert envelope.payload["status"] == "generated"

    def test_generate_memo_idempotency(
        self, memo_gen, mock_s3, sample_property, sample_score, tenant_id
    ):
        """Test that generating same memo twice is idempotent"""
        # First generation
        pdf_url1, envelope1 = memo_gen.generate_memo(
            sample_property, sample_score, tenant_id
        )

        # Mock that PDF now exists
        mock_s3.head_object.side_effect = None
        mock_s3.head_object.return_value = {}

        # Reset put_object call count
        mock_s3.put_object.reset_mock()

        # Second generation (should skip upload)
        pdf_url2, envelope2 = memo_gen.generate_memo(
            sample_property, sample_score, tenant_id
        )

        # Should return same URL
        assert pdf_url1 == pdf_url2

        # Should NOT upload again
        assert not mock_s3.put_object.called

        # Envelopes should have same idempotency key
        assert envelope1.idempotency_key == envelope2.idempotency_key

    @pytest.mark.timeout(30)  # PDF generation can take a while
    def test_s3_key_tenant_isolation(
        self, memo_gen, mock_s3, sample_property, sample_score
    ):
        """Test that different tenants get different S3 keys"""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())

        pdf_url1, _ = memo_gen.generate_memo(sample_property, sample_score, tenant1)
        pdf_url2, _ = memo_gen.generate_memo(sample_property, sample_score, tenant2)

        assert tenant1 in pdf_url1
        assert tenant2 in pdf_url2
        assert pdf_url1 != pdf_url2

    def test_get_memo_url_exists(self, memo_gen, mock_s3, tenant_id):
        """Test getting URL for existing memo"""
        # Clear the side_effect and set a return value instead
        mock_s3.head_object.side_effect = None
        mock_s3.head_object.return_value = {}

        url = memo_gen.get_memo_url(tenant_id, "abc123")

        assert url is not None
        assert "abc123.pdf" in url
        assert tenant_id in url

    def test_get_memo_url_not_exists(self, memo_gen, mock_s3, tenant_id):
        """Test getting URL for non-existent memo"""
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "head_object"
        )

        url = memo_gen.get_memo_url(tenant_id, "nonexistent")

        assert url is None

    @pytest.mark.timeout(30)  # PDF generation can take a while
    def test_envelope_structure(
        self, memo_gen, mock_s3, sample_property, sample_score, tenant_id
    ):
        """Test envelope has correct structure for event.docgen.memo"""
        _, envelope = memo_gen.generate_memo(sample_property, sample_score, tenant_id)

        # Check envelope fields
        assert envelope.id is not None
        assert str(envelope.tenant_id) == tenant_id
        assert envelope.subject == "event.docgen.memo"
        assert envelope.schema_version == "1.0"
        assert envelope.idempotency_key.startswith("memo-")
        assert envelope.at is not None

        # Check payload structure
        payload = envelope.payload
        assert "property_id" in payload
        assert "pdf_url" in payload
        assert "memo_hash" in payload
        assert "status" in payload
        assert payload["status"] == "generated"

    def test_template_handles_missing_optional_fields(
        self, memo_gen, sample_property, sample_score, tenant_id
    ):
        """Test template renders correctly with missing optional fields"""
        # Remove optional fields
        sample_property.owner = None
        sample_property.provenance = None
        sample_property.url = None

        html = memo_gen._render_template(sample_property, sample_score, tenant_id)

        # Should still render without errors
        assert "123 Main St" in html
        assert len(html) > 0

    def test_score_reasons_rendered(
        self, memo_gen, sample_property, sample_score, tenant_id
    ):
        """Test that all score reasons are rendered in template"""
        html = memo_gen._render_template(sample_property, sample_score, tenant_id)

        # Check each score reason is in HTML
        for reason in sample_score.reasons:
            assert reason.feature.replace("_", " ").title() in html or reason.note in html


class TestGoldenPDFSnapshot:
    """Golden PDF snapshot test"""

    @pytest.fixture
    def golden_dir(self):
        """Directory for golden PDF snapshots"""
        golden_path = Path(__file__).parent / "golden_snapshots"
        golden_path.mkdir(exist_ok=True)
        return golden_path

    @pytest.mark.timeout(30)  # PDF generation can take a while
    @pytest.mark.skipif(
        os.getenv("SKIP_GOLDEN_TESTS") == "1",
        reason="Golden tests skipped (set SKIP_GOLDEN_TESTS=0 to run)",
    )
    def test_golden_pdf_snapshot(
        self, sample_property, sample_score, tenant_id, golden_dir
    ):
        """
        Test that generated PDF matches golden snapshot.

        This is a visual regression test. If the PDF changes:
        1. Review the changes carefully
        2. If intentional, update the golden snapshot:
           - Delete golden_snapshots/golden_memo.pdf
           - Re-run this test to generate new golden snapshot
        """
        # Use in-memory S3 mock
        with patch("boto3.client") as mock_client:
            s3_mock = MagicMock()
            mock_client.return_value = s3_mock
            s3_mock.head_bucket.return_value = {}
            s3_mock.head_object.side_effect = ClientError(
                {"Error": {"Code": "404"}}, "head_object"
            )
            s3_mock.put_object.return_value = {}

            memo_gen = DocgenMemo(
                s3_bucket="test-bucket",
                s3_endpoint="http://localhost:9000",
                s3_access_key="test",
                s3_secret_key="test",
            )

            # Generate PDF
            _, envelope = memo_gen.generate_memo(
                sample_property, sample_score, tenant_id
            )

            # Get PDF bytes from S3 put_object call
            put_call = s3_mock.put_object.call_args
            pdf_bytes = put_call.kwargs["Body"]

            golden_path = golden_dir / "golden_memo.pdf"

            if not golden_path.exists():
                # Create golden snapshot
                golden_path.write_bytes(pdf_bytes)
                pytest.skip(
                    f"Golden snapshot created at {golden_path}. Re-run test to verify."
                )

            # Compare with golden snapshot
            golden_bytes = golden_path.read_bytes()

            # PDF comparison: check size is similar (within 5%)
            # Exact byte comparison not reliable due to timestamps
            size_diff_pct = abs(len(pdf_bytes) - len(golden_bytes)) / len(golden_bytes)
            assert (
                size_diff_pct < 0.05
            ), f"PDF size differs by {size_diff_pct:.1%} from golden snapshot"

            # Check PDF magic number
            assert pdf_bytes[:4] == b"%PDF"
            assert golden_bytes[:4] == b"%PDF"


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.timeout(30)
    def test_bucket_creation(self):
        """Test S3 bucket creation when bucket doesn't exist"""
        with patch("boto3.client") as mock_client:
            s3_mock = MagicMock()
            mock_client.return_value = s3_mock

            # Mock head_bucket to fail (bucket doesn't exist)
            s3_mock.head_bucket.side_effect = ClientError(
                {"Error": {"Code": "404"}}, "head_bucket"
            )
            # Mock create_bucket to succeed
            s3_mock.create_bucket.return_value = {}

            memo_gen = DocgenMemo(
                s3_bucket="test-bucket",
                s3_endpoint="http://localhost:9000",
                s3_access_key="test",
                s3_secret_key="test",
            )

            # Verify bucket was created
            assert s3_mock.create_bucket.called
            assert memo_gen is not None

    @pytest.mark.timeout(30)
    def test_bucket_creation_non_us_east(self):
        """Test S3 bucket creation in non us-east-1 region"""
        with patch("boto3.client") as mock_client:
            s3_mock = MagicMock()
            mock_client.return_value = s3_mock

            # Mock head_bucket to fail (bucket doesn't exist)
            s3_mock.head_bucket.side_effect = ClientError(
                {"Error": {"Code": "404"}}, "head_bucket"
            )
            # Mock create_bucket to succeed
            s3_mock.create_bucket.return_value = {}

            memo_gen = DocgenMemo(
                s3_bucket="test-bucket",
                s3_region="eu-west-1",
            )

            # Verify bucket was created with location constraint
            call_kwargs = s3_mock.create_bucket.call_args.kwargs
            assert "CreateBucketConfiguration" in call_kwargs
            assert call_kwargs["CreateBucketConfiguration"]["LocationConstraint"] == "eu-west-1"

    @pytest.mark.timeout(30)
    def test_invalid_s3_credentials(self):
        """Test initialization with invalid S3 credentials"""
        with patch("boto3.client") as mock_client:
            s3_mock = MagicMock()
            mock_client.return_value = s3_mock
            s3_mock.head_bucket.return_value = {}

            # Should initialize without error (errors occur on actual S3 operations)
            memo_gen = DocgenMemo(
                s3_bucket="test-bucket",
                s3_endpoint="http://localhost:9000",
                s3_access_key="invalid",
                s3_secret_key="invalid",
            )
            assert memo_gen is not None

    @pytest.mark.timeout(30)
    def test_missing_template(self, sample_property, sample_score, tenant_id):
        """Test error when template file is missing"""
        from jinja2.exceptions import TemplateNotFound

        with patch("boto3.client") as mock_client:
            s3_mock = MagicMock()
            mock_client.return_value = s3_mock
            s3_mock.head_bucket.return_value = {}
            s3_mock.head_object.side_effect = ClientError(
                {"Error": {"Code": "404"}}, "head_object"
            )

            # Use non-existent template directory
            with tempfile.TemporaryDirectory() as tmpdir:
                memo_gen = DocgenMemo(
                    s3_bucket="test-bucket",
                    template_dir=Path(tmpdir),
                )

                with pytest.raises(TemplateNotFound):
                    memo_gen.generate_memo(sample_property, sample_score, tenant_id)
