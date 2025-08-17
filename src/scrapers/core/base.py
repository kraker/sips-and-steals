#!/usr/bin/env python3
"""
Simplified base scraper interface focusing on core scraping concerns
HTTP handling, parsing, and post-processing are delegated to specialized classes
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

# Import our models and components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from models import Restaurant, Deal, ScrapingStatus, DealValidator

from .http_client import HttpClient
from ..processors.post_processor import PostProcessor
from ..exceptions import ScrapingError, TemporaryScrapingError, PermanentScrapingError

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Simplified base scraper focusing on core responsibilities:
    1. Define scraping interface
    2. Orchestrate HTTP client, parsers, and post-processors
    3. Handle high-level error management
    """
    
    def __init__(self, restaurant: Restaurant, config: Dict[str, Any] = None):
        self.restaurant = restaurant
        self.config = config or {}
        self.start_time = datetime.now()
        
        # Initialize specialized components
        self.http_client = HttpClient(self._get_http_config())
        self.post_processor = PostProcessor(self.config) if self.config else None
    
    def _get_http_config(self) -> Dict[str, Any]:
        """Extract HTTP-specific configuration"""
        http_config = {}
        
        if hasattr(self.restaurant, 'scraping_config'):
            scraping_config = self.restaurant.scraping_config
            http_config.update({
                'timeout_seconds': getattr(scraping_config, 'timeout_seconds', 30),
                'custom_headers': getattr(scraping_config, 'custom_headers', {}),
                'base_delay': 2.0,
                'max_delay': 60.0
            })
        
        return http_config
    
    @abstractmethod
    def scrape_deals(self) -> List[Deal]:
        """
        Core scraping method to be implemented by subclasses
        Should return raw deals before post-processing
        """
        pass
    
    def fetch_page(self, url: Optional[str] = None) -> str:
        """Fetch and return page content as string"""
        if url:
            urls_to_try = [url]
        elif hasattr(self.restaurant, 'websites') and getattr(self.restaurant, 'websites'):
            urls_to_try = getattr(self.restaurant, 'websites')
        else:
            urls_to_try = [self.restaurant.website] if self.restaurant.website else []
        
        if not urls_to_try:
            raise PermanentScrapingError("No URLs provided for scraping")
        
        # Try each URL until we get valid content
        for url in urls_to_try:
            try:
                response = self.http_client.fetch_url(url)
                # Basic content validation
                if len(response.text) > 500:  # Minimum content threshold
                    return response.text
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                continue
        
        raise PermanentScrapingError("No valid content found at any URL")
    
    def run(self) -> Tuple[ScrapingStatus, List[Deal], Optional[str]]:
        """
        Main execution method with comprehensive error handling
        Returns (status, deals, error_message)
        """
        error_message = None
        deals = []
        
        try:
            logger.info(f"Starting scrape for {self.restaurant.name}")
            
            # Update scraping metadata
            if hasattr(self.restaurant, 'scraping_config'):
                self.restaurant.scraping_config.last_scraped = datetime.now()
            
            # Scrape raw deals
            raw_deals = self.scrape_deals()
            
            # Apply post-processing if configured
            if self.post_processor:
                deals = self.post_processor.enhance_deals(raw_deals)
                logger.info(f"Post-processing enhanced {len(raw_deals)} deals to {len(deals)} deals")
            else:
                deals = raw_deals
            
            # Validate deals
            valid_deals = []
            for deal in deals:
                issues = DealValidator.validate_deal(deal)
                if not issues:
                    valid_deals.append(deal)
                else:
                    logger.warning(f"Invalid deal for {self.restaurant.name}: {issues}")
            
            if valid_deals:
                # Update restaurant with live deals
                self.restaurant.live_deals = valid_deals
                self.restaurant.deals_last_updated = datetime.now()
                
                if hasattr(self.restaurant, 'scraping_config'):
                    self.restaurant.scraping_config.last_success = datetime.now()
                    self.restaurant.scraping_config.consecutive_failures = 0
                
                logger.info(f"Successfully scraped {len(valid_deals)} deals for {self.restaurant.name}")
                return ScrapingStatus.SUCCESS, valid_deals, None
            else:
                return ScrapingStatus.FAILURE, [], "No valid deals found"
        
        except PermanentScrapingError as e:
            error_message = f"Permanent error: {str(e)}"
            logger.error(f"Permanent scraping error for {self.restaurant.name}: {e}")
            
            if hasattr(self.restaurant, 'scraping_config'):
                self.restaurant.scraping_config.consecutive_failures += 1
                # Disable scraping if too many permanent failures
                if self.restaurant.scraping_config.consecutive_failures >= 5:
                    self.restaurant.scraping_config.enabled = False
                    error_message += " (scraping disabled due to repeated failures)"
            
            return ScrapingStatus.ERROR, [], error_message
        
        except TemporaryScrapingError as e:
            error_message = f"Temporary error: {str(e)}"
            logger.warning(f"Temporary scraping error for {self.restaurant.name}: {e}")
            
            if hasattr(self.restaurant, 'scraping_config'):
                self.restaurant.scraping_config.consecutive_failures += 1
            
            return ScrapingStatus.FAILURE, [], error_message
        
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error scraping {self.restaurant.name}: {e}")
            
            if hasattr(self.restaurant, 'scraping_config'):
                self.restaurant.scraping_config.consecutive_failures += 1
            
            return ScrapingStatus.ERROR, [], error_message
        
        finally:
            # Always be polite with delays
            self.http_client.adaptive_delay()
            
            elapsed = (datetime.now() - self.start_time).total_seconds()
            logger.info(f"Scraping completed for {self.restaurant.name} in {elapsed:.2f}s")


class ConfigBasedScraper(BaseScraper):
    """
    Scraper that uses YAML configuration for pattern matching
    This replaces the complex pattern matching logic from the original BaseScraper
    """
    
    def scrape_deals(self) -> List[Deal]:
        """Scrape using configuration-based patterns"""
        from ..processors.text_processor import TextProcessor
        from bs4 import BeautifulSoup
        
        # Fetch page content
        content = self.fetch_page()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Use text processor to extract deals based on config
        text_processor = TextProcessor(self.config)
        deals = text_processor.extract_deals(soup)
        
        return deals