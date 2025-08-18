#!/usr/bin/env python3
"""
Create Expanded Downtown Dashboard
Generate comprehensive happy hour discovery dashboard for downtown Denver core.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


def create_expanded_dashboard():
    """Create comprehensive dashboard for downtown Denver districts"""
    
    # Load data
    with open('data/cache/downtown_restaurants.json') as f:
        downtown_data = json.load(f)
    
    with open('data/deals.json') as f:
        deals_data = json.load(f)
    
    print("🏗️ Creating Expanded Downtown Dashboard")
    print("="*50)
    
    # Process restaurant data by district
    districts = {}
    restaurant_lookup = {}
    
    for slug, restaurant in downtown_data['restaurants'].items():
        district = restaurant.get('district', 'Unknown')
        neighborhood = restaurant.get('neighborhood', 'Unknown')
        
        if district not in districts:
            districts[district] = {
                'name': district,
                'neighborhoods': {},
                'restaurant_count': 0,
                'deals_count': 0
            }
        
        if neighborhood not in districts[district]['neighborhoods']:
            districts[district]['neighborhoods'][neighborhood] = {
                'restaurants': [],
                'deals_count': 0
            }
        
        districts[district]['neighborhoods'][neighborhood]['restaurants'].append(restaurant)
        districts[district]['restaurant_count'] += 1
        restaurant_lookup[slug] = {
            'district': district,
            'neighborhood': neighborhood,
            'restaurant': restaurant
        }
    
    # Match deals to restaurants
    deals_by_restaurant = {}
    for deal in deals_data.get('deals', []):
        restaurant_slug = deal.get('restaurant_slug')
        if restaurant_slug and restaurant_slug in restaurant_lookup:
            if restaurant_slug not in deals_by_restaurant:
                deals_by_restaurant[restaurant_slug] = []
            deals_by_restaurant[restaurant_slug].append(deal)
    
    # Update district deal counts
    for restaurant_slug, deals in deals_by_restaurant.items():
        if restaurant_slug in restaurant_lookup:
            district = restaurant_lookup[restaurant_slug]['district']
            neighborhood = restaurant_lookup[restaurant_slug]['neighborhood']
            deal_count = len(deals)
            
            districts[district]['deals_count'] += deal_count
            districts[district]['neighborhoods'][neighborhood]['deals_count'] += deal_count
    
    # Create dashboard data structure
    dashboard_data = {
        'generated_at': datetime.now().isoformat(),
        'title': 'Downtown Denver Happy Hour Discovery',
        'description': 'Comprehensive happy hour guide for downtown Denver core + adjacent districts',
        'coverage': {
            'districts': len(districts),
            'total_restaurants': len(downtown_data['restaurants']),
            'restaurants_with_deals': len(deals_by_restaurant),
            'total_deals': sum(len(deals) for deals in deals_by_restaurant.values())
        },
        'geographic_scope': [
            'Central District (LoDo, Capitol Hill, CBD, Union Station)',
            'Northwest Denver (Highland, Berkeley, Sunnyside)', 
            'North Denver (RiNo, Five Points, Curtis Park)'
        ],
        'districts': districts,
        'restaurants': {},
        'deals_by_restaurant': deals_by_restaurant
    }
    
    # Add enriched restaurant data
    for slug, restaurant in downtown_data['restaurants'].items():
        enhanced_restaurant = restaurant.copy()
        
        # Add deal information
        restaurant_deals = deals_by_restaurant.get(slug, [])
        enhanced_restaurant['happy_hour'] = {
            'status': 'active' if restaurant_deals else 'unknown',
            'deals_count': len(restaurant_deals),
            'current_deals': restaurant_deals[:3],  # Preview of deals
            'last_updated': datetime.now().isoformat()
        }
        
        # Add district/neighborhood context
        enhanced_restaurant['geographic_context'] = {
            'district': restaurant.get('district'),
            'neighborhood': restaurant.get('neighborhood'),
            'walkable_from_lodo': True,  # All selected districts are walkable
            'transit_accessible': True   # All have light rail or bus access
        }
        
        dashboard_data['restaurants'][slug] = enhanced_restaurant
    
    # Generate statistics
    print(f"📊 Dashboard Statistics:")
    print(f"   • Districts: {dashboard_data['coverage']['districts']}")
    print(f"   • Total restaurants: {dashboard_data['coverage']['total_restaurants']}")
    print(f"   • Restaurants with deals: {dashboard_data['coverage']['restaurants_with_deals']}")
    print(f"   • Total deals: {dashboard_data['coverage']['total_deals']}")
    print(f"   • Coverage rate: {dashboard_data['coverage']['restaurants_with_deals']/dashboard_data['coverage']['total_restaurants']*100:.1f}%")
    
    print(f"\n🏙️ District Breakdown:")
    for district_name, district_data in districts.items():
        print(f"   • {district_name}: {district_data['restaurant_count']} restaurants, {district_data['deals_count']} deals")
        for neighborhood, neighborhood_data in district_data['neighborhoods'].items():
            restaurant_count = len(neighborhood_data['restaurants'])
            deals_count = neighborhood_data['deals_count']
            if restaurant_count > 0:
                print(f"     - {neighborhood}: {restaurant_count} restaurants, {deals_count} deals")
    
    # Save dashboard data
    output_file = 'data/cache/downtown_dashboard.json'
    with open(output_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2, default=str)
    
    print(f"\n💾 Dashboard saved: {output_file}")
    
    # Create HTML dashboard
    create_html_dashboard(dashboard_data)
    
    return dashboard_data


def create_html_dashboard(dashboard_data: Dict[str, Any]):
    """Create HTML dashboard for expanded downtown coverage"""
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{dashboard_data['title']}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <style>
        :root {{
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --background-color: #0f172a;
            --card-background-color: #1e293b;
            --card-border-color: #334155;
            --color: #f1f5f9;
            --muted-color: #94a3b8;
        }}
        
        body {{
            background-color: var(--background-color);
            color: var(--color);
        }}
        
        .district-card {{
            background: var(--card-background-color);
            border: 1px solid var(--card-border-color);
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
        }}
        
        .restaurant-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }}
        
        .restaurant-card {{
            background: #334155;
            border-radius: 6px;
            padding: 1rem;
            border-left: 4px solid var(--primary);
        }}
        
        .status-active {{ color: #10b981; }}
        .status-unknown {{ color: #f59e0b; }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }}
        
        .stat-card {{
            text-align: center;
            background: var(--card-background-color);
            padding: 1rem;
            border-radius: 6px;
        }}
        
        .stat-number {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary);
        }}
    </style>
</head>
<body>
    <main class="container">
        <header style="text-align: center; margin: 2rem 0;">
            <h1>🍻 {dashboard_data['title']}</h1>
            <p>{dashboard_data['description']}</p>
            <small>Generated {dashboard_data['generated_at'][:10]}</small>
        </header>
        
        <section class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{dashboard_data['coverage']['districts']}</div>
                <div>Districts</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{dashboard_data['coverage']['total_restaurants']}</div>
                <div>Restaurants</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{dashboard_data['coverage']['restaurants_with_deals']}</div>
                <div>With Deals</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{dashboard_data['coverage']['total_deals']}</div>
                <div>Total Deals</div>
            </div>
        </section>
        
        <section>
            <h2>🏙️ Geographic Coverage</h2>
            <ul>'''
    
    for scope in dashboard_data['geographic_scope']:
        html_content += f'<li>{scope}</li>'
    
    html_content += '</ul></section>'
    
    # Add district sections
    for district_name, district_data in dashboard_data['districts'].items():
        html_content += f'''
        <section class="district-card">
            <h2>📍 {district_name}</h2>
            <p><strong>{district_data['restaurant_count']}</strong> restaurants • <strong>{district_data['deals_count']}</strong> deals</p>
            
            <div class="restaurant-grid">'''
        
        # Add restaurants by neighborhood
        for neighborhood, neighborhood_data in district_data['neighborhoods'].items():
            if neighborhood_data['restaurants']:
                for restaurant in neighborhood_data['restaurants']:
                    slug = restaurant['slug']
                    deals = dashboard_data['deals_by_restaurant'].get(slug, [])
                    status = 'active' if deals else 'unknown'
                    status_text = f"{len(deals)} deals" if deals else 'No deals found'
                    
                    html_content += f'''
                    <div class="restaurant-card">
                        <h4>{restaurant['name']}</h4>
                        <p><strong>{neighborhood}</strong> • {restaurant.get('cuisine', 'Restaurant')}</p>
                        <p class="status-{status}">📊 {status_text}</p>
                        <small>{restaurant.get('address', {}).get('formatted_address', '') if restaurant.get('address') else 'Address unavailable'}</small>
                    </div>'''
        
        html_content += '</div></section>'
    
    html_content += '''
        <footer style="text-align: center; margin: 3rem 0; color: var(--muted-color);">
            <p>🤖 Generated with <a href="https://claude.ai/code">Claude Code</a></p>
            <p>Data sourced from restaurant websites via respectful web scraping</p>
        </footer>
    </main>
</body>
</html>'''
    
    # Save HTML dashboard
    html_output = 'docs/downtown_dashboard.html'
    Path('docs').mkdir(exist_ok=True)
    
    with open(html_output, 'w') as f:
        f.write(html_content)
    
    print(f"🌐 HTML dashboard saved: {html_output}")
    print(f"   View at: file://{Path(html_output).absolute()}")


if __name__ == '__main__':
    create_expanded_dashboard()