#!/usr/bin/env python3
"""
Generate a static HTML website from our CSV data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.csv_manager import CSVManager
from datetime import datetime
import json

# Restaurant area mapping (based on Giovanni's data)
RESTAURANT_AREAS = {
    'Jax Fish House': 'Union Station',
    'Hapa Sushi': 'Union Station', 
    'Tamayo': 'Union Station'
}

def parse_days(day_string):
    """Parse day string into list of days"""
    if not day_string:
        return []
    return [day.strip() for day in day_string.split(',')]

def parse_time(time_string):
    """Parse time string and return 24hr format for sorting"""
    if not time_string or time_string in ['Happy Hour', 'All Day']:
        return time_string
    
    # Handle formats like "3:00 PM", "10:00 PM", etc.
    try:
        if 'PM' in time_string and '12:' not in time_string:
            hour = int(time_string.split(':')[0])
            if hour != 12:
                hour += 12
            return f"{hour:02d}:00"
        elif 'AM' in time_string:
            hour = int(time_string.split(':')[0])
            if hour == 12:
                hour = 0
            return f"{hour:02d}:00"
        else:
            return time_string
    except:
        return time_string

def get_price_category(price_str):
    """Categorize prices into $, $$, $$$"""
    if not price_str or price_str == '':
        return ''
    
    try:
        # Extract numeric value
        price_num = float(price_str.replace('$', '').replace(',', ''))
        if price_num <= 8:
            return '$'
        elif price_num <= 15:
            return '$$'
        else:
            return '$$$'
    except:
        return ''

def generate_html():
    """Generate the HTML website"""
    
    csv_manager = CSVManager()
    deals = csv_manager.get_all_deals()
    
    if not deals:
        print("No deals found. Run the scraper first!")
        return
    
    # Organize data
    areas = {}
    for deal in deals:
        restaurant = deal['restaurant_name']
        area = RESTAURANT_AREAS.get(restaurant, 'Other')
        
        if area not in areas:
            areas[area] = {}
        
        if restaurant not in areas[area]:
            areas[area][restaurant] = []
        
        # Add parsed data for filtering
        deal['parsed_days'] = parse_days(deal['day_of_week'])
        deal['parsed_start_time'] = parse_time(deal['start_time'])
        deal['price_category'] = get_price_category(deal['price'])
        
        areas[area][restaurant].append(deal)
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sips and Steals - Denver Happy Hour Deals</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        
        h1 {{
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .tagline {{
            font-size: 1.2em;
            opacity: 0.9;
            margin-bottom: 20px;
        }}
        
        .filters {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
        }}
        
        .filter-group {{
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}
        
        .filter-group label {{
            font-weight: 600;
            font-size: 0.9em;
            color: #555;
        }}
        
        select, button {{
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }}
        
        button {{
            background: #667eea;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
        }}
        
        button:hover {{
            background: #5a67d8;
        }}
        
        .area {{
            background: white;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .area-header {{
            background: #667eea;
            color: white;
            padding: 20px;
            font-size: 1.5em;
            font-weight: 600;
        }}
        
        .restaurant {{
            border-bottom: 1px solid #eee;
        }}
        
        .restaurant:last-child {{
            border-bottom: none;
        }}
        
        .restaurant-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            font-size: 1.2em;
            font-weight: 600;
            color: #333;
            border-left: 4px solid #667eea;
        }}
        
        .deals {{
            padding: 20px;
        }}
        
        .deal {{
            padding: 15px;
            border-left: 3px solid #e2e8f0;
            margin-bottom: 15px;
            background: #f8f9fa;
            border-radius: 0 5px 5px 0;
        }}
        
        .deal.happy-hour {{
            border-left-color: #48bb78;
        }}
        
        .deal.weekly-special {{
            border-left-color: #ed8936;
        }}
        
        .deal.food {{
            border-left-color: #4299e1;
        }}
        
        .deal.drink {{
            border-left-color: #9f7aea;
        }}
        
        .deal-title {{
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 5px;
            color: #2d3748;
        }}
        
        .deal-description {{
            color: #666;
            margin-bottom: 10px;
            font-size: 0.95em;
        }}
        
        .deal-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            font-size: 0.9em;
        }}
        
        .meta-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .meta-icon {{
            font-size: 1.1em;
        }}
        
        .price {{
            background: #667eea;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.9em;
        }}
        
        .time-badge {{
            background: #48bb78;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.85em;
        }}
        
        .day-badge {{
            background: #ed8936;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.85em;
        }}
        
        .now-open {{
            background: #e53e3e;
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 600;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
            100% {{ opacity: 1; }}
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            opacity: 0.8;
        }}
        
        .hidden {{
            display: none !important;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            h1 {{
                font-size: 2em;
            }}
            
            .filters {{
                flex-direction: column;
                align-items: stretch;
            }}
            
            .filter-group {{
                flex-direction: row;
                align-items: center;
                justify-content: space-between;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🍻 Sips and Steals</h1>
            <div class="tagline">Denver's Happy Hour Deal Finder</div>
            <div class="tagline">Updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
        </header>
        
        <div class="filters">
            <div class="filter-group">
                <label for="day-filter">Day:</label>
                <select id="day-filter">
                    <option value="">All Days</option>
                    <option value="Monday">Monday</option>
                    <option value="Tuesday">Tuesday</option>
                    <option value="Wednesday">Wednesday</option>
                    <option value="Thursday">Thursday</option>
                    <option value="Friday">Friday</option>
                    <option value="Saturday">Saturday</option>
                    <option value="Sunday">Sunday</option>
                </select>
            </div>
            
            <div class="filter-group">
                <label for="time-filter">Time:</label>
                <select id="time-filter">
                    <option value="">All Times</option>
                    <option value="lunch">Lunch (11am-3pm)</option>
                    <option value="afternoon">Afternoon (3pm-6pm)</option>
                    <option value="evening">Evening (6pm-9pm)</option>
                    <option value="late">Late Night (9pm+)</option>
                </select>
            </div>
            
            <div class="filter-group">
                <label for="price-filter">Price:</label>
                <select id="price-filter">
                    <option value="">All Prices</option>
                    <option value="$">$ (Under $8)</option>
                    <option value="$$">$$ ($8-$15)</option>
                    <option value="$$$">$$$ (Over $15)</option>
                </select>
            </div>
            
            <div class="filter-group">
                <label for="type-filter">Type:</label>
                <select id="type-filter">
                    <option value="">All Types</option>
                    <option value="happy_hour">Happy Hour</option>
                    <option value="weekly_special">Weekly Special</option>
                    <option value="food">Food</option>
                    <option value="drink">Drinks</option>
                </select>
            </div>
            
            <button onclick="clearFilters()">Clear All</button>
        </div>
        
        <div id="deals-container">
"""
    
    # Add areas and restaurants
    for area_name, restaurants in areas.items():
        html += f"""
        <div class="area">
            <div class="area-header">📍 {area_name}</div>
"""
        
        for restaurant_name, restaurant_deals in restaurants.items():
            html += f"""
            <div class="restaurant">
                <div class="restaurant-header">{restaurant_name}</div>
                <div class="deals">
"""
            
            for deal in restaurant_deals:
                # Format days
                days_display = ', '.join(deal['parsed_days'][:3])
                if len(deal['parsed_days']) > 3:
                    days_display += f" +{len(deal['parsed_days'])-3} more"
                
                # Format time
                time_display = ""
                if deal['start_time'] and deal['end_time']:
                    if deal['start_time'] == deal['end_time']:
                        time_display = deal['start_time']
                    else:
                        time_display = f"{deal['start_time']} - {deal['end_time']}"
                
                deal_classes = f"deal {deal['deal_type']}"
                
                html += f"""
                    <div class="{deal_classes}" 
                         data-days="{deal['day_of_week']}" 
                         data-start-time="{deal['parsed_start_time']}" 
                         data-price-category="{deal['price_category']}"
                         data-deal-type="{deal['deal_type']}">
                        <div class="deal-title">{deal['title']}</div>
"""
                
                if deal['description']:
                    html += f'<div class="deal-description">{deal["description"][:120]}{"..." if len(deal["description"]) > 120 else ""}</div>'
                
                html += '<div class="deal-meta">'
                
                if days_display:
                    html += f'<div class="meta-item"><span class="meta-icon">📅</span><span class="day-badge">{days_display}</span></div>'
                
                if time_display:
                    html += f'<div class="meta-item"><span class="meta-icon">⏰</span><span class="time-badge">{time_display}</span></div>'
                
                if deal['price']:
                    html += f'<div class="meta-item"><span class="meta-icon">💰</span><span class="price">{deal["price"]}</span></div>'
                
                deal_type_display = deal['deal_type'].replace('_', ' ').title()
                html += f'<div class="meta-item"><span class="meta-icon">🏷️</span>{deal_type_display}</div>'
                
                html += '</div></div>'
            
            html += '</div></div>'
        
        html += '</div>'
    
    # Add footer
    html += f"""
        </div>
        
        <div class="footer">
            <p>🤖 Generated from live restaurant data • Total deals: {len(deals)}</p>
            <p>Data last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
    """
    
    # Generate JavaScript separately to avoid f-string formatting issues
    js_deals_data = json.dumps([{
        'restaurant': deal['restaurant_name'],
        'title': deal['title'],
        'days': deal['parsed_days'],
        'start_time': deal['parsed_start_time'],
        'price_category': deal['price_category'],
        'deal_type': deal['deal_type']
    } for deal in deals])
    
    html += """
    <script>
        // Store original deals data
        const dealsData = """ + js_deals_data + """;
        
        function filterDeals() {
            const dayFilter = document.getElementById('day-filter').value;
            const timeFilter = document.getElementById('time-filter').value;
            const priceFilter = document.getElementById('price-filter').value;
            const typeFilter = document.getElementById('type-filter').value;
            
            const deals = document.querySelectorAll('.deal');
            
            deals.forEach(deal => {
                let visible = true;
                
                // Day filter
                if (dayFilter && !deal.dataset.days.includes(dayFilter)) {
                    visible = false;
                }
                
                // Time filter
                if (timeFilter && deal.dataset.startTime) {
                    const startTime = deal.dataset.startTime;
                    if (startTime !== 'Happy Hour' && startTime !== 'All Day') {
                        const hour = parseInt(startTime.split(':')[0]);
                        switch(timeFilter) {
                            case 'lunch':
                                if (hour < 11 || hour >= 15) visible = false;
                                break;
                            case 'afternoon':
                                if (hour < 15 || hour >= 18) visible = false;
                                break;
                            case 'evening':
                                if (hour < 18 || hour >= 21) visible = false;
                                break;
                            case 'late':
                                if (hour < 21) visible = false;
                                break;
                        }
                    }
                }
                
                // Price filter
                if (priceFilter && deal.dataset.priceCategory !== priceFilter) {
                    visible = false;
                }
                
                // Type filter
                if (typeFilter && deal.dataset.dealType !== typeFilter) {
                    visible = false;
                }
                
                deal.classList.toggle('hidden', !visible);
            });
            
            // Hide empty restaurants and areas
            document.querySelectorAll('.restaurant').forEach(restaurant => {
                const visibleDeals = restaurant.querySelectorAll('.deal:not(.hidden)');
                restaurant.classList.toggle('hidden', visibleDeals.length === 0);
            });
            
            document.querySelectorAll('.area').forEach(area => {
                const visibleRestaurants = area.querySelectorAll('.restaurant:not(.hidden)');
                area.classList.toggle('hidden', visibleRestaurants.length === 0);
            });
        }
        
        function clearFilters() {
            document.getElementById('day-filter').value = '';
            document.getElementById('time-filter').value = '';
            document.getElementById('price-filter').value = '';
            document.getElementById('type-filter').value = '';
            filterDeals();
        }
        
        // Add event listeners
        document.getElementById('day-filter').addEventListener('change', filterDeals);
        document.getElementById('time-filter').addEventListener('change', filterDeals);
        document.getElementById('price-filter').addEventListener('change', filterDeals);
        document.getElementById('type-filter').addEventListener('change', filterDeals);
        
        // Initialize with current day
        const today = new Date().toLocaleDateString('en-US', {weekday: 'long'});
        document.getElementById('day-filter').value = today;
        filterDeals();
    </script>
</body>
</html>"""
    
    # Write the HTML file
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("✅ Generated website at docs/index.html")
    print("🌐 Open in browser to view the visual interface!")

if __name__ == "__main__":
    # Create docs directory
    os.makedirs('docs', exist_ok=True)
    generate_html()