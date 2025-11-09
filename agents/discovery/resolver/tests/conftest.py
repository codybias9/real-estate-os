"""Test configuration for discovery resolver agent"""

import sys
from pathlib import Path

# Add resolver src to sys.path
resolver_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(resolver_src))

# Also add contracts to path
contracts_src = Path(__file__).parent.parent.parent.parent / "packages" / "contracts" / "src"
sys.path.insert(0, str(contracts_src))
