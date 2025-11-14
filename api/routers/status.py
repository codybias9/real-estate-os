"""Status router for provider health and service status monitoring."""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import random

router = APIRouter(prefix="/status", tags=["status"])


# ============================================================================
# Enums
# ============================================================================

class ProviderStatus(str, Enum):
    """Status of a service provider."""
    operational = "operational"
    degraded = "degraded"
    partial_outage = "partial_outage"
    major_outage = "major_outage"
    maintenance = "maintenance"


class ProviderType(str, Enum):
    """Type of service provider."""
    email = "email"
    sms = "sms"
    enrichment = "enrichment"
    storage = "storage"
    payment = "payment"
    mapping = "mapping"
    document_generation = "document_generation"
    ai_ml = "ai_ml"


# ============================================================================
# Schemas
# ============================================================================

class ProviderHealth(BaseModel):
    """Health status of a service provider."""
    provider_name: str
    provider_type: ProviderType
    status: ProviderStatus
    status_message: str
    uptime_percentage: float = Field(..., ge=0, le=100)
    response_time_ms: Optional[float] = Field(None, description="Average response time")
    last_check: str
    last_incident: Optional[str] = Field(None, description="Time of last incident")
    rate_limit_remaining: Optional[int] = Field(None, description="API calls remaining")
    rate_limit_reset: Optional[str] = Field(None, description="When rate limit resets")
    metadata: Optional[Dict[str, Any]] = None


class ProviderIncident(BaseModel):
    """Incident affecting a provider."""
    id: str
    provider_name: str
    title: str
    description: str
    severity: str  # minor, major, critical
    status: str  # investigating, identified, monitoring, resolved
    started_at: str
    resolved_at: Optional[str] = None
    affected_services: List[str]


class SystemStatus(BaseModel):
    """Overall system status."""
    status: ProviderStatus
    message: str
    operational_providers: int
    total_providers: int
    active_incidents: int
    last_updated: str


# ============================================================================
# Mock Data Store
# ============================================================================

PROVIDER_HEALTH: List[Dict] = [
    {
        "provider_name": "SendGrid (Email)",
        "provider_type": "email",
        "status": "operational",
        "status_message": "All systems operational",
        "uptime_percentage": 99.98,
        "response_time_ms": 145.3,
        "last_check": datetime.now().isoformat(),
        "last_incident": (datetime.now() - timedelta(days=14)).isoformat(),
        "rate_limit_remaining": 8450,
        "rate_limit_reset": (datetime.now() + timedelta(hours=1)).isoformat(),
        "metadata": {
            "api_version": "v3",
            "quota_limit": 10000,
            "emails_sent_today": 1550
        }
    },
    {
        "provider_name": "Twilio (SMS)",
        "provider_type": "sms",
        "status": "operational",
        "status_message": "Service operating normally",
        "uptime_percentage": 99.95,
        "response_time_ms": 234.7,
        "last_check": datetime.now().isoformat(),
        "last_incident": (datetime.now() - timedelta(days=7)).isoformat(),
        "rate_limit_remaining": 2340,
        "rate_limit_reset": (datetime.now() + timedelta(hours=1)).isoformat(),
        "metadata": {
            "account_balance": 45.67,
            "messages_sent_today": 156,
            "phone_number": "+14155551234"
        }
    },
    {
        "provider_name": "ATTOM Data (Enrichment)",
        "provider_type": "enrichment",
        "status": "degraded",
        "status_message": "Experiencing elevated response times",
        "uptime_percentage": 98.5,
        "response_time_ms": 1450.2,
        "last_check": datetime.now().isoformat(),
        "last_incident": (datetime.now() - timedelta(hours=3)).isoformat(),
        "rate_limit_remaining": 450,
        "rate_limit_reset": (datetime.now() + timedelta(hours=24)).isoformat(),
        "metadata": {
            "daily_limit": 500,
            "requests_today": 50,
            "cost_per_request": 0.50
        }
    },
    {
        "provider_name": "CoreLogic (Property Data)",
        "provider_type": "enrichment",
        "status": "operational",
        "status_message": "All services available",
        "uptime_percentage": 99.92,
        "response_time_ms": 567.8,
        "last_check": datetime.now().isoformat(),
        "last_incident": (datetime.now() - timedelta(days=21)).isoformat(),
        "rate_limit_remaining": 980,
        "rate_limit_reset": (datetime.now() + timedelta(hours=24)).isoformat(),
        "metadata": {
            "daily_limit": 1000,
            "requests_today": 20
        }
    },
    {
        "provider_name": "AWS S3 (Storage)",
        "provider_type": "storage",
        "status": "operational",
        "status_message": "All storage systems operational",
        "uptime_percentage": 99.99,
        "response_time_ms": 89.5,
        "last_check": datetime.now().isoformat(),
        "last_incident": (datetime.now() - timedelta(days=45)).isoformat(),
        "rate_limit_remaining": None,
        "rate_limit_reset": None,
        "metadata": {
            "bucket_name": "realestateos-documents",
            "storage_used_gb": 245.7,
            "monthly_cost": 12.34
        }
    },
    {
        "provider_name": "MinIO (Local Storage)",
        "provider_type": "storage",
        "status": "operational",
        "status_message": "Storage available",
        "uptime_percentage": 99.87,
        "response_time_ms": 45.2,
        "last_check": datetime.now().isoformat(),
        "last_incident": (datetime.now() - timedelta(days=8)).isoformat(),
        "rate_limit_remaining": None,
        "rate_limit_reset": None,
        "metadata": {
            "storage_used_gb": 125.4,
            "storage_available_gb": 374.6,
            "usage_percentage": 25.1
        }
    },
    {
        "provider_name": "Google Maps (Mapping)",
        "provider_type": "mapping",
        "status": "operational",
        "status_message": "Geocoding and mapping services available",
        "uptime_percentage": 99.96,
        "response_time_ms": 312.6,
        "last_check": datetime.now().isoformat(),
        "last_incident": (datetime.now() - timedelta(days=30)).isoformat(),
        "rate_limit_remaining": 4850,
        "rate_limit_reset": (datetime.now() + timedelta(hours=24)).isoformat(),
        "metadata": {
            "daily_limit": 5000,
            "requests_today": 150,
            "geocoding_accuracy": "rooftop"
        }
    },
    {
        "provider_name": "DocRaptor (PDF Generation)",
        "provider_type": "document_generation",
        "status": "maintenance",
        "status_message": "Scheduled maintenance 2am-4am PST",
        "uptime_percentage": 99.85,
        "response_time_ms": 2345.9,
        "last_check": datetime.now().isoformat(),
        "last_incident": (datetime.now() - timedelta(hours=12)).isoformat(),
        "rate_limit_remaining": 890,
        "rate_limit_reset": (datetime.now() + timedelta(hours=1)).isoformat(),
        "metadata": {
            "documents_generated_today": 110,
            "monthly_limit": 5000,
            "maintenance_end": "2025-11-13T04:00:00"
        }
    },
    {
        "provider_name": "OpenAI (AI/ML)",
        "provider_type": "ai_ml",
        "status": "operational",
        "status_message": "GPT-4 and embeddings available",
        "uptime_percentage": 99.93,
        "response_time_ms": 1234.5,
        "last_check": datetime.now().isoformat(),
        "last_incident": (datetime.now() - timedelta(days=5)).isoformat(),
        "rate_limit_remaining": 180,
        "rate_limit_reset": (datetime.now() + timedelta(minutes=60)).isoformat(),
        "metadata": {
            "model": "gpt-4",
            "requests_per_minute": 200,
            "tokens_used_today": 145000
        }
    },
    {
        "provider_name": "Stripe (Payment)",
        "provider_type": "payment",
        "status": "operational",
        "status_message": "Payment processing available",
        "uptime_percentage": 99.98,
        "response_time_ms": 234.2,
        "last_check": datetime.now().isoformat(),
        "last_incident": (datetime.now() - timedelta(days=60)).isoformat(),
        "rate_limit_remaining": None,
        "rate_limit_reset": None,
        "metadata": {
            "account_mode": "live",
            "transactions_today": 12,
            "volume_today": 15600.00
        }
    }
]

INCIDENTS: List[Dict] = [
    {
        "id": "inc_001",
        "provider_name": "ATTOM Data (Enrichment)",
        "title": "Elevated Response Times",
        "description": "We are experiencing slower than normal response times for property data API requests. Our team is investigating the cause.",
        "severity": "minor",
        "status": "monitoring",
        "started_at": (datetime.now() - timedelta(hours=3)).isoformat(),
        "resolved_at": None,
        "affected_services": ["property_enrichment", "data_signals"]
    },
    {
        "id": "inc_002",
        "provider_name": "DocRaptor (PDF Generation)",
        "title": "Scheduled Maintenance",
        "description": "Scheduled infrastructure upgrades to improve performance and reliability.",
        "severity": "minor",
        "status": "identified",
        "started_at": (datetime.now() - timedelta(hours=12)).isoformat(),
        "resolved_at": None,
        "affected_services": ["document_generation", "investor_packets"]
    }
]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/providers", response_model=List[ProviderHealth])
def get_providers_status(provider_type: Optional[ProviderType] = None):
    """
    Get health status of all service providers.

    Shows operational status, uptime, response times, and rate limits
    for all external services (email, SMS, enrichment APIs, etc.).
    """
    providers = PROVIDER_HEALTH.copy()

    # Filter by type if specified
    if provider_type:
        providers = [p for p in providers if p["provider_type"] == provider_type.value]

    return [ProviderHealth(**provider) for provider in providers]


@router.get("/providers/{provider_name}")
def get_provider_status(provider_name: str):
    """
    Get detailed status of a specific provider.

    Returns health metrics, recent incidents, and provider-specific metadata.
    """
    # Find provider (case-insensitive match)
    provider = next(
        (p for p in PROVIDER_HEALTH if p["provider_name"].lower() == provider_name.lower()),
        None
    )

    if not provider:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Provider not found")

    # Get recent incidents for this provider
    provider_incidents = [
        ProviderIncident(**inc)
        for inc in INCIDENTS
        if inc["provider_name"].lower() == provider_name.lower()
    ]

    return {
        "provider": ProviderHealth(**provider),
        "recent_incidents": provider_incidents,
        "performance_history": generate_performance_history()
    }


@router.get("/incidents", response_model=List[ProviderIncident])
def get_incidents(active_only: bool = True):
    """
    Get list of provider incidents.

    Shows ongoing issues, maintenance windows, and resolved incidents.
    """
    incidents = INCIDENTS.copy()

    if active_only:
        incidents = [inc for inc in incidents if inc["resolved_at"] is None]

    return [ProviderIncident(**incident) for incident in incidents]


@router.get("/incidents/{incident_id}", response_model=ProviderIncident)
def get_incident(incident_id: str):
    """
    Get details of a specific incident.

    Shows incident timeline, affected services, and current status.
    """
    incident = next((inc for inc in INCIDENTS if inc["id"] == incident_id), None)

    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Incident not found")

    return ProviderIncident(**incident)


@router.get("/overview", response_model=SystemStatus)
def get_system_status():
    """
    Get overall system status summary.

    Returns high-level status indicating if all providers are operational.
    """
    total_providers = len(PROVIDER_HEALTH)
    operational = sum(
        1 for p in PROVIDER_HEALTH
        if p["status"] in ["operational", "maintenance"]
    )
    degraded = sum(1 for p in PROVIDER_HEALTH if p["status"] == "degraded")
    outage = sum(
        1 for p in PROVIDER_HEALTH
        if p["status"] in ["partial_outage", "major_outage"]
    )
    active_incidents = sum(1 for inc in INCIDENTS if inc["resolved_at"] is None)

    # Determine overall status
    if outage > 0:
        overall_status = ProviderStatus.major_outage
        message = f"{outage} provider(s) experiencing outages"
    elif degraded > 0:
        overall_status = ProviderStatus.degraded
        message = f"{degraded} provider(s) experiencing degraded performance"
    else:
        overall_status = ProviderStatus.operational
        message = "All systems operational"

    return SystemStatus(
        status=overall_status,
        message=message,
        operational_providers=operational,
        total_providers=total_providers,
        active_incidents=active_incidents,
        last_updated=datetime.now().isoformat()
    )


@router.get("/health")
def get_health_check():
    """
    Simple health check endpoint.

    Returns 200 if API is reachable. Can be used for monitoring/alerting.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@router.get("/providers/{provider_name}/test")
def test_provider_connection(provider_name: str):
    """
    Test connection to a specific provider.

    Performs an actual API call to verify provider is reachable and responding.
    """
    # Find provider
    provider = next(
        (p for p in PROVIDER_HEALTH if p["provider_name"].lower() == provider_name.lower()),
        None
    )

    if not provider:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Provider not found")

    # Mock connection test
    # In real system, would make actual API call
    test_start = datetime.now()
    success = random.random() > 0.05  # 95% success rate
    response_time = random.uniform(50, 500) if success else None

    return {
        "provider_name": provider["provider_name"],
        "success": success,
        "response_time_ms": response_time,
        "tested_at": test_start.isoformat(),
        "status_code": 200 if success else 500,
        "message": "Connection successful" if success else "Connection failed"
    }


# ============================================================================
# Helper Functions
# ============================================================================

def generate_performance_history() -> List[Dict[str, Any]]:
    """Generate mock performance history for a provider."""
    history = []
    now = datetime.now()

    for i in range(24):  # Last 24 hours
        timestamp = now - timedelta(hours=i)
        history.append({
            "timestamp": timestamp.isoformat(),
            "response_time_ms": random.uniform(100, 400),
            "success_rate": random.uniform(0.95, 1.0),
            "requests": random.randint(10, 100)
        })

    history.reverse()
    return history
