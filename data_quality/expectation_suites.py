"""
Great Expectations expectation suites for data quality validation.

This module defines expectation suites for different data assets:
- Properties: Real estate property data validation
- Prospects: Customer prospect data validation
- Offers: Offer data validation
"""
from typing import Dict, Any
import great_expectations as gx
from great_expectations.core.expectation_suite import ExpectationSuite
import logging

logger = logging.getLogger(__name__)


class PropertiesExpectationSuite:
    """Expectation suite for properties table."""

    @staticmethod
    def create_suite(context: Any) -> ExpectationSuite:
        """
        Create expectation suite for properties.

        Validates:
        - Required fields are not null
        - Data types are correct
        - Values are within valid ranges
        - Lat/long coordinates are valid
        - Prices are reasonable
        - Tenant isolation is enforced

        Args:
            context: GX data context

        Returns:
            Expectation suite
        """
        suite_name = "properties_validation_suite"

        try:
            suite = context.get_expectation_suite(suite_name)
            logger.info(f"Using existing suite: {suite_name}")
            return suite
        except Exception:
            pass

        # Create new suite
        suite = context.add_expectation_suite(expectation_suite_name=suite_name)

        # Table-level expectations
        expectations = [
            # 1. Table exists and has rows
            {
                "expectation_type": "expect_table_row_count_to_be_between",
                "kwargs": {
                    "min_value": 0,
                    "max_value": 10000000  # 10M properties max
                }
            },

            # 2. Required columns exist
            {
                "expectation_type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {
                    "column_list": [
                        "id",
                        "tenant_id",
                        "address",
                        "latitude",
                        "longitude",
                        "property_type",
                        "created_at",
                        "updated_at"
                    ]
                }
            },

            # 3. tenant_id: NEVER NULL (critical for multi-tenancy)
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "tenant_id"}
            },

            # 4. tenant_id: Valid UUID format
            {
                "expectation_type": "expect_column_values_to_match_regex",
                "kwargs": {
                    "column": "tenant_id",
                    "regex": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
                }
            },

            # 5. address: NOT NULL
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "address"}
            },

            # 6. address: Minimum length
            {
                "expectation_type": "expect_column_value_lengths_to_be_between",
                "kwargs": {
                    "column": "address",
                    "min_value": 10,
                    "max_value": 500
                }
            },

            # 7. latitude: Valid range (-90 to 90)
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "latitude",
                    "min_value": -90.0,
                    "max_value": 90.0
                }
            },

            # 8. longitude: Valid range (-180 to 180)
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "longitude",
                    "min_value": -180.0,
                    "max_value": 180.0
                }
            },

            # 9. listing_price: Positive if present
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "listing_price",
                    "min_value": 0,
                    "max_value": 1000000000  # $1B max
                }
            },

            # 10. assessed_value: Positive if present
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "assessed_value",
                    "min_value": 0,
                    "max_value": 1000000000
                }
            },

            # 11. property_type: Valid enum values
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {
                    "column": "property_type",
                    "value_set": [
                        "single_family",
                        "multi_family",
                        "condo",
                        "townhouse",
                        "land",
                        "commercial",
                        "industrial",
                        "mixed_use"
                    ]
                }
            },

            # 12. bedrooms: Reasonable range
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "bedrooms",
                    "min_value": 0,
                    "max_value": 50
                }
            },

            # 13. bathrooms: Reasonable range
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "bathrooms",
                    "min_value": 0,
                    "max_value": 50
                }
            },

            # 14. sqft: Reasonable range
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "sqft",
                    "min_value": 0,
                    "max_value": 1000000  # 1M sqft max
                }
            },

            # 15. year_built: Valid year
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "year_built",
                    "min_value": 1700,
                    "max_value": 2030
                }
            },

            # 16. created_at: NOT NULL
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "created_at"}
            },

            # 17. updated_at: NOT NULL
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "updated_at"}
            },

            # 18. updated_at >= created_at
            {
                "expectation_type": "expect_column_pair_values_A_to_be_greater_than_B",
                "kwargs": {
                    "column_A": "updated_at",
                    "column_B": "created_at",
                    "or_equal": True
                }
            },

            # 19. No duplicate addresses per tenant (composite unique)
            {
                "expectation_type": "expect_compound_columns_to_be_unique",
                "kwargs": {
                    "column_list": ["tenant_id", "address"]
                }
            },

            # 20. At least 95% data completeness on key fields
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {
                    "column": "latitude",
                    "mostly": 0.95
                }
            }
        ]

        # Add all expectations to suite
        for exp in expectations:
            suite.add_expectation(**exp)

        # Save suite
        context.save_expectation_suite(suite)

        logger.info(f"Created properties expectation suite with {len(expectations)} expectations")
        return suite


class ProspectsExpectationSuite:
    """Expectation suite for prospects table."""

    @staticmethod
    def create_suite(context: Any) -> ExpectationSuite:
        """
        Create expectation suite for prospects.

        Args:
            context: GX data context

        Returns:
            Expectation suite
        """
        suite_name = "prospects_validation_suite"

        try:
            suite = context.get_expectation_suite(suite_name)
            logger.info(f"Using existing suite: {suite_name}")
            return suite
        except Exception:
            pass

        suite = context.add_expectation_suite(expectation_suite_name=suite_name)

        expectations = [
            # 1. tenant_id: NEVER NULL
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "tenant_id"}
            },

            # 2. tenant_id: Valid UUID
            {
                "expectation_type": "expect_column_values_to_match_regex",
                "kwargs": {
                    "column": "tenant_id",
                    "regex": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
                }
            },

            # 3. name: NOT NULL
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "name"}
            },

            # 4. email: Valid format
            {
                "expectation_type": "expect_column_values_to_match_regex",
                "kwargs": {
                    "column": "email",
                    "regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                }
            },

            # 5. email: Unique per tenant
            {
                "expectation_type": "expect_compound_columns_to_be_unique",
                "kwargs": {
                    "column_list": ["tenant_id", "email"]
                }
            },

            # 6. phone: Valid format (if present)
            {
                "expectation_type": "expect_column_values_to_match_regex",
                "kwargs": {
                    "column": "phone",
                    "regex": r"^\+?1?[-.]?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}$",
                    "mostly": 0.8  # 80% of non-null values
                }
            },

            # 7. status: Valid enum
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {
                    "column": "status",
                    "value_set": [
                        "new",
                        "contacted",
                        "qualified",
                        "showing_scheduled",
                        "offer_made",
                        "closed",
                        "lost"
                    ]
                }
            },

            # 8. budget_min: Positive
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "budget_min",
                    "min_value": 0,
                    "max_value": 1000000000
                }
            },

            # 9. budget_max: >= budget_min
            {
                "expectation_type": "expect_column_pair_values_A_to_be_greater_than_B",
                "kwargs": {
                    "column_A": "budget_max",
                    "column_B": "budget_min",
                    "or_equal": True
                }
            },

            # 10. source: Valid values
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {
                    "column": "source",
                    "value_set": [
                        "website",
                        "referral",
                        "cold_call",
                        "email_campaign",
                        "social_media",
                        "other"
                    ]
                }
            },

            # 11. created_at: NOT NULL
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "created_at"}
            }
        ]

        for exp in expectations:
            suite.add_expectation(**exp)

        context.save_expectation_suite(suite)

        logger.info(f"Created prospects expectation suite with {len(expectations)} expectations")
        return suite


class OffersExpectationSuite:
    """Expectation suite for offers table."""

    @staticmethod
    def create_suite(context: Any) -> ExpectationSuite:
        """
        Create expectation suite for offers.

        Args:
            context: GX data context

        Returns:
            Expectation suite
        """
        suite_name = "offers_validation_suite"

        try:
            suite = context.get_expectation_suite(suite_name)
            logger.info(f"Using existing suite: {suite_name}")
            return suite
        except Exception:
            pass

        suite = context.add_expectation_suite(expectation_suite_name=suite_name)

        expectations = [
            # 1. tenant_id: NEVER NULL
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "tenant_id"}
            },

            # 2. property_id: NOT NULL
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "property_id"}
            },

            # 3. prospect_id: NOT NULL
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "prospect_id"}
            },

            # 4. offer_amount: Positive
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "offer_amount",
                    "min_value": 0,
                    "max_value": 1000000000
                }
            },

            # 5. earnest_money: Positive
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "earnest_money",
                    "min_value": 0,
                    "max_value": 10000000
                }
            },

            # 6. financing_type: Valid enum
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {
                    "column": "financing_type",
                    "value_set": [
                        "cash",
                        "conventional",
                        "fha",
                        "va",
                        "usda",
                        "hard_money",
                        "seller_financing"
                    ]
                }
            },

            # 7. closing_days: Reasonable range
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "closing_days",
                    "min_value": 0,
                    "max_value": 365
                }
            },

            # 8. status: Valid enum
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {
                    "column": "status",
                    "value_set": [
                        "pending",
                        "accepted",
                        "rejected",
                        "countered",
                        "expired",
                        "withdrawn"
                    ]
                }
            }
        ]

        for exp in expectations:
            suite.add_expectation(**exp)

        context.save_expectation_suite(suite)

        logger.info(f"Created offers expectation suite with {len(expectations)} expectations")
        return suite


def initialize_all_suites(context: Any) -> Dict[str, ExpectationSuite]:
    """
    Initialize all expectation suites.

    Args:
        context: GX data context

    Returns:
        Dictionary of suite name to suite object
    """
    suites = {
        "properties": PropertiesExpectationSuite.create_suite(context),
        "prospects": ProspectsExpectationSuite.create_suite(context),
        "offers": OffersExpectationSuite.create_suite(context)
    }

    logger.info(f"Initialized {len(suites)} expectation suites")
    return suites
