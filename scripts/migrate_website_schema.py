#!/usr/bin/env python3
"""
Migrate Website Schema for Better Data Organization

Moves service_info.website → google_places.website to consolidate all
Google Places API data in one location.
"""

import json
from datetime import datetime

def migrate_website_schema():
    """Move Google Places website data to proper location"""
    
    with open('data/restaurants.json', 'r') as f:
        data = json.load(f)
    
    restaurants = data['restaurants']
    migrated_count = 0
    cleaned_service_info = 0
    
    print("🚀 MIGRATING WEBSITE SCHEMA")
    print("=" * 40)
    print("Moving service_info.website → google_places.website")
    
    for slug, restaurant in restaurants.items():
        name = restaurant.get('name', slug)
        
        # Check if migration needed
        service_website = restaurant.get('service_info', {}).get('website')
        google_places = restaurant.get('google_places', {})
        
        if service_website and google_places:
            # Move website to google_places
            google_places['website'] = service_website
            
            # Remove from service_info
            if 'service_info' in restaurant and 'website' in restaurant['service_info']:
                del restaurant['service_info']['website']
                migrated_count += 1
                
                if migrated_count <= 3:  # Show first few examples
                    print(f"\n🏪 {name}")
                    print(f"   Moved: {service_website}")
                    print(f"   From: service_info.website")
                    print(f"   To:   google_places.website")
            
            # Clean up empty service_info sections
            if restaurant.get('service_info') == {}:
                del restaurant['service_info']
                cleaned_service_info += 1
    
    # Update metadata
    data['metadata']['updated_at'] = datetime.now().isoformat()
    
    # Save migrated data
    with open('data/restaurants.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ MIGRATION COMPLETE")
    print(f"📊 Migrated website fields: {migrated_count}/{len(restaurants)}")
    print(f"🧹 Cleaned empty service_info sections: {cleaned_service_info}")
    print(f"💾 Updated restaurants.json with consistent schema")
    
    # Verify new structure
    sample = next(iter(restaurants.values()))
    print(f"\n🔍 VERIFICATION - NEW SCHEMA:")
    print(f"• Top-level website: {sample.get('website', 'N/A')}")
    print(f"• google_places.website: {sample.get('google_places', {}).get('website', 'N/A')}")
    print(f"• service_info.website: {sample.get('service_info', {}).get('website', 'REMOVED ✅')}")
    
    return migrated_count, cleaned_service_info

if __name__ == "__main__":
    migrate_website_schema()