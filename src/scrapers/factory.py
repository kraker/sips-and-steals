#!/usr/bin/env python3
"""
Scraper factory for creating appropriate scrapers based on restaurant configuration
"""

import logging
from typing import Optional, Dict, Any
import importlib

# Import models and base classes
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Restaurant
from config_manager import ConfigManager

from .core.base import BaseScraper, ConfigBasedScraper
from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ScraperFactory:
    """Factory for creating appropriate scrapers based on restaurant configuration"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self._scraper_cache = {}
    
    def create_scraper(self, restaurant: Restaurant) -> BaseScraper:
        """Create appropriate scraper for the restaurant"""
        
        # Use the restaurant's actual slug if available, otherwise generate one
        restaurant_slug = getattr(restaurant, 'slug', None) or self._generate_slug(restaurant.name)
        
        # Check if we have a custom scraper implementation
        custom_scraper = self._try_load_custom_scraper(restaurant_slug, restaurant)
        if custom_scraper:
            return custom_scraper
        
        # Check if we have a YAML configuration
        config = self.config_manager.get_full_config(restaurant_slug)
        if config:
            logger.info(f"Using config-based scraper for {restaurant.name}")
            return ConfigBasedScraper(restaurant, config)
        
        # Fallback to basic config scraper
        logger.info(f"Using default config scraper for {restaurant.name}")
        return ConfigBasedScraper(restaurant, {})
    
    def _try_load_custom_scraper(self, restaurant_slug: str, restaurant: Restaurant) -> Optional[BaseScraper]:
        """Try to load a custom scraper implementation"""
        
        # Check cache first
        cache_key = f"custom_{restaurant_slug}"
        if cache_key in self._scraper_cache:
            scraper_class = self._scraper_cache[cache_key]
            if scraper_class:
                return scraper_class(restaurant)
            else:
                return None
        
        try:
            # Try to import custom scraper module
            module_name = f"scrapers.restaurant_scrapers.{restaurant_slug}"
            module = importlib.import_module(module_name)
            
            # Look for scraper class (should end with 'Scraper')
            scraper_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseScraper) and 
                    attr != BaseScraper and
                    attr_name.endswith('Scraper')):
                    scraper_class = attr
                    break
            
            if scraper_class:
                logger.info(f"Found custom scraper: {scraper_class.__name__} for {restaurant.name}")
                self._scraper_cache[cache_key] = scraper_class
                return scraper_class(restaurant)
            else:
                logger.debug(f"No scraper class found in module {module_name}")
                self._scraper_cache[cache_key] = None
                return None
                
        except ImportError:
            logger.debug(f"No custom scraper module found for {restaurant_slug}")
            self._scraper_cache[cache_key] = None
            return None
        except Exception as e:
            logger.error(f"Error loading custom scraper for {restaurant_slug}: {e}")
            self._scraper_cache[cache_key] = None
            return None
    
    def _generate_slug(self, restaurant_name: str) -> str:
        """Generate URL-safe slug from restaurant name"""
        import re
        
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = restaurant_name.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special characters except hyphens
        slug = re.sub(r'\s+', '-', slug)      # Replace spaces with hyphens
        slug = re.sub(r'-+', '-', slug)       # Collapse multiple hyphens to single hyphen
        slug = slug.strip('-')                # Remove leading/trailing hyphens
        
        return slug
    
    def list_available_scrapers(self) -> Dict[str, str]:
        """List all available scrapers (custom and config-based)"""
        scrapers = {}
        
        # Add custom scrapers
        try:
            scrapers_dir = os.path.join(os.path.dirname(__file__), 'restaurant_scrapers')
            if os.path.exists(scrapers_dir):
                for filename in os.listdir(scrapers_dir):
                    if filename.endswith('.py') and not filename.startswith('__'):
                        slug = filename[:-3]  # Remove .py extension
                        scrapers[slug] = 'custom'
        except Exception as e:
            logger.warning(f"Error scanning custom scrapers: {e}")
        
        # Add config-based scrapers
        for restaurant_slug in self.config_manager.list_configured_restaurants():
            if restaurant_slug not in scrapers:  # Don't override custom scrapers
                scrapers[restaurant_slug] = 'config'
        
        return scrapers
    
    def get_scraper_info(self, restaurant_slug: str) -> Dict[str, Any]:
        """Get detailed information about a scraper"""
        info = {
            'slug': restaurant_slug,
            'type': 'none',
            'has_config': False,
            'has_post_processing': False,
            'has_custom_implementation': False
        }
        
        # Check for custom implementation
        custom_scraper = self._try_load_custom_scraper(restaurant_slug, None)
        if custom_scraper:
            info['type'] = 'custom'
            info['has_custom_implementation'] = True
        
        # Check for YAML configuration
        config = self.config_manager.get_full_config(restaurant_slug)
        if config:
            info['has_config'] = True
            if info['type'] == 'none':
                info['type'] = 'config'
            
            # Check for post-processing
            if 'post_processing' in config:
                info['has_post_processing'] = True
                info['post_processing_features'] = list(config['post_processing'].keys())
        
        return info


# Test the factory
if __name__ == "__main__":
    from models import Restaurant, ScrapingConfig
    
    factory = ScraperFactory()
    
    print("Available scrapers:")
    for slug, scraper_type in factory.list_available_scrapers().items():
        print(f"  {slug}: {scraper_type}")
        info = factory.get_scraper_info(slug)
        if info['has_post_processing']:
            print(f"    - Post-processing: {info['post_processing_features']}")
    
    # Test creating a scraper
    test_restaurant = Restaurant(
        name="Fogo de Chão",
        website="https://fogodechao.com/location/denver/",
        scraping_config=ScrapingConfig()
    )
    
    scraper = factory.create_scraper(test_restaurant)
    print(f"\nCreated scraper for Fogo de Chão: {type(scraper).__name__}")
    
    if hasattr(scraper, 'post_processor') and scraper.post_processor:
        print("  - Has post-processor configured")