"""
Tests for Outreach.Orchestrator
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from uuid import uuid4
from datetime import datetime, timezone

from orchestrator import OutreachOrchestrator, OutreachStatus, OutreachCampaign
from orchestrator.repository import OutreachRepository
from orchestrator.models import OutreachStatusEnum


class TestCampaignCreation:
    """Test campaign creation"""

    @pytest.fixture
    def mock_repository(self):
        """Mock repository for testing"""
        repo = MagicMock(spec=OutreachRepository)
        return repo

    @pytest.fixture
    def orchestrator(self, mock_repository):
        """OutreachOrchestrator instance with mocked repository"""
        return OutreachOrchestrator(
            repository=mock_repository,
            sendgrid_api_key="test-key",
            from_email="test@example.com",
            from_name="Test Sender",
        )

    def test_initialization(self, orchestrator):
        """Test OutreachOrchestrator initialization"""
        assert orchestrator.repository is not None
        assert orchestrator.from_email == "test@example.com"
        assert orchestrator.from_name == "Test Sender"

    def test_initialization_without_api_key_raises_error(self, mock_repository):
        """Test that missing API key raises error"""
        with pytest.raises(ValueError, match="SendGrid API key"):
            OutreachOrchestrator(
                repository=mock_repository,
                sendgrid_api_key=None,
            )

    def test_create_campaign_success(
        self,
        orchestrator,
        mock_repository,
        tenant_id,
        property_id,
        sample_property,
        sample_score,
        memo_url,
    ):
        """Test successful campaign creation"""
        # Mock: no existing campaign
        mock_repository.get_campaign_by_property.return_value = None

        # Mock: campaign creation
        mock_campaign = MagicMock()
        mock_campaign.id = uuid4()
        mock_campaign.property_id = property_id
        mock_campaign.owner_email = "john.doe@example.com"
        mock_campaign.status = "scheduled"
        mock_campaign.scheduled_at = datetime.now(timezone.utc)
        mock_repository.create_campaign.return_value = mock_campaign

        # Create campaign
        campaign = orchestrator.create_campaign(
            tenant_id=tenant_id,
            property_record=sample_property,
            score_result=sample_score,
            memo_url=memo_url,
        )

        # Verify repository was called
        assert mock_repository.create_campaign.called
        call_args = mock_repository.create_campaign.call_args.kwargs
        assert call_args["tenant_id"] == tenant_id
        assert call_args["property_id"] == property_id
        assert call_args["owner_email"] == "john.doe@example.com"
        assert "Investment Opportunity" in call_args["subject"]

        # Verify campaign was returned
        assert campaign is not None
        assert campaign.property_id == str(property_id)

    def test_create_campaign_idempotent(
        self,
        orchestrator,
        mock_repository,
        tenant_id,
        property_id,
        sample_property,
        sample_score,
        memo_url,
    ):
        """Test that creating duplicate campaign is idempotent"""
        # Mock: existing campaign found
        existing_campaign = MagicMock()
        existing_campaign.id = uuid4()
        existing_campaign.property_id = property_id
        existing_campaign.owner_email = "john.doe@example.com"
        existing_campaign.status = "sent"
        mock_repository.get_campaign_by_property.return_value = existing_campaign

        # Create campaign (should return existing)
        campaign = orchestrator.create_campaign(
            tenant_id=tenant_id,
            property_record=sample_property,
            score_result=sample_score,
            memo_url=memo_url,
        )

        # Verify create was NOT called
        assert not mock_repository.create_campaign.called

        # Verify existing campaign was returned
        assert campaign.property_id == str(property_id)

    def test_create_campaign_without_owner_email_raises_error(
        self,
        orchestrator,
        mock_repository,
        tenant_id,
        sample_property,
        sample_score,
        memo_url,
    ):
        """Test that missing owner email raises error"""
        # Remove owner email
        sample_property["owner"]["email"] = None

        with pytest.raises(ValueError, match="owner email is required"):
            orchestrator.create_campaign(
                tenant_id=tenant_id,
                property_record=sample_property,
                score_result=sample_score,
                memo_url=memo_url,
            )


class TestEmailSending:
    """Test email sending via SendGrid"""

    @pytest.fixture
    def mock_repository(self):
        """Mock repository"""
        repo = MagicMock(spec=OutreachRepository)
        return repo

    @pytest.fixture
    def mock_sendgrid(self):
        """Mock SendGrid client"""
        with patch("orchestrator.orchestrator.SendGridAPIClient") as mock_sg:
            client = MagicMock()
            mock_sg.return_value = client

            # Mock send response
            response = MagicMock()
            response.status_code = 202
            response.headers = {"X-Message-Id": "test-message-id"}
            client.send.return_value = response

            yield client

    @pytest.fixture
    def orchestrator(self, mock_repository, mock_sendgrid):
        """OutreachOrchestrator with mocked SendGrid"""
        return OutreachOrchestrator(
            repository=mock_repository,
            sendgrid_api_key="test-key",
            from_email="test@example.com",
        )

    def test_send_campaign_success(
        self,
        orchestrator,
        mock_repository,
        mock_sendgrid,
        tenant_id,
        campaign_id,
        property_id,
        sample_property,
        sample_score,
    ):
        """Test successful email sending"""
        # Mock: campaign exists and is scheduled
        mock_campaign = MagicMock()
        mock_campaign.id = campaign_id
        mock_campaign.property_id = property_id
        mock_campaign.owner_email = "john.doe@example.com"
        mock_campaign.owner_name = "John Doe"
        mock_campaign.status = OutreachStatusEnum.SCHEDULED.value
        mock_campaign.subject = "Test Subject"
        mock_campaign.memo_url = "https://example.com/memo.pdf"
        mock_repository.get_campaign.return_value = mock_campaign

        # Send campaign
        result = orchestrator.send_campaign(
            campaign_id=campaign_id,
            tenant_id=tenant_id,
            property_record=sample_property,
            score_result=sample_score,
        )

        # Verify SendGrid was called
        assert mock_sendgrid.send.called

        # Verify campaign status was updated
        assert mock_repository.update_campaign_status.called
        update_call = mock_repository.update_campaign_status.call_args.kwargs
        assert update_call["status"] == OutreachStatusEnum.SENT
        assert "sent_at" in update_call

        # Verify event was logged
        assert mock_repository.log_event.called

        # Verify result
        assert result["status"] == "sent"
        assert result["message_id"] == "test-message-id"

    def test_send_campaign_already_sent(
        self,
        orchestrator,
        mock_repository,
        mock_sendgrid,
        tenant_id,
        campaign_id,
        sample_property,
        sample_score,
    ):
        """Test that sending already-sent campaign is idempotent"""
        # Mock: campaign already sent
        mock_campaign = MagicMock()
        mock_campaign.id = campaign_id
        mock_campaign.status = OutreachStatusEnum.SENT.value
        mock_campaign.sendgrid_message_id = "existing-message-id"
        mock_repository.get_campaign.return_value = mock_campaign

        # Send campaign
        result = orchestrator.send_campaign(
            campaign_id=campaign_id,
            tenant_id=tenant_id,
            property_record=sample_property,
            score_result=sample_score,
        )

        # Verify SendGrid was NOT called
        assert not mock_sendgrid.send.called

        # Verify result
        assert result["status"] == "already_sent"
        assert result["message_id"] == "existing-message-id"

    def test_send_campaign_not_found_raises_error(
        self,
        orchestrator,
        mock_repository,
        tenant_id,
        campaign_id,
        sample_property,
        sample_score,
    ):
        """Test that sending non-existent campaign raises error"""
        # Mock: campaign not found
        mock_repository.get_campaign.return_value = None

        with pytest.raises(ValueError, match="Campaign not found"):
            orchestrator.send_campaign(
                campaign_id=campaign_id,
                tenant_id=tenant_id,
                property_record=sample_property,
                score_result=sample_score,
            )

    def test_send_campaign_sendgrid_failure(
        self,
        orchestrator,
        mock_repository,
        mock_sendgrid,
        tenant_id,
        campaign_id,
        property_id,
        sample_property,
        sample_score,
    ):
        """Test handling of SendGrid API failure"""
        # Mock: campaign exists
        mock_campaign = MagicMock()
        mock_campaign.id = campaign_id
        mock_campaign.property_id = property_id
        mock_campaign.owner_email = "john.doe@example.com"
        mock_campaign.owner_name = "John Doe"
        mock_campaign.status = OutreachStatusEnum.SCHEDULED.value
        mock_campaign.subject = "Test Subject"
        mock_campaign.memo_url = "https://example.com/memo.pdf"
        mock_repository.get_campaign.return_value = mock_campaign

        # Mock: SendGrid failure
        mock_sendgrid.send.side_effect = Exception("SendGrid API error")

        # Send campaign (should raise)
        with pytest.raises(Exception, match="SendGrid API error"):
            orchestrator.send_campaign(
                campaign_id=campaign_id,
                tenant_id=tenant_id,
                property_record=sample_property,
                score_result=sample_score,
            )

        # Verify status was updated to FAILED
        update_call = mock_repository.update_campaign_status.call_args.kwargs
        assert update_call["status"] == OutreachStatusEnum.FAILED

        # Verify failure event was logged
        log_call = mock_repository.log_event.call_args.kwargs
        assert log_call["event_type"] == "failed"


class TestWebhookHandling:
    """Test SendGrid webhook handling"""

    @pytest.fixture
    def mock_repository(self):
        """Mock repository"""
        repo = MagicMock(spec=OutreachRepository)
        return repo

    @pytest.fixture
    def orchestrator(self, mock_repository):
        """OutreachOrchestrator instance"""
        return OutreachOrchestrator(
            repository=mock_repository,
            sendgrid_api_key="test-key",
        )

    def test_handle_webhook_delivered(
        self, orchestrator, mock_repository, tenant_id, campaign_id
    ):
        """Test handling of 'delivered' webhook event"""
        # Mock: campaign exists
        mock_campaign = MagicMock()
        mock_campaign.id = campaign_id
        mock_repository.get_campaign.return_value = mock_campaign

        # Webhook data
        webhook_data = {
            "event": "delivered",
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
            "timestamp": 1234567890,
        }

        # Handle webhook
        result = orchestrator.handle_webhook(webhook_data)

        # Verify status was updated
        assert mock_repository.update_campaign_status.called
        update_call = mock_repository.update_campaign_status.call_args.kwargs
        assert update_call["status"] == OutreachStatusEnum.DELIVERED
        assert "delivered_at" in update_call

        # Verify event was logged
        assert mock_repository.log_event.called

        # Verify result
        assert result["event_type"] == "delivered"
        assert result["status"] == "delivered"

    def test_handle_webhook_opened(
        self, orchestrator, mock_repository, tenant_id, campaign_id
    ):
        """Test handling of 'open' webhook event"""
        # Mock: campaign exists
        mock_campaign = MagicMock()
        mock_campaign.id = campaign_id
        mock_repository.get_campaign.return_value = mock_campaign

        # Webhook data
        webhook_data = {
            "event": "open",
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
        }

        # Handle webhook
        result = orchestrator.handle_webhook(webhook_data)

        # Verify status was updated
        update_call = mock_repository.update_campaign_status.call_args.kwargs
        assert update_call["status"] == OutreachStatusEnum.OPENED
        assert "opened_at" in update_call

    def test_handle_webhook_clicked(
        self, orchestrator, mock_repository, tenant_id, campaign_id
    ):
        """Test handling of 'click' webhook event"""
        mock_campaign = MagicMock()
        mock_campaign.id = campaign_id
        mock_repository.get_campaign.return_value = mock_campaign

        webhook_data = {
            "event": "click",
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
        }

        result = orchestrator.handle_webhook(webhook_data)

        update_call = mock_repository.update_campaign_status.call_args.kwargs
        assert update_call["status"] == OutreachStatusEnum.CLICKED
        assert "clicked_at" in update_call

    def test_handle_webhook_bounced(
        self, orchestrator, mock_repository, tenant_id, campaign_id
    ):
        """Test handling of 'bounce' webhook event"""
        mock_campaign = MagicMock()
        mock_campaign.id = campaign_id
        mock_repository.get_campaign.return_value = mock_campaign

        webhook_data = {
            "event": "bounce",
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
        }

        result = orchestrator.handle_webhook(webhook_data)

        update_call = mock_repository.update_campaign_status.call_args.kwargs
        assert update_call["status"] == OutreachStatusEnum.BOUNCED

    def test_handle_webhook_no_campaign_id(self, orchestrator):
        """Test that webhook without campaign_id is ignored"""
        webhook_data = {"event": "delivered"}

        result = orchestrator.handle_webhook(webhook_data)

        assert result is None

    def test_handle_webhook_unknown_event(
        self, orchestrator, mock_repository, tenant_id, campaign_id
    ):
        """Test that unknown event type is ignored"""
        mock_campaign = MagicMock()
        mock_repository.get_campaign.return_value = mock_campaign

        webhook_data = {
            "event": "unknown_event",
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
        }

        result = orchestrator.handle_webhook(webhook_data)

        assert result is None


class TestTemplateRendering:
    """Test email template rendering"""

    @pytest.fixture
    def orchestrator(self):
        """OutreachOrchestrator instance"""
        repo = MagicMock(spec=OutreachRepository)
        return OutreachOrchestrator(
            repository=repo,
            sendgrid_api_key="test-key",
        )

    def test_render_html_template(
        self, orchestrator, sample_property, sample_score, memo_url
    ):
        """Test HTML template rendering"""
        html = orchestrator._render_template(
            "memo_delivery_email.html",
            property=sample_property,
            score=sample_score,
            owner=sample_property["owner"],
            memo_url=memo_url,
            company_name="Test Company",
            company_email="test@example.com",
        )

        # Verify key content is present
        assert "123 Main St" in html
        assert "John Doe" in html
        assert "78" in html or "78/100" in html
        assert memo_url in html

    def test_render_text_template(
        self, orchestrator, sample_property, sample_score, memo_url
    ):
        """Test plain text template rendering"""
        text = orchestrator._render_template(
            "memo_delivery_email.txt",
            property=sample_property,
            score=sample_score,
            owner=sample_property["owner"],
            memo_url=memo_url,
            company_name="Test Company",
            company_email="test@example.com",
        )

        # Verify key content is present
        assert "123 Main St" in text
        assert "John Doe" in text
        assert "78" in text
        assert memo_url in text


class TestCampaignQueries:
    """Test campaign query methods"""

    @pytest.fixture
    def orchestrator(self):
        """OutreachOrchestrator instance"""
        repo = MagicMock(spec=OutreachRepository)
        return OutreachOrchestrator(
            repository=repo,
            sendgrid_api_key="test-key",
        )

    def test_get_campaign(self, orchestrator, tenant_id, campaign_id):
        """Test getting campaign by ID"""
        mock_campaign = MagicMock()
        mock_campaign.id = campaign_id
        mock_campaign.property_id = uuid4()
        mock_campaign.owner_email = "test@example.com"
        mock_campaign.status = "sent"
        orchestrator.repository.get_campaign.return_value = mock_campaign

        campaign = orchestrator.get_campaign(campaign_id, tenant_id)

        assert campaign is not None
        assert campaign.id == str(campaign_id)

    def test_get_campaign_not_found(self, orchestrator, tenant_id, campaign_id):
        """Test getting non-existent campaign"""
        orchestrator.repository.get_campaign.return_value = None

        campaign = orchestrator.get_campaign(campaign_id, tenant_id)

        assert campaign is None

    def test_get_campaigns_by_status(self, orchestrator, tenant_id):
        """Test querying campaigns by status"""
        mock_campaigns = [MagicMock(), MagicMock()]
        for i, mock in enumerate(mock_campaigns):
            mock.id = uuid4()
            mock.property_id = uuid4()
            mock.owner_email = f"test{i}@example.com"
            mock.status = "sent"

        orchestrator.repository.get_campaigns_by_status.return_value = mock_campaigns

        campaigns = orchestrator.get_campaigns_by_status(
            OutreachStatus.SENT, tenant_id
        )

        assert len(campaigns) == 2

    def test_get_statistics(self, orchestrator, tenant_id):
        """Test getting campaign statistics"""
        stats = {
            "scheduled": 10,
            "sent": 5,
            "opened": 2,
            "clicked": 1,
        }
        orchestrator.repository.count_by_status.return_value = stats

        result = orchestrator.get_statistics(tenant_id)

        assert result["scheduled"] == 10
        assert result["sent"] == 5


class TestOutreachCampaign:
    """Test OutreachCampaign wrapper class"""

    def test_campaign_properties(self):
        """Test campaign property access"""
        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.property_id = uuid4()
        mock_model.owner_email = "test@example.com"
        mock_model.status = "sent"
        mock_model.sent_at = datetime.now(timezone.utc)
        mock_model.opened_at = None

        campaign = OutreachCampaign(mock_model)

        assert campaign.id == str(mock_model.id)
        assert campaign.property_id == str(mock_model.property_id)
        assert campaign.owner_email == "test@example.com"
        assert campaign.status == "sent"
        assert campaign.sent_at is not None
        assert campaign.opened_at is None

    def test_campaign_to_dict(self):
        """Test campaign serialization"""
        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.property_id = uuid4()
        mock_model.owner_name = "John Doe"
        mock_model.owner_email = "test@example.com"
        mock_model.status = "sent"
        mock_model.subject = "Test Subject"
        mock_model.scheduled_at = datetime.now(timezone.utc)
        mock_model.sent_at = datetime.now(timezone.utc)
        mock_model.opened_at = None

        campaign = OutreachCampaign(mock_model)
        data = campaign.to_dict()

        assert "id" in data
        assert "property_id" in data
        assert data["owner_email"] == "test@example.com"
        assert data["status"] == "sent"
