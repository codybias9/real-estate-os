"""
ARV (After Repair Value) Calculator Demo.

Demonstrates fix-and-flip and value-add investment analysis.
"""
from ml.arv.arv_calculator import (
    ARVCalculator,
    PropertyCondition,
    RenovationItem,
    RenovationPlan,
    calculate_fix_and_flip_roi
)


def demo_basic_flip():
    """Demonstrate basic fix-and-flip analysis."""
    print("=" * 80)
    print("ARV Calculator - Basic Fix-and-Flip Analysis")
    print("=" * 80)
    print()

    calculator = ARVCalculator()

    # Property details
    purchase_price = 180000
    current_value = 200000
    property_sqft = 1800

    print("PROPERTY DETAILS:")
    print(f"  Purchase Price:    ${purchase_price:,}")
    print(f"  Current Value:     ${current_value:,}")
    print(f"  Square Footage:    {property_sqft:,} sqft")
    print(f"  Price per sqft:    ${current_value/property_sqft:.0f}/sqft")
    print()

    # Property condition
    condition = PropertyCondition(
        overall_condition="Fair",
        condition_score=5.5,
        roof_condition=6.0,
        hvac_condition=5.0,
        plumbing_condition=6.0,
        electrical_condition=7.0,
        kitchen_condition=4.0,  # Needs renovation
        bathroom_condition=4.5,  # Needs renovation
        flooring_condition=5.0,
        paint_condition=4.0,
        foundation_condition=7.0,
        year_built=1975,
        last_renovation_year=None
    )

    print("CURRENT CONDITION:")
    print(f"  Overall:           {condition.overall_condition} ({condition.condition_score}/10)")
    print(f"  Kitchen:           {condition.kitchen_condition}/10")
    print(f"  Bathrooms:         {condition.bathroom_condition}/10")
    print(f"  Paint:             {condition.paint_condition}/10")
    print(f"  Year Built:        {condition.year_built}")
    print()

    # Renovation plan
    renovation_items = [
        {
            "category": "Kitchen Remodel (Major)",
            "description": "Complete kitchen renovation with new cabinets, countertops, appliances",
            "cost": 35000,
            "duration_days": 21,
            "priority": "High"
        },
        {
            "category": "Bathroom Remodel (Major)",
            "description": "Master bathroom renovation",
            "cost": 18000,
            "duration_days": 14,
            "priority": "High"
        },
        {
            "category": "Bathroom Remodel (Minor)",
            "description": "Guest bathroom update",
            "cost": 8000,
            "duration_days": 7,
            "priority": "Medium"
        },
        {
            "category": "Paint (Interior)",
            "description": "Full interior paint",
            "cost": 4000,
            "duration_days": 5,
            "priority": "High"
        },
        {
            "category": "Flooring",
            "description": "New hardwood flooring throughout",
            "cost": 12000,
            "duration_days": 7,
            "priority": "High"
        },
        {
            "category": "Landscaping",
            "description": "Front and back yard landscaping",
            "cost": 5000,
            "duration_days": 5,
            "priority": "Medium"
        },
        {
            "category": "Garage Door Replacement",
            "description": "New 2-car garage door",
            "cost": 2500,
            "duration_days": 1,
            "priority": "Medium"
        }
    ]

    renovation_plan = calculator.create_renovation_plan(renovation_items, contingency_percent=0.10)

    print("RENOVATION PLAN:")
    for i, item in enumerate(renovation_plan.items, 1):
        print(f"  {i}. {item.category}")
        print(f"     Cost: ${item.cost:,}")
        print(f"     Value Add: {item.value_add_factor:.0%} (${item.cost * item.value_add_factor:,.0f})")
        print(f"     Duration: {item.duration_days} days")
        print()

    print(f"  Subtotal:          ${sum(i.cost for i in renovation_plan.items):,}")
    print(f"  Contingency (10%): ${renovation_plan.total_cost - sum(i.cost for i in renovation_plan.items):,}")
    print(f"  TOTAL COST:        ${renovation_plan.total_cost:,}")
    print(f"  Expected Value Add: ${renovation_plan.expected_value_add:,}")
    print(f"  Total Duration:    {renovation_plan.total_duration_days} days")
    print()

    # Calculate ARV
    analysis = calculator.calculate_arv(
        current_value=current_value,
        purchase_price=purchase_price,
        condition=condition,
        renovation_plan=renovation_plan,
        property_sqft=property_sqft,
        comp_properties=None  # No comps in this example
    )

    print("=" * 80)
    print("ARV ANALYSIS RESULTS")
    print("=" * 80)
    print()

    print("VALUATION:")
    print(f"  Current Value:     ${analysis.current_value:,}")
    print(f"  Expected Value Add: ${analysis.expected_value_add:,}")
    print(f"  ARV:               ${analysis.arv:,}")
    print(f"  Method:            {analysis.arv_method}")
    print(f"  Confidence:        {analysis.confidence_score:.0%}")
    print()

    print("INVESTMENT:")
    print(f"  Purchase Price:    ${analysis.purchase_price:,}")
    print(f"  Renovation Cost:   ${analysis.renovation_cost:,}")
    print(f"  Total Investment:  ${analysis.total_investment:,}")
    print()

    print("GROSS PROFIT:")
    print(f"  ARV:               ${analysis.arv:,}")
    print(f"  - Investment:      ${analysis.total_investment:,}")
    print(f"  = Gross Profit:    ${analysis.gross_profit:,}")
    print(f"  Gross ROI:         {analysis.roi_percent:.1f}%")
    print()

    print("COSTS:")
    print(f"  Holding Costs ({analysis.holding_months} mo):  ${analysis.holding_costs:,}")
    print(f"  Selling Costs ({analysis.selling_costs_percent:.0%}):  ${analysis.selling_costs:,}")
    print(f"  Total Costs:       ${analysis.holding_costs + analysis.selling_costs:,}")
    print()

    print("NET PROFIT:")
    print(f"  Gross Profit:      ${analysis.gross_profit:,}")
    print(f"  - Holding Costs:   ${analysis.holding_costs:,}")
    print(f"  - Selling Costs:   ${analysis.selling_costs:,}")
    print(f"  = NET PROFIT:      ${analysis.net_profit:,}")
    print(f"  NET ROI:           {analysis.net_roi_percent:.1f}%")
    print()

    print("RENOVATION ROI:")
    print(f"  Renovation Cost:   ${analysis.renovation_cost:,}")
    print(f"  Value Add:         ${analysis.expected_value_add:,}")
    print(f"  ROI:               {analysis.renovation_roi_percent:.1f}%")
    print()

    print("RISK ASSESSMENT:")
    print(f"  Risk Level:        {analysis.risk_level}")
    print(f"  Risk Factors:")
    for factor in analysis.risk_factors:
        print(f"    - {factor}")
    print()

    # Summary
    if analysis.net_roi_percent >= 20:
        verdict = "✓ STRONG DEAL"
    elif analysis.net_roi_percent >= 10:
        verdict = "○ DECENT DEAL"
    else:
        verdict = "✗ WEAK DEAL"

    print(f"VERDICT: {verdict}")
    print()


def demo_quick_roi():
    """Demonstrate quick ROI calculator."""
    print("=" * 80)
    print("Quick Fix-and-Flip ROI Calculator")
    print("=" * 80)
    print()

    scenarios = [
        {
            "name": "Conservative Deal",
            "purchase": 150000,
            "current_value": 160000,
            "renovation": 40000,
            "arv": 240000
        },
        {
            "name": "Aggressive Deal",
            "purchase": 200000,
            "current_value": 220000,
            "renovation": 80000,
            "arv": 350000
        },
        {
            "name": "Marginal Deal",
            "purchase": 180000,
            "current_value": 190000,
            "renovation": 50000,
            "arv": 250000
        }
    ]

    for scenario in scenarios:
        print(f"{scenario['name']}:")
        print(f"  Purchase:  ${scenario['purchase']:,}")
        print(f"  Renovation: ${scenario['renovation']:,}")
        print(f"  ARV:       ${scenario['arv']:,}")
        print()

        metrics = calculate_fix_and_flip_roi(
            purchase_price=scenario['purchase'],
            current_value=scenario['current_value'],
            renovation_cost=scenario['renovation'],
            expected_arv=scenario['arv'],
            holding_months=6
        )

        print(f"  Results:")
        print(f"    Total Investment:   ${metrics['total_investment']:,}")
        print(f"    Gross Profit:       ${metrics['gross_profit']:,}")
        print(f"    Holding Costs:      ${metrics['holding_costs']:,}")
        print(f"    Selling Costs:      ${metrics['selling_costs']:,}")
        print(f"    Net Profit:         ${metrics['net_profit']:,}")
        print(f"    ROI:                {metrics['roi_percent']:.1f}%")
        print()

        if metrics['roi_percent'] >= 20:
            print(f"    ✓ Strong ROI (>20%)")
        elif metrics['roi_percent'] >= 10:
            print(f"    ○ Decent ROI (10-20%)")
        else:
            print(f"    ✗ Weak ROI (<10%)")
        print()
        print("-" * 80)
        print()


def demo_value_add_factors():
    """Demonstrate value add factors by category."""
    print("=" * 80)
    print("Industry-Standard Value Add Factors")
    print("=" * 80)
    print()
    print("Based on Remodeling Magazine Cost vs Value Report")
    print()

    calculator = ARVCalculator()

    # Group by category
    high_roi = []
    medium_roi = []
    low_roi = []

    for category, factor in calculator.value_add_factors.items():
        if factor >= 0.75:
            high_roi.append((category, factor))
        elif factor >= 0.60:
            medium_roi.append((category, factor))
        else:
            low_roi.append((category, factor))

    print("HIGH ROI (≥75% cost recovery):")
    for category, factor in sorted(high_roi, key=lambda x: x[1], reverse=True):
        print(f"  {category:30s}  {factor:.0%}")
    print()

    print("MEDIUM ROI (60-74% cost recovery):")
    for category, factor in sorted(medium_roi, key=lambda x: x[1], reverse=True):
        print(f"  {category:30s}  {factor:.0%}")
    print()

    print("LOWER ROI (<60% cost recovery):")
    for category, factor in sorted(low_roi, key=lambda x: x[1], reverse=True):
        print(f"  {category:30s}  {factor:.0%}")
    print()

    print("Key Insights:")
    print("  ✓ Garage door replacement has highest ROI (94%)")
    print("  ✓ Interior paint delivers 100% cost recovery")
    print("  ✓ Major additions (master suite, bathrooms) have lower ROI")
    print("  ✓ Focus on cosmetic updates for best returns")
    print()


def main():
    """Run all demos."""
    demo_basic_flip()
    print("\n" * 2)
    demo_quick_roi()
    print("\n" * 2)
    demo_value_add_factors()

    print("=" * 80)
    print("ARV Calculator Demo Complete")
    print("=" * 80)
    print()
    print("Key Capabilities:")
    print("  ✓ Complete ARV calculation (cost-based, comp-based, hybrid)")
    print("  ✓ Renovation ROI analysis by category")
    print("  ✓ Fix-and-flip profit calculation (gross and net)")
    print("  ✓ Holding costs and selling costs")
    print("  ✓ Risk assessment")
    print("  ✓ Industry-standard value add factors")
    print()
    print("API Endpoints:")
    print("  POST /api/v1/arv/calculate - Full ARV analysis")
    print("  POST /api/v1/arv/quick-flip-roi - Quick ROI calculator")
    print("  POST /api/v1/arv/renovation-budget - Budget calculator")
    print("  GET  /api/v1/arv/value-add-factors - Standard factors")
    print()


if __name__ == "__main__":
    main()
