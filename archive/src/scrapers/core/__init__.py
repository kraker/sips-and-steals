"""
Core scraping components: HTTP client, base scraper interface, validators
"""

from .base import BaseScraper, ConfigBasedScraper
from .http_client import HttpClient, CircuitBreaker

__all__ = ['BaseScraper', 'ConfigBasedScraper', 'HttpClient', 'CircuitBreaker']