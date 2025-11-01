"""PostGIS geographic search (PR#6)

Provides:
- Polygon/radius geographic search
- 200+ property filters
- Saved searches
- Distance calculations
"""

from .search import GeoSearchEngine
from .filters import PropertyFilters

__all__ = ['GeoSearchEngine', 'PropertyFilters']
