#!/usr/bin/env python3
"""
Run Google Places Enrichment

Runs the Google Places API enrichment on restaurants with batch processing
and progress tracking.
"""

import json
import os
from enrich_with_new_places_api import NewGooglePlacesEnricher


def run_batch_enrichment(limit=5):
    """Run enrichment on a batch of restaurants"""
    
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("❌ Error: GOOGLE_PLACES_API_KEY environment variable not set")
        return
    
    enricher = NewGooglePlacesEnricher(api_key)
    
    # Load current data
    with open('data/restaurants.json', 'r') as f:
        data = json.load(f)
    
    restaurants = data['restaurants']
    
    print(f"🌟 Google Places API Enrichment Starting...")
    print(f"Processing {min(limit, len(restaurants))} restaurants")
    print("=" * 60)
    
    count = 0
    successes = 0
    
    for slug, restaurant in restaurants.items():
        if count >= limit:
            break
            
        # Skip if already has Google Places data
        if restaurant.get('google_places', {}).get('place_id'):
            print(f"⏭️ Skipping {restaurant.get('name', slug)} (already enriched)")
            count += 1
            continue
        
        success = enricher.enrich_restaurant(slug, restaurant)
        if success:
            successes += 1
        
        count += 1
        
        # Save progress every 5 restaurants
        if count % 5 == 0:
            with open('data/restaurants.json', 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Progress saved: {count} processed, {successes} successful")
    
    # Final save
    with open('data/restaurants.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("🏆 GOOGLE PLACES ENRICHMENT COMPLETE")
    print("=" * 60)
    print(f"📊 Processed: {count} restaurants")
    print(f"✅ Successful: {successes} restaurants")
    print(f"❌ Failed: {count - successes} restaurants")
    print(f"💰 Estimated cost: ${enricher.stats['cost_estimate']:.2f}")
    
    success_rate = (successes / count * 100) if count > 0 else 0
    print(f"📈 Success rate: {success_rate:.1f}%")
    
    return successes, count


if __name__ == "__main__":
    import sys
    
    # Allow specifying batch size
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    
    print(f"Starting batch enrichment with {batch_size} restaurants...")
    run_batch_enrichment(batch_size)