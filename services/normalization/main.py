"""Address Normalization Service
Uses libpostal for address parsing and normalization

Endpoints:
- POST /normalize - Normalize single address
- POST /normalize/batch - Normalize batch of addresses
- POST /parse - Parse address into components
- GET /health - Health check
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import postal.parser
import postal.expand
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Address Normalization Service",
    description="Address parsing and normalization using libpostal",
    version="1.0.0"
)


# ============================================================================
# Models
# ============================================================================

class Address(BaseModel):
    raw_address: str
    country: Optional[str] = "us"


class AddressBatch(BaseModel):
    addresses: List[Address]


class ParsedAddress(BaseModel):
    raw_address: str
    components: Dict[str, str]
    confidence: float


class NormalizedAddress(BaseModel):
    raw_address: str
    canonical_address: str
    components: Dict[str, str]
    expansions: List[str]
    confidence: float


# ============================================================================
# Endpoints
# ============================================================================

@app.post("/normalize", response_model=NormalizedAddress)
async def normalize_address(address: Address):
    """Normalize a single address

    Steps:
    1. Parse address into components
    2. Generate canonical form
    3. Generate expansions (e.g., "St" -> "Street")
    4. Calculate confidence based on coverage

    Args:
        address: Address to normalize

    Returns:
        Normalized address with components and confidence
    """
    try:
        raw = address.raw_address

        # Parse into components
        parsed = postal.parser.parse_address(raw)
        components = {item[1]: item[0] for item in parsed}

        # Generate expansions
        expansions = postal.expand.expand_address(raw)

        # Canonical form (first expansion, typically most complete)
        canonical = expansions[0] if expansions else raw

        # Calculate confidence
        confidence = _calculate_confidence(components)

        logger.info(f"Normalized address: {raw} -> {canonical}")

        return NormalizedAddress(
            raw_address=raw,
            canonical_address=canonical,
            components=components,
            expansions=expansions,
            confidence=confidence
        )

    except Exception as e:
        logger.error(f"Failed to normalize address: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/normalize/batch", response_model=List[NormalizedAddress])
async def normalize_batch(batch: AddressBatch):
    """Normalize batch of addresses

    Args:
        batch: Batch of addresses to normalize

    Returns:
        List of normalized addresses
    """
    results = []

    for address in batch.addresses:
        try:
            result = await normalize_address(address)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to normalize address in batch: {e}")
            # Return partial result with low confidence
            results.append(NormalizedAddress(
                raw_address=address.raw_address,
                canonical_address=address.raw_address,
                components={},
                expansions=[],
                confidence=0.0
            ))

    return results


@app.post("/parse", response_model=ParsedAddress)
async def parse_address(address: Address):
    """Parse address into components

    Components:
    - house_number: 123
    - road: main st
    - unit: apt 4
    - city: las vegas
    - state: nv
    - postcode: 89101
    - country: usa

    Args:
        address: Address to parse

    Returns:
        Parsed address with components
    """
    try:
        raw = address.raw_address

        # Parse
        parsed = postal.parser.parse_address(raw)
        components = {item[1]: item[0] for item in parsed}

        # Confidence
        confidence = _calculate_confidence(components)

        logger.info(f"Parsed address: {raw}")

        return ParsedAddress(
            raw_address=raw,
            components=components,
            confidence=confidence
        )

    except Exception as e:
        logger.error(f"Failed to parse address: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "address-normalization"}


# ============================================================================
# Helper Functions
# ============================================================================

def _calculate_confidence(components: Dict[str, str]) -> float:
    """Calculate confidence based on component coverage

    Confidence = (essential_fields_present / total_essential_fields)

    Essential fields:
    - road (or house for standalone)
    - city
    - state (or country)
    - postcode

    Args:
        components: Parsed address components

    Returns:
        Confidence score 0.0-1.0
    """
    essential_fields = ["road", "city", "state", "postcode"]
    optional_fields = ["house_number", "unit"]

    # Check essential fields
    present = sum(1 for field in essential_fields if field in components)
    confidence = present / len(essential_fields)

    # Boost confidence if optional fields present
    bonus = sum(0.05 for field in optional_fields if field in components)
    confidence = min(1.0, confidence + bonus)

    return round(confidence, 2)


# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize libpostal on startup"""
    logger.info("Address Normalization Service starting...")
    logger.info("libpostal initialized and ready")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
