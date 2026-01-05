"""
Multi-state property scrapers for tax deed/lien auctions.

This module contains scrapers for various state tax sale platforms:
- Alabama DOR (tax lien) - not yet integrated
- Arkansas COSL (tax deed) - active
- Texas counties (redeemable deed) - future
- Florida counties (hybrid) - future
"""

from .arkansas_cosl import ArkansasCOSLScraper
from .factory import ScraperFactory, ScrapeResult

__all__ = [
    'ArkansasCOSLScraper',
    'ScraperFactory',
    'ScrapeResult',
]
