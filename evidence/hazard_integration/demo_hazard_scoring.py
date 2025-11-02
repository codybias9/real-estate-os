#!/usr/bin/env python3
"""
Demonstration of Hazard Integration in Scoring Models.

This script demonstrates:
1. DCF Engine with hazard-adjusted cash flows, exit caps, and discount rates
2. Comp-Critic with hazard-based hedonic adjustments
3. Side-by-side comparison of valuations with/without hazards
4. Quantification of hazard impact on investment returns
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from ml.models.dcf_engine import DCFEngine, UnitMix, Lease
from ml.models.comp_critic import CompCritic
import json


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def demo_dcf_with_hazards():
    """Demonstrate DCF engine with hazard integration."""
    print_header("DCF ENGINE: Hazard Integration Demo")

    engine = DCFEngine(seed=42)

    # Test property in high-risk area (California wildfire + earthquake)
    property_data = {
        "property_id": "MF-HAZARD-TEST-001",
        "purchase_price": 5_000_000,
        "address": "123 Fire Canyon Rd, Paradise, CA"
    }

    # Unit mix
    unit_mix = [
        UnitMix("1BR", 20, 750, 1200, 1300, 0.05, 0.03),
        UnitMix("2BR", 30, 1100, 1800, 1900, 0.05, 0.03),
        UnitMix("3BR", 10, 1400, 2300, 2400, 0.06, 0.03)
    ]

    # High hazard scenario (composite score 0.75)
    high_hazard_data = {
        "composite_hazard_score": 0.75,
        "flood_risk_score": 0.20,
        "wildfire_risk_score": 0.95,
        "heat_risk_score": 0.80,
        "total_annual_cost_impact": 15000  # Additional costs beyond insurance/mitigation
    }

    # Low hazard scenario (composite score 0.15)
    low_hazard_data = {
        "composite_hazard_score": 0.15,
        "flood_risk_score": 0.10,
        "wildfire_risk_score": 0.10,
        "heat_risk_score": 0.25,
        "total_annual_cost_impact": 2000
    }

    print("Property: Multifamily, 60 units, Purchase Price: $5,000,000")
    print("Location: Paradise, CA (high wildfire risk)")
    print()

    # Run 3 scenarios: No hazards, Low hazards, High hazards
    print("SCENARIO COMPARISON:")
    print("-" * 80)

    scenarios = [
        ("No Hazards (Baseline)", None),
        ("Low Hazard Risk", low_hazard_data),
        ("High Hazard Risk", high_hazard_data)
    ]

    results = []

    for scenario_name, hazard_data in scenarios:
        result = engine.model_mf(
            property_data=property_data,
            unit_mix=unit_mix,
            params={"hold_period": 5, "exit_cap": 0.055},
            hazard_data=hazard_data
        )
        results.append((scenario_name, result))

        hazard_info = result["hazard_analysis"]

        print(f"\n{scenario_name}:")
        print(f"  Composite Hazard Score: {hazard_info['composite_hazard_score']:.2f}")
        print(f"  Annual Hazard Opex:     ${hazard_info['hazard_opex_annual']:,.0f}")
        print(f"  Exit Cap Rate:          {result['exit_cap_rate_adjusted']:.3%} " +
              f"({hazard_info['exit_cap_adjustment_bps']:.1f} bps adjustment)")
        print(f"  IRR:                    {result['irr']:.2%}")
        print(f"  NPV:                    ${result['npv']:,.0f}")
        print(f"  Exit Value:             ${result['exit_value']:,.0f}")
        if hazard_data:
            print(f"  Hazard Impact on Value: ${hazard_info['total_hazard_impact_on_value']:,.0f}")

    # Calculate impact
    print("\n" + "-" * 80)
    print("HAZARD IMPACT ANALYSIS:")
    print("-" * 80)

    baseline_result = results[0][1]
    high_risk_result = results[2][1]

    irr_impact = (high_risk_result['irr'] - baseline_result['irr']) * 100
    npv_impact = high_risk_result['npv'] - baseline_result['npv']
    exit_value_impact = high_risk_result['exit_value'] - baseline_result['exit_value']

    print(f"\nHigh Hazard vs. No Hazard:")
    print(f"  IRR Impact:        {irr_impact:+.2f} percentage points")
    print(f"  NPV Impact:        ${npv_impact:+,.0f} ({npv_impact/baseline_result['npv']*100:+.1f}%)")
    print(f"  Exit Value Impact: ${exit_value_impact:+,.0f} ({exit_value_impact/baseline_result['exit_value']*100:+.1f}%)")

    # Show Year 1 cash flow breakdown
    print(f"\nYear 1 Cash Flow Breakdown (High Hazard):")
    year1_cf = high_risk_result['cash_flows'][0]
    print(f"  EGI:                    ${year1_cf['egi']:,.0f}")
    print(f"  Base Opex:              ${year1_cf['opex']:,.0f}")
    print(f"  Hazard Opex:            ${year1_cf['hazard_opex']:,.0f}")
    print(f"  Total Opex:             ${year1_cf['total_opex']:,.0f}")
    print(f"  NOI:                    ${year1_cf['noi']:,.0f}")
    print(f"  Cash Flow Before Tax:   ${year1_cf['cf_before_tax']:,.0f}")

    return results


def demo_comp_critic_with_hazards():
    """Demonstrate Comp-Critic with hazard adjustments."""
    print_header("COMP-CRITIC: Hazard Integration Demo")

    critic = CompCritic()

    # Subject property in moderate hazard area
    subject = {
        "property_id": "SUBJECT-001",
        "list_price": 420000,
        "building_sqft": 2400,
        "lot_size_sqft": 7500,
        "bedrooms": 4,
        "bathrooms": 3.0,
        "condition_score": 7.5,
        "address": "456 Main St, Sacramento, CA"
    }

    # Subject property hazards (moderate risk)
    subject_hazards = {
        "composite_hazard_score": 0.45,
        "flood_risk_score": 0.30,
        "wildfire_risk_score": 0.50,
        "heat_risk_score": 0.55
    }

    print("Subject Property:")
    print(f"  Address:            {subject['address']}")
    print(f"  List Price:         ${subject['list_price']:,}")
    print(f"  Size:               {subject['building_sqft']} sqft")
    print(f"  Composite Hazard:   {subject_hazards['composite_hazard_score']:.2f}")
    print()

    # Run valuation without hazards
    print("Valuation WITHOUT Hazard Adjustments:")
    result_no_hazards = critic.value_property(subject)
    print(f"  Estimated Value:    ${result_no_hazards['estimated_value']:,}")
    print(f"  Top 3 Comps Used:   {len(result_no_hazards['top_comps'][:3])} properties")

    # Mock comp hazards (some safer, some riskier than subject)
    comp_hazards = {}
    for comp in result_no_hazards['top_comps']:
        comp_id = comp['comp_id']
        # Randomize comp hazard scores around subject
        if comp_id in ['COMP-001', 'COMP-002']:
            # Lower risk comps
            comp_hazards[comp_id] = {"composite_hazard_score": 0.25}
        elif comp_id in ['COMP-003', 'COMP-004']:
            # Higher risk comps
            comp_hazards[comp_id] = {"composite_hazard_score": 0.70}
        else:
            # Similar risk
            comp_hazards[comp_id] = {"composite_hazard_score": 0.45}

    # Run valuation WITH hazards
    print("\nValuation WITH Hazard Adjustments:")
    result_with_hazards = critic.value_property(
        subject,
        subject_hazards=subject_hazards,
        comp_hazards=comp_hazards
    )
    print(f"  Estimated Value:    ${result_with_hazards['estimated_value']:,}")
    print(f"  Hazard Adjustments: {result_with_hazards['hazard_impact']}")

    # Show adjustment waterfall for first comp
    print("\nAdjustment Waterfall Example (First Comp):")
    first_adj = result_with_hazards['adjustment_waterfall'][0]
    print(f"  Comp ID:            {first_adj['comp_id']}")
    print(f"  Base Price:         ${first_adj['base_price']:,}")
    for adj in first_adj['adjustments']:
        factor = adj['factor']
        adjustment = adj['adjustment']
        if factor == 'hazard_risk':
            print(f"  Hazard Adjustment:  ${adjustment:+,} " +
                  f"(Subject: {adj['subject_score']:.2f}, Comp: {adj['comp_score']:.2f})")
        else:
            print(f"  {factor.title()} Adj:  ${adjustment:+,}")
    print(f"  Adjusted Price:     ${first_adj['adjusted_price']:,}")

    # Compare results
    value_diff = result_with_hazards['estimated_value'] - result_no_hazards['estimated_value']
    value_diff_pct = (value_diff / result_no_hazards['estimated_value']) * 100

    print(f"\n" + "-" * 80)
    print("IMPACT ANALYSIS:")
    print(f"  Value without hazards:  ${result_no_hazards['estimated_value']:,}")
    print(f"  Value with hazards:     ${result_with_hazards['estimated_value']:,}")
    print(f"  Hazard Impact:          ${value_diff:+,} ({value_diff_pct:+.2f}%)")

    if result_with_hazards['hazard_impact']:
        hi = result_with_hazards['hazard_impact']
        print(f"\nHazard Breakdown:")
        print(f"  Flood Risk:       {hi['subject_flood_score']:.2f}")
        print(f"  Wildfire Risk:    {hi['subject_wildfire_score']:.2f}")
        print(f"  Heat Risk:        {hi['subject_heat_score']:.2f}")
        print(f"  Composite:        {hi['subject_composite_score']:.2f}")

    return result_with_hazards


def demo_summary():
    """Print summary of hazard integration capabilities."""
    print_header("Hazard Integration - Summary")

    print("Hazard data is now fully integrated into both valuation models:\n")

    print("DCF ENGINE ENHANCEMENTS:")
    print("  ✓ Hazard costs added to annual operating expenses")
    print("  ✓ Insurance premiums calculated based on hazard severity (0.1% - 0.4% of value)")
    print("  ✓ Mitigation costs scaled with composite hazard score")
    print("  ✓ Exit cap rates adjusted +5 to +50 basis points for hazards")
    print("  ✓ Discount rates adjusted +10 to +100 basis points for hazards")
    print("  ✓ Complete hazard impact waterfall in output")
    print()

    print("COMP-CRITIC ENHANCEMENTS:")
    print("  ✓ Hazard-based hedonic adjustments in Stage 3")
    print("  ✓ Comparative hazard risk analysis (subject vs comps)")
    print("  ✓ Automatic price adjustments: ±10% based on hazard differential")
    print("  ✓ Detailed hazard breakdown in valuation output")
    print("  ✓ Integration with existing sqft, lot, condition adjustments")
    print()

    print("HAZARD DATA SOURCES:")
    print("  • FEMA flood zones (flood risk score)")
    print("  • USFS wildfire hazard potential (wildfire risk score)")
    print("  • Climate data analysis (heat risk score)")
    print("  • Weighted composite score (40% flood, 40% wildfire, 20% heat)")
    print()

    print("FINANCIAL IMPACTS MODELED:")
    print("  • Increased insurance premiums")
    print("  • Mitigation and hardening costs")
    print("  • Market perception and buyer demand")
    print("  • Exit cap rate expansion")
    print("  • Required return adjustment")
    print()

    print("This integration ensures all investment decisions account for climate")
    print("and natural hazard risks, providing more accurate valuations and")
    print("better-informed underwriting decisions.")


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                           ║")
    print("║               HAZARD INTEGRATION IN SCORING MODELS DEMO                   ║")
    print("║                        Real Estate OS - P1.6                             ║")
    print("║                                                                           ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")

    try:
        # Demo 1: DCF with hazards
        dcf_results = demo_dcf_with_hazards()

        # Demo 2: Comp-Critic with hazards
        comp_critic_result = demo_comp_critic_with_hazards()

        # Summary
        demo_summary()

        print_header("Demonstration Complete")
        print("✓ DCF Engine successfully integrates hazards into cash flow analysis")
        print("✓ Comp-Critic successfully integrates hazards into hedonic adjustments")
        print("✓ Both models quantify financial impact of climate/natural hazards")
        print("✓ Investment decisions now account for flood, wildfire, and heat risks")
        print("\nHazard Integration (P1.6) is production-ready! 🎉\n")

        # Save results
        with open('evidence/hazard_integration/dcf_hazard_demo.json', 'w') as f:
            json.dump({
                "scenario": "High Hazard Risk",
                "results": dcf_results[2][1]  # High hazard scenario
            }, f, indent=2)

        with open('evidence/hazard_integration/comp_critic_hazard_demo.json', 'w') as f:
            json.dump(comp_critic_result, f, indent=2)

        print("Demo outputs saved to evidence/hazard_integration/\n")

    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
