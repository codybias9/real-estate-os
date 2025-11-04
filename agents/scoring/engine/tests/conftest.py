"""Test configuration for scoring engine agent"""

import sys
from pathlib import Path

# Add scoring engine src to sys.path
engine_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(engine_src))

# Also add contracts to path
contracts_src = Path(__file__).parent.parent.parent.parent.parent / "packages" / "contracts" / "src"
sys.path.insert(0, str(contracts_src))
