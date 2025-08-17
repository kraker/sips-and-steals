"""
Senor Bear scraper for happy hour deals
"""
from typing import List
from src.scrapers.base import BaseScraper
from src.models import Deal, DealType
from src.scrapers.core.base import ConfigBasedScraper


class SenorBearScraper(ConfigBasedScraper):
    """Scraper for Senor Bear using YAML configuration"""
    
    def __init__(self):
        super().__init__('senor-bear')
    
    def get_restaurant_identifier(self) -> str:
        return "senor-bear"