#!/usr/bin/env python3
"""
Configuration manager for restaurant-specific scraping settings
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from src.models import ScrapingConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages restaurant-specific scraping configurations"""
    
    def __init__(self, config_dir: str = "config/scrapers"):
        self.config_dir = Path(config_dir)
        self.config_cache = {}
        
    def load_config(self, restaurant_slug: str) -> Optional[Dict[str, Any]]:
        """Load configuration for a specific restaurant"""
        
        # Check cache first
        if restaurant_slug in self.config_cache:
            return self.config_cache[restaurant_slug]
        
        config_file = self.config_dir / f"{restaurant_slug}.yaml"
        
        if not config_file.exists():
            logger.debug(f"No custom config found for {restaurant_slug}")
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Cache the config
            self.config_cache[restaurant_slug] = config
            logger.info(f"Loaded custom config for {restaurant_slug}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading config for {restaurant_slug}: {e}")
            return None
    
    def apply_config_to_scraping_config(self, restaurant_slug: str, scraping_config: ScrapingConfig) -> ScrapingConfig:
        """Apply custom configuration to a ScrapingConfig object"""
        
        config = self.load_config(restaurant_slug)
        if not config or 'scraping_config' not in config:
            return scraping_config
        
        custom_config = config['scraping_config']
        
        # Apply custom settings
        if 'enabled' in custom_config:
            scraping_config.enabled = custom_config['enabled']
        
        if 'fallback_to_static' in custom_config:
            scraping_config.fallback_to_static = custom_config['fallback_to_static']
        
        if 'custom_selectors' in custom_config:
            scraping_config.custom_selectors = custom_config['custom_selectors']
        
        if 'time_pattern_regex' in custom_config:
            scraping_config.time_pattern_regex = custom_config['time_pattern_regex']
        
        if 'day_pattern_regex' in custom_config:
            scraping_config.day_pattern_regex = custom_config['day_pattern_regex']
        
        if 'price_pattern_regex' in custom_config:
            scraping_config.price_pattern_regex = custom_config['price_pattern_regex']
        
        if 'exclude_patterns' in custom_config:
            scraping_config.exclude_patterns = custom_config['exclude_patterns']
        
        if 'content_containers' in custom_config:
            scraping_config.content_containers = custom_config['content_containers']
        
        logger.info(f"Applied custom configuration to {restaurant_slug}")
        return scraping_config
    
    def get_full_config(self, restaurant_slug: str) -> Optional[Dict[str, Any]]:
        """Get the full configuration including post-processing rules"""
        return self.load_config(restaurant_slug)
    
    def has_post_processing(self, restaurant_slug: str) -> bool:
        """Check if restaurant has post-processing configuration"""
        config = self.load_config(restaurant_slug)
        return config and 'post_processing' in config
    
    def list_configured_restaurants(self) -> list:
        """List all restaurants with custom configurations"""
        if not self.config_dir.exists():
            return []
        
        configs = []
        for config_file in self.config_dir.glob("*.yaml"):
            slug = config_file.stem
            configs.append(slug)
        
        return configs
    
    def validate_config(self, restaurant_slug: str) -> Dict[str, Any]:
        """Validate a configuration file and return validation results"""
        config = self.load_config(restaurant_slug)
        
        if not config:
            return {"valid": False, "errors": ["Config file not found"]}
        
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['name', 'slug']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate scraping_config section
        if 'scraping_config' in config:
            scraping_config = config['scraping_config']
            
            # Check for valid regex patterns
            import re
            for pattern_field in ['time_pattern_regex', 'day_pattern_regex', 'price_pattern_regex']:
                if pattern_field in scraping_config:
                    try:
                        re.compile(scraping_config[pattern_field])
                    except re.error as e:
                        errors.append(f"Invalid regex in {pattern_field}: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "config": config
        }


if __name__ == "__main__":
    # Test the config manager
    manager = ConfigManager()
    
    print("Configured restaurants:")
    for restaurant in manager.list_configured_restaurants():
        print(f"  - {restaurant}")
        validation = manager.validate_config(restaurant)
        if validation["valid"]:
            print(f"    ✅ Valid configuration")
        else:
            print(f"    ❌ Errors: {validation['errors']}")