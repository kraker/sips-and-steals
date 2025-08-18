#!/usr/bin/env python3
"""
Create Union Station Dataset
Generate focused dataset for Union Station district expansion with LoDo.
"""

import json
from pathlib import Path
from datetime import datetime


def create_union_station_dataset():
    """Create Union Station dataset for focused high-quality expansion"""
    
    # Load master restaurants data
    with open('data/restaurants.json') as f:
        data = json.load(f)
    
    # Define Union Station area (adjacent to LoDo)
    union_station_neighborhoods = [
        'Union Station',
        'Ballpark / Union Station',
        'Ballpark / Five Points',
        'Ballpark / RiNo',
        'Curtis / Ballpark / Five Points',
        'RiNo / Ballpark / Five Points'
    ]
    
    # Filter for Union Station + LoDo restaurants
    filtered_restaurants = {}
    
    # Add LoDo restaurants (existing high-quality data)
    lodo_count = 0
    union_station_count = 0
    
    for slug, restaurant in data['restaurants'].items():
        neighborhood = restaurant.get('neighborhood', '')
        
        # Include LoDo (our proven baseline)
        if neighborhood == 'LoDo':
            filtered_restaurants[slug] = restaurant
            lodo_count += 1
        
        # Include Union Station area
        elif neighborhood in union_station_neighborhoods:
            filtered_restaurants[slug] = restaurant
            union_station_count += 1
    
    # Create combined dataset
    combined_data = {
        'metadata': {
            'source': 'lodo_union_station_expansion',
            'created_at': datetime.now().isoformat(),
            'description': 'LoDo + Union Station districts for focused expansion',
            'strategy': 'Quality over quantity - maintain LoDo demo standards',
            'geographic_scope': 'Adjacent walkable districts',
            'coverage': {
                'lodo_restaurants': lodo_count,
                'union_station_restaurants': union_station_count,
                'total_restaurants': len(filtered_restaurants)
            },
            'target_neighborhoods': {
                'proven': ['LoDo'],
                'expansion': union_station_neighborhoods
            }
        },
        'restaurants': filtered_restaurants
    }
    
    # Save dataset
    output_file = 'data/cache/lodo_union_station_restaurants.json'
    with open(output_file, 'w') as f:
        json.dump(combined_data, f, indent=2, default=str)
    
    print(f"✅ Created LoDo + Union Station dataset: {output_file}")
    print(f"📊 Dataset Summary:")
    print(f"   • LoDo restaurants: {lodo_count} (proven baseline)")
    print(f"   • Union Station restaurants: {union_station_count} (expansion)")
    print(f"   • Total restaurants: {len(filtered_restaurants)}")
    
    # Show restaurant breakdown
    print(f"\n🏙️ Restaurant Breakdown:")
    neighborhoods = {}
    for restaurant in filtered_restaurants.values():
        neighborhood = restaurant.get('neighborhood', 'Unknown')
        if neighborhood not in neighborhoods:
            neighborhoods[neighborhood] = []
        neighborhoods[neighborhood].append(restaurant['name'])
    
    for neighborhood, restaurants in sorted(neighborhoods.items()):
        print(f"   • {neighborhood}: {len(restaurants)} restaurants")
        for restaurant in sorted(restaurants):
            print(f"     - {restaurant}")
    
    # Analyze data quality
    print(f"\n📋 Data Quality Analysis:")
    with_address = len([r for r in filtered_restaurants.values() if r.get('address', {}).get('formatted_address')])
    with_cuisine = len([r for r in filtered_restaurants.values() if r.get('cuisine')])
    with_website = len([r for r in filtered_restaurants.values() if r.get('website')])
    
    total = len(filtered_restaurants)
    print(f"   • Restaurants with addresses: {with_address}/{total} ({with_address/total*100:.1f}%)")
    print(f"   • Restaurants with cuisine: {with_cuisine}/{total} ({with_cuisine/total*100:.1f}%)")
    print(f"   • Restaurants with websites: {with_website}/{total} ({with_website/total*100:.1f}%)")
    
    print(f"\n🎯 Next Steps:")
    print(f"   1. Enrich missing metadata for Union Station restaurants")
    print(f"   2. Run focused discovery on {union_station_count} expansion targets")
    print(f"   3. Create LoDo + Union Station demo with complete data")
    
    return output_file, len(filtered_restaurants)


if __name__ == '__main__':
    create_union_station_dataset()