#!/usr/bin/env python3
"""
Deals Refinement Pipeline

Processes raw extraction data to create clean, validated, and normalized
deals data for presentation. Implements quality control and deduplication.
"""

import json
import sys
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional, Set
import uuid
import re

# Add src to path for imports
sys.path.append('src')
from models.deals import (
    DealType, DataQuality, ItemCategory,
    normalize_day_name, normalize_time_24h, classify_deal_type
)


class DealsRefinementPipeline:
    """Refines raw extraction data into clean, presentable format"""
    
    def __init__(self):
        self.data_dir = Path('data')
        self.raw_dir = self.data_dir / 'raw'
        self.refined_dir = self.data_dir / 'refined'
        self.public_dir = self.data_dir / 'public'
        
        self.stats = {
            'raw_items_processed': 0,
            'schedules_created': 0,
            'schedules_updated': 0,
            'menus_created': 0,
            'items_extracted': 0,
            'duplicates_merged': 0,
            'quality_improvements': 0
        }

    def run_refinement(self):
        """Run the complete refinement pipeline"""
        
        print("🔧 STARTING DEALS REFINEMENT PIPELINE")
        print("=" * 45)
        
        # Load raw data
        raw_deals = self._load_raw_deals()
        if not raw_deals:
            print("❌ No raw deals data found")
            return
        
        print(f"📊 Processing {len(raw_deals)} raw extractions")
        
        # Process raw data into refined structures
        schedules, menus = self._process_raw_deals(raw_deals)
        
        # Apply quality improvements
        schedules = self._improve_schedule_quality(schedules)
        menus = self._improve_menu_quality(menus)
        
        # Save refined data
        self._save_refined_schedules(schedules)
        self._save_refined_menus(menus)
        
        # Generate public presentation data
        public_deals = self._create_public_deals(schedules, menus)
        self._save_public_deals(public_deals)
        
        # Create updated summary
        self._create_deal_summary(public_deals)
        
        print("\n✅ REFINEMENT PIPELINE COMPLETE")
        print("-" * 35)
        for key, value in self.stats.items():
            print(f"   {key.replace('_', ' ').title()}: {value}")

    def _load_raw_deals(self) -> List[Dict]:
        """Load raw extraction data"""
        raw_file = self.raw_dir / 'extracted_deals_raw.json'
        
        if not raw_file.exists():
            return []
        
        with open(raw_file, 'r') as f:
            data = json.load(f)
        
        return data.get('raw_extractions', [])

    def _process_raw_deals(self, raw_deals: List[Dict]) -> tuple:
        """Process raw deals into schedules and menus"""
        
        schedules = {}
        menus = {}
        
        for raw_deal in raw_deals:
            self.stats['raw_items_processed'] += 1
            
            # Create schedule from raw deal
            schedule_id = self._create_schedule_from_raw(raw_deal, schedules)
            
            # Create menu if pricing data exists
            if schedule_id and raw_deal.get('raw_prices'):
                self._create_menu_from_raw(raw_deal, schedule_id, menus)
        
        return list(schedules.values()), list(menus.values())

    def _create_schedule_from_raw(self, raw_deal: Dict, schedules: Dict) -> Optional[str]:
        """Create or update schedule from raw extraction"""
        
        restaurant_slug = raw_deal.get('restaurant_slug', '')
        if not restaurant_slug:
            return None
        
        # Extract and normalize schedule information
        days = self._normalize_days(raw_deal.get('raw_days', []))
        start_time = self._normalize_time(raw_deal.get('raw_times', [''])[0])
        end_time = self._normalize_time(raw_deal.get('raw_times', ['', ''])[1])
        
        # Classify deal type
        title = raw_deal.get('raw_title', '')
        description = raw_deal.get('raw_description', '')
        deal_type = classify_deal_type(title, description, days, [start_time or ''])
        
        # Create schedule ID
        day_key = '-'.join(sorted(days)) if days else 'unknown'
        time_key = f"{start_time or 'any'}-{end_time or 'any'}"
        schedule_id = f"{restaurant_slug}-{deal_type.value}-{day_key}-{time_key}"
        
        # Check if schedule already exists
        if schedule_id in schedules:
            # Update existing schedule with better data
            existing = schedules[schedule_id]
            self._merge_schedule_data(existing, raw_deal)
            self.stats['schedules_updated'] += 1
            return schedule_id
        
        # Create new schedule
        schedule = {
            'id': schedule_id,
            'restaurant_slug': restaurant_slug,
            'deal_type': deal_type.value,
            'name': self._clean_title(title) or f"{deal_type.value.replace('_', ' ').title()}",
            
            # Schedule information
            'days': days,
            'start_time': start_time,
            'end_time': end_time,
            'timezone': 'America/Denver',
            'is_all_day': self._is_all_day(raw_deal),
            
            # Metadata
            'active_status': 'active',
            'last_verified': raw_deal.get('extracted_at', '')[:10],
            'data_quality': self._calculate_quality_score(raw_deal),
            'source_urls': [raw_deal.get('source_url', '')],
            'confidence_scores': [raw_deal.get('confidence_score', 0.0)],
            'raw_extraction_ids': [raw_deal.get('extraction_id', '')]
        }
        
        schedules[schedule_id] = schedule
        self.stats['schedules_created'] += 1
        return schedule_id

    def _create_menu_from_raw(self, raw_deal: Dict, schedule_id: str, menus: Dict):
        """Create menu from raw extraction with pricing"""
        
        raw_prices = raw_deal.get('raw_prices', [])
        if not raw_prices:
            return
        
        # Parse pricing information
        items = []
        for price_data in raw_prices:
            item = self._parse_price_item(price_data)
            if item:
                items.append(item)
        
        if not items:
            return
        
        menu = {
            'schedule_id': schedule_id,
            'restaurant_slug': raw_deal.get('restaurant_slug', ''),
            'menu_type': self._classify_menu_type(items),
            'items': items,
            'source': 'website',
            'menu_url': raw_deal.get('source_url', ''),
            'last_updated': raw_deal.get('extracted_at', '')[:10],
            'data_quality': self._calculate_quality_score(raw_deal),
            'item_count': len(items),
            'categories': list(set(item.get('category', 'unknown') for item in items))
        }
        
        menus[schedule_id] = menu
        self.stats['menus_created'] += 1
        self.stats['items_extracted'] += len(items)

    def _normalize_days(self, raw_days: List[str]) -> List[str]:
        """Normalize and validate day names"""
        normalized = []
        
        for day in raw_days:
            if isinstance(day, str):
                clean_day = normalize_day_name(day.strip())
                if clean_day and clean_day not in normalized:
                    normalized.append(clean_day)
        
        return normalized

    def _normalize_time(self, raw_time: str) -> Optional[str]:
        """Normalize time to 24-hour format"""
        if not raw_time or not isinstance(raw_time, str):
            return None
        
        return normalize_time_24h(raw_time.strip())

    def _clean_title(self, title: str) -> Optional[str]:
        """Clean and validate title"""
        if not title or not isinstance(title, str):
            return None
        
        # Remove extra whitespace and normalize
        cleaned = ' '.join(title.strip().split())
        
        # Remove common noise
        noise_patterns = [
            r'^Time:\s*',
            r'\s*\|\s*Days:.*$',
            r'\s*\|\s*Time:.*$'
        ]
        
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip() if cleaned.strip() else None

    def _is_all_day(self, raw_deal: Dict) -> bool:
        """Determine if deal is all-day"""
        description = raw_deal.get('raw_description', '').lower()
        title = raw_deal.get('raw_title', '').lower()
        
        all_day_indicators = ['all day', 'all-day', '24 hours', 'always']
        
        return any(indicator in f"{title} {description}" for indicator in all_day_indicators)

    def _calculate_quality_score(self, raw_deal: Dict) -> str:
        """Calculate data quality based on completeness and confidence"""
        
        confidence = raw_deal.get('confidence_score', 0.0)
        
        # Check data completeness
        completeness_score = 0
        if raw_deal.get('raw_title'):
            completeness_score += 1
        if raw_deal.get('raw_days'):
            completeness_score += 1
        if raw_deal.get('raw_times'):
            completeness_score += 1
        if raw_deal.get('source_url'):
            completeness_score += 1
        
        # Combine confidence and completeness
        total_score = (confidence + (completeness_score / 4)) / 2
        
        if total_score >= 0.8:
            return 'high'
        elif total_score >= 0.5:
            return 'medium'
        else:
            return 'low'

    def _parse_price_item(self, price_data) -> Optional[Dict]:
        """Parse price data into menu item"""
        
        if isinstance(price_data, dict):
            # Structured price data
            return {
                'name': price_data.get('item', 'Special Item'),
                'category': self._categorize_item(price_data.get('item', '')),
                'deal_price': float(price_data.get('price', 0)),
                'description': price_data.get('description'),
                'confidence_score': price_data.get('confidence', 0.8)
            }
        elif isinstance(price_data, str):
            # Parse string price data
            price_match = re.search(r'\$?(\d+(?:\.\d{2})?)', price_data)
            if price_match:
                return {
                    'name': price_data.replace(price_match.group(0), '').strip(),
                    'category': self._categorize_item(price_data),
                    'deal_price': float(price_match.group(1)),
                    'confidence_score': 0.6
                }
        
        return None

    def _categorize_item(self, item_name: str) -> str:
        """Categorize menu item by name"""
        if not item_name:
            return 'unknown'
        
        item_lower = item_name.lower()
        
        category_keywords = {
            'cocktails': ['cocktail', 'martini', 'margarita', 'mojito', 'negroni', 'old fashioned'],
            'wine': ['wine', 'chardonnay', 'pinot', 'cabernet', 'merlot', 'rosé', 'glass'],
            'beer': ['beer', 'ipa', 'lager', 'ale', 'stout', 'pint', 'draft'],
            'appetizers': ['appetizer', 'starter', 'small plate', 'shareables', 'apps'],
            'entrees': ['entree', 'main', 'dinner', 'lunch', 'burger', 'steak', 'chicken'],
            'oysters': ['oyster', 'shellfish', 'raw bar'],
            'tacos': ['taco', 'quesadilla', 'burrito'],
            'pizza': ['pizza', 'flatbread'],
            'sushi': ['sushi', 'sashimi', 'roll', 'nigiri']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in item_lower for keyword in keywords):
                return category
        
        return 'unknown'

    def _classify_menu_type(self, items: List[Dict]) -> str:
        """Classify menu type based on items"""
        categories = [item.get('category', 'unknown') for item in items]
        
        drink_categories = {'cocktails', 'wine', 'beer', 'spirits'}
        food_categories = {'appetizers', 'entrees', 'oysters', 'tacos', 'pizza', 'sushi'}
        
        has_drinks = any(cat in drink_categories for cat in categories)
        has_food = any(cat in food_categories for cat in categories)
        
        if has_drinks and has_food:
            return 'combo'
        elif has_drinks:
            return 'drinks'
        elif has_food:
            return 'food'
        else:
            return 'unknown'

    def _merge_schedule_data(self, existing: Dict, raw_deal: Dict):
        """Merge new data into existing schedule"""
        
        # Update confidence scores
        new_confidence = raw_deal.get('confidence_score', 0.0)
        existing['confidence_scores'].append(new_confidence)
        
        # Update source URLs
        new_url = raw_deal.get('source_url', '')
        if new_url and new_url not in existing['source_urls']:
            existing['source_urls'].append(new_url)
        
        # Update extraction IDs
        extraction_id = raw_deal.get('extraction_id', '')
        if extraction_id:
            existing['raw_extraction_ids'].append(extraction_id)
        
        # Update last verified if newer
        new_date = raw_deal.get('extracted_at', '')[:10]
        if new_date > existing.get('last_verified', ''):
            existing['last_verified'] = new_date

    def _improve_schedule_quality(self, schedules: List[Dict]) -> List[Dict]:
        """Apply quality improvements to schedules"""
        
        improved = []
        
        for schedule in schedules:
            # Improve confidence calculation
            confidences = schedule.get('confidence_scores', [])
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                schedule['average_confidence'] = avg_confidence
            
            # Improve name if generic
            if schedule.get('name') in ['Happy Hour', 'Deal', 'Special']:
                schedule['name'] = self._generate_better_name(schedule)
            
            # Validate day/time consistency
            if self._validate_schedule_consistency(schedule):
                improved.append(schedule)
                self.stats['quality_improvements'] += 1
        
        return improved

    def _improve_menu_quality(self, menus: List[Dict]) -> List[Dict]:
        """Apply quality improvements to menus"""
        
        for menu in menus:
            # Improve item categorization
            for item in menu.get('items', []):
                if item.get('category') == 'unknown':
                    item['category'] = self._categorize_item(item.get('name', ''))
            
            # Calculate price ranges
            prices = [item.get('deal_price', 0) for item in menu.get('items', []) if item.get('deal_price')]
            if prices:
                menu['price_range'] = f"${min(prices):.0f}-{max(prices):.0f}"
        
        return menus

    def _generate_better_name(self, schedule: Dict) -> str:
        """Generate a better name for generic schedules"""
        
        deal_type = schedule.get('deal_type', '')
        days = schedule.get('days', [])
        
        # Format days
        if len(days) >= 5 and all(day in days for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']):
            day_part = "Weekday"
        elif len(days) == 2 and all(day in days for day in ['saturday', 'sunday']):
            day_part = "Weekend"
        elif len(days) == 1:
            day_part = days[0].title()
        else:
            day_part = ""
        
        # Format deal type
        type_part = deal_type.replace('_', ' ').title()
        
        return f"{day_part} {type_part}".strip()

    def _validate_schedule_consistency(self, schedule: Dict) -> bool:
        """Validate schedule data consistency"""
        
        # Must have restaurant
        if not schedule.get('restaurant_slug'):
            return False
        
        # Must have some temporal information
        has_days = bool(schedule.get('days'))
        has_times = bool(schedule.get('start_time') or schedule.get('end_time'))
        
        return has_days or has_times

    def _create_public_deals(self, schedules: List[Dict], menus: List[Dict]) -> List[Dict]:
        """Create user-facing public deals"""
        
        public_deals = []
        menu_map = {menu['schedule_id']: menu for menu in menus}
        
        for schedule in schedules:
            schedule_id = schedule['id']
            restaurant_slug = schedule['restaurant_slug']
            
            # Get associated menu
            menu = menu_map.get(schedule_id)
            
            # Create highlights
            highlights = []
            if menu:
                items = menu.get('items', [])
                # Get top 3 cheapest items as highlights
                sorted_items = sorted(items, key=lambda x: x.get('deal_price', 999))
                for item in sorted_items[:3]:
                    price = item.get('deal_price', 0)
                    name = item.get('name', 'Special Item')
                    highlights.append(f"${price:.0f} {name}")
            
            # Format schedule display
            when = self._format_schedule_display(schedule)
            
            public_deal = {
                'id': schedule_id,
                'restaurant_slug': restaurant_slug,
                'restaurant_name': restaurant_slug.replace('-', ' ').title(),
                'deal_name': schedule.get('name', 'Special Deal'),
                'deal_type': schedule.get('deal_type', 'unknown'),
                'when': when,
                'highlights': highlights,
                'savings_range': menu.get('price_range') if menu else None,
                'active_now': False,  # To be calculated real-time
                'confidence': self._map_confidence_to_display(schedule),
                'last_verified': schedule.get('last_verified'),
                'menu_url': schedule.get('source_urls', [None])[0]
            }
            
            public_deals.append(public_deal)
        
        return public_deals

    def _format_schedule_display(self, schedule: Dict) -> str:
        """Format schedule for user display"""
        
        days = schedule.get('days', [])
        start_time = schedule.get('start_time')
        end_time = schedule.get('end_time')
        
        # Format days
        if len(days) >= 5 and all(day in days for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']):
            day_display = "Mon-Fri"
        elif len(days) == 2 and all(day in days for day in ['saturday', 'sunday']):
            day_display = "Weekends"
        elif len(days) == 1:
            day_display = days[0].title()[:3]
        elif days:
            day_display = ", ".join([day.title()[:3] for day in days[:3]])
        else:
            day_display = "Daily"
        
        # Format times
        if start_time and end_time:
            # Convert 24h to 12h format for display
            start_12h = self._format_time_12h(start_time)
            end_12h = self._format_time_12h(end_time)
            time_display = f"{start_12h}-{end_12h}"
        elif start_time:
            start_12h = self._format_time_12h(start_time)
            time_display = f"Starting {start_12h}"
        else:
            time_display = ""
        
        return f"{day_display} {time_display}".strip()

    def _format_time_12h(self, time_24h: str) -> str:
        """Convert 24h time to 12h format for display"""
        try:
            hour, minute = map(int, time_24h.split(':'))
            if hour == 0:
                return f"12:{minute:02d} AM"
            elif hour < 12:
                return f"{hour}:{minute:02d} AM"
            elif hour == 12:
                return f"12:{minute:02d} PM"
            else:
                return f"{hour-12}:{minute:02d} PM"
        except:
            return time_24h

    def _map_confidence_to_display(self, schedule: Dict) -> str:
        """Map confidence to user-friendly display"""
        avg_confidence = schedule.get('average_confidence', 0.5)
        
        if avg_confidence >= 0.8:
            return 'high'
        elif avg_confidence >= 0.5:
            return 'medium'
        else:
            return 'low'

    def _save_refined_schedules(self, schedules: List[Dict]):
        """Save refined schedules"""
        data = {
            'refined_at': datetime.now().isoformat(),
            'total_schedules': len(schedules),
            'schedules': schedules
        }
        
        with open(self.refined_dir / 'deal_schedules.json', 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_refined_menus(self, menus: List[Dict]):
        """Save refined menus"""
        data = {
            'refined_at': datetime.now().isoformat(),
            'total_menus': len(menus),
            'menus': menus
        }
        
        with open(self.refined_dir / 'deal_menus.json', 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_public_deals(self, public_deals: List[Dict]):
        """Save public presentation deals"""
        data = {
            'generated_at': datetime.now().isoformat(),
            'total_deals': len(public_deals),
            'deals': public_deals
        }
        
        with open(self.public_dir / 'active_deals.json', 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _create_deal_summary(self, public_deals: List[Dict]):
        """Create updated deal summary"""
        
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
            'data_quality_stats': {
                'high': len([d for d in public_deals if d.get('confidence') == 'high']),
                'medium': len([d for d in public_deals if d.get('confidence') == 'medium']),
                'low': len([d for d in public_deals if d.get('confidence') == 'low'])
            },
            'refinement_stats': self.stats
        }
        
        with open(self.public_dir / 'deal_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


def main():
    """Run the refinement pipeline"""
    pipeline = DealsRefinementPipeline()
    pipeline.run_refinement()


if __name__ == "__main__":
    main()