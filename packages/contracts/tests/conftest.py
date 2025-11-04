"""Test configuration for contracts package"""

import sys
from pathlib import Path

# Add contracts src to sys.path
contracts_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(contracts_src))
