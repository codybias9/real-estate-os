#!/usr/bin/env python3
"""
Generate DCF Golden Path Examples for P0.9

Creates reference outputs for both Multifamily (MF) and Commercial Real Estate (CRE)
DCF models with realistic inputs and hazard integration.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ml.models.dcf_engine import DCFEngine, UnitMix, Lease


def generate_multifamily_golden_example() -> Dict[str, Any]:
    """
    Generate golden path example for multifamily DCF.

    Scenario: 50-unit apartment complex in Austin, TX
    - Mix of 1BR, 2BR, 3BR units
    - Moderate hazard risk (flood + heat)
    - 5-year hold period
    """
    print("=" * 60)
    print("Generating Multifamily DCF Golden Example")
    print("=" * 60)

    # Initialize engine
    engine = DCFEngine(seed=42)

    # Property data
    property_data = {
        "address": "123 Riverside Dr, Austin, TX 78704",
        "year_built": 2015,
        "total_units": 50,
        "total_sqft": 55000,
        "current_noi": 450000,
        "purchase_price": 7500000,
        "acquisition_costs": 150000  # 2% of purchase
    }

    # Unit mix
    unit_mix = [
        UnitMix(
            unit_type="1BR",
            count=20,
            sqft=650,
            current_rent=1200,
            market_rent=1250,
            vacancy_rate=0.05,
            annual_increase=0.03
        ),
        UnitMix(
            unit_type="2BR",
            count=25,
            sqft=950,
            current_rent=1600,
            market_rent=1700,
            vacancy_rate=0.04,
            annual_increase=0.03
        ),
        UnitMix(
            unit_type="3BR",
            count=5,
            sqft=1200,
            current_rent=2100,
            market_rent=2200,
            vacancy_rate=0.03,
            annual_increase=0.03
        )
    ]

    # Hazard data (Austin: moderate flood + high heat)
    hazard_data = {
        "composite_hazard_score": 0.35,  # Moderate risk
        "total_annual_cost_impact": 12000,  # $240/unit/year
        "flood_risk_score": 0.15,
        "wildfire_risk_score": 0.08,
        "heat_risk_score": 0.55  # High heat risk
    }

    # DCF parameters
    params = {
        "hold_period_years": 5,
        "discount_rate": 0.08,
        "exit_cap_rate": 0.055,
        "annual_rent_growth": 0.03,
        "annual_expense_growth": 0.025,
        "renovation_year_3": 250000,  # Mid-cycle renovation
        "refinance_year_3": True,
        "refinance_ltv": 0.70
    }

    print(f"Property: {property_data['address']}")
    print(f"Total Units: {property_data['total_units']}")
    print(f"Purchase Price: ${property_data['purchase_price']:,}")
    print(f"Hazard Score: {hazard_data['composite_hazard_score']:.2f}")
    print()

    # Run DCF model
    print("Running multifamily DCF model...")
    result = engine.model_mf(
        property_data=property_data,
        unit_mix=unit_mix,
        params=params,
        hazard_data=hazard_data
    )

    print("✓ Model complete")
    print(f"NPV: ${result.get('npv', 0):,.2f}")
    print(f"IRR: {result.get('irr', 0):.2%}")
    if 'cash_on_cash_y1' in result:
        print(f"Cash-on-Cash Y1: {result['cash_on_cash_y1']:.2%}")
    print(f"Exit Value: ${result.get('exit_value', 0):,.2f}")
    print()

    return result


def generate_cre_golden_example() -> Dict[str, Any]:
    """
    Generate golden path example for commercial real estate DCF.

    Scenario: Small office building in Denver, CO
    - 3 tenants with varying lease structures
    - Low hazard risk
    - 7-year hold period
    """
    print("=" * 60)
    print("Generating Commercial Real Estate DCF Golden Example")
    print("=" * 60)

    # Initialize engine
    engine = DCFEngine(seed=42)

    # Property data
    property_data = {
        "address": "456 Tech Park Blvd, Denver, CO 80202",
        "year_built": 2010,
        "total_sqft": 25000,
        "current_noi": 275000,
        "purchase_price": 4500000,
        "acquisition_costs": 90000  # 2% of purchase
    }

    # Lease rollover schedule
    leases = [
        Lease(
            tenant_name="Tech Startup Inc",
            sqft=10000,
            annual_rent=120000,  # $12/sqft
            lease_start="2022-01-01",
            lease_end="2027-01-01",
            lease_type="NNN",
            renewal_probability=0.70,
            ti_per_sqft=25.0,
            free_rent_months=2
        ),
        Lease(
            tenant_name="Law Firm LLC",
            sqft=8000,
            annual_rent=112000,  # $14/sqft
            lease_start="2021-06-01",
            lease_end="2026-06-01",
            lease_type="NN",
            renewal_probability=0.85,
            ti_per_sqft=30.0,
            free_rent_months=1
        ),
        Lease(
            tenant_name="Accounting Services",
            sqft=7000,
            annual_rent=91000,  # $13/sqft
            lease_start="2023-03-01",
            lease_end="2028-03-01",
            lease_type="Gross",
            renewal_probability=0.75,
            ti_per_sqft=20.0,
            free_rent_months=1
        )
    ]

    # Hazard data (Denver: low hazard risk)
    hazard_data = {
        "composite_hazard_score": 0.12,  # Low risk
        "total_annual_cost_impact": 3000,  # $120/thousand sqft
        "flood_risk_score": 0.05,
        "wildfire_risk_score": 0.15,
        "heat_risk_score": 0.10
    }

    # DCF parameters
    params = {
        "hold_period_years": 7,
        "discount_rate": 0.075,
        "exit_cap_rate": 0.06,
        "management_fee_pct": 0.03,
        "leasing_commission_pct": 0.05,
        "capex_reserve_per_sqft": 1.50,
        "structural_vacancy_rate": 0.05
    }

    print(f"Property: {property_data['address']}")
    print(f"Total SF: {property_data['total_sqft']:,}")
    print(f"Purchase Price: ${property_data['purchase_price']:,}")
    print(f"Tenants: {len(leases)}")
    print(f"Hazard Score: {hazard_data['composite_hazard_score']:.2f}")
    print()

    # Run DCF model
    print("Running commercial real estate DCF model...")
    result = engine.model_cre(
        property_data=property_data,
        leases=leases,
        params=params,
        hazard_data=hazard_data
    )

    print("✓ Model complete")
    print(f"NPV: ${result.get('npv', 0):,.2f}")
    print(f"IRR: {result.get('irr', 0):.2%}")
    if 'equity_multiple' in result:
        print(f"Equity Multiple: {result['equity_multiple']:.2f}x")
    print(f"Exit Value: ${result.get('exit_value', 0):,.2f}")
    print()

    return result


def main():
    """Generate golden path examples for both MF and CRE."""
    print("\n" + "=" * 60)
    print("DCF GOLDEN PATH GENERATION")
    print("=" * 60)
    print(f"Timestamp: {Path(__file__).stem}")
    print("=" * 60 + "\n")

    # Create artifacts directory
    artifacts_dir = project_root / "artifacts" / "dcf"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Generate multifamily example
        mf_result = generate_multifamily_golden_example()
        mf_output_file = artifacts_dir / "golden-mf-output.json"
        with open(mf_output_file, 'w') as f:
            json.dump(mf_result, f, indent=2, default=str)
        print(f"✓ Saved: {mf_output_file}")
        print()

        # Generate CRE example
        cre_result = generate_cre_golden_example()
        cre_output_file = artifacts_dir / "golden-cre-output.json"
        with open(cre_output_file, 'w') as f:
            json.dump(cre_result, f, indent=2, default=str)
        print(f"✓ Saved: {cre_output_file}")
        print()

        # Generate summary comparison
        summary = {
            "multifamily": {
                "property": "50-unit apartment, Austin TX",
                "purchase_price": mf_result.get("inputs", {}).get("purchase_price", 7500000),
                "hazard_score": 0.35,
                "hold_period": 5,
                "npv": mf_result.get("npv", 0),
                "irr": mf_result.get("irr", 0),
                "equity_multiple": mf_result.get("equity_multiple", 0)
            },
            "commercial": {
                "property": "25K SF office, Denver CO",
                "purchase_price": cre_result.get("inputs", {}).get("purchase_price", 4500000),
                "hazard_score": 0.12,
                "hold_period": 7,
                "npv": cre_result.get("npv", 0),
                "irr": cre_result.get("irr", 0),
                "equity_multiple": cre_result.get("equity_multiple", 0)
            },
            "comparison": {
                "mf_higher_risk": bool(0.35 > 0.12),
                "mf_shorter_hold": bool(5 < 7),
                "mf_higher_irr": bool(mf_result.get("irr", 0) > cre_result.get("irr", 0)),
                "notes": "MF has higher risk, shorter hold, but higher IRR"
            }
        }

        summary_file = artifacts_dir / "golden-comparison.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✓ Saved: {summary_file}")
        print()

        # Success summary
        print("=" * 60)
        print("GOLDEN PATH GENERATION COMPLETE")
        print("=" * 60)
        print(f"✓ Generated 2 DCF golden examples")
        print(f"✓ MF NPV: ${mf_result.get('npv', 0):,.2f}")
        print(f"✓ CRE NPV: ${cre_result.get('npv', 0):,.2f}")
        print(f"✓ Artifacts saved to: {artifacts_dir}")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
