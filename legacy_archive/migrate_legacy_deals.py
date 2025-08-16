#!/usr/bin/env python3
"""
Migration script to convert legacy happy_hour_times strings to structured Deal objects
"""
import json
import re
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models import Deal, DealType, DayOfWeek


class HappyHourParser:
    """Parser to convert legacy happy hour time strings to Deal objects"""
    
    # Day mapping
    DAY_MAPPING = {
        'mon': DayOfWeek.MONDAY,
        'tue': DayOfWeek.TUESDAY, 
        'wed': DayOfWeek.WEDNESDAY,
        'thu': DayOfWeek.THURSDAY,
        'fri': DayOfWeek.FRIDAY,
        'sat': DayOfWeek.SATURDAY,
        'sun': DayOfWeek.SUNDAY
    }
    
    def __init__(self):
        # Common patterns for parsing
        self.patterns = [
            # Pattern: "Mon, Tue, Wed, Thu, Fri 4 - 6"
            r'([A-Za-z, ]+?)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm|a|p)?)\s*[-–]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm|a|p|close)?)',
            # Pattern: "All Day" variations
            r'([A-Za-z, ]+?)\s+(All\s+Day)',
            # Pattern: "Bottomless brunch 10:30 am - 3"
            r'(Bottomless\s+brunch|Brunch)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*[-–]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
        ]
    
    def parse_days(self, day_str: str) -> List[DayOfWeek]:
        """Parse day string into list of DayOfWeek enums"""
        days = []
        day_str = day_str.lower().strip()
        
        # Handle "All Day" separately - return all days
        if 'all day' in day_str:
            return list(DayOfWeek)
        
        # Split by comma and clean
        day_parts = [part.strip() for part in day_str.split(',')]
        
        for part in day_parts:
            # Clean up the part
            part = re.sub(r'[^\w]', '', part).lower()
            
            # Match against our mapping
            for short_name, day_enum in self.DAY_MAPPING.items():
                if part.startswith(short_name):
                    days.append(day_enum)
                    break
        
        return days
    
    def normalize_time(self, time_str: str) -> str:
        """Normalize time format"""
        time_str = time_str.strip().lower()
        
        # Handle "close"
        if 'close' in time_str:
            return "Close"
        
        # Handle missing am/pm
        if re.match(r'^\d{1,2}(?::\d{2})?$', time_str):
            hour = int(time_str.split(':')[0])
            if hour <= 6:
                time_str += " PM"
            elif hour >= 7 and hour <= 11:
                time_str += " AM" if hour > 6 else " PM"
            else:
                time_str += " PM"
        
        # Standardize format
        time_str = re.sub(r'\ba\b', 'AM', time_str)
        time_str = re.sub(r'\bp\b', 'PM', time_str)
        
        # Ensure proper case
        time_str = re.sub(r'am', 'AM', time_str)
        time_str = re.sub(r'pm', 'PM', time_str)
        
        return time_str.strip()
    
    def parse_single_time_entry(self, time_entry: str) -> List[Deal]:
        """Parse a single happy hour time entry into Deal objects"""
        deals = []
        time_entry = time_entry.strip()
        
        print(f"Parsing: '{time_entry}'")
        
        # Split by | for multiple time periods
        periods = [p.strip() for p in time_entry.split('|')]
        
        for period in periods:
            deal = self.parse_time_period(period)
            if deal:
                deals.append(deal)
        
        return deals
    
    def parse_time_period(self, period: str) -> Optional[Deal]:
        """Parse a single time period into a Deal object"""
        period = period.strip()
        
        # Try each pattern
        for pattern in self.patterns:
            match = re.search(pattern, period, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if len(groups) == 2 and 'all day' in groups[1].lower():
                    # All day pattern
                    days = self.parse_days(groups[0])
                    return Deal(
                        title="Happy Hour",
                        description=f"All day happy hour - {period}",
                        deal_type=DealType.HAPPY_HOUR,
                        days_of_week=days,
                        is_all_day=True,
                        confidence_score=0.3,  # Legacy data confidence
                        special_notes=["Migrated from legacy data"]
                    )
                
                elif len(groups) >= 3:
                    # Time range pattern
                    day_part = groups[0]
                    start_time = self.normalize_time(groups[1])
                    end_time = self.normalize_time(groups[2])
                    
                    # Determine deal type
                    deal_type = DealType.HAPPY_HOUR
                    title = "Happy Hour"
                    if 'brunch' in period.lower():
                        deal_type = DealType.BRUNCH_SPECIAL
                        title = "Brunch Special"
                    
                    days = self.parse_days(day_part)
                    
                    return Deal(
                        title=title,
                        description=f"Scheduled {title.lower()} - {period}",
                        deal_type=deal_type,
                        days_of_week=days,
                        start_time=start_time,
                        end_time=end_time,
                        is_all_day=False,
                        confidence_score=0.3,  # Legacy data confidence
                        special_notes=["Migrated from legacy data"]
                    )
        
        # Fallback for unparsed entries
        return Deal(
            title="Happy Hour",
            description=f"Legacy happy hour info: {period}",
            deal_type=DealType.HAPPY_HOUR,
            days_of_week=[],
            is_all_day=True,
            confidence_score=0.1,  # Low confidence for unparsed
            special_notes=["Migrated from legacy data", "Manual review needed"]
        )


def migrate_restaurant_deals():
    """Main migration function"""
    print("🔄 Starting migration of legacy happy_hour_times to Deal objects...")
    
    # Load restaurants data
    with open('data/restaurants.json', 'r') as f:
        data = json.load(f)
    
    parser = HappyHourParser()
    migration_stats = {
        'restaurants_processed': 0,
        'deals_created': 0,
        'parsing_errors': 0
    }
    
    # Process each restaurant
    for area_name, area_data in data.get('areas', {}).items():
        for restaurant_slug, restaurant in area_data.items():
            happy_hour_times = restaurant.get('happy_hour_times', [])
            
            if happy_hour_times:
                print(f"\n📍 Processing {restaurant['name']} ({restaurant_slug})")
                migration_stats['restaurants_processed'] += 1
                
                # Parse all happy hour times
                all_deals = []
                for time_entry in happy_hour_times:
                    try:
                        deals = parser.parse_single_time_entry(time_entry)
                        all_deals.extend(deals)
                        migration_stats['deals_created'] += len(deals)
                    except Exception as e:
                        print(f"  ❌ Error parsing '{time_entry}': {e}")
                        migration_stats['parsing_errors'] += 1
                
                # Add static deals to restaurant
                if all_deals:
                    # Convert Deal objects to dicts for JSON serialization
                    static_deals = []
                    for deal in all_deals:
                        deal_dict = {
                            'title': deal.title,
                            'description': deal.description,
                            'deal_type': deal.deal_type.value,
                            'days_of_week': [day.value for day in deal.days_of_week],
                            'start_time': deal.start_time,
                            'end_time': deal.end_time,
                            'price': deal.price,
                            'is_all_day': deal.is_all_day,
                            'special_notes': deal.special_notes,
                            'scraped_at': datetime.now().isoformat(),
                            'source_url': None,
                            'confidence_score': deal.confidence_score
                        }
                        static_deals.append(deal_dict)
                    
                    restaurant['static_deals'] = static_deals
                    print(f"  ✅ Created {len(static_deals)} static deals")
    
    # Update metadata
    data['metadata']['migration_completed'] = datetime.now().isoformat()
    data['metadata']['migration_stats'] = migration_stats
    
    # Save updated data
    backup_file = f"data/restaurants_pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    print(f"\n💾 Creating backup: {backup_file}")
    
    # Create backup
    with open(backup_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Save migrated data
    with open('data/restaurants.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Migration completed!")
    print(f"📊 Migration Statistics:")
    print(f"   • Restaurants processed: {migration_stats['restaurants_processed']}")
    print(f"   • Deals created: {migration_stats['deals_created']}")
    print(f"   • Parsing errors: {migration_stats['parsing_errors']}")
    print(f"💾 Backup saved to: {backup_file}")
    print(f"💾 Updated data saved to: data/restaurants.json")


if __name__ == "__main__":
    migrate_restaurant_deals()