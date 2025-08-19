#!/usr/bin/env python3
"""
Google Places Data Updater

Implements periodic refresh strategy for Google Places data with different
update frequencies based on data type importance and change frequency.
"""

import json
import os
from datetime import datetime, timedelta
from enrich_with_google_places import GooglePlacesEnricher


class GoogleDataUpdater:
    """Manages periodic updates of Google Places data"""
    
    def __init__(self, api_key: str = None):
        self.enricher = GooglePlacesEnricher(api_key)
        self.restaurants_file = 'data/restaurants.json'
    
    def needs_update(self, restaurant: dict, update_type: str) -> bool:
        """Check if restaurant needs update based on type and last update time"""
        google_info = restaurant.get('google_places', {})
        last_updated = google_info.get('last_updated')
        
        if not last_updated:
            return True  # Never updated
        
        last_update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        now = datetime.now()
        time_diff = now - last_update_time
        
        # Update frequencies by type
        update_intervals = {
            'daily': timedelta(days=1),     # Business status, temporary closures
            'weekly': timedelta(days=7),    # Operating hours, phone numbers
            'monthly': timedelta(days=30),  # Address, price level, ratings
            'quarterly': timedelta(days=90) # Static info like place_id
        }
        
        return time_diff >= update_intervals.get(update_type, timedelta(days=7))
    
    def update_daily_data(self):
        """Update business status and other daily-changing data"""
        print("📅 DAILY UPDATE: Business Status & Hours")
        print("=" * 50)
        
        with open(self.restaurants_file, 'r') as f:
            data = json.load(f)
        
        restaurants_to_update = []
        for slug, restaurant in data['restaurants'].items():
            if self.needs_update(restaurant, 'daily'):
                restaurants_to_update.append((slug, restaurant))
        
        print(f"Found {len(restaurants_to_update)} restaurants needing daily updates")
        
        if not restaurants_to_update:
            print("✅ All restaurants have current daily data")
            return
        
        # Update in batches to manage API costs
        for slug, restaurant in restaurants_to_update[:10]:  # Limit to 10 per day
            success = self.enricher.enrich_restaurant(slug, restaurant)
            if success:
                print(f"✅ Updated daily data for {restaurant.get('name', slug)}")
        
        # Save progress
        with open(self.restaurants_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💰 Estimated cost: ${len(restaurants_to_update[:10]) * 0.049:.2f}")
    
    def update_weekly_data(self):
        """Update operating hours and contact information"""
        print("📅 WEEKLY UPDATE: Operating Hours & Contact Info")
        print("=" * 50)
        
        with open(self.restaurants_file, 'r') as f:
            data = json.load(f)
        
        restaurants_to_update = []
        for slug, restaurant in data['restaurants'].items():
            if self.needs_update(restaurant, 'weekly'):
                restaurants_to_update.append((slug, restaurant))
        
        print(f"Found {len(restaurants_to_update)} restaurants needing weekly updates")
        
        if not restaurants_to_update:
            print("✅ All restaurants have current weekly data")
            return
        
        # Update all restaurants needing weekly refresh
        for slug, restaurant in restaurants_to_update:
            success = self.enricher.enrich_restaurant(slug, restaurant)
            if success:
                print(f"✅ Updated weekly data for {restaurant.get('name', slug)}")
        
        # Save progress
        with open(self.restaurants_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💰 Estimated cost: ${len(restaurants_to_update) * 0.049:.2f}")
    
    def update_monthly_data(self):
        """Update ratings, reviews, and other monthly-changing data"""
        print("📅 MONTHLY UPDATE: Ratings, Reviews & Metadata")
        print("=" * 50)
        
        with open(self.restaurants_file, 'r') as f:
            data = json.load(f)
        
        restaurants_to_update = []
        for slug, restaurant in data['restaurants'].items():
            if self.needs_update(restaurant, 'monthly'):
                restaurants_to_update.append((slug, restaurant))
        
        print(f"Found {len(restaurants_to_update)} restaurants needing monthly updates")
        
        if restaurants_to_update:
            for slug, restaurant in restaurants_to_update:
                success = self.enricher.enrich_restaurant(slug, restaurant)
                if success:
                    print(f"✅ Updated monthly data for {restaurant.get('name', slug)}")
            
            # Save progress
            with open(self.restaurants_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"💰 Estimated cost: ${len(restaurants_to_update) * 0.049:.2f}")
        else:
            print("✅ All restaurants have current monthly data")
    
    def check_missing_data(self):
        """Report on restaurants missing Google Places data"""
        with open(self.restaurants_file, 'r') as f:
            data = json.load(f)
        
        missing_data = []
        for slug, restaurant in data['restaurants'].items():
            google_info = restaurant.get('google_places', {})
            
            if not google_info.get('place_id'):
                missing_data.append({
                    'slug': slug,
                    'name': restaurant.get('name', slug),
                    'issue': 'No Google Places data'
                })
            elif not restaurant.get('coordinates'):
                missing_data.append({
                    'slug': slug,
                    'name': restaurant.get('name', slug),
                    'issue': 'Missing coordinates'
                })
        
        if missing_data:
            print("⚠️ RESTAURANTS MISSING GOOGLE DATA:")
            for item in missing_data:
                print(f"  • {item['name']}: {item['issue']}")
        else:
            print("✅ All restaurants have Google Places data")
        
        return missing_data
    
    def data_quality_report(self):
        """Generate comprehensive data quality report"""
        with open(self.restaurants_file, 'r') as f:
            data = json.load(f)
        
        total_restaurants = len(data['restaurants'])
        
        quality_metrics = {
            'google_places_id': 0,
            'operating_hours': 0,
            'phone_numbers': 0,
            'coordinates': 0,
            'business_status': 0,
            'ratings': 0,
            'complete_profiles': 0
        }
        
        for slug, restaurant in data['restaurants'].items():
            google_info = restaurant.get('google_places', {})
            contact_info = restaurant.get('contact_info', {})
            
            if google_info.get('place_id'):
                quality_metrics['google_places_id'] += 1
            if restaurant.get('operating_hours'):
                quality_metrics['operating_hours'] += 1
            if contact_info.get('primary_phone'):
                quality_metrics['phone_numbers'] += 1
            if restaurant.get('coordinates'):
                quality_metrics['coordinates'] += 1
            if google_info.get('business_status'):
                quality_metrics['business_status'] += 1
            if google_info.get('rating'):
                quality_metrics['ratings'] += 1
            
            # Complete profile check
            if all([
                google_info.get('place_id'),
                restaurant.get('operating_hours'),
                contact_info.get('primary_phone'),
                restaurant.get('coordinates'),
                restaurant.get('dining_info', {}).get('price_range'),
                restaurant.get('dining_info', {}).get('atmosphere')
            ]):
                quality_metrics['complete_profiles'] += 1
        
        print("📊 DATA QUALITY REPORT")
        print("=" * 40)
        print(f"Total Restaurants: {total_restaurants}")
        print()
        
        for metric, count in quality_metrics.items():
            percentage = (count / total_restaurants) * 100
            status = "✅" if percentage >= 80 else "⚠️" if percentage >= 60 else "❌"
            print(f"{status} {metric.replace('_', ' ').title()}: {count}/{total_restaurants} ({percentage:.1f}%)")
        
        # Identify high-priority improvements
        print("\n🎯 IMPROVEMENT PRIORITIES:")
        low_coverage = [(k, v) for k, v in quality_metrics.items() if (v / total_restaurants) < 0.8]
        for metric, count in sorted(low_coverage, key=lambda x: x[1]):
            missing = total_restaurants - count
            print(f"  • {metric.replace('_', ' ').title()}: {missing} restaurants need updates")


def main():
    """Main execution - can be called with different update types"""
    import sys
    
    # Check for API key
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("❌ Error: GOOGLE_PLACES_API_KEY environment variable not set")
        print("See GOOGLE_PLACES_SETUP.md for setup instructions")
        return
    
    updater = GoogleDataUpdater(api_key)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        update_type = sys.argv[1].lower()
        
        if update_type == 'daily':
            updater.update_daily_data()
        elif update_type == 'weekly':
            updater.update_weekly_data()
        elif update_type == 'monthly':
            updater.update_monthly_data()
        elif update_type == 'report':
            updater.data_quality_report()
        elif update_type == 'check':
            updater.check_missing_data()
        else:
            print("Usage: python update_google_data.py [daily|weekly|monthly|report|check]")
    else:
        # Default: show data quality report
        updater.data_quality_report()


if __name__ == "__main__":
    main()