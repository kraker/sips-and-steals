#!/usr/bin/env python3
"""
Cleanup script to remove legacy happy_hour_times fields after successful migration
"""
import json
from datetime import datetime

def cleanup_legacy_fields():
    """Remove legacy happy_hour_times fields from restaurants.json"""
    print("🧹 Cleaning up legacy happy_hour_times fields...")
    
    # Load restaurants data
    with open('data/restaurants.json', 'r') as f:
        data = json.load(f)
    
    cleanup_stats = {
        'restaurants_cleaned': 0,
        'fields_removed': 0
    }
    
    # Process each restaurant
    for area_name, area_data in data.get('areas', {}).items():
        for restaurant_slug, restaurant in area_data.items():
            if 'happy_hour_times' in restaurant:
                print(f"🔧 Cleaning {restaurant['name']} ({restaurant_slug})")
                # Remove the legacy field
                del restaurant['happy_hour_times']
                cleanup_stats['restaurants_cleaned'] += 1
                cleanup_stats['fields_removed'] += 1
    
    # Update metadata
    data['metadata']['legacy_cleanup_completed'] = datetime.now().isoformat()
    data['metadata']['cleanup_stats'] = cleanup_stats
    
    # Create backup before cleanup
    backup_file = f"data/restaurants_pre_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    print(f"💾 Creating backup: {backup_file}")
    
    with open(backup_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Save cleaned data
    with open('data/restaurants.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Legacy field cleanup completed!")
    print(f"📊 Cleanup Statistics:")
    print(f"   • Restaurants cleaned: {cleanup_stats['restaurants_cleaned']}")
    print(f"   • Fields removed: {cleanup_stats['fields_removed']}")
    print(f"💾 Backup saved to: {backup_file}")
    print(f"💾 Cleaned data saved to: data/restaurants.json")

if __name__ == "__main__":
    cleanup_legacy_fields()