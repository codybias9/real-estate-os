"""Document generation package for investor memos and property reports."""

from .generator import InvestorMemoGenerator
from .service import DocumentService

__all__ = ['InvestorMemoGenerator', 'DocumentService']
