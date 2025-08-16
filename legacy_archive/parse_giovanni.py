#!/usr/bin/env python3
"""
Final parser for Giovanni's markdown file - cleaned up for production
Creates optimized JSON structure for multi-page restaurant site
"""

import re
import json
from datetime import datetime

def main():
    """Parse Giovanni's markdown and create production-ready JSON"""
    
    with open('data/giovanni_happy_hours.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse restaurants
    restaurants_by_area = parse_all_areas(content)
    
    # Extract neighborhoods for each district
    districts_with_neighborhoods = {}
    for area, restaurants in restaurants_by_area.items():
        neighborhoods = set()
        for restaurant in restaurants.values():
            if restaurant.get('sub_location'):
                neighborhoods.add(restaurant['sub_location'])
        districts_with_neighborhoods[area] = sorted(list(neighborhoods))
    
    # Create final optimized structure
    final_data = {
        'metadata': {
            'source': 'giovanni_happy_hours.md',
            'updated_at': datetime.now().isoformat(),
            'districts': list(restaurants_by_area.keys()),
            'districts_with_neighborhoods': districts_with_neighborhoods,
            'total_restaurants': sum(len(restaurants) for restaurants in restaurants_by_area.values()),
            'target_user': 'Value-Conscious Culinary Adventurer',
            'focus': 'Quality dining experiences at accessible prices'
        },
        'areas': restaurants_by_area  # Keep as 'areas' for backwards compatibility
    }
    
    # Save to consolidated data file
    with open('data/restaurants.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Restaurant data parsed successfully!")
    print(f"📊 {final_data['metadata']['total_restaurants']} restaurants across {len(restaurants_by_area)} districts")
    print(f"💾 Saved to data/restaurants.json")
    
    # Print district summary with neighborhoods
    for district, restaurants in restaurants_by_area.items():
        neighborhoods = districts_with_neighborhoods.get(district, [])
        if neighborhoods:
            print(f"  {district}: {len(restaurants)} restaurants in {len(neighborhoods)} neighborhoods")
            print(f"    Neighborhoods: {', '.join(neighborhoods[:5])}{'...' if len(neighborhoods) > 5 else ''}")
        else:
            print(f"  {district}: {len(restaurants)} restaurants")

def parse_all_areas(content):
    """Parse all restaurant areas from markdown content"""
    
    # Split by area headers
    sections = re.split(r'\*{3}([^*]+)\*{3}', content)
    restaurants_by_area = {}
    
    for i in range(1, len(sections), 2):
        if i + 1 >= len(sections):
            break
            
        area_name = sections[i].strip()
        area_content = sections[i + 1]
        
        # Skip non-location sections
        skip_areas = ['Swanky Happy Hour', 'Speakeasy', 'Taco Tuesday', 'Classic bar', 'Service Industry', 'Other Awesome']
        if any(skip in area_name for skip in skip_areas):
            continue
            
        restaurants = parse_area_restaurants(area_content, area_name)
        if restaurants:
            restaurants_by_area[area_name] = restaurants
    
    return restaurants_by_area

def parse_area_restaurants(content, area_name):
    """Parse restaurants within a specific area - optimized version"""
    restaurants = {}
    
    # Split into restaurant blocks by double newlines followed by **Restaurant Name**
    blocks = re.split(r'\n\n(?=\*\*[^*\n]*\*\*)', content)
    
    for block in blocks:
        block = block.strip()
        if not block or len(block) < 10:
            continue
            
        restaurant = parse_restaurant_block(block, area_name)
        if restaurant:
            slug = create_slug(restaurant['name'])
            restaurants[slug] = restaurant
    
    return restaurants

def parse_restaurant_block(block, area_name):
    """Parse individual restaurant block with improved accuracy"""
    lines = [line.strip() for line in block.split('\n') if line.strip()]
    if not lines:
        return None
    
    restaurant = {
        'name': None,
        'slug': None,
        'district': area_name,  # Using 'district' for clarity
        'area': area_name,  # Keep for backwards compatibility
        'sub_location': None,
        'address': None,
        'cuisine': None,
        'happy_hour_times': [],
        'website': None,
        'special_notes': []
    }
    
    # Find restaurant name (first **text** that looks like a name)
    restaurant_name = None
    for line in lines:
        if line.startswith('**') and line.endswith('**'):
            potential_name = line.strip('*').strip()
            if is_restaurant_name(potential_name):
                # Clean escaped characters like \- and \| from restaurant names
                restaurant_name = potential_name.replace('\\-', '-').replace('\\|', '|').replace('\\#', '#')
                restaurant['name'] = restaurant_name
                restaurant['slug'] = create_slug(restaurant_name)
                break
    
    if not restaurant_name:
        return None
    
    # Parse remaining content
    for line in lines:
        line = line.strip()
        
        # Skip the name line we already processed
        if line == f"**{restaurant_name}**":
            continue
            
        # Happy hour times (bold text with time patterns)
        if line.startswith('**') and line.endswith('**'):
            time_text = line.strip('*').strip()
            if is_happy_hour_time(time_text):
                # Clean escaped characters like \- and \|
                clean_time = time_text.replace('\\-', '-').replace('\\|', '|').replace('\\#', '#')
                restaurant['happy_hour_times'].append(clean_time)
                continue
        
        # Cuisine type (italic text)
        if (line.startswith('*') and line.endswith('*') and 
            not line.startswith('**') and len(line) > 2):
            cuisine = line.strip('*').strip()
            if not any(word in cuisine.lower() for word in ['hours', 'not', 'website']):
                restaurant['cuisine'] = cuisine
                continue
            
        # Website URLs
        if '[' in line and '](' in line and 'http' in line:
            url_match = re.search(r'\(([^)]+)\)', line)
            if url_match and 'http' in url_match.group(1):
                restaurant['website'] = url_match.group(1)
                continue
                
        # Address (has numbers and address words)
        if (any(char.isdigit() for char in line) and 
            any(word in line.lower() for word in ['st', 'street', 'ave', 'avenue', 'blvd', 'rd', 'drive', 'co', 'denver']) and
            not restaurant['address']):
            restaurant['address'] = line
            continue
            
        # Sub-location (neighborhood/area info)
        if (not any(char.isdigit() for char in line) and 
            not line.startswith('[') and 
            'http' not in line.lower() and
            2 < len(line) < 60 and
            not restaurant['sub_location'] and
            not any(word in line.lower() for word in ['plant', 'hours', 'website', 'menu'])):
            restaurant['sub_location'] = line
            continue
            
        # Special dietary options
        if ('🥕' in line or 'plant' in line.lower() or 'vegan' in line.lower()):
            if 'Plant-Based Options' not in restaurant['special_notes']:
                restaurant['special_notes'].append('Plant-Based Options')
    
    # Refine sub_location based on address if in Central district
    if restaurant['area'] == 'Central' and restaurant['address']:
        restaurant['sub_location'] = refine_central_neighborhood(restaurant['sub_location'], restaurant['address'])
    
    return restaurant

def is_restaurant_name(text):
    """Improved logic to identify restaurant names vs schedules"""
    # Time-related words that indicate this is NOT a restaurant name
    time_words = [
        'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
        'am', 'pm', 'close', 'all day', 'night', 'open', 'hour'
    ]
    
    text_lower = text.lower()
    
    # Count time indicators
    time_count = sum(1 for word in time_words if word in text_lower)
    
    # If multiple time words or contains time patterns, likely not a name
    if time_count >= 2:
        return False
    
    # If very long with time indicators, probably not a name
    if len(text) > 60 and time_count > 0:
        return False
    
    # If contains time patterns like "3 - 6" or "Mon |", probably not a name
    if (re.search(r'\d+\s*[-|]\s*\d+', text) or 
        re.search(r'(mon|tue|wed|thu|fri|sat|sun)\s*[|&]', text_lower)):
        return False
    
    return True

def is_happy_hour_time(text):
    """Identify happy hour time schedules"""
    time_indicators = [
        'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
        'am', 'pm', 'close', 'all day', 'night', 'open'
    ]
    
    text_lower = text.lower()
    
    # Must have time indicators and time separators
    has_time_words = any(word in text_lower for word in time_indicators)
    has_time_separators = any(char in text for char in ['-', '|', ':'])
    
    return has_time_words and has_time_separators

def refine_central_neighborhood(original_location, address):
    """Refine neighborhood identification for Central Denver based on address"""
    if not address:
        return original_location
    
    address_lower = address.lower()
    
    # LoDo streets (Lower Downtown)
    lodo_streets = ['larimer', 'market', 'blake', 'wazee']
    
    # Check for LoDo indicators
    if any(street in address_lower for street in lodo_streets):
        # Streets that are clearly LoDo (1400-1500 blocks of Larimer, Market, Blake)
        if 'larimer' in address_lower and any(num in address for num in ['1400', '1431', '1433', '1453']):
            return 'LoDo'
        if 'market' in address_lower and any(num in address for num in ['1550']):
            return 'LoDo'
        if 'blake' in address_lower and any(num in address for num in ['1514', '1520']):
            return 'LoDo'
        if 'wazee' in address_lower and any(num in address for num in ['1400', '1659']):
            return 'LoDo'
    
    # Union Station area (1600-1700 blocks, Wynkoop area)
    if 'wynkoop' in address_lower:
        return 'Union Station'
    
    # 17th Street locations
    if '17th st' in address_lower and '1539' in address:
        return 'LoDo'
    
    # Keep original if no better match
    return original_location if original_location else 'Central'

def create_slug(name):
    """Create clean URL slug"""
    slug = name.lower()
    # Remove special characters except spaces and hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug

if __name__ == "__main__":
    main()