"""
Test configuration for API tests
"""

import sys
from pathlib import Path

# Add project root to sys.path so we can import from api package
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
