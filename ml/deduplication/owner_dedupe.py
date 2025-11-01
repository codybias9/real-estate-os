"""Owner deduplication with Splink (PR#7)

Uses probabilistic record linkage to identify duplicate owner entities.
"""

from typing import List, Dict
import splink
from splink.duckdb.linker import DuckDBLinker

class OwnerDeduplicator:
    """Deduplicate owner entities using Splink"""
    
    def __init__(self):
        self.linker = None
        self.model_trained = False
    
    def normalize_owner_name(self, name: str) -> str:
        """Normalize owner name using libpostal
        
        Args:
            name: Raw owner name
            
        Returns:
            Normalized name
        """
        # Use libpostal for address parsing
        # import postal
        # parsed = postal.parser.parse_address(name)
        pass
    
    def train_linkage_model(self, training_data: List[Dict]):
        """Train Splink linkage model
        
        Args:
            training_data: List of owner records
        """
        settings = {
            "link_type": "dedupe_only",
            "blocking_rules_to_generate_predictions": [
                "l.owner_last_name = r.owner_last_name",
                "l.mailing_zip = r.mailing_zip",
            ],
            "comparisons": [
                splink.comparison_library.jaro_winkler_at_thresholds("owner_name"),
                splink.comparison_library.exact_match("mailing_address"),
                splink.comparison_library.levenshtein_at_thresholds("phone"),
            ],
        }
        
        self.linker = DuckDBLinker(training_data, settings)
        self.model_trained = True
    
    def find_duplicates(self, owners: List[Dict], confidence_threshold: float = 0.9):
        """Find duplicate owners
        
        Args:
            owners: List of owner records
            confidence_threshold: Minimum confidence for match
            
        Returns:
            Clusters of duplicate owners with confidence scores
        """
        if not self.model_trained:
            self.train_linkage_model(owners)
        
        results = self.linker.predict()
        clusters = self.linker.cluster_pairwise_predictions_at_threshold(
            results, confidence_threshold
        )
        return clusters
