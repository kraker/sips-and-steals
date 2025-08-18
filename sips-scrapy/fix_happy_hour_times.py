#!/usr/bin/env python3
"""
Happy Hour Time Data Cleaner

Fixes parsing issues in happy hour timeframes and creates clean, 
user-friendly schedule information for the dashboard.
"""

import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class HappyHourTimeCleaner:
    """Clean and normalize happy hour time data"""
    
    def __init__(self, summary_file: str, enriched_restaurants_file: str):
        self.summary_file = summary_file
        self.enriched_restaurants_file = enriched_restaurants_file
        self.summary_data = self._load_summary_data()
        self.restaurant_data = self._load_restaurant_data()
        
    def _load_summary_data(self) -> Dict:
        """Load happy hour deals summary"""
        with open(self.summary_file, 'r') as f:
            return json.load(f)
    
    def _load_restaurant_data(self) -> Dict:
        """Load enriched restaurant data"""
        with open(self.enriched_restaurants_file, 'r') as f:
            return json.load(f)
    
    def clean_timeframe(self, timeframe: str) -> Optional[str]:
        """Clean a single timeframe string"""
        if not timeframe or not isinstance(timeframe, str):
            return None
        
        timeframe = timeframe.strip()
        
        # Skip obviously invalid times
        invalid_patterns = [
            r'\d{2,}:\d{2}',  # 30:00, 84:00, etc.
            r'(AM|PM)\s*-\s*(PM|AM)',  # Mixed AM/PM ranges
            r'\d{2,}\s*-\s*\d{2,}(?!\s*(AM|PM))',  # Large numbers without AM/PM
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, timeframe):
                return None
        
        # Normalize common patterns
        timeframe_lower = timeframe.lower()
        
        # Handle "All Day" variations
        if re.search(r'all\s*day', timeframe_lower):
            return 'All Day'
        
        # Handle simple hour ranges like "3:00 - 5:30"
        simple_range = re.search(r'(\d{1,2}):?(\d{2})?\s*-\s*(\d{1,2}):?(\d{2})?', timeframe)
        if simple_range:
            start_hour = int(simple_range.group(1))
            start_min = simple_range.group(2) or '00'
            end_hour = int(simple_range.group(3))
            end_min = simple_range.group(4) or '00'
            
            # Validate reasonable hours
            if 1 <= start_hour <= 12 and 1 <= end_hour <= 12:
                # Assume PM for typical happy hour times
                start_period = 'PM' if start_hour >= 3 else 'PM'
                end_period = 'PM' if end_hour >= 3 else 'PM'
                return f"{start_hour}:{start_min} {start_period} - {end_hour}:{end_min} {end_period}"
        
        # Handle times with explicit AM/PM
        am_pm_range = re.search(r'(\d{1,2}):?(\d{2})?\s*(AM|PM)\s*-\s*(\d{1,2}):?(\d{2})?\s*(AM|PM)', timeframe, re.IGNORECASE)
        if am_pm_range:
            start_hour = am_pm_range.group(1)
            start_min = am_pm_range.group(2) or '00'
            start_period = am_pm_range.group(3).upper()
            end_hour = am_pm_range.group(4)
            end_min = am_pm_range.group(5) or '00'
            end_period = am_pm_range.group(6).upper()
            
            return f"{start_hour}:{start_min} {start_period} - {end_hour}:{end_min} {end_period}"
        
        # Handle single times with periods like "5:30 - PM"
        single_time = re.search(r'(\d{1,2}):?(\d{2})?\s*-\s*(PM|AM)', timeframe, re.IGNORECASE)
        if single_time:
            hour = single_time.group(1)
            minute = single_time.group(2) or '00'
            period = single_time.group(3).upper()
            return f"{hour}:{minute} {period}"
        
        return None
    
    def clean_day_list(self, days: List[str]) -> List[str]:
        """Clean and normalize day names"""
        day_mapping = {
            'mon': 'Monday', 'tue': 'Tuesday', 'wed': 'Wednesday', 'thu': 'Thursday',
            'fri': 'Friday', 'sat': 'Saturday', 'sun': 'Sunday',
            'weekday': 'Weekdays', 'weekend': 'Weekends', 'daily': 'Daily'
        }
        
        clean_days = []
        seen = set()
        
        for day in days:
            if not day:
                continue
            
            normalized = day_mapping.get(day.lower(), day.title())
            if normalized not in seen:
                clean_days.append(normalized)
                seen.add(normalized)
        
        return clean_days
    
    def create_user_schedule(self, restaurant_slug: str) -> Dict[str, Any]:
        """Create user-friendly schedule for a restaurant"""
        schedule = {
            'status': 'unknown',
            'next_happy_hour': None,
            'current_deals': [],
            'weekly_schedule': [],
            'quick_summary': 'Check restaurant for details'
        }
        
        # Get data from both sources
        deal_data = self.summary_data['deals_summary'].get(restaurant_slug, {})
        restaurant_info = self.restaurant_data['restaurants'].get(restaurant_slug, {})
        
        # Use manually curated schedule if available
        if restaurant_info.get('happy_hour_schedule'):
            manual_schedule = restaurant_info['happy_hour_schedule']
            schedule['weekly_schedule'] = self._format_manual_schedule(manual_schedule)
            schedule['quick_summary'] = self._create_quick_summary(manual_schedule)
        else:
            # Fall back to cleaned extracted data
            timeframes = deal_data.get('timeframes', [])
            days = deal_data.get('days', [])
            
            clean_times = []
            for tf in timeframes[:5]:  # Limit to top 5
                clean_time = self.clean_timeframe(tf)
                if clean_time:
                    clean_times.append(clean_time)
            
            clean_days = self.clean_day_list(days)
            
            if clean_times:
                schedule['weekly_schedule'] = [{
                    'days': clean_days,
                    'times': clean_times
                }]
                schedule['quick_summary'] = f"{', '.join(clean_days[:3])} • {clean_times[0]}"
        
        return schedule
    
    def _format_manual_schedule(self, manual_schedule: Dict) -> List[Dict]:
        """Format manually curated schedule data"""
        formatted = []
        
        for period, time_range in manual_schedule.items():
            if 'daily' in period.lower():
                formatted.append({
                    'days': ['Daily'],
                    'times': [time_range]
                })
            elif '_' in period:
                # Handle formats like "tuesday_wednesday" or "friday_saturday"
                days = period.replace('_', ', ').title()
                formatted.append({
                    'days': [days],
                    'times': [time_range]
                })
            else:
                formatted.append({
                    'days': [period.title()],
                    'times': [time_range]
                })
        
        return formatted
    
    def _create_quick_summary(self, manual_schedule: Dict) -> str:
        """Create a quick summary from manual schedule"""
        if 'daily' in str(manual_schedule).lower():
            daily_time = next((time for period, time in manual_schedule.items() if 'daily' in period.lower()), None)
            if daily_time:
                return f"Daily • {daily_time}"
        
        # Get first schedule item
        if manual_schedule:
            first_period, first_time = next(iter(manual_schedule.items()))
            days = first_period.replace('_', ', ').title()
            return f"{days} • {first_time}"
        
        return "Check restaurant for details"
    
    def process_all_restaurants(self):
        """Process all restaurants and create clean schedule data"""
        print("🕒 **Cleaning Happy Hour Time Data**")
        print("=" * 50)
        
        cleaned_data = {
            'generated_at': datetime.now().isoformat(),
            'district': 'LoDo (Lower Downtown)',
            'restaurants': {}
        }
        
        processed_count = 0
        
        for slug in self.summary_data['deals_summary'].keys():
            if slug in self.restaurant_data['restaurants']:
                restaurant_info = self.restaurant_data['restaurants'][slug]
                deal_data = self.summary_data['deals_summary'][slug]
                
                # Create clean schedule
                schedule = self.create_user_schedule(slug)
                
                # Combine restaurant info with clean schedule
                clean_restaurant = {
                    'name': restaurant_info['name'],
                    'cuisine': restaurant_info['cuisine'],
                    'price_range': restaurant_info.get('price_range', '$$'),
                    'contact': restaurant_info.get('contact', {}),
                    'hours': restaurant_info.get('hours', {}),
                    'reservations': restaurant_info.get('reservations', {}),
                    'social': restaurant_info.get('social', {}),
                    'happy_hour': schedule,
                    'deals_summary': {
                        'total_deals': deal_data.get('total_deals', 0),
                        'avg_food_price': deal_data.get('average_food_price', 0),
                        'avg_drink_price': deal_data.get('average_drink_price', 0)
                    }
                }
                
                cleaned_data['restaurants'][slug] = clean_restaurant
                processed_count += 1
                
                print(f"✅ Cleaned schedule for {restaurant_info['name']}")
                print(f"   Schedule: {schedule['quick_summary']}")
            else:
                print(f"⚠️  No restaurant data for {slug}")
        
        print(f"\n📊 Processed {processed_count} restaurants with clean schedules")
        
        return cleaned_data
    
    def save_cleaned_data(self, cleaned_data: Dict, output_file: str = 'data/lodo_dashboard_data.json'):
        """Save cleaned data for dashboard use"""
        with open(output_file, 'w') as f:
            json.dump(cleaned_data, f, indent=2, default=str)
        
        print(f"💾 Clean dashboard data saved to: {output_file}")
        return output_file


def main():
    """Clean happy hour time data for user dashboard"""
    print("🧹 **Happy Hour Time Data Cleanup**")
    print("Fixing parsing issues and creating user-friendly schedules")
    print("=" * 60)
    
    cleaner = HappyHourTimeCleaner(
        summary_file='data/happy_hour_deals_summary.json',
        enriched_restaurants_file='data/lodo_restaurants_enriched.json'
    )
    
    # Process all restaurants
    cleaned_data = cleaner.process_all_restaurants()
    
    # Save cleaned data
    output_file = cleaner.save_cleaned_data(cleaned_data)
    
    print(f"\n✅ **Time Cleanup Complete**")
    print(f"Clean, user-friendly happy hour schedules ready for dashboard")
    print(f"Output: {output_file}")


if __name__ == '__main__':
    main()