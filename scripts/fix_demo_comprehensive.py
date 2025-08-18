#!/usr/bin/env python3
"""
Comprehensive Demo Fix
Extract ALL available data from restaurants, both enriched and original data.
"""

import json
import re


def calculate_drink_price_estimate(restaurant, extracted_prices):
    """Calculate realistic drink price estimates based on restaurant data"""
    
    # If we extracted prices from deals, use them
    if extracted_prices:
        return round(sum(extracted_prices) / len(extracted_prices), 2)
    
    # No deals or no price data - estimate based on restaurant characteristics
    price_range = restaurant.get('price_range', '$$')
    cuisine = (restaurant.get('cuisine') or '').lower()
    name = restaurant.get('name', '').lower()
    
    # Base estimates by price range
    if price_range == '$$$$':  # High-end
        base_price = 14.0
    elif price_range == '$$$':  # Upscale
        base_price = 11.0
    elif price_range == '$$':  # Mid-range
        base_price = 8.0
    else:  # $ - Budget
        base_price = 6.0
    
    # Adjust based on cuisine type (some cuisines tend to have higher/lower drink prices)
    if any(word in cuisine for word in ['steakhouse', 'brazilian', 'japanese']):
        base_price += 2.0
    elif any(word in cuisine for word in ['cocktail', 'bar']):
        base_price += 1.0
    elif any(word in cuisine for word in ['mexican', 'asian']):
        base_price -= 0.5
    
    # Adjust based on restaurant name indicators
    if any(word in name for word in ['stk', 'urban farmer', 'uchi']):
        base_price += 1.0
    elif 'vinyl' in name:  # Cocktail-focused
        base_price += 0.5
    
    # Only return price estimate if restaurant likely has happy hour (has deals)
    return base_price


def calculate_food_price_estimate(restaurant, extracted_prices):
    """Calculate realistic food price estimates based on restaurant data"""
    
    # If we extracted prices from deals, use them
    if extracted_prices:
        return round(sum(extracted_prices) / len(extracted_prices), 2)
    
    # No deals or no price data - estimate based on restaurant characteristics  
    price_range = restaurant.get('price_range', '$$')
    cuisine = (restaurant.get('cuisine') or '').lower()
    name = restaurant.get('name', '').lower()
    
    # Base estimates by price range (food is typically higher than drinks)
    if price_range == '$$$$':  # High-end
        base_price = 18.0
    elif price_range == '$$$':  # Upscale  
        base_price = 14.0
    elif price_range == '$$':  # Mid-range
        base_price = 11.0
    else:  # $ - Budget
        base_price = 8.0
    
    # Adjust based on cuisine type
    if any(word in cuisine for word in ['steakhouse', 'brazilian']):
        base_price += 3.0
    elif any(word in cuisine for word in ['japanese', 'sushi']):
        base_price += 2.0
    elif any(word in cuisine for word in ['italian', 'mediterranean']):
        base_price += 1.0
    elif any(word in cuisine for word in ['mexican', 'asian']):
        base_price -= 1.0
    
    # Cocktail bars typically have lighter food options
    if 'cocktail' in cuisine or 'bar' in cuisine:
        base_price -= 2.0
    
    # Only return price estimate if restaurant likely has happy hour (has deals)
    return base_price


def fix_demo_comprehensive():
    """Extract all available contact data from enriched dataset"""
    
    # Load demo data
    with open('data/cache/lodo_union_station_demo.json') as f:
        demo_data = json.load(f)
    
    # Load enriched data (has all original data + enrichments)
    with open('data/cache/lodo_union_station_enriched.json') as f:
        enriched_data = json.load(f)
    
    # Load current deals data to get deal summaries
    with open('data/deals.json') as f:
        deals_data = json.load(f)
    
    print("🔍 Comprehensive Data Extraction for Demo")
    print("=" * 60)
    
    # Create deals lookup
    deals_by_restaurant = {}
    for deal in deals_data.get('deals', []):
        restaurant_slug = deal.get('restaurant_slug')
        if restaurant_slug:
            if restaurant_slug not in deals_by_restaurant:
                deals_by_restaurant[restaurant_slug] = []
            deals_by_restaurant[restaurant_slug].append(deal)
    
    # Convert to LoDo-compatible format with comprehensive data extraction
    lodo_format_data = {}
    total_restaurants = 0
    enriched_count = 0
    original_count = 0
    
    for slug in demo_data['restaurants'].keys():
        total_restaurants += 1
        enriched_restaurant = enriched_data['restaurants'].get(slug, {})
        
        if not enriched_restaurant:
            print(f"⚠️  {slug} not found in enriched data")
            continue
        
        # Get deals for this restaurant
        restaurant_deals = deals_by_restaurant.get(slug, [])
        
        # Calculate deal prices - improved logic
        drink_prices = []
        food_prices = []
        for deal in restaurant_deals:
            # Get price from multiple possible fields
            price_str = deal.get('price', '') or deal.get('title', '') or deal.get('description', '')
            
            # Look for price patterns like $5, $12.50, $5-8, etc.
            price_matches = re.findall(r'\$([0-9]+(?:\.[0-9]{2})?)', price_str)
            if price_matches:
                # Use first price found (usually the main price)
                price = float(price_matches[0])
                
                # Categorize by deal type or description keywords
                description = (deal.get('description', '') + ' ' + deal.get('title', '')).lower()
                deal_type = deal.get('deal_type', '').lower()
                
                # Categorize as drink if it mentions drinks/beverages or is explicitly a drink deal
                is_drink = any(word in description for word in [
                    'drink', 'cocktail', 'beer', 'wine', 'beverage', 'martini', 'margarita', 
                    'spirits', 'liquor', 'bourbon', 'whiskey', 'vodka', 'rum', 'gin'
                ])
                
                # Categorize as food if it mentions food items or is explicitly a food deal
                is_food = any(word in description for word in [
                    'food', 'appetizer', 'plate', 'dish', 'entree', 'meal', 'burger', 
                    'sandwich', 'salad', 'pizza', 'wings', 'tacos', 'nachos', 'fries'
                ])
                
                # If unclear from description, try deal type
                if not is_drink and not is_food:
                    if 'drink' in deal_type or 'beverage' in deal_type:
                        is_drink = True
                    elif 'food' in deal_type or 'appetizer' in deal_type:
                        is_food = True
                    else:
                        # Default assumption: prices under $10 tend to be drinks, over $10 tend to be food
                        if price <= 10:
                            is_drink = True
                        else:
                            is_food = True
                
                if is_drink:
                    drink_prices.append(price)
                if is_food:
                    food_prices.append(price)
        
        # COMPREHENSIVE CONTACT INFO EXTRACTION
        
        # Phone - try all possible fields
        phone = ''
        phone_sources = [
            enriched_restaurant.get('contact', {}).get('phone'),
            enriched_restaurant.get('contact_info', {}).get('primary_phone'),
            enriched_restaurant.get('contact_info', {}).get('reservation_phone')
        ]
        for source in phone_sources:
            if source:
                phone = source
                break
        
        # Address - try all possible fields
        address = ''
        address_sources = [
            enriched_restaurant.get('contact', {}).get('formatted_address'),
            enriched_restaurant.get('contact', {}).get('address'),
            enriched_restaurant.get('address', {}).get('formatted_address')
        ]
        for source in address_sources:
            if source:
                address = source
                break
        
        # If no formatted address, try to construct from google maps URL
        if not address:
            google_maps_url = enriched_restaurant.get('address', {}).get('google_maps_url', '')
            if google_maps_url and 'maps.google.com' in google_maps_url:
                # Extract address from Google Maps URL
                import urllib.parse
                parsed = urllib.parse.urlparse(google_maps_url)
                query = urllib.parse.parse_qs(parsed.query).get('q', [''])
                if query[0]:
                    address = urllib.parse.unquote_plus(query[0])
        
        # Website - try all possible fields
        website = ''
        website_sources = [
            enriched_restaurant.get('social', {}).get('website'),
            enriched_restaurant.get('website')
        ]
        for source in website_sources:
            if source:
                website = source
                break
        
        # Reservation URL and platform
        reservation_url = ''
        reservation_platform = ''
        
        reservation_sources = [
            enriched_restaurant.get('reservations', {}).get('url'),
            enriched_restaurant.get('service_info', {}).get('opentable_url')
        ]
        for source in reservation_sources:
            if source:
                reservation_url = source
                break
        
        # Determine platform from URL if not set
        if reservation_url:
            reservation_platform = enriched_restaurant.get('reservations', {}).get('platform', '')
            if not reservation_platform:
                if 'opentable' in reservation_url.lower():
                    reservation_platform = 'OpenTable'
                elif 'resy' in reservation_url.lower():
                    reservation_platform = 'Resy'
                else:
                    reservation_platform = 'Reservations'
        
        # Happy hour schedule conversion
        schedule = []
        demo_restaurant = demo_data['restaurants'][slug]
        if demo_restaurant.get('happy_hour', {}).get('weekly_schedule'):
            for sched in demo_restaurant['happy_hour']['weekly_schedule']:
                if sched.get('days') and sched.get('time'):
                    schedule.append({
                        'days': sched['days'],
                        'times': [sched['time']]
                    })
        
        # Build LoDo-compatible restaurant object
        lodo_format_data[slug] = {
            'name': enriched_restaurant['name'],
            'cuisine': enriched_restaurant.get('cuisine') or 'Restaurant',
            'price_range': enriched_restaurant.get('price_range', '$$'),
            'website': website,
            'contact': {
                'address': address,
                'phone': phone
            },
            'reservations': {
                'platform': reservation_platform,
                'url': reservation_url
            },
            'social': {
                'website': website
            },
            'happy_hour': {
                'weekly_schedule': schedule
            },
            'deals_summary': {
                'total_deals': len(restaurant_deals),
                'avg_food_price': calculate_food_price_estimate(enriched_restaurant, food_prices),
                'avg_drink_price': calculate_drink_price_estimate(enriched_restaurant, drink_prices)
            }
        }
        
        # Track data sources and pricing
        if any([phone, address, reservation_url, website]):
            if slug in ['tavernetta', 'uchi', 'work-class', 'fogo-de-chão', 'mercantile', 
                       'ultreia', 'sunday-vinyl', 'sushi-rama', 'a5-steakhouse', 'thirsty-lion']:
                enriched_count += 1
            else:
                original_count += 1
                print(f"✅ Extracted data for {enriched_restaurant['name']} from original sources")
        
        # Debug pricing for restaurants with deals
        if len(restaurant_deals) > 0:
            avg_drink = round(sum(drink_prices) / len(drink_prices), 2) if drink_prices else 0
            avg_food = round(sum(food_prices) / len(food_prices), 2) if food_prices else 0
            if avg_drink > 0 or avg_food > 0:
                print(f"💰 {enriched_restaurant['name']}: {len(restaurant_deals)} deals → Drinks: ${avg_drink}, Food: ${avg_food}")
    
    # Read the working LoDo demo HTML
    with open('docs/index.html') as f:
        lodo_html = f.read()
    
    # Replace the title and description
    fixed_html = lodo_html.replace(
        '<title>LoDo Happy Hours | Denver</title>',
        '<title>LoDo + Union Station Happy Hours | Denver</title>'
    )
    
    fixed_html = fixed_html.replace(
        '<h1>🍻 LoDo Happy Hours</h1>',
        '<h1>🍻 LoDo + Union Station Happy Hours</h1>'
    )
    
    fixed_html = fixed_html.replace(
        '<div class="district-status" id="districtStatus">Lower Downtown Denver</div>',
        '<div class="district-status" id="districtStatus">LoDo + Union Station Districts</div>'
    )
    
    # Replace the RESTAURANT_DATA
    data_start = fixed_html.find('const RESTAURANT_DATA = {')
    data_end = fixed_html.find('        };', data_start) + 10
    
    new_data = f"const RESTAURANT_DATA = {json.dumps(lodo_format_data, indent=12)};"
    
    fixed_html = fixed_html[:data_start] + new_data + fixed_html[data_end:]
    
    # Save the fixed demo
    with open('docs/lodo_union_station_demo_fixed.html', 'w') as f:
        f.write(fixed_html)
    
    print("✅ Comprehensive LoDo + Union Station demo created!")
    print("📁 File: docs/lodo_union_station_demo_fixed.html")
    print(f"📊 Restaurants: {len(lodo_format_data)}")
    
    # Comprehensive statistics
    with_deals = len([r for r in lodo_format_data.values() if r['deals_summary']['total_deals'] > 0])
    with_phone = len([r for r in lodo_format_data.values() if r['contact']['phone']])
    with_address = len([r for r in lodo_format_data.values() if r['contact']['address']])
    with_reservations = len([r for r in lodo_format_data.values() if r['reservations']['url']])
    with_website = len([r for r in lodo_format_data.values() if r['website']])
    
    # Count restaurants that will have action buttons
    with_buttons = len([r for r in lodo_format_data.values() if 
                       r['contact']['phone'] or r['contact']['address'] or 
                       r['reservations']['url'] or r['website']])
    
    print(f"📈 Comprehensive Statistics:")
    print(f"   • Restaurants with deals: {with_deals}/{len(lodo_format_data)}")
    print(f"   • Restaurants with phone: {with_phone}/{len(lodo_format_data)}")
    print(f"   • Restaurants with address: {with_address}/{len(lodo_format_data)}")
    print(f"   • Restaurants with reservations: {with_reservations}/{len(lodo_format_data)}")
    print(f"   • Restaurants with website: {with_website}/{len(lodo_format_data)}")
    print(f"   • Restaurants with action buttons: {with_buttons}/{len(lodo_format_data)}")
    print(f"   • Data from manual enrichment: {enriched_count}")
    print(f"   • Data from original sources: {original_count}")
    
    # Show missing data restaurants
    missing_data = [r['name'] for r in lodo_format_data.values() if 
                   not (r['contact']['phone'] or r['contact']['address'] or 
                        r['reservations']['url'] or r['website'])]
    
    if missing_data:
        print(f"\n⚠️  Restaurants still missing contact data:")
        for name in missing_data:
            print(f"   • {name}")
    
    return 'docs/lodo_union_station_demo_fixed.html'


if __name__ == '__main__':
    fix_demo_comprehensive()