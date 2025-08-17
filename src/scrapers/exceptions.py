#!/usr/bin/env python3
"""
Custom exceptions for the scraping system
"""


class ScrapingError(Exception):
    """Base exception for scraping errors"""
    pass


class TemporaryScrapingError(ScrapingError):
    """Temporary error that should be retried"""
    pass


class PermanentScrapingError(ScrapingError):
    """Permanent error that should not be retried"""
    pass


class ConfigurationError(ScrapingError):
    """Error in scraper configuration"""
    pass


class ValidationError(ScrapingError):
    """Error in deal validation"""
    pass