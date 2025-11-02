"""
Address Normalization Module

This module provides address parsing and normalization functionality
using the libpostal service for the Real Estate OS platform.
"""

from .libpostal_client import LibpostalClient, AddressComponents, NormalizedAddress

__all__ = ['LibpostalClient', 'AddressComponents', 'NormalizedAddress']
__version__ = '1.0.0'
