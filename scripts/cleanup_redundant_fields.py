#!/usr/bin/env python3
"""
Clean Up Redundant Business Status Fields

Removes the top-level business_status field since we now have accurate
Google Places business_status data.
"""

import json
from datetime import datetime

def cleanup_business_status():
    """Remove redundant top-level business_status field"""
    
    with open('data/restaurants.json', 'r') as f:
        data = json.load(f)
    
    restaurants = data['restaurants']
    cleaned_count = 0
    
    print("🧹 CLEANING UP REDUNDANT BUSINESS STATUS FIELDS")
    print("=" * 50)
    
    for slug, restaurant in restaurants.items():
        if 'business_status' in restaurant:
            # Check values before removal
            old_status = restaurant['business_status']
            google_status = restaurant.get('google_places', {}).get('business_status', 'N/A')
            
            # Remove the redundant field
            del restaurant['business_status']
            cleaned_count += 1
            
            if cleaned_count <= 3:  # Show first few examples
                print(f"🏪 {restaurant.get('name', slug)}")
                print(f"   Removed: business_status = '{old_status}'")
                print(f"   Keeping: google_places.business_status = '{google_status}'")
    
    # Update metadata
    data['metadata']['updated_at'] = datetime.now().isoformat()
    
    # Save cleaned data
    with open('data/restaurants.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ CLEANUP COMPLETE")
    print(f"📊 Removed redundant business_status from {cleaned_count}/{len(restaurants)} restaurants")
    print(f"💾 Updated restaurants.json with cleaned data structure")
    
    return cleaned_count

if __name__ == "__main__":
    cleanup_business_status()