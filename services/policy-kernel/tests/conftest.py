"""Test configuration for policy-kernel service"""

import sys
from pathlib import Path

# Add policy-kernel src to sys.path
policy_kernel_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(policy_kernel_src))
