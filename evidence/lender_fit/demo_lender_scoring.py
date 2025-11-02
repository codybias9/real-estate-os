"""
Lender Fit Scoring Demo.

Demonstrates lender matching for different deal and borrower profiles.
"""
from ml.lender_fit.lender_scoring import (
    LenderFitScorer,
    DealCharacteristics,
    BorrowerProfile,
    PropertyType,
    LoanPurpose,
    get_sample_lenders
)


def print_lender_matches(matches, deal, borrower):
    """Print lender match results."""
    print(f"Deal LTV: {deal.ltv:.1f}%")
    if deal.dscr:
        print(f"Deal DSCR: {deal.dscr:.2f}x")
    print(f"Borrower Credit: {borrower.credit_score}")
    print(f"Borrower Experience: {borrower.num_properties_owned} properties, {borrower.years_experience:.1f} years")
    print()

    qualified = [m for m in matches if m.qualified]
    print(f"Qualified Lenders: {len(qualified)}/{len(matches)}")
    print()

    if qualified:
        print("=" * 100)
        print("QUALIFIED LENDERS (ranked by fit score)")
        print("=" * 100)
        print()

        for i, match in enumerate(qualified, 1):
            print(f"{i}. {match.lender.lender_name} - {match.lender.loan_program_name}")
            print(f"   Fit Score: {match.fit_score:.1f}/100")
            print()
            print(f"   Terms:")
            print(f"     Rate:            {match.estimated_rate:.2f}%")
            print(f"     Term:            {match.lender.loan_term_years} years")
            print(f"     Monthly Payment: ${match.estimated_monthly_payment:,.0f}")
            print(f"     Origination Fee: ${match.estimated_origination_fee:,.0f}")
            print()
            print(f"   Requirements:")
            print(f"     Max LTV:         {match.lender.max_ltv:.0f}%")
            if match.lender.min_dscr:
                print(f"     Min DSCR:        {match.lender.min_dscr:.2f}x")
            print(f"     Min Credit:      {match.lender.min_credit_score}")
            print(f"     Min Properties:  {match.lender.min_properties_owned}")
            print(f"     Min Reserves:    {match.lender.min_reserves_months:.0f} months")
            print()
            print(f"   Fit Breakdown:")
            print(f"     LTV:       {match.ltv_fit:.1f}/100")
            print(f"     DSCR:      {match.dscr_fit:.1f}/100")
            print(f"     Credit:    {match.credit_fit:.1f}/100")
            print(f"     Experience: {match.experience_fit:.1f}/100")
            print(f"     Reserves:  {match.reserves_fit:.1f}/100")
            print()
            if match.warnings:
                print(f"   Warnings:")
                for warning in match.warnings:
                    print(f"     ⚠ {warning}")
                print()
            print("-" * 100)
            print()
    else:
        print("NO QUALIFIED LENDERS")
        print()
        print("Disqualification reasons:")
        for match in matches:
            if match.disqualification_reasons:
                print(f"\n{match.lender.lender_name}:")
                for reason in match.disqualification_reasons:
                    print(f"  ✗ {reason}")
        print()


def demo_experienced_investor():
    """Demo: Experienced investor with good deal."""
    print("=" * 100)
    print("SCENARIO 1: Experienced Investor with Good Deal")
    print("=" * 100)
    print()

    deal = DealCharacteristics(
        property_type=PropertyType.MULTIFAMILY_5_PLUS,
        property_value=1200000,
        loan_amount=900000,  # 75% LTV
        state="CA",
        city="San Francisco",
        msa="San Francisco-Oakland-Berkeley, CA",
        purchase_price=1200000,
        monthly_rent=18000,
        monthly_expenses=7000,
        loan_purpose=LoanPurpose.PURCHASE
    )

    borrower = BorrowerProfile(
        credit_score=740,
        num_properties_owned=5,
        years_experience=8.0,
        liquid_reserves=18.0,  # 18 months
        net_worth=2500000,
        annual_income=180000
    )

    lenders = get_sample_lenders()
    scorer = LenderFitScorer(lenders)
    matches = scorer.score_lenders(deal, borrower)

    print("Property: 10-unit multifamily building")
    print(f"Value: ${deal.property_value:,}")
    print(f"Loan Amount: ${deal.loan_amount:,}")
    print()

    print_lender_matches(matches, deal, borrower)


def demo_first_time_investor():
    """Demo: First-time investor with moderate deal."""
    print("\n\n")
    print("=" * 100)
    print("SCENARIO 2: First-Time Investor")
    print("=" * 100)
    print()

    deal = DealCharacteristics(
        property_type=PropertyType.RESIDENTIAL_1_4_UNIT,
        property_value=400000,
        loan_amount=320000,  # 80% LTV
        state="TX",
        city="Austin",
        purchase_price=400000,
        monthly_rent=2800,
        monthly_expenses=800,
        loan_purpose=LoanPurpose.PURCHASE
    )

    borrower = BorrowerProfile(
        credit_score=680,
        num_properties_owned=0,  # First property
        years_experience=0,
        liquid_reserves=9.0,  # 9 months
        net_worth=200000,
        annual_income=120000
    )

    lenders = get_sample_lenders()
    scorer = LenderFitScorer(lenders)
    matches = scorer.score_lenders(deal, borrower)

    print("Property: Single-family rental")
    print(f"Value: ${deal.property_value:,}")
    print(f"Loan Amount: ${deal.loan_amount:,}")
    print()

    print_lender_matches(matches, deal, borrower)


def demo_marginal_deal():
    """Demo: Marginal deal with tight metrics."""
    print("\n\n")
    print("=" * 100)
    print("SCENARIO 3: Marginal Deal with Tight Metrics")
    print("=" * 100)
    print()

    deal = DealCharacteristics(
        property_type=PropertyType.RESIDENTIAL_1_4_UNIT,
        property_value=500000,
        loan_amount=400000,  # 80% LTV
        state="CA",
        city="Los Angeles",
        purchase_price=500000,
        monthly_rent=3200,  # Low rent = low DSCR
        monthly_expenses=700,
        loan_purpose=LoanPurpose.PURCHASE
    )

    borrower = BorrowerProfile(
        credit_score=650,  # Lower credit
        num_properties_owned=1,
        years_experience=1.5,
        liquid_reserves=7.0,  # Moderate reserves
        net_worth=150000,
        annual_income=95000
    )

    lenders = get_sample_lenders()
    scorer = LenderFitScorer(lenders)
    matches = scorer.score_lenders(deal, borrower)

    print("Property: Small multifamily (duplex)")
    print(f"Value: ${deal.property_value:,}")
    print(f"Loan Amount: ${deal.loan_amount:,}")
    print()

    print_lender_matches(matches, deal, borrower)


def demo_fix_and_flip():
    """Demo: Fix-and-flip with hard money."""
    print("\n\n")
    print("=" * 100)
    print("SCENARIO 4: Fix-and-Flip Deal (Hard Money)")
    print("=" * 100)
    print()

    deal = DealCharacteristics(
        property_type=PropertyType.RESIDENTIAL_1_4_UNIT,
        property_value=300000,  # ARV
        loan_amount=210000,  # 70% LTV on ARV
        state="FL",
        city="Tampa",
        purchase_price=180000,  # Discounted purchase
        monthly_rent=None,  # No rent (will flip)
        monthly_expenses=None,
        loan_purpose=LoanPurpose.BRIDGE  # Short-term bridge loan
    )

    borrower = BorrowerProfile(
        credit_score=620,
        num_properties_owned=2,
        years_experience=3.0,
        liquid_reserves=4.0,  # Lower reserves OK for flip
        net_worth=250000,
        annual_income=80000
    )

    lenders = get_sample_lenders()
    scorer = LenderFitScorer(lenders)
    matches = scorer.score_lenders(deal, borrower)

    print("Property: Fix-and-flip opportunity")
    print(f"ARV: ${deal.property_value:,}")
    print(f"Purchase Price: ${deal.purchase_price:,}")
    print(f"Loan Amount: ${deal.loan_amount:,}")
    print()

    print_lender_matches(matches, deal, borrower)


def demo_lender_comparison():
    """Compare all lender programs side-by-side."""
    print("\n\n")
    print("=" * 100)
    print("LENDER PROGRAM COMPARISON")
    print("=" * 100)
    print()

    lenders = get_sample_lenders()

    print(f"{'Lender':<30} {'Rate':<8} {'Max LTV':<10} {'Min DSCR':<10} {'Min Credit':<12} {'Terms':<10}")
    print("-" * 100)

    for lender in lenders:
        dscr_str = f"{lender.min_dscr:.2f}x" if lender.min_dscr else "N/A"
        print(
            f"{lender.lender_name:<30} "
            f"{lender.interest_rate:.2f}%    "
            f"{lender.max_ltv:.0f}%       "
            f"{dscr_str:<10} "
            f"{lender.min_credit_score:<12} "
            f"{lender.loan_term_years}yr"
        )

    print()
    print("Key Insights:")
    print("  • Prime National Bank: Best rate (6.5%) but strictest requirements")
    print("  • Investor Capital Group: Good balance of terms and flexibility")
    print("  • DSCR Lending: No income verification, first-time investors OK")
    print("  • Quick Close Capital: Hard money for bridge/rehab, highest rate (10%)")
    print()


def main():
    """Run all demos."""
    demo_experienced_investor()
    demo_first_time_investor()
    demo_marginal_deal()
    demo_fix_and_flip()
    demo_lender_comparison()

    print("=" * 100)
    print("Lender Fit Scoring Demo Complete")
    print("=" * 100)
    print()
    print("Key Capabilities:")
    print("  ✓ Multi-factor fit scoring (LTV, DSCR, credit, experience, reserves)")
    print("  ✓ Hard requirement validation (property type, geography, loan size)")
    print("  ✓ Ranked lender recommendations")
    print("  ✓ Detailed disqualification reasons")
    print("  ✓ Warning flags for close matches")
    print("  ✓ Estimated terms and payments")
    print()
    print("API Endpoints:")
    print("  POST /api/v1/lenders/score - Score lender fit for a deal")
    print("  GET  /api/v1/lenders/programs - List all loan programs")
    print("  GET  /api/v1/lenders/requirements/{id} - Get lender requirements")
    print()


if __name__ == "__main__":
    main()
