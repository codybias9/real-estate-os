"""Feature engineering for property scoring

Extracts numerical features from property data for ML model training and inference.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from decimal import Decimal
import numpy as np

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Feature engineering pipeline for property scoring

    Extracts and transforms features from:
    - Property characteristics (size, bedrooms, etc.)
    - Financial data (prices, values, taxes)
    - Market data (time on market, comparable sales)
    - Location data (demographics, market trends)
    - Temporal features (age, time since sale)
    """

    # Feature names in order
    FEATURE_NAMES = [
        # Property characteristics
        'square_footage',
        'bedrooms',
        'bathrooms',
        'lot_size_sqft',
        'age_years',
        'price_per_sqft',
        'bed_bath_ratio',
        'lot_to_building_ratio',

        # Financial features
        'listing_price',
        'assessed_value',
        'market_value',
        'assessed_to_market_ratio',
        'listing_to_assessed_ratio',
        'listing_to_market_ratio',
        'annual_tax',
        'tax_rate',
        'estimated_equity',

        # Sale history
        'years_since_last_sale',
        'last_sale_price',
        'price_appreciation',
        'annual_appreciation_rate',

        # Market features
        'days_on_market',
        'listing_status_active',
        'property_type_single_family',
        'property_type_condo',
        'property_type_townhouse',

        # Location features (from Census data)
        'zip_population',
        'zip_median_income',
        'zip_median_home_value',
        'zip_owner_occupied_rate',
        'zip_unemployment_rate',

        # Derived features
        'income_to_price_ratio',
        'relative_price_in_zip',
        'is_undervalued',
        'potential_roi',
    ]

    def __init__(self):
        self.current_year = datetime.now().year

    def extract_features(
        self,
        prospect: Dict[str, Any],
        enrichment: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Extract all features from property data

        Args:
            prospect: Prospect data from prospect_queue
            enrichment: Enrichment data from property_enrichment

        Returns:
            Dictionary of feature_name -> value
        """
        features = {}

        # Parse payload
        payload = prospect.get('payload', {})

        # Extract base features
        features.update(self._extract_property_features(payload, enrichment))
        features.update(self._extract_financial_features(payload, enrichment))
        features.update(self._extract_temporal_features(payload, enrichment))
        features.update(self._extract_market_features(payload, enrichment))
        features.update(self._extract_location_features(enrichment))
        features.update(self._extract_derived_features(features, payload, enrichment))

        # Ensure all features are present (fill missing with 0)
        for feature_name in self.FEATURE_NAMES:
            if feature_name not in features:
                features[feature_name] = 0.0

        return features

    def _extract_property_features(
        self,
        payload: Dict,
        enrichment: Optional[Dict]
    ) -> Dict[str, float]:
        """Extract property characteristic features"""
        features = {}

        # Square footage (prefer enrichment, fallback to payload)
        sqft = self._get_value(enrichment, 'square_footage') or \
               self._get_value(payload, 'square_footage')
        features['square_footage'] = float(sqft) if sqft else 0.0

        # Bedrooms
        beds = self._get_value(enrichment, 'bedrooms') or \
               self._get_value(payload, 'bedrooms')
        features['bedrooms'] = float(beds) if beds else 0.0

        # Bathrooms
        baths = self._get_value(enrichment, 'bathrooms') or \
                self._get_value(payload, 'bathrooms')
        features['bathrooms'] = float(baths) if baths else 0.0

        # Lot size
        lot_size = self._get_value(enrichment, 'lot_size_sqft') or \
                   self._get_value(payload, 'lot_size_sqft')
        features['lot_size_sqft'] = float(lot_size) if lot_size else 0.0

        # Age of property
        year_built = self._get_value(enrichment, 'year_built') or \
                     self._get_value(payload, 'year_built')
        if year_built:
            features['age_years'] = max(0, self.current_year - int(year_built))
        else:
            features['age_years'] = 0.0

        # Derived ratios
        if features['square_footage'] > 0 and features['bedrooms'] > 0 and features['bathrooms'] > 0:
            features['bed_bath_ratio'] = features['bedrooms'] / features['bathrooms']
        else:
            features['bed_bath_ratio'] = 0.0

        if features['lot_size_sqft'] > 0 and features['square_footage'] > 0:
            features['lot_to_building_ratio'] = features['lot_size_sqft'] / features['square_footage']
        else:
            features['lot_to_building_ratio'] = 0.0

        return features

    def _extract_financial_features(
        self,
        payload: Dict,
        enrichment: Optional[Dict]
    ) -> Dict[str, float]:
        """Extract financial features"""
        features = {}

        # Listing price
        listing_price = self._get_value(payload, 'listing_price')
        features['listing_price'] = float(listing_price) if listing_price else 0.0

        # Assessed value (from county)
        assessed = self._get_value(enrichment, 'assessed_value')
        features['assessed_value'] = float(assessed) if assessed else 0.0

        # Market value (from county or API)
        market = self._get_value(enrichment, 'market_value')
        features['market_value'] = float(market) if market else 0.0

        # Annual taxes
        tax = self._get_value(enrichment, 'tax_amount_annual')
        features['annual_tax'] = float(tax) if tax else 0.0

        # Price per square foot
        sqft = self._get_value(enrichment, 'square_footage') or \
               self._get_value(payload, 'square_footage')
        if features['listing_price'] > 0 and sqft and float(sqft) > 0:
            features['price_per_sqft'] = features['listing_price'] / float(sqft)
        else:
            features['price_per_sqft'] = 0.0

        # Financial ratios
        if features['assessed_value'] > 0:
            if features['market_value'] > 0:
                features['assessed_to_market_ratio'] = \
                    features['assessed_value'] / features['market_value']
            else:
                features['assessed_to_market_ratio'] = 0.0

            if features['listing_price'] > 0:
                features['listing_to_assessed_ratio'] = \
                    features['listing_price'] / features['assessed_value']
            else:
                features['listing_to_assessed_ratio'] = 0.0
        else:
            features['assessed_to_market_ratio'] = 0.0
            features['listing_to_assessed_ratio'] = 0.0

        if features['market_value'] > 0 and features['listing_price'] > 0:
            features['listing_to_market_ratio'] = \
                features['listing_price'] / features['market_value']
        else:
            features['listing_to_market_ratio'] = 0.0

        # Tax rate (annual tax / assessed value)
        if features['assessed_value'] > 0:
            features['tax_rate'] = features['annual_tax'] / features['assessed_value']
        else:
            features['tax_rate'] = 0.0

        # Estimated equity (assuming market value is current value)
        # This is simplified - would need loan data for accuracy
        if features['market_value'] > 0:
            features['estimated_equity'] = features['market_value']
        else:
            features['estimated_equity'] = 0.0

        return features

    def _extract_temporal_features(
        self,
        payload: Dict,
        enrichment: Optional[Dict]
    ) -> Dict[str, float]:
        """Extract time-based features"""
        features = {}

        # Last sale date
        last_sale_date = self._get_value(enrichment, 'last_sale_date')
        if last_sale_date:
            if isinstance(last_sale_date, str):
                last_sale_date = datetime.fromisoformat(last_sale_date).date()
            elif isinstance(last_sale_date, datetime):
                last_sale_date = last_sale_date.date()

            years_since_sale = (date.today() - last_sale_date).days / 365.25
            features['years_since_last_sale'] = max(0, years_since_sale)
        else:
            features['years_since_last_sale'] = 0.0

        # Last sale price
        last_sale_price = self._get_value(enrichment, 'last_sale_price')
        features['last_sale_price'] = float(last_sale_price) if last_sale_price else 0.0

        # Price appreciation since last sale
        if features['last_sale_price'] > 0:
            current_value = features.get('market_value', 0) or \
                          features.get('listing_price', 0)
            if current_value > 0:
                features['price_appreciation'] = current_value - features['last_sale_price']

                # Annual appreciation rate
                if features['years_since_last_sale'] > 0:
                    appreciation_multiple = current_value / features['last_sale_price']
                    features['annual_appreciation_rate'] = \
                        (appreciation_multiple ** (1 / features['years_since_last_sale'])) - 1
                else:
                    features['annual_appreciation_rate'] = 0.0
            else:
                features['price_appreciation'] = 0.0
                features['annual_appreciation_rate'] = 0.0
        else:
            features['price_appreciation'] = 0.0
            features['annual_appreciation_rate'] = 0.0

        return features

    def _extract_market_features(
        self,
        payload: Dict,
        enrichment: Optional[Dict]
    ) -> Dict[str, float]:
        """Extract market-related features"""
        features = {}

        # Days on market
        dom = self._get_value(payload, 'days_on_market')
        features['days_on_market'] = float(dom) if dom else 0.0

        # Listing status (binary features)
        status = self._get_value(payload, 'listing_status', '').lower()
        features['listing_status_active'] = 1.0 if 'active' in status else 0.0

        # Property type (one-hot encoding)
        prop_type = self._get_value(enrichment, 'property_type') or \
                    self._get_value(payload, 'property_type', '')
        prop_type = prop_type.lower()

        features['property_type_single_family'] = 1.0 if 'single' in prop_type or 'family' in prop_type else 0.0
        features['property_type_condo'] = 1.0 if 'condo' in prop_type else 0.0
        features['property_type_townhouse'] = 1.0 if 'town' in prop_type else 0.0

        return features

    def _extract_location_features(self, enrichment: Optional[Dict]) -> Dict[str, float]:
        """Extract location-based features from Census data"""
        features = {}

        if not enrichment:
            features.update({
                'zip_population': 0.0,
                'zip_median_income': 0.0,
                'zip_median_home_value': 0.0,
                'zip_owner_occupied_rate': 0.0,
                'zip_unemployment_rate': 0.0,
            })
            return features

        # Extract Census data from raw_response
        raw_response = enrichment.get('raw_response', {})
        if isinstance(raw_response, str):
            import json
            try:
                raw_response = json.loads(raw_response)
            except:
                raw_response = {}

        census = raw_response.get('census', {})

        features['zip_population'] = float(census.get('population', 0) or 0)
        features['zip_median_income'] = float(census.get('median_household_income', 0) or 0)
        features['zip_median_home_value'] = float(census.get('median_home_value', 0) or 0)
        features['zip_owner_occupied_rate'] = float(census.get('owner_occupied_rate', 0) or 0)
        features['zip_unemployment_rate'] = float(census.get('unemployment_rate', 0) or 0)

        return features

    def _extract_derived_features(
        self,
        features: Dict[str, float],
        payload: Dict,
        enrichment: Optional[Dict]
    ) -> Dict[str, float]:
        """Calculate derived/composite features"""
        derived = {}

        # Income to price ratio (affordability indicator)
        if features.get('zip_median_income', 0) > 0 and features.get('listing_price', 0) > 0:
            derived['income_to_price_ratio'] = \
                features['zip_median_income'] / features['listing_price']
        else:
            derived['income_to_price_ratio'] = 0.0

        # Relative price in ZIP (compared to ZIP median)
        if features.get('zip_median_home_value', 0) > 0 and features.get('listing_price', 0) > 0:
            derived['relative_price_in_zip'] = \
                features['listing_price'] / features['zip_median_home_value']
        else:
            derived['relative_price_in_zip'] = 0.0

        # Is undervalued? (listing price < assessed or market value)
        listing = features.get('listing_price', 0)
        assessed = features.get('assessed_value', 0)
        market = features.get('market_value', 0)

        if listing > 0 and (assessed > 0 or market > 0):
            comparison_value = max(assessed, market)
            derived['is_undervalued'] = 1.0 if listing < comparison_value * 0.9 else 0.0
        else:
            derived['is_undervalued'] = 0.0

        # Potential ROI estimate
        # This is a simplified calculation - real ROI would need rental estimates, expenses, etc.
        if listing > 0 and features.get('annual_appreciation_rate', 0) > 0:
            derived['potential_roi'] = features['annual_appreciation_rate']
        else:
            derived['potential_roi'] = 0.0

        return derived

    @staticmethod
    def _get_value(data: Optional[Dict], key: str, default=None):
        """Safely get value from dictionary"""
        if not data:
            return default

        value = data.get(key, default)

        # Convert Decimal to float
        if isinstance(value, Decimal):
            return float(value)

        return value

    def get_feature_vector(self, features: Dict[str, float]) -> List[float]:
        """
        Convert feature dictionary to ordered vector

        Args:
            features: Dictionary of feature_name -> value

        Returns:
            List of feature values in standard order
        """
        return [features.get(name, 0.0) for name in self.FEATURE_NAMES]

    def get_feature_importance_dict(self, importance_array: np.ndarray) -> Dict[str, float]:
        """
        Convert feature importance array to dictionary

        Args:
            importance_array: Array of importance values from model

        Returns:
            Dictionary mapping feature names to importance
        """
        return dict(zip(self.FEATURE_NAMES, importance_array.tolist()))
