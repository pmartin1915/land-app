"""
Multi-state property scrapers for tax deed/lien auctions.

This module contains scrapers for various state tax sale platforms:
- Alabama DOR (tax lien)
- Arkansas COSL (tax deed)
- Texas counties (redeemable deed) - future
- Florida counties (hybrid) - future
"""

from .arkansas_cosl import ArkansasCOSLScraper

__all__ = ['ArkansasCOSLScraper']
