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
from models import Restaurant, Deal, ScrapingConfig, DealValidator

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
        self.live_deals_file = self.data_dir / "live_deals.json"  # Latest scraped deals
        self.deals_archive_dir = self.data_dir / "deals_archive"  # Historical data
        self.deals_archive_dir.mkdir(exist_ok=True)
        
        # Create backup directory
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.restaurants: Dict[str, Restaurant] = {}
        self._load_data()
    
    def _load_data(self):
        """Load all data from files"""
        self._load_restaurants()
        self._load_live_deals()
        logger.info(f"Loaded {len(self.restaurants)} restaurants")
    
    def _load_restaurants(self):
        """Load restaurant data from single source (restaurants.json)"""
        if self.restaurants_file.exists():
            with open(self.restaurants_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert format to Restaurant objects
            for area_name, restaurants in data.get('areas', {}).items():
                for slug, restaurant_data in restaurants.items():
                    restaurant = self._convert_giovanni_to_restaurant(restaurant_data, area_name)
                    self.restaurants[slug] = restaurant
    
    def _convert_giovanni_to_restaurant(self, data: Dict[str, Any], area: str) -> Restaurant:
        """Convert Giovanni's restaurant format to Restaurant object"""
        # Extract phone number from address if present
        address = data.get('address', '')
        phone = None
        
        # Create scraping config based on website availability
        website = data.get('website')
        scraping_config = ScrapingConfig(
            enabled=bool(website),
            scraping_frequency_hours=24,  # Default to daily
            max_retries=3,
            fallback_to_static=True
        )
        
        restaurant = Restaurant(
            name=data.get('name', ''),
            slug=data.get('slug', ''),
            district=data.get('district', area),
            neighborhood=data.get('sub_location'),
            address=address,
            cuisine=data.get('cuisine'),
            website=website,
            phone=phone,
            static_happy_hour_times=data.get('happy_hour_times', []),
            special_notes=data.get('special_notes', []),
            scraping_config=scraping_config
        )
        
        # Add multiple URLs support
        if 'websites' in data:
            restaurant.websites = data['websites']
        
        # Add scraping hints support
        if 'scraping_hints' in data:
            restaurant.scraping_hints = data['scraping_hints']
        
        return restaurant
    
    def _load_live_deals(self):
        """Load live deals and associate with restaurants"""
        if not self.live_deals_file.exists():
            return
        
        try:
            with open(self.live_deals_file, 'r', encoding='utf-8') as f:
                deals_data = json.load(f)
            
            for slug, restaurant_deals in deals_data.items():
                if slug in self.restaurants:
                    deals = [Deal.from_dict(deal_data) for deal_data in restaurant_deals.get('deals', [])]
                    self.restaurants[slug].live_deals = deals
                    
                    if restaurant_deals.get('last_updated'):
                        self.restaurants[slug].deals_last_updated = datetime.fromisoformat(
                            restaurant_deals['last_updated']
                        )
                        
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading live deals: {e}")
    
    def save_data(self, create_backup: bool = True):
        """Save all data to files with optional backup"""
        if create_backup:
            self._create_backup()
        
        self._save_restaurants()
        self._save_live_deals()
        logger.info("Data saved successfully")
    
    def _create_backup(self):
        """Create timestamped backup of current data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = self.backup_dir / f"backup_{timestamp}"
        backup_subdir.mkdir(exist_ok=True)
        
        # Backup restaurants
        if self.restaurants_file.exists():
            shutil.copy2(self.restaurants_file, backup_subdir / "restaurants.json")
        
        # Backup live deals
        if self.live_deals_file.exists():
            shutil.copy2(self.live_deals_file, backup_subdir / "live_deals.json")
        
        # Keep only last 10 backups
        backups = sorted(self.backup_dir.glob("backup_*"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                shutil.rmtree(old_backup)
    
    def _save_restaurants(self):
        """Save restaurant data back to single source (restaurants.json)"""
        # Reconstruct the areas format for restaurants.json
        data = {
            'metadata': {
                'source': 'giovanni_happy_hours.md',
                'updated_at': datetime.now().isoformat(),
                'districts': [],
                'districts_with_neighborhoods': {}
            },
            'areas': {}
        }
        
        # Group restaurants by area and build structure
        areas = {}
        districts = set()
        neighborhoods = {}
        
        for slug, restaurant in self.restaurants.items():
            area = restaurant.district
            if area not in areas:
                areas[area] = {}
            
            # Convert restaurant back to Giovanni format but preserve live data info
            restaurant_dict = {
                'name': restaurant.name,
                'slug': restaurant.slug,
                'district': restaurant.district,
                'area': restaurant.district,  # Keep same as district for consistency
                'sub_location': restaurant.neighborhood,
                'address': restaurant.address,
                'cuisine': restaurant.cuisine,
                'website': restaurant.website,
                'phone': restaurant.phone,
                'happy_hour_times': restaurant.static_happy_hour_times or [],
                'special_notes': restaurant.special_notes or []
            }
            
            # Add multiple URLs support if present
            if hasattr(restaurant, 'websites') and restaurant.websites:
                restaurant_dict['websites'] = restaurant.websites
            
            # Add scraping hints if present
            if hasattr(restaurant, 'scraping_hints') and restaurant.scraping_hints:
                restaurant_dict['scraping_hints'] = restaurant.scraping_hints
            
            # Add live data metadata if available
            if restaurant.live_deals and restaurant.deals_last_updated:
                restaurant_dict['live_data_available'] = True
                restaurant_dict['last_updated'] = restaurant.deals_last_updated.isoformat()
            else:
                restaurant_dict['live_data_available'] = False
                restaurant_dict['last_updated'] = None
            
            areas[area][slug] = restaurant_dict
            districts.add(area)
            
            # Track neighborhoods
            if area not in neighborhoods:
                neighborhoods[area] = set()
            if restaurant.neighborhood:
                neighborhoods[area].add(restaurant.neighborhood)
        
        # Set metadata
        data['areas'] = areas
        data['metadata']['districts'] = sorted(list(districts))
        data['metadata']['districts_with_neighborhoods'] = {
            district: sorted(list(neighs)) for district, neighs in neighborhoods.items()
        }
        
        with open(self.restaurants_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _save_live_deals(self):
        """Save live deals data separately for faster loading"""
        data = {}
        for slug, restaurant in self.restaurants.items():
            if restaurant.live_deals or restaurant.deals_last_updated:
                data[slug] = {
                    'deals': [deal.to_dict() for deal in restaurant.live_deals],
                    'last_updated': restaurant.deals_last_updated.isoformat() if restaurant.deals_last_updated else None
                }
        
        with open(self.live_deals_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def get_restaurant(self, slug: str) -> Optional[Restaurant]:
        """Get restaurant by slug"""
        return self.restaurants.get(slug)
    
    def get_restaurants_needing_scraping(self) -> List[Restaurant]:
        """Get list of restaurants that need scraping"""
        return [restaurant for restaurant in self.restaurants.values() if restaurant.needs_scraping()]
    
    def get_restaurants_by_district(self, district: str) -> List[Restaurant]:
        """Get restaurants in a specific district"""
        return [r for r in self.restaurants.values() if r.district == district]
    
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
        # Start with the original format but enhanced with live data
        export_data = {
            'metadata': {
                'source': 'enhanced_data_pipeline',
                'updated_at': datetime.now().isoformat(),
                'districts': list(set(r.district for r in self.restaurants.values())),
                'total_restaurants': len(self.restaurants),
                'target_user': 'Value-Conscious Culinary Adventurer',
                'focus': 'Quality dining experiences at accessible prices',
                'scraping_stats': self.get_scraping_stats()
            },
            'areas': {}
        }
        
        # Group restaurants by district for website compatibility
        for restaurant in self.restaurants.values():
            district = restaurant.district
            if district not in export_data['areas']:
                export_data['areas'][district] = {}
            
            # Get current deals (live or fallback to static)
            current_deals = restaurant.get_current_deals()
            
            # Convert back to website format
            restaurant_data = {
                'name': restaurant.name,
                'slug': restaurant.slug,
                'district': restaurant.district,
                'area': restaurant.district,  # Backwards compatibility
                'sub_location': restaurant.neighborhood,
                'address': restaurant.address,
                'cuisine': restaurant.cuisine,
                'website': restaurant.website,
                'phone': restaurant.phone,
                'happy_hour_times': self._format_deals_for_index(current_deals[:3]),  # Limit for display
                'special_notes': restaurant.special_notes,
                'live_data_available': bool(restaurant.live_deals),
                'last_updated': restaurant.deals_last_updated.isoformat() if restaurant.deals_last_updated else None
            }
            
            export_data['areas'][district][restaurant.slug] = restaurant_data
        
        # Add district/neighborhood mapping
        districts_with_neighborhoods = {}
        for restaurant in self.restaurants.values():
            district = restaurant.district
            if district not in districts_with_neighborhoods:
                districts_with_neighborhoods[district] = set()
            if restaurant.neighborhood:
                districts_with_neighborhoods[district].add(restaurant.neighborhood)
        
        # Convert sets to sorted lists
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
            if deal.price:
                parts.append(f"({deal.price})")
            
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