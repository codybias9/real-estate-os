"""Test configuration for enrichment hub agent"""

import sys
from pathlib import Path

# Add enrichment hub src to sys.path
hub_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(hub_src))

# Also add contracts to path
contracts_src = Path(__file__).parent.parent.parent.parent.parent / "packages" / "contracts" / "src"
sys.path.insert(0, str(contracts_src))
