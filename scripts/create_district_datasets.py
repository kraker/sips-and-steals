#!/usr/bin/env python3
"""
Create District-Specific Datasets
Generate filtered restaurant datasets for discovery and extraction targeting.
"""

import json
from pathlib import Path
from datetime import datetime


def create_district_datasets():
    """Create filtered datasets for target districts"""
    
    # Load master restaurants data
    with open('data/restaurants.json') as f:
        data = json.load(f)
    
    # Define target districts
    target_districts = {
        'central_expanded': {
            'districts': ['Central'],
            'description': 'All Central district restaurants (LoDo + surrounding)'
        },
        'northwest_denver': {
            'districts': ['Northwest Denver'], 
            'description': 'Highland, Berkeley, Sunnyside neighborhoods'
        },
        'north_denver': {
            'districts': ['North Denver'],
            'description': 'RiNo, Five Points, Curtis Park neighborhoods'
        }
    }
    
    # Create filtered datasets
    for dataset_name, config in target_districts.items():
        restaurants = {}
        
        # Filter restaurants by district
        for slug, restaurant in data['restaurants'].items():
            if restaurant.get('district') in config['districts']:
                restaurants[slug] = restaurant
        
        # Create filtered dataset
        filtered_data = {
            'metadata': {
                'source': 'district_expansion',
                'created_at': datetime.now().isoformat(),
                'target_districts': config['districts'],
                'description': config['description'],
                'total_restaurants': len(restaurants)
            },
            'restaurants': restaurants
        }
        
        # Save dataset
        output_file = f'data/cache/{dataset_name}_restaurants.json'
        with open(output_file, 'w') as f:
            json.dump(filtered_data, f, indent=2, default=str)
        
        print(f"✅ Created {output_file}")
        print(f"   {len(restaurants)} restaurants in {config['districts']}")
        
        # Show neighborhood breakdown
        neighborhoods = {}
        for restaurant in restaurants.values():
            neighborhood = restaurant.get('neighborhood', 'Unknown')
            neighborhoods[neighborhood] = neighborhoods.get(neighborhood, 0) + 1
        
        print(f"   Neighborhoods:")
        for neighborhood, count in sorted(neighborhoods.items(), key=lambda x: x[1], reverse=True):
            print(f"     • {neighborhood}: {count}")
        print()
    
    # Create combined downtown dataset
    downtown_restaurants = {}
    target_districts_list = ['Central', 'Northwest Denver', 'North Denver']
    
    for slug, restaurant in data['restaurants'].items():
        if restaurant.get('district') in target_districts_list:
            downtown_restaurants[slug] = restaurant
    
    downtown_data = {
        'metadata': {
            'source': 'downtown_expansion',
            'created_at': datetime.now().isoformat(),
            'target_districts': target_districts_list,
            'description': 'Complete downtown Denver core + adjacent trendy districts',
            'total_restaurants': len(downtown_restaurants)
        },
        'restaurants': downtown_restaurants
    }
    
    with open('data/cache/downtown_restaurants.json', 'w') as f:
        json.dump(downtown_data, f, indent=2, default=str)
    
    print(f"✅ Created data/cache/downtown_restaurants.json")
    print(f"   {len(downtown_restaurants)} restaurants across downtown Denver")
    
    # Summary
    print(f"\n📊 District Expansion Summary:")
    print(f"   • Central (expanded): {len([r for r in data['restaurants'].values() if r.get('district') == 'Central'])} restaurants")
    print(f"   • Northwest Denver: {len([r for r in data['restaurants'].values() if r.get('district') == 'Northwest Denver'])} restaurants") 
    print(f"   • North Denver: {len([r for r in data['restaurants'].values() if r.get('district') == 'North Denver'])} restaurants")
    print(f"   • Total expansion: {len(downtown_restaurants)} restaurants")
    print(f"   • Geographic coverage: Complete walkable downtown core")


if __name__ == '__main__':
    create_district_datasets()