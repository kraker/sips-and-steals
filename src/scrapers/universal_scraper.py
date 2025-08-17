#!/usr/bin/env python3
"""
Universal Happy Hour Scraper

A wrapper around UniversalHappyHourExtractor that implements the BaseScraper interface
for seamless integration with the scraping architecture.
"""

import logging
from typing import List, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

from models import Restaurant, Deal
from .core.base import BaseScraper
from .universal_extractor import UniversalHappyHourExtractor
from .url_discovery import HappyHourUrlDiscovery

logger = logging.getLogger(__name__)


class UniversalScraper(BaseScraper):
    """
    Universal scraper that works without configuration using intelligent pattern recognition.
    
    Uses the UniversalHappyHourExtractor to identify happy hour content across diverse
    restaurant websites without requiring custom configuration.
    """
    
    def __init__(self, restaurant: Restaurant):
        super().__init__(restaurant)
        self.extractor = UniversalHappyHourExtractor()
        self.url_discovery = HappyHourUrlDiscovery(timeout=8)  # Faster timeout for discovery
        logger.info(f"Initialized universal scraper for {restaurant.name}")
    
    def scrape_deals(self) -> List[Deal]:
        """
        Scrape deals using universal pattern recognition.
        
        Returns:
            List of Deal objects found using universal extraction
        """
        website = self.restaurant.website
        if not website:
            logger.warning(f"No website available for {self.restaurant.name}")
            return []
        
        try:
            # Step 1: Discover best happy hour URL (if URL discovery is enabled)
            best_url = None
            if self.url_discovery:
                try:
                    best_url = self.url_discovery.get_best_url(website)
                except Exception as e:
                    logger.warning(f"URL discovery failed for {self.restaurant.name}: {e}")
            
            target_url = best_url if best_url else website
            
            if best_url:
                logger.info(f"Discovered better happy hour URL for {self.restaurant.name}: {best_url}")
            
            # Step 2: Validate URL before scraping
            is_valid, error_msg = self.extractor.validate_restaurant_url(target_url)
            if not is_valid:
                logger.warning(f"URL validation failed for {self.restaurant.name}: {error_msg}")
                # Try original URL if discovered URL fails
                if best_url and target_url != website:
                    logger.info(f"Trying original URL as fallback: {website}")
                    is_valid, error_msg = self.extractor.validate_restaurant_url(website)
                    if is_valid:
                        target_url = website
                    else:
                        return []
                else:
                    return []
            
            # Step 2: Calculate restaurant type score for debugging
            restaurant_data = {
                'name': self.restaurant.name or '',
                'cuisine': getattr(self.restaurant, 'cuisine', '') or '',
                'type': getattr(self.restaurant, 'type', '') or ''
            }
            type_score = self.extractor.calculate_restaurant_type_score(restaurant_data)
            logger.info(f"Restaurant type score for {self.restaurant.name}: {type_score:.2f}")
            
            # Step 3: Fetch website content
            logger.info(f"Fetching content from {target_url}")
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; SipsAndSteals/1.0; +https://sips-and-steals.com)'
                }
                response = client.get(target_url, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} for {target_url}")
                return []
            
            # Step 4: Parse HTML and extract deals
            soup = BeautifulSoup(response.content, 'html.parser')
            result = self.extractor.extract_from_soup(soup, target_url)
            
            # Step 5: Log extraction results
            if result.deals:
                logger.info(f"Universal extraction found {len(result.deals)} deals for {self.restaurant.name} "
                           f"(confidence: {result.confidence_score:.2f})")
                logger.debug(f"Extraction method: {result.extraction_method}")
            else:
                logger.info(f"No deals found for {self.restaurant.name} using universal extraction")
            
            return result.deals
            
        except Exception as e:
            logger.error(f"Error in universal scraping for {self.restaurant.name}: {e}")
            return []
    
    def get_scraper_info(self) -> dict:
        """Get information about this scraper"""
        return {
            'type': 'universal',
            'description': 'Universal pattern recognition scraper',
            'requires_config': False,
            'supports_js': False,
            'extraction_methods': [
                'happy_hour_keywords',
                'content_container_discovery',
                'context_aware_time_extraction',
                'restaurant_type_scoring'
            ]
        }