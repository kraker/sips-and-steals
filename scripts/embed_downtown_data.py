#!/usr/bin/env python3
"""
Embed Downtown Restaurant Data
Replace LoDo data with downtown data in the fixed demo file.
"""

import json
import re
from pathlib import Path


def embed_downtown_data():
    """Replace restaurant data in downtown demo with expanded dataset"""
    
    # Load downtown restaurant data
    with open('data/cache/downtown_restaurants.json') as f:
        downtown_data = json.load(f)
    
    # Load deals data
    with open('data/deals.json') as f:
        deals_data = json.load(f)
    
    # Create deals lookup
    deals_by_restaurant = {}
    for deal in deals_data.get('deals', []):
        restaurant_slug = deal.get('restaurant_slug')
        if restaurant_slug:
            if restaurant_slug not in deals_by_restaurant:
                deals_by_restaurant[restaurant_slug] = []
            deals_by_restaurant[restaurant_slug].append(deal)
    
    # Convert to LoDo demo format
    formatted_restaurants = {}
    
    for slug, restaurant in downtown_data['restaurants'].items():
        restaurant_deals = deals_by_restaurant.get(slug, [])
        
        # Calculate average prices
        drink_prices = []
        food_prices = []
        
        for deal in restaurant_deals:
            description = deal.get('description', '').lower()
            price_str = deal.get('price', '')
            
            if price_str and '$' in price_str:
                import re
                price_match = re.search(r'\\$([0-9.]+)', price_str)
                if price_match:
                    price = float(price_match.group(1))
                    
                    if any(word in description for word in ['drink', 'cocktail', 'beer', 'wine']):
                        drink_prices.append(price)
                    elif any(word in description for word in ['food', 'appetizer', 'entree']):
                        food_prices.append(price)
        
        avg_drink_price = round(sum(drink_prices) / len(drink_prices), 2) if drink_prices else 0
        avg_food_price = round(sum(food_prices) / len(food_prices), 2) if food_prices else 0
        
        # Create schedule from deals
        weekly_schedule = []
        for deal in restaurant_deals[:3]:  # Limit to 3 deals
            days = deal.get('days_of_week', [])
            start_time = deal.get('start_time', '')
            end_time = deal.get('end_time', '')
            
            if days and (start_time or end_time):
                day_names = []
                day_map = {
                    'monday': 'Monday', 'tuesday': 'Tuesday', 'wednesday': 'Wednesday',
                    'thursday': 'Thursday', 'friday': 'Friday', 'saturday': 'Saturday', 'sunday': 'Sunday'
                }
                
                for day in days:
                    if day.lower() in day_map:
                        day_names.append(day_map[day.lower()])
                
                times = []
                if start_time and end_time:
                    times.append(f"{start_time} - {end_time}")
                elif start_time:
                    times.append(f"From {start_time}")
                
                if day_names and times:
                    weekly_schedule.append({
                        'days': day_names,
                        'times': times
                    })
        
        # Build restaurant object matching LoDo format
        formatted_restaurant = {
            'name': restaurant['name'],
            'cuisine': restaurant.get('cuisine', 'Restaurant'),
            'price_range': restaurant.get('price_range', '$$'),
            'website': restaurant.get('website', ''),
            'contact': restaurant.get('contact', {}),
            'reservations': restaurant.get('reservations', {}),
            'social': restaurant.get('social', {}),
            'happy_hour': {
                'weekly_schedule': weekly_schedule
            },
            'deals_summary': {
                'total_deals': len(restaurant_deals),
                'avg_food_price': avg_food_price,
                'avg_drink_price': avg_drink_price
            }
        }
        
        formatted_restaurants[slug] = formatted_restaurant
    
    # Read the fixed HTML file
    with open('docs/downtown_demo_fixed.html', 'r') as f:
        html_content = f.read()
    
    # Find and replace the RESTAURANT_DATA section
    data_start = html_content.find('const RESTAURANT_DATA = {')
    data_end = html_content.find('};', data_start) + 2
    
    if data_start == -1 or data_end == -1:
        print("❌ Could not find RESTAURANT_DATA section")
        return
    
    # Create new data section
    new_data_section = f'const RESTAURANT_DATA = {json.dumps(formatted_restaurants, indent=12)};'
    
    # Replace the data section
    new_html_content = html_content[:data_start] + new_data_section + html_content[data_end:]
    
    # Save the updated file
    with open('docs/downtown_demo_fixed.html', 'w') as f:
        f.write(new_html_content)
    
    print(f"✅ Downtown data embedded successfully")
    print(f"   📊 {len(formatted_restaurants)} restaurants")
    print(f"   🍻 {sum(len(deals_by_restaurant.get(slug, [])) for slug in formatted_restaurants.keys())} total deals")
    print(f"   🏙️ Coverage: Central, Northwest Denver, North Denver districts")
    
    return True


if __name__ == '__main__':
    embed_downtown_data()