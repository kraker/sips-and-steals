#!/usr/bin/env python3
"""
Migrate to Three-Layer Data Architecture

Migrates existing deals.json to the new three-layer architecture:
- Raw extraction data (debugging/refinement)
- Refined clean data (validated/normalized)
- Presentation data (user-facing)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import uuid

# Add src to path for imports
sys.path.append('src')
from models.deals import (
    DealType, DataQuality, MenuFormat,
    RawExtractionItem, DealSchedule, MenuItem, DealMenu,
    PublicDeal, DealSummary,
    normalize_day_name, normalize_time_24h, classify_deal_type
)


class ThreeLayerMigrator:
    """Migrates existing data to three-layer architecture"""
    
    def __init__(self):
        self.base_dir = Path('.')
        self.data_dir = self.base_dir / 'data'
        
        # Create directories
        (self.data_dir / 'raw').mkdir(exist_ok=True)
        (self.data_dir / 'refined').mkdir(exist_ok=True)
        (self.data_dir / 'public').mkdir(exist_ok=True)
        
        # Statistics
        self.stats = {
            'raw_items_created': 0,
            'schedules_created': 0,
            'menus_created': 0,
            'public_deals_created': 0,
            'extraction_artifacts_preserved': 0
        }

    def migrate_existing_deals(self):
        """Migrate current deals.json to new structure"""
        
        print("🔄 MIGRATING TO THREE-LAYER ARCHITECTURE")
        print("=" * 50)
        
        # Load existing deals
        deals_file = self.data_dir / 'deals.json'
        if not deals_file.exists():
            print("❌ No existing deals.json found")
            return
        
        with open(deals_file, 'r') as f:
            existing_data = json.load(f)
        
        deals = existing_data.get('deals', [])
        print(f"📊 Found {len(deals)} existing deals to migrate")
        
        # Process each deal
        raw_items = []
        schedules = {}
        menus = {}
        public_deals = []
        
        for deal in deals:
            # Create raw extraction item
            raw_item = self._create_raw_item(deal)
            raw_items.append(raw_item)
            
            # Create refined schedule and menu
            schedule_id = self._create_schedule(deal, schedules)
            if schedule_id:
                self._create_menu(deal, schedule_id, menus)
                
                # Create public deal
                public_deal = self._create_public_deal(deal, schedule_id)
                if public_deal:
                    public_deals.append(public_deal)
        
        # Save to new structure
        self._save_raw_data(raw_items, existing_data)
        self._save_refined_data(list(schedules.values()), list(menus.values()))
        self._save_public_data(public_deals)
        
        # Create summary
        self._create_deal_summary(public_deals)
        
        # Backup original
        self._backup_original_file(deals_file)
        
        print("\n✅ MIGRATION COMPLETE")
        print("-" * 25)
        for key, value in self.stats.items():
            print(f"   {key.replace('_', ' ').title()}: {value}")

    def _create_raw_item(self, deal: Dict) -> Dict:
        """Create raw extraction item preserving all original data"""
        
        raw_item = {
            'extraction_id': str(uuid.uuid4()),
            'extracted_at': deal.get('scraped_at', datetime.now().isoformat()),
            'restaurant_slug': deal.get('restaurant_slug', ''),
            'source_url': deal.get('source_url', ''),
            'extraction_method': deal.get('extraction_method', 'legacy_migration'),
            
            # Preserve extraction artifacts
            'source_text': deal.get('source_text', ''),
            'html_context': deal.get('html_context', ''),
            'extraction_patterns': deal.get('extraction_patterns', []),
            'raw_matches': {
                'time_matches': deal.get('raw_time_matches', []),
                'day_matches': deal.get('raw_day_matches', [])
            },
            
            # Extracted content
            'raw_title': deal.get('title', ''),
            'raw_description': deal.get('description', ''),
            'raw_times': [deal.get('start_time', ''), deal.get('end_time', '')],
            'raw_days': deal.get('days_of_week', []),
            'raw_prices': deal.get('prices', []),
            
            # Metadata
            'confidence_score': deal.get('confidence_score', 0.0),
            'processor_version': '1.0',
            'data_quality': deal.get('data_quality', 'medium'),
            'source_file': deal.get('source_file', 'legacy')
        }
        
        self.stats['raw_items_created'] += 1
        if deal.get('source_text') or deal.get('html_context'):
            self.stats['extraction_artifacts_preserved'] += 1
        
        return raw_item

    def _create_schedule(self, deal: Dict, schedules: Dict) -> str:
        """Create refined deal schedule"""
        
        restaurant_slug = deal.get('restaurant_slug', '')
        deal_type_str = deal.get('deal_type', 'happy_hour')
        
        # Create unique schedule ID
        days = deal.get('days_of_week', [])
        start_time = deal.get('start_time', '')
        day_key = '-'.join(sorted(days)) if days else 'unknown'
        schedule_id = f"{restaurant_slug}-{deal_type_str}-{day_key}"
        
        # Avoid duplicates
        if schedule_id in schedules:
            return schedule_id
        
        # Classify deal type
        title = deal.get('title', '')
        description = deal.get('description', '')
        deal_type = classify_deal_type(title, description, days, [start_time])
        
        # Normalize times
        start_24h = normalize_time_24h(start_time)
        end_24h = normalize_time_24h(deal.get('end_time', ''))
        
        # Normalize days
        normalized_days = [normalize_day_name(day) for day in days]
        
        schedule = {
            'id': schedule_id,
            'restaurant_slug': restaurant_slug,
            'deal_type': deal_type.value,
            'name': title or f"{deal_type.value.replace('_', ' ').title()}",
            
            # Schedule
            'days': normalized_days,
            'start_time': start_24h,
            'end_time': end_24h,
            'timezone': 'America/Denver',
            'is_all_day': deal.get('is_all_day', False),
            
            # Status
            'active_status': 'active',
            'last_verified': deal.get('scraped_at', '')[:10],  # Date only
            'data_quality': self._map_data_quality(deal.get('confidence_score', 0.0)),
            'source_urls': [deal.get('source_url', '')]
        }
        
        schedules[schedule_id] = schedule
        self.stats['schedules_created'] += 1
        return schedule_id

    def _create_menu(self, deal: Dict, schedule_id: str, menus: Dict):
        """Create refined deal menu if pricing info exists"""
        
        prices = deal.get('prices', [])
        if not prices:
            return
        
        restaurant_slug = deal.get('restaurant_slug', '')
        
        # Create menu items from prices
        items = []
        for price_info in prices:
            if isinstance(price_info, dict):
                item = {
                    'name': price_info.get('item', 'Special Item'),
                    'category': 'cocktails',  # Default category
                    'deal_price': price_info.get('price', 0.0),
                    'description': price_info.get('description'),
                    'confidence_score': deal.get('confidence_score', 0.0)
                }
                items.append(item)
        
        if items:
            menu = {
                'schedule_id': schedule_id,
                'restaurant_slug': restaurant_slug,
                'menu_type': 'combo',
                'items': items,
                'source': 'website',
                'menu_url': deal.get('source_url'),
                'last_updated': deal.get('scraped_at', '')[:10],
                'data_quality': self._map_data_quality(deal.get('confidence_score', 0.0)),
                'item_count': len(items)
            }
            
            menus[schedule_id] = menu
            self.stats['menus_created'] += 1

    def _create_public_deal(self, deal: Dict, schedule_id: str) -> Dict:
        """Create user-facing public deal"""
        
        restaurant_slug = deal.get('restaurant_slug', '')
        restaurant_name = deal.get('restaurant_name', restaurant_slug.replace('-', ' ').title())
        
        # Format schedule display
        days = deal.get('days_of_week', [])
        start_time = deal.get('start_time', '')
        end_time = deal.get('end_time', '')
        
        when = self._format_schedule_display(days, start_time, end_time)
        
        # Create highlights from description
        description = deal.get('description', '')
        highlights = []
        if description:
            # Extract price mentions
            if '$' in description:
                highlights.append(description[:100] + '...' if len(description) > 100 else description)
        
        public_deal = {
            'id': schedule_id,
            'restaurant_slug': restaurant_slug,
            'restaurant_name': restaurant_name,
            'deal_name': deal.get('title', 'Happy Hour'),
            'deal_type': deal.get('deal_type', 'happy_hour'),
            'when': when,
            'highlights': highlights,
            'description': description,
            'active_now': False,  # Will be calculated in real-time
            'confidence': self._map_confidence_display(deal.get('confidence_score', 0.0)),
            'last_verified': deal.get('scraped_at', '')[:10],
            'menu_url': deal.get('source_url')
        }
        
        self.stats['public_deals_created'] += 1
        return public_deal

    def _format_schedule_display(self, days: List[str], start_time: str, end_time: str) -> str:
        """Format schedule for user display"""
        if not days:
            return "Schedule varies"
        
        # Format days
        if len(days) >= 5 and all(day in days for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']):
            day_display = "Mon-Fri"
        elif len(days) == 2 and all(day in days for day in ['saturday', 'sunday']):
            day_display = "Weekends"
        elif len(days) == 1:
            day_display = days[0].title()
        else:
            day_display = ", ".join([day[:3].title() for day in days])
        
        # Format times
        if start_time and end_time:
            time_display = f"{start_time}-{end_time}"
        elif start_time:
            time_display = f"Starting {start_time}"
        else:
            time_display = "Times vary"
        
        return f"{day_display} {time_display}"

    def _map_data_quality(self, confidence_score: float) -> str:
        """Map confidence score to data quality enum"""
        if confidence_score >= 0.9:
            return 'high'
        elif confidence_score >= 0.6:
            return 'medium'
        else:
            return 'low'

    def _map_confidence_display(self, confidence_score: float) -> str:
        """Map confidence score to user-friendly display"""
        if confidence_score >= 0.8:
            return 'high'
        elif confidence_score >= 0.5:
            return 'medium'
        else:
            return 'low'

    def _save_raw_data(self, raw_items: List[Dict], original_metadata: Dict):
        """Save raw extraction data"""
        raw_data = {
            'migrated_at': datetime.now().isoformat(),
            'original_metadata': {
                'consolidated_at': original_metadata.get('consolidated_at'),
                'total_deals': original_metadata.get('total_deals'),
                'sources': original_metadata.get('sources', [])
            },
            'migration_stats': self.stats,
            'raw_extractions': raw_items
        }
        
        with open(self.data_dir / 'raw' / 'extracted_deals_raw.json', 'w') as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(raw_items)} raw extraction items")

    def _save_refined_data(self, schedules: List[Dict], menus: List[Dict]):
        """Save refined clean data"""
        
        # Save schedules
        schedule_data = {
            'migrated_at': datetime.now().isoformat(),
            'total_schedules': len(schedules),
            'schedules': schedules
        }
        
        with open(self.data_dir / 'refined' / 'deal_schedules.json', 'w') as f:
            json.dump(schedule_data, f, indent=2, ensure_ascii=False)
        
        # Save menus
        menu_data = {
            'migrated_at': datetime.now().isoformat(),
            'total_menus': len(menus),
            'menus': menus
        }
        
        with open(self.data_dir / 'refined' / 'deal_menus.json', 'w') as f:
            json.dump(menu_data, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Saved {len(schedules)} schedules and {len(menus)} menus")

    def _save_public_data(self, public_deals: List[Dict]):
        """Save user-facing presentation data"""
        public_data = {
            'generated_at': datetime.now().isoformat(),
            'total_deals': len(public_deals),
            'deals': public_deals
        }
        
        with open(self.data_dir / 'public' / 'active_deals.json', 'w') as f:
            json.dump(public_data, f, indent=2, ensure_ascii=False)
        
        print(f"🎯 Saved {len(public_deals)} public deals")

    def _create_deal_summary(self, public_deals: List[Dict]):
        """Create aggregated summary for presentation"""
        
        # Count deal types
        deal_types_count = {}
        for deal in public_deals:
            deal_type = deal.get('deal_type', 'unknown')
            deal_types_count[deal_type] = deal_types_count.get(deal_type, 0) + 1
        
        # Get restaurants
        restaurants = set(deal.get('restaurant_slug') for deal in public_deals)
        
        summary = {
            'generated_at': datetime.now().isoformat(),
            'total_active_deals': len(public_deals),
            'total_restaurants': len(restaurants),
            'deal_types_count': deal_types_count,
            'top_savings': [],  # To be calculated with real pricing data
            'starting_soon': [],  # To be calculated with real-time logic
            'active_now': [],   # To be calculated with real-time logic
            'data_quality_stats': {
                'high': len([d for d in public_deals if d.get('confidence') == 'high']),
                'medium': len([d for d in public_deals if d.get('confidence') == 'medium']),
                'low': len([d for d in public_deals if d.get('confidence') == 'low'])
            }
        }
        
        with open(self.data_dir / 'public' / 'deal_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Created deal summary")

    def _backup_original_file(self, original_file: Path):
        """Backup original deals.json"""
        backup_file = self.data_dir / 'raw' / 'deals_original_backup.json'
        
        import shutil
        shutil.copy2(original_file, backup_file)
        
        print(f"💾 Backed up original to {backup_file}")


def main():
    """Run the migration"""
    migrator = ThreeLayerMigrator()
    migrator.migrate_existing_deals()
    
    print("\n🎉 THREE-LAYER ARCHITECTURE READY")
    print("-" * 35)
    print("📁 Raw data: data/raw/ (debugging/refinement)")
    print("📁 Refined data: data/refined/ (clean/validated)")
    print("📁 Public data: data/public/ (user-facing)")
    print("\nNext steps:")
    print("1. Update scrapers to populate raw layer")
    print("2. Build refinement pipeline")
    print("3. Create real-time status calculation")


if __name__ == "__main__":
    main()