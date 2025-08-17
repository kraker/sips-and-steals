#!/usr/bin/env python3
"""
Data pipeline to merge scraped data with restaurant metadata
Handles loading, updating, and saving restaurant and deal data
"""

import json
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging
import shutil
from dataclasses import asdict

# Import our models
from src.models import Restaurant, Deal, ScrapingConfig, DealValidator
from src.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class DataManager:
    """
    Manages the data pipeline for restaurant and deal information
    Merges static data from Giovanni's markdown with live scraped data
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Data file paths - Single source architecture
        self.restaurants_file = self.data_dir / "restaurants.json"  # Single source of truth for all restaurant data
        self.deals_archive_dir = self.data_dir / "deals_archive"  # Historical data
        self.deals_archive_dir.mkdir(exist_ok=True)
        
        # Create backup directory
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Initialize config manager for custom scraping configurations
        self.config_manager = ConfigManager()
        
        self.restaurants: Dict[str, Restaurant] = {}
        self._load_data()
    
    def _load_data(self):
        """Load all data from files"""
        self._load_restaurants()
        logger.info(f"Loaded {len(self.restaurants)} restaurants")
    
    def _load_restaurants(self):
        """Load restaurant data from single source (restaurants.json)"""
        if self.restaurants_file.exists():
            with open(self.restaurants_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both old nested format and new flat format
            if 'restaurants' in data:
                # New flat format
                for slug, restaurant_data in data['restaurants'].items():
                    restaurant = self._convert_restaurant_data(restaurant_data)
                    self.restaurants[slug] = restaurant
            elif 'areas' in data:
                # Legacy nested format - convert to flat
                for area_name, restaurants in data.get('areas', {}).items():
                    for slug, restaurant_data in restaurants.items():
                        restaurant = self._convert_giovanni_to_restaurant(restaurant_data, area_name)
                        self.restaurants[slug] = restaurant
    
    def _convert_restaurant_data(self, data: Dict[str, Any]) -> Restaurant:
        """Convert flat restaurant format to Restaurant object"""
        # Handle address data with backward compatibility
        address_data = data.get('address')
        address = None
        if address_data:
            if isinstance(address_data, dict):
                # New structured format
                from src.models import Address
                address = Address.from_dict(address_data)
            elif isinstance(address_data, str):
                # Legacy string format - convert to structured
                from src.models import Address
                address = Address.from_string(address_data, confidence_score=0.5)
        
        # Phone is now managed through contact_info only
        
        # Create scraping config based on website availability
        website = data.get('website')
        slug = data.get('slug')
        scraping_config = ScrapingConfig(
            enabled=bool(website),
            scraping_frequency_hours=24,  # Default to daily
            max_retries=3,
            fallback_to_static=True
        )
        
        # Apply custom configuration if available
        if slug:
            scraping_config = self.config_manager.apply_config_to_scraping_config(slug, scraping_config)
        
        restaurant = Restaurant(
            name=data.get('name', ''),
            slug=data.get('slug', ''),
            district=data.get('district'),  # Use district field directly
            neighborhood=data.get('neighborhood'),  # Renamed from sub_location
            address=address,
            cuisine=data.get('cuisine'),
            website=website,
            timezone=data.get('timezone', 'America/Denver'),
            operating_hours=data.get('operating_hours', {}),
            special_notes=data.get('special_notes', []),
            scraping_config=scraping_config
        )
        
        # Load static deals if present (stored as raw dicts)
        restaurant.static_deals = data.get('static_deals', [])
        
        # Load live deals if present (convert from dicts to Deal objects)
        live_deals_data = data.get('live_deals', [])
        restaurant.live_deals = [Deal.from_dict(deal_data) for deal_data in live_deals_data]
        
        # Load deals last updated timestamp
        if data.get('deals_last_updated'):
            restaurant.deals_last_updated = datetime.fromisoformat(data['deals_last_updated'])
        
        # Add multiple URLs support
        if 'scraping_urls' in data:
            restaurant.scraping_urls = data['scraping_urls']
        elif 'websites' in data:  # Legacy support
            restaurant.scraping_urls = data['websites']
        
        # Add scraping hints support
        if 'scraping_hints' in data:
            restaurant.scraping_hints = data['scraping_hints']
        
        # Load contact_info if present
        if 'contact_info' in data and data['contact_info']:
            from src.models import ContactInfo
            contact_data = data['contact_info']
            restaurant.contact_info = ContactInfo(
                primary_phone=contact_data.get('primary_phone'),
                reservation_phone=contact_data.get('reservation_phone'),
                general_email=contact_data.get('general_email'),
                reservations_email=contact_data.get('reservations_email'),
                events_email=contact_data.get('events_email'),
                instagram=contact_data.get('instagram'),
                facebook=contact_data.get('facebook'),
                twitter=contact_data.get('twitter'),
                tiktok=contact_data.get('tiktok')
            )
        
        return restaurant
    
    def _convert_giovanni_to_restaurant(self, data: Dict[str, Any], area: str) -> Restaurant:
        """Convert Giovanni's restaurant format to Restaurant object"""
        # Extract address  
        address = data.get('address', '')
        
        # Create scraping config based on website availability
        website = data.get('website')
        slug = data.get('slug')
        scraping_config = ScrapingConfig(
            enabled=bool(website),
            scraping_frequency_hours=24,  # Default to daily
            max_retries=3,
            fallback_to_static=True
        )
        
        # Apply custom configuration if available
        if slug:
            scraping_config = self.config_manager.apply_config_to_scraping_config(slug, scraping_config)
        
        restaurant = Restaurant(
            name=data.get('name', ''),
            slug=data.get('slug', ''),
            district=data.get('district', area),
            neighborhood=data.get('sub_location'),
            address=address,
            cuisine=data.get('cuisine'),
            website=website,
            static_deals=data.get('static_deals', []),
            special_notes=data.get('special_notes', []),
            scraping_config=scraping_config
        )
        
        # Add multiple URLs support
        if 'scraping_urls' in data:
            restaurant.scraping_urls = data['scraping_urls']
        elif 'websites' in data:  # Legacy support
            restaurant.scraping_urls = data['websites']
        
        # Add scraping hints support
        if 'scraping_hints' in data:
            restaurant.scraping_hints = data['scraping_hints']
        
        return restaurant
    
    
    def save_data(self, create_backup: bool = True):
        """Save all data to single restaurants.json file with optional backup"""
        if create_backup:
            self._create_backup()
        
        self._save_restaurants()
        logger.info("Data saved successfully")
    
    def save_single_restaurant(self, restaurant_slug: str, create_backup: bool = False):
        """Save a single restaurant's data immediately after successful extraction"""
        if restaurant_slug not in self.restaurants:
            logger.warning(f"Restaurant {restaurant_slug} not found, cannot save")
            return
        
        # For single restaurant saves, we update the full file but skip backup by default
        # This prevents data loss while being efficient for batch operations
        if create_backup:
            self._create_backup()
        
        self._save_restaurants()
        logger.info(f"Successfully saved data for {restaurant_slug}")
    
    def _create_backup(self):
        """Create timestamped backup of current data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = self.backup_dir / f"backup_{timestamp}"
        backup_subdir.mkdir(exist_ok=True)
        
        # Backup restaurants
        if self.restaurants_file.exists():
            shutil.copy2(self.restaurants_file, backup_subdir / "restaurants.json")
        
        
        # Keep only last 10 backups
        backups = sorted(self.backup_dir.glob("backup_*"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                shutil.rmtree(old_backup)
    
    def _save_restaurants(self):
        """Save restaurant data back to single source (restaurants.json)"""
        # Use new flat format
        data = {
            'metadata': {
                'source': 'enhanced_data_pipeline',
                'updated_at': datetime.now().isoformat(),
                'districts': [],
                'districts_with_neighborhoods': {}
            },
            'restaurants': {}
        }
        
        # Build flat structure
        districts = set()
        neighborhoods = {}
        
        for slug, restaurant in self.restaurants.items():
            districts.add(restaurant.district)
            
            # Track neighborhoods by district
            if restaurant.district not in neighborhoods:
                neighborhoods[restaurant.district] = set()
            if restaurant.neighborhood:
                neighborhoods[restaurant.district].add(restaurant.neighborhood)
            
            # Convert restaurant using the complete to_dict() method to include all enhanced fields
            restaurant_dict = restaurant.to_dict()
            
            # Remove fields that shouldn't be persisted to restaurants.json
            if 'live_deals' in restaurant_dict:
                del restaurant_dict['live_deals']  # Live deals are saved separately
            if 'deals_last_updated' in restaurant_dict:
                del restaurant_dict['deals_last_updated']  # This goes in metadata below
            
            # Add multiple URLs support if present
            if hasattr(restaurant, 'scraping_urls') and restaurant.scraping_urls:
                restaurant_dict['scraping_urls'] = restaurant.scraping_urls
            
            # Add scraping hints if present
            if hasattr(restaurant, 'scraping_hints') and restaurant.scraping_hints:
                restaurant_dict['scraping_hints'] = restaurant.scraping_hints
            
            # Add live data metadata if available
            if restaurant.live_deals and restaurant.deals_last_updated:
                restaurant_dict['live_data_available'] = True
                restaurant_dict['last_updated'] = restaurant.deals_last_updated.isoformat()
            else:
                restaurant_dict['live_data_available'] = False
                if 'last_updated' not in restaurant_dict:
                    restaurant_dict['last_updated'] = None
            
            data['restaurants'][slug] = restaurant_dict
        
        # Set metadata
        data['metadata']['districts'] = sorted(list(districts))
        data['metadata']['districts_with_neighborhoods'] = {
            district: sorted(list(neighs)) for district, neighs in neighborhoods.items()
        }
        
        with open(self.restaurants_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    
    def get_restaurant(self, slug: str) -> Optional[Restaurant]:
        """Get restaurant by slug"""
        return self.restaurants.get(slug)
    
    def get_restaurants_needing_scraping(self) -> List[Restaurant]:
        """Get list of restaurants that need scraping"""
        return [restaurant for restaurant in self.restaurants.values() if restaurant.needs_scraping()]
    
    def get_restaurants_by_district(self, district: str) -> List[Restaurant]:
        """Get restaurants in a specific district"""
        return [r for r in self.restaurants.values() if r.district == district]
    
    def get_restaurants_by_neighborhood(self, neighborhood: str) -> List[Restaurant]:
        """Get restaurants in a specific neighborhood"""
        return [r for r in self.restaurants.values() if r.neighborhood and r.neighborhood.lower() == neighborhood.lower()]
    
    def get_restaurants_with_website(self) -> List[Restaurant]:
        """Get restaurants that have websites for scraping"""
        return [r for r in self.restaurants.values() if r.website and r.scraping_config.enabled]
    
    def update_restaurant_deals(self, slug: str, deals: List[Deal], status: str = "success"):
        """Update deals for a specific restaurant"""
        if slug not in self.restaurants:
            logger.error(f"Restaurant {slug} not found")
            return
        
        restaurant = self.restaurants[slug]
        
        # Validate deals before saving
        valid_deals = []
        for deal in deals:
            issues = DealValidator.validate_deal(deal)
            if not issues:
                valid_deals.append(deal)
            else:
                logger.warning(f"Invalid deal for {restaurant.name}: {issues}")
        
        # Update restaurant
        restaurant.live_deals = valid_deals
        restaurant.deals_last_updated = datetime.now()
        
        if status == "success":
            restaurant.scraping_config.last_success = datetime.now()
            restaurant.scraping_config.consecutive_failures = 0
        else:
            restaurant.scraping_config.consecutive_failures += 1
        
        # Archive deals for historical tracking
        self._archive_deals(slug, valid_deals)
        
        logger.info(f"Updated {len(valid_deals)} deals for {restaurant.name}")
    
    def _archive_deals(self, slug: str, deals: List[Deal]):
        """Archive deals for historical analysis"""
        if not deals:
            return
        
        archive_file = self.deals_archive_dir / f"{slug}_{datetime.now().strftime('%Y%m%d')}.json"
        
        archive_data = {
            'restaurant_slug': slug,
            'archived_at': datetime.now().isoformat(),
            'deals': [deal.to_dict() for deal in deals]
        }
        
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(archive_data, f, indent=2, ensure_ascii=False, default=str)
    
    def get_scraping_stats(self) -> Dict[str, Any]:
        """Get statistics about scraping performance"""
        total_restaurants = len(self.restaurants)
        with_websites = len(self.get_restaurants_with_website())
        with_live_deals = len([r for r in self.restaurants.values() if r.live_deals])
        
        # Calculate freshness
        fresh_deals = 0
        for restaurant in self.restaurants.values():
            if (restaurant.deals_last_updated and 
                (datetime.now() - restaurant.deals_last_updated).days < 2):
                fresh_deals += 1
        
        # Calculate success rate
        recent_successes = 0
        recent_attempts = 0
        for restaurant in self.restaurants.values():
            if restaurant.scraping_config.last_scraped:
                recent_attempts += 1
                if (restaurant.scraping_config.last_success and
                    restaurant.scraping_config.consecutive_failures == 0):
                    recent_successes += 1
        
        success_rate = recent_successes / recent_attempts * 100 if recent_attempts > 0 else 0
        
        return {
            'total_restaurants': total_restaurants,
            'restaurants_with_websites': with_websites,
            'restaurants_with_live_deals': with_live_deals,
            'restaurants_with_fresh_deals': fresh_deals,
            'scraping_success_rate': round(success_rate, 1),
            'coverage_percentage': round(with_live_deals / total_restaurants * 100, 1) if total_restaurants > 0 else 0
        }
    
    def export_for_website(self) -> Dict[str, Any]:
        """Export data in format needed for website generation"""
        # Collect new district names after geographic mapping
        new_districts = set()
        
        export_data = {
            'metadata': {
                'source': 'enhanced_data_pipeline',
                'updated_at': datetime.now().isoformat(),
                'districts': [],  # Will be populated below
                'total_restaurants': len(self.restaurants),
                'target_user': 'Value-Conscious Culinary Adventurer',
                'focus': 'Quality dining experiences at accessible prices',
                'scraping_stats': self.get_scraping_stats()
            },
            'restaurants': {}
        }
        
        # Export restaurants in a flat structure organized by slug
        for restaurant in self.restaurants.values():
            # Get current deals (live or fallback to static)
            current_deals = restaurant.get_current_deals()
            
            # Get geographic grouping
            metro_area, district_name = self._get_geographic_grouping(restaurant.district)
            new_districts.add(district_name)  # Collect new district names
            
            # Convert to simplified website format
            restaurant_data = {
                'name': restaurant.name,
                'slug': restaurant.slug,
                'district': district_name,  # Use new district name
                'metro_area': metro_area,   # Add metro area grouping
                'neighborhood': restaurant.neighborhood,
                'address': restaurant.address.to_dict() if restaurant.address else None,
                'cuisine': restaurant.cuisine,
                'website': restaurant.website,
                'phone': restaurant.contact_info.primary_phone if restaurant.contact_info else None,
                'operating_hours': restaurant.operating_hours,
                'timezone': restaurant.timezone,
                'is_open_now': restaurant.is_open_now() if restaurant.operating_hours else None,
                'time_until_opens': restaurant.time_until_opens() if restaurant.operating_hours else None,
                'happy_hour_times': self._format_deals_for_index([d for d in current_deals if d.confidence_score >= 0.7][:3]),  # Only high-confidence deals
                'special_notes': restaurant.special_notes,
                'live_data_available': bool(restaurant.live_deals),
                'last_updated': restaurant.deals_last_updated.isoformat() if restaurant.deals_last_updated else None
            }
            
            export_data['restaurants'][restaurant.slug] = restaurant_data
        
        # Add geographic area mapping with new district structure
        metro_areas = {}
        districts_with_neighborhoods = {}
        
        for restaurant in self.restaurants.values():
            metro_area, district_name = self._get_geographic_grouping(restaurant.district)
            
            # Track metro areas
            if metro_area not in metro_areas:
                metro_areas[metro_area] = set()
            metro_areas[metro_area].add(district_name)
            
            # Track districts and neighborhoods
            if district_name not in districts_with_neighborhoods:
                districts_with_neighborhoods[district_name] = set()
            if restaurant.neighborhood:
                districts_with_neighborhoods[district_name].add(restaurant.neighborhood)
        
        # Convert sets to sorted lists and update metadata
        export_data['metadata']['districts'] = sorted(list(new_districts))
        export_data['metadata']['metro_areas'] = {
            area: sorted(list(districts)) for area, districts in metro_areas.items()
        }
        export_data['metadata']['districts_with_neighborhoods'] = {
            district: sorted(list(neighborhoods))
            for district, neighborhoods in districts_with_neighborhoods.items()
        }
        
        return export_data
    
    def _format_deals_for_index(self, deals: List['Deal']) -> List[str]:
        """Format deals for display on the index page with compact day ranges"""
        formatted_deals = []
        
        for deal in deals:
            if not deal:
                continue
                
            # Build the deal string with formatted days
            parts = []
            
            # Add formatted days
            if deal.days_of_week:
                days_str = self._format_day_range([day.value for day in deal.days_of_week])
                parts.append(days_str)
            
            # Add time range
            if deal.is_all_day:
                parts.append("All Day")
            elif deal.start_time and deal.end_time:
                parts.append(f"{deal.start_time} - {deal.end_time}")
            
            # Add price if available
            if deal.prices:
                parts.append(f"({', '.join(deal.prices)})")
            
            if parts:
                formatted_deals.append(" ".join(parts))
            elif deal.description:
                # Fallback to description if we can't format properly
                formatted_deals.append(deal.description)
        
        return formatted_deals
    
    def _format_day_range(self, days):
        """Format a list of days into compact ranges like 'Mon - Sun' or 'Mon, Wed, Fri'"""
        if not days:
            return ""
        
        # Define day order for sorting and range detection
        day_order = {
            'monday': 1, 'tuesday': 2, 'wednesday': 3, 'thursday': 4,
            'friday': 5, 'saturday': 6, 'sunday': 7
        }
        
        day_abbrev = {
            'monday': 'Mon', 'tuesday': 'Tue', 'wednesday': 'Wed', 'thursday': 'Thu',
            'friday': 'Fri', 'saturday': 'Sat', 'sunday': 'Sun'
        }
        
        # Normalize to lowercase and sort by day order
        normalized_days = [day.lower().strip() for day in days if day.lower().strip() in day_order]
        sorted_days = sorted(normalized_days, key=lambda x: day_order[x])
        
        if not sorted_days:
            return ", ".join(days)  # Fallback to original if we can't parse
        
        # Special case: all 7 days
        if len(sorted_days) == 7:
            return "Daily"
        
        # Special case: Monday through Friday
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        if sorted_days == weekdays:
            return "Mon - Fri"
        
        # Special case: Saturday and Sunday
        weekend = ['saturday', 'sunday']
        if sorted_days == weekend:
            return "Sat - Sun"
        
        # Look for consecutive ranges
        ranges = []
        start = 0
        
        while start < len(sorted_days):
            end = start
            
            # Find the end of consecutive days
            while (end + 1 < len(sorted_days) and 
                   day_order[sorted_days[end + 1]] == day_order[sorted_days[end]] + 1):
                end += 1
            
            # If we have a range of 3 or more consecutive days, format as range
            if end - start >= 2:
                ranges.append(f"{day_abbrev[sorted_days[start]]} - {day_abbrev[sorted_days[end]]}")
            elif end - start == 1:
                # Two consecutive days, still show as range for brevity
                ranges.append(f"{day_abbrev[sorted_days[start]]} - {day_abbrev[sorted_days[end]]}")
            else:
                # Single day
                ranges.append(day_abbrev[sorted_days[start]])
            
            start = end + 1
        
        return ", ".join(ranges)
    
    def _get_geographic_grouping(self, district: str) -> tuple[str, str]:
        """
        Map old district names to new geographic groupings.
        Returns (metro_area, district_name)
        """
        district_mapping = {
            # Denver Metropolitan Area
            "Central": ("Denver Metro", "Central Denver"),
            "East & Southeast Denver": ("Denver Metro", "East & Southeast Denver"),
            "Northwest Denver": ("Denver Metro", "Northwest Denver"),
            "North Denver": ("Denver Metro", "North Denver"),
            "Northeast Denver": ("Denver Metro", "Northeast Denver"),
            "South": ("Denver Metro", "South Denver"),
            "West & Southwest Denver": ("Denver Metro", "West & Southwest Denver"),
            "Aurora": ("Denver Metro", "Aurora"),
            "Greenwood Village, Englewood, Littleton, Centennial": ("Denver Metro", "South Suburbs"),
            "Lakewood/Wheat Ridge/Golden": ("Denver Metro", "West Suburbs"),
            
            # Boulder Area
            "Boulder": ("Boulder", "Boulder")
        }
        
        return district_mapping.get(district, ("Denver Metro", district))
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old archived data"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for archive_file in self.deals_archive_dir.glob("*.json"):
            if archive_file.stat().st_mtime < cutoff_date.timestamp():
                archive_file.unlink()
                logger.info(f"Deleted old archive file: {archive_file.name}")


if __name__ == "__main__":
    # Test the data manager
    dm = DataManager()
    
    print(f"Loaded {len(dm.restaurants)} restaurants")
    print("Scraping stats:", dm.get_scraping_stats())
    
    # Show restaurants that need scraping
    need_scraping = dm.get_restaurants_needing_scraping()
    print(f"{len(need_scraping)} restaurants need scraping")
    
    for restaurant in need_scraping[:5]:  # Show first 5
        print(f"  - {restaurant.name} ({restaurant.website})")