#!/usr/bin/env python3
"""
Create Downtown Demo Dashboard
Build expanded downtown dashboard following exact LoDo demo style and UX patterns.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


def create_downtown_demo():
    """Create downtown demo matching LoDo dashboard style exactly"""
    
    # Load expanded restaurant data
    with open('data/cache/downtown_restaurants.json') as f:
        downtown_data = json.load(f)
    
    # Load deals data
    with open('data/deals.json') as f:
        deals_data = json.load(f)
    
    print("🏗️ Creating Downtown Demo Dashboard")
    print("Following LoDo demo UX patterns...")
    
    # Create deals lookup
    deals_by_restaurant = {}
    for deal in deals_data.get('deals', []):
        restaurant_slug = deal.get('restaurant_slug')
        if restaurant_slug:
            if restaurant_slug not in deals_by_restaurant:
                deals_by_restaurant[restaurant_slug] = []
            deals_by_restaurant[restaurant_slug].append(deal)
    
    # Enhanced restaurant data with LoDo-style structure
    enhanced_restaurants = {}
    district_stats = {'Central': 0, 'Northwest Denver': 0, 'North Denver': 0}
    
    for slug, restaurant in downtown_data['restaurants'].items():
        # Count by district
        district = restaurant.get('district', 'Unknown')
        if district in district_stats:
            district_stats[district] += 1
        
        # Get deals for this restaurant
        restaurant_deals = deals_by_restaurant.get(slug, [])
        
        # Build enhanced restaurant following LoDo pattern
        enhanced_restaurant = {
            'name': restaurant['name'],
            'cuisine': restaurant.get('cuisine', 'Restaurant'),
            'price_range': restaurant.get('price_range', '$$'),
            'district': district,
            'neighborhood': restaurant.get('neighborhood', ''),
            'contact': restaurant.get('contact', {}),
            'hours': restaurant.get('hours', {}),
            'reservations': restaurant.get('reservations', {}),
            'social': restaurant.get('social', {}),
            'happy_hour': {
                'status': 'active' if restaurant_deals else 'unknown',
                'next_happy_hour': None,
                'current_deals': restaurant_deals[:3],  # Preview deals
                'weekly_schedule': create_schedule_from_deals(restaurant_deals),
                'deals_count': len(restaurant_deals)
            },
            'deals': {
                'total_deals': len(restaurant_deals),
                'avg_drink_price': calculate_avg_price(restaurant_deals, 'drink'),
                'avg_food_price': calculate_avg_price(restaurant_deals, 'food'),
                'confidence_score': max([d.get('confidence_score', 0) for d in restaurant_deals]) if restaurant_deals else 0
            }
        }
        
        enhanced_restaurants[slug] = enhanced_restaurant
    
    # Count restaurants with deals per district
    deals_by_district = {'Central': 0, 'Northwest Denver': 0, 'North Denver': 0}
    for restaurant in enhanced_restaurants.values():
        district = restaurant['district']
        if district in deals_by_district and restaurant['deals']['total_deals'] > 0:
            deals_by_district[district] += 1
    
    # Create dashboard summary
    total_restaurants = len(enhanced_restaurants)
    total_with_deals = len([r for r in enhanced_restaurants.values() if r['deals']['total_deals'] > 0])
    
    print(f"📊 Downtown Dashboard Stats:")
    print(f"   • Total restaurants: {total_restaurants}")
    print(f"   • Restaurants with deals: {total_with_deals}")
    print(f"   • Coverage rate: {total_with_deals/total_restaurants*100:.1f}%")
    
    for district, count in district_stats.items():
        deals_count = deals_by_district[district]
        print(f"   • {district}: {count} restaurants, {deals_count} with deals")
    
    # Generate HTML dashboard
    create_downtown_html(enhanced_restaurants, district_stats, deals_by_district)
    
    return enhanced_restaurants


def create_schedule_from_deals(deals: List[Dict]) -> List[Dict]:
    """Convert deals to weekly schedule format matching LoDo demo"""
    if not deals:
        return []
    
    # Group deals by time patterns
    schedules = []
    for deal in deals[:3]:  # Limit to top 3 deals
        days = deal.get('days_of_week', [])
        start_time = deal.get('start_time', '')
        end_time = deal.get('end_time', '')
        
        if days and (start_time or end_time):
            # Format days
            day_names = []
            day_map = {
                'monday': 'Monday', 'tuesday': 'Tuesday', 'wednesday': 'Wednesday',
                'thursday': 'Thursday', 'friday': 'Friday', 'saturday': 'Saturday', 'sunday': 'Sunday'
            }
            
            for day in days:
                if day.lower() in day_map:
                    day_names.append(day_map[day.lower()])
            
            # Format times
            times = []
            if start_time and end_time:
                times.append(f"{start_time} - {end_time}")
            elif start_time:
                times.append(f"From {start_time}")
            elif end_time:
                times.append(f"Until {end_time}")
            
            if day_names and times:
                schedules.append({
                    'days': day_names,
                    'times': times
                })
    
    return schedules


def calculate_avg_price(deals: List[Dict], item_type: str) -> float:
    """Calculate average price for drinks or food from deals"""
    prices = []
    
    for deal in deals:
        description = deal.get('description', '').lower()
        price_str = deal.get('price', '')
        
        if price_str and '$' in price_str:
            # Extract numeric price
            import re
            price_match = re.search(r'\\$([0-9.]+)', price_str)
            if price_match:
                price = float(price_match.group(1))
                
                # Categorize by type
                if item_type == 'drink' and any(word in description for word in ['drink', 'cocktail', 'beer', 'wine', 'beverage']):
                    prices.append(price)
                elif item_type == 'food' and any(word in description for word in ['food', 'appetizer', 'entree', 'meal', 'plate']):
                    prices.append(price)
    
    return round(sum(prices) / len(prices), 2) if prices else 0


def create_downtown_html(restaurants: Dict, district_stats: Dict, deals_by_district: Dict):
    """Create HTML dashboard matching LoDo demo exactly"""
    
    # Read the LoDo demo HTML as template
    with open('docs/index.html', 'r') as f:
        lodo_html = f.read()
    
    # Extract CSS and JavaScript structure from LoDo demo
    css_start = lodo_html.find('<style>')
    css_end = lodo_html.find('</style>') + 8
    css_section = lodo_html[css_start:css_end]
    
    js_start = lodo_html.find('<script>')
    js_end = lodo_html.find('</script>') + 9
    js_section = lodo_html[js_start:js_end]
    
    # Count totals
    total_restaurants = len(restaurants)
    total_with_deals = len([r for r in restaurants.values() if r['deals']['total_deals'] > 0])
    
    # Create downtown-specific HTML
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Downtown Denver Happy Hours | Denver</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    {css_section}
</head>
<body>
    <main class="container">
        <div class="header">
            <h1><i class="fas fa-city"></i> Downtown Denver Happy Hours</h1>
            <div class="current-time" id="currentTime"></div>
            <div class="district-status">
                🏙️ {total_restaurants} restaurants • {total_with_deals} with deals • 3 districts
            </div>
        </div>

        <div class="controls">
            <button class="filter-btn active" data-filter="all">
                <i class="fas fa-list"></i> All Restaurants
            </button>
            <button class="filter-btn" data-filter="active">
                <i class="fas fa-check-circle"></i> Open Now
            </button>
            <button class="filter-btn" data-filter="soon">
                <i class="fas fa-clock"></i> Starting Soon
            </button>
            <button class="filter-btn" data-filter="deals">
                <i class="fas fa-star"></i> Has Deals
            </button>
        </div>

        <div class="restaurant-grid" id="restaurantGrid">
            <!-- Restaurants will be rendered here -->
        </div>

        <div class="no-results" id="noResults" style="display: none;">
            <i class="fas fa-search"></i>
            <p>No restaurants match your current filter.</p>
        </div>

        <div class="footer">
            <p>🤖 Generated with <a href="https://claude.ai/code" target="_blank">Claude Code</a></p>
            <p>Data sourced from restaurant websites via respectful web scraping</p>
            <p>Downtown Denver: Central • Northwest • North Districts</p>
        </div>
    </main>

    {js_section.replace('LoDo', 'Downtown Denver').replace('lodo', 'downtown')}

    <script>
        // Embedded restaurant data - following LoDo demo pattern
        const restaurantData = {json.dumps(restaurants, indent=8, default=str)};

        // Initialize dashboard - following LoDo demo pattern
        document.addEventListener('DOMContentLoaded', function() {{
            const dashboard = new HappyHourDashboard();
            dashboard.init(restaurantData);
        }});
    </script>
</body>
</html>'''
    
    # Save downtown demo
    output_file = 'docs/downtown_demo.html'
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"🌐 Downtown demo created: {output_file}")
    print(f"   Following LoDo demo UX patterns")
    print(f"   Same responsive design and status filtering")
    print(f"   Same card layout and interaction patterns")
    
    return output_file


if __name__ == '__main__':
    create_downtown_demo()