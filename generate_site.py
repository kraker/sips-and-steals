#!/usr/bin/env python3
"""
Enhanced site generator using enhanced scraping data
Generates static site with live scraped data integration
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from urllib.parse import quote

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data_manager import DataManager


def main():
    """Generate the complete multi-page restaurant site with enhanced data"""
    
    # Use DataManager to get enhanced data
    dm = DataManager()
    enhanced_data = dm.export_for_website()
    
    print("🏗️  Generating Enhanced Sips and Steals website...")
    print(f"📊 Processing {enhanced_data['metadata']['total_restaurants']} restaurants")
    print(f"📈 {enhanced_data['metadata']['scraping_stats']['restaurants_with_live_deals']} have live deal data")
    
    # Setup Jinja2 environment with enhanced filters
    env = Environment(
        loader=FileSystemLoader('templates'),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # Add custom filters
    env.filters['slugify'] = slugify
    env.filters['dateformat'] = format_date
    env.filters['urlencode'] = quote
    env.filters['deal_confidence'] = deal_confidence_icon
    env.filters['time_since'] = time_since_update
    env.filters['time_ago'] = time_since_update  # Alias for consistency
    env.filters['format_days'] = format_day_range
    
    # Create output directories
    docs_dir = Path('docs')
    restaurants_dir = docs_dir / 'restaurants'
    docs_dir.mkdir(exist_ok=True)
    restaurants_dir.mkdir(exist_ok=True)
    
    # Generate index page with enhanced features
    generate_enhanced_index_page(env, enhanced_data, docs_dir)
    
    # Generate individual restaurant pages with live data
    generate_enhanced_restaurant_pages(env, enhanced_data, restaurants_dir, dm)
    
    # Generate additional pages
    generate_stats_page(env, enhanced_data, docs_dir)
    
    print(f"✅ Enhanced site generated successfully!")
    print(f"📁 Output: {docs_dir}")
    print(f"🏠 Index: {docs_dir}/index.html")
    print(f"📊 Stats: {docs_dir}/stats.html")
    print(f"📄 Restaurant pages: {len([r for area in enhanced_data['areas'].values() for r in area.values()])} pages")


def generate_enhanced_index_page(env, data, output_dir):
    """Generate the main index page with enhanced features"""
    template = env.get_template('index.html')
    
    # Extract unique neighborhoods and cuisines for filters
    neighborhoods = set()
    cuisines = set()
    
    for area_restaurants in data['areas'].values():
        for restaurant in area_restaurants.values():
            if restaurant.get('sub_location'):
                neighborhoods.add(restaurant['sub_location'])
            if restaurant.get('cuisine'):
                cuisines.add(restaurant['cuisine'])
    
    # Sort alphabetically
    neighborhoods = sorted(list(neighborhoods))
    cuisines = sorted(list(cuisines))
    
    # Add data freshness indicators
    fresh_data_count = 0
    total_with_live_data = 0
    
    for area_restaurants in data['areas'].values():
        for restaurant in area_restaurants.values():
            if restaurant.get('live_data_available'):
                total_with_live_data += 1
                if restaurant.get('last_updated'):
                    try:
                        updated = datetime.fromisoformat(restaurant['last_updated'])
                        if (datetime.now() - updated).days < 2:
                            fresh_data_count += 1
                    except:
                        pass
    
    html = template.render(
        metadata=data['metadata'],
        areas=data['areas'],
        neighborhoods=neighborhoods,
        cuisines=cuisines,
        data_freshness={
            'total_with_live_data': total_with_live_data,
            'fresh_data_count': fresh_data_count,
            'live_data_percentage': round(total_with_live_data / data['metadata']['total_restaurants'] * 100, 1) if data['metadata']['total_restaurants'] > 0 else 0
        }
    )
    
    output_file = output_dir / 'index.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"📄 Generated enhanced index page: {output_file}")


def generate_enhanced_restaurant_pages(env, data, output_dir, dm):
    """Generate individual restaurant profile pages with live data"""
    template = env.get_template('restaurant.html')
    
    total_restaurants = 0
    restaurants_with_live_data = 0
    
    for area_name, restaurants in data['areas'].items():
        for slug, restaurant_data in restaurants.items():
            # Get enhanced restaurant object for live deals
            restaurant_obj = dm.get_restaurant(slug)
            
            # Enhance restaurant data with live deals if available
            enhanced_restaurant_data = restaurant_data.copy()
            enhanced_restaurant_data['area'] = area_name
            
            if restaurant_obj:
                current_deals = restaurant_obj.get_current_deals()
                enhanced_restaurant_data['live_deals'] = [
                    {
                        'title': deal.title,
                        'description': deal.description,
                        'deal_type': deal.deal_type.value,
                        'days_of_week': [day.value for day in deal.days_of_week],
                        'start_time': deal.start_time,
                        'end_time': deal.end_time,
                        'price': deal.price,
                        'is_all_day': deal.is_all_day,
                        'confidence_score': deal.confidence_score,
                        'scraped_at': deal.scraped_at.isoformat(),
                        'source_url': deal.source_url
                    }
                    for deal in current_deals
                ]
                
                enhanced_restaurant_data['scraping_info'] = {
                    'last_scraped': restaurant_obj.scraping_config.last_scraped.isoformat() if restaurant_obj.scraping_config.last_scraped else None,
                    'last_success': restaurant_obj.scraping_config.last_success.isoformat() if restaurant_obj.scraping_config.last_success else None,
                    'consecutive_failures': restaurant_obj.scraping_config.consecutive_failures,
                    'enabled': restaurant_obj.scraping_config.enabled
                }
                
                if current_deals:
                    restaurants_with_live_data += 1
            else:
                enhanced_restaurant_data['live_deals'] = []
                enhanced_restaurant_data['scraping_info'] = None
            
            html = template.render(
                restaurant=enhanced_restaurant_data,
                metadata=data['metadata']
            )
            
            output_file = output_dir / f"{slug}.html"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            total_restaurants += 1
    
    print(f"📄 Generated {total_restaurants} enhanced restaurant pages")
    print(f"📈 {restaurants_with_live_data} pages include live deal data")


def generate_stats_page(env, data, output_dir):
    """Generate a statistics page showing system health"""
    template_content = """
{% extends "base.html" %}

{% block title %}System Statistics - Sips and Steals{% endblock %}

{% block content %}
    <div class="container">
        <h1>📊 System Statistics</h1>
        
        <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
            
            <div class="stat-card" style="background: var(--pico-card-background-color); padding: 1rem; border-radius: var(--pico-border-radius); border: 1px solid var(--pico-muted-border-color);">
                <h3>🏪 Restaurant Coverage</h3>
                <p><strong>{{ metadata.total_restaurants }}</strong> restaurants tracked</p>
                <p><strong>{{ metadata.scraping_stats.restaurants_with_websites }}</strong> with websites</p>
                <p><strong>{{ metadata.scraping_stats.restaurants_with_live_deals }}</strong> with live data</p>
                <p><strong>{{ metadata.scraping_stats.coverage_percentage }}%</strong> live data coverage</p>
            </div>
            
            <div class="stat-card" style="background: var(--pico-card-background-color); padding: 1rem; border-radius: var(--pico-border-radius); border: 1px solid var(--pico-muted-border-color);">
                <h3>🎯 Data Quality</h3>
                <p><strong>{{ metadata.scraping_stats.scraping_success_rate }}%</strong> success rate</p>
                <p><strong>{{ metadata.scraping_stats.restaurants_with_fresh_deals }}</strong> with fresh data (&lt;48h)</p>
                <p><strong>{{ districts|length }}</strong> districts covered</p>
                <p><strong>{{ neighborhoods_count }}</strong> neighborhoods</p>
            </div>
            
            <div class="stat-card" style="background: var(--pico-card-background-color); padding: 1rem; border-radius: var(--pico-border-radius); border: 1px solid var(--pico-muted-border-color);">
                <h3>📅 Last Updated</h3>
                <p>{{ metadata.updated_at | dateformat }}</p>
                <p><small>Data source: {{ metadata.source }}</small></p>
                <p><small>Target user: {{ metadata.target_user }}</small></p>
            </div>
            
        </div>
        
        <h2>🏢 Districts Overview</h2>
        <div class="districts-overview">
            {% for district, neighborhoods in metadata.districts_with_neighborhoods.items() %}
            <div class="district-card" style="margin-bottom: 1rem; padding: 1rem; background: var(--pico-code-background-color); border-radius: var(--pico-border-radius);">
                <h3>{{ district }}</h3>
                <p><strong>{{ area_restaurant_counts[district] or 0 }}</strong> restaurants in <strong>{{ neighborhoods|length }}</strong> neighborhoods</p>
                {% if neighborhoods %}
                <p><small>Neighborhoods: {{ neighborhoods|join(', ') }}</small></p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        
        <div style="margin-top: 2rem; padding: 1rem; background: var(--pico-code-background-color); border-radius: var(--pico-border-radius);">
            <h3>🔧 System Information</h3>
            <p>Enhanced scraping system with intelligent data collection, quality validation, and automatic retry logic.</p>
            <p>Data freshness varies by restaurant - most active locations are updated daily.</p>
        </div>
        
        <div style="margin-top: 1rem; text-align: center;">
            <a href="index.html" role="button">← Back to Restaurant List</a>
        </div>
    </div>
{% endblock %}
"""
    
    # Create template from string
    template = env.from_string(template_content)
    
    # Calculate area restaurant counts
    area_restaurant_counts = {}
    for area_name, restaurants in data['areas'].items():
        area_restaurant_counts[area_name] = len(restaurants)
    
    # Count total neighborhoods
    total_neighborhoods = sum(len(neighborhoods) for neighborhoods in data['metadata']['districts_with_neighborhoods'].values())
    
    html = template.render(
        metadata=data['metadata'],
        districts=data['metadata']['districts'],
        area_restaurant_counts=area_restaurant_counts,
        neighborhoods_count=total_neighborhoods
    )
    
    output_file = output_dir / 'stats.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"📊 Generated statistics page: {output_file}")


def slugify(text):
    """Convert text to URL-friendly slug"""
    if not text:
        return ""
    
    slug = str(text).lower()
    # Replace spaces and special chars with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


def format_date(date_string):
    """Format ISO date string for display"""
    try:
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return dt.strftime('%B %d, %Y at %I:%M %p')
    except:
        return date_string


def deal_confidence_icon(confidence_score):
    """Return icon based on deal confidence score"""
    if confidence_score >= 0.8:
        return "🟢"  # High confidence
    elif confidence_score >= 0.5:
        return "🟡"  # Medium confidence
    else:
        return "🔴"  # Low confidence


def time_since_update(date_string):
    """Return human-readable time since update"""
    if not date_string:
        return "Never"
    
    try:
        updated = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        delta = datetime.now() - updated
        
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    except:
        return "Unknown"


def format_day_range(days):
    """Format a list of days into compact ranges like 'Mon - Sun' or 'Mon, Wed, Fri'"""
    if not days:
        return ""
    
    # Define day order for sorting and range detection
    day_order = {
        'monday': 1, 'tuesday': 2, 'wednesday': 3, 'thursday': 4,
        'friday': 5, 'saturday': 6, 'sunday': 7
    }
    
    day_abbrev = {
        'monday': 'Mon', 'tuesday': 'Tue', 'wednesday': 'Wed', 'thursday': 'Thu',
        'friday': 'Fri', 'saturday': 'Sat', 'sunday': 'Sun'
    }
    
    # Normalize to lowercase and sort by day order
    normalized_days = [day.lower().strip() for day in days if day.lower().strip() in day_order]
    sorted_days = sorted(normalized_days, key=lambda x: day_order[x])
    
    if not sorted_days:
        return ", ".join(days)  # Fallback to original if we can't parse
    
    # Special case: all 7 days
    if len(sorted_days) == 7:
        return "Daily"
    
    # Special case: Monday through Friday
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    if sorted_days == weekdays:
        return "Mon - Fri"
    
    # Special case: Saturday and Sunday
    weekend = ['saturday', 'sunday']
    if sorted_days == weekend:
        return "Sat - Sun"
    
    # Look for consecutive ranges
    ranges = []
    start = 0
    
    while start < len(sorted_days):
        end = start
        
        # Find the end of consecutive days
        while (end + 1 < len(sorted_days) and 
               day_order[sorted_days[end + 1]] == day_order[sorted_days[end]] + 1):
            end += 1
        
        # If we have a range of 3 or more consecutive days, format as range
        if end - start >= 2:
            ranges.append(f"{day_abbrev[sorted_days[start]]} - {day_abbrev[sorted_days[end]]}")
        elif end - start == 1:
            # Two consecutive days, still show as range for brevity
            ranges.append(f"{day_abbrev[sorted_days[start]]} - {day_abbrev[sorted_days[end]]}")
        else:
            # Single day
            ranges.append(day_abbrev[sorted_days[start]])
        
        start = end + 1
    
    return ", ".join(ranges)


if __name__ == "__main__":
    main()