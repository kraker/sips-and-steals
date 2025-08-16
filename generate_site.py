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
from urllib.parse import quote, urlparse

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data_manager import DataManager


def group_deals_by_schedule(deals):
    """Group deals by their schedule (day + time combination) for better display"""
    if not deals:
        return []
    
    # Create a consolidated schedule and separate specific offerings
    schedule_entries = []
    all_offerings = []
    schedule_confidence = 0.0
    schedule_sources = set()
    
    for deal in deals:
        title = deal.get('title', '').lower()
        description = deal.get('description', '').lower()
        cleaned_description = clean_description(description).lower()
        
        # Check if this deal has specific offerings (discounts, prices, etc.)
        has_specific_offerings = any(offer in (title + ' ' + cleaned_description) for offer in [
            '$', '%', 'off', 'price', 'maki', 'sake', 'drink', 'food', 'appetizer', 'cocktail', 'beer', 'wine'
        ])
        
        # Every deal with days/times contributes to the schedule
        if deal.get('days_of_week') or deal.get('start_time') or deal.get('is_all_day'):
            days = deal.get('days_of_week', [])
            start_time = deal.get('start_time')
            end_time = deal.get('end_time')
            is_all_day = deal.get('is_all_day', False)
            
            # Format schedule entry
            if days:
                if len(days) == 1:
                    day_str = days[0].title()
                elif len(days) == 7:
                    day_str = "Daily"
                elif set(days) == {'monday', 'tuesday', 'wednesday', 'thursday', 'friday'}:
                    day_str = "Weekdays"
                elif set(days) == {'saturday', 'sunday'}:
                    day_str = "Weekends"
                else:
                    day_str = ", ".join([day.title() for day in days])
                
                if is_all_day:
                    time_str = "All Day"
                elif start_time and end_time:
                    time_str = f"{start_time} - {end_time}"
                else:
                    time_str = "Happy Hour"
                
                schedule_entry = f"{day_str}: {time_str}"
                if schedule_entry not in schedule_entries:
                    schedule_entries.append(schedule_entry)
            
            # Track highest confidence and sources for schedule
            confidence = deal.get('confidence_score', 0.0)
            if confidence > schedule_confidence:
                schedule_confidence = confidence
            if deal.get('source_url'):
                schedule_sources.add(deal.get('source_url'))
        
        # If this deal has specific offerings, keep it for the offerings section
        if has_specific_offerings:
            all_offerings.append(deal)
    
    # Create the grouped deals list
    grouped_deals = []
    
    # Always create a Happy Hours schedule if we have any schedule entries
    if schedule_entries:
        # Sort schedule entries by day order
        day_order_map = {
            'monday': 1, 'tuesday': 2, 'wednesday': 3, 'thursday': 4,
            'friday': 5, 'saturday': 6, 'sunday': 7, 'daily': 0, 'weekdays': 0, 'weekends': 8
        }
        
        schedule_entries.sort(key=lambda entry: day_order_map.get(entry.split(':')[0].lower(), 9))
        
        grouped_deals.append({
            'title': 'Happy Hours',
            'days_of_week': [],
            'start_time': None,
            'end_time': None,
            'is_all_day': False,
            'deals': [{'description': entry, 'title': '', 'price': None, 'confidence_score': schedule_confidence} for entry in schedule_entries],
            'confidence_score': schedule_confidence,
            'source_urls': list(schedule_sources),
            'deal_count': len(schedule_entries),
            'is_schedule_group': True
        })
    
    # Group offering deals by schedule key  
    if all_offerings:
        schedule_groups = {}
        
        for deal in all_offerings:
            # Create schedule key based on days and time
            days_key = tuple(sorted(deal.get('days_of_week', [])))
            time_key = (
                deal.get('start_time'),
                deal.get('end_time'), 
                deal.get('is_all_day', False)
            )
            schedule_key = (days_key, time_key)
            
            if schedule_key not in schedule_groups:
                schedule_groups[schedule_key] = {
                    'deals': [],
                    'days_of_week': deal.get('days_of_week', []),
                    'start_time': deal.get('start_time'),
                    'end_time': deal.get('end_time'),
                    'is_all_day': deal.get('is_all_day', False),
                    'highest_confidence': 0.0,
                    'source_urls': set()
                }
            
            # Add deal to group
            schedule_groups[schedule_key]['deals'].append(deal)
            
            # Track highest confidence score for the group
            confidence = deal.get('confidence_score', 0.0)
            if confidence > schedule_groups[schedule_key]['highest_confidence']:
                schedule_groups[schedule_key]['highest_confidence'] = confidence
            
            # Collect unique source URLs
            if deal.get('source_url'):
                schedule_groups[schedule_key]['source_urls'].add(deal.get('source_url'))
        
        # Convert offering groups to list
        for (days_key, time_key), group_data in schedule_groups.items():
            # Generate descriptive group title for offerings (not just schedule)
            if group_data['days_of_week']:
                if len(group_data['days_of_week']) == 1:
                    day_name = group_data['days_of_week'][0].title()
                    group_title = f"{day_name} Specials"
                else:
                    group_title = "Special Offers"
            else:
                group_title = "Special Offers"
            
            # Consolidate deal descriptions
            consolidated_deals = consolidate_deal_descriptions(group_data['deals'])
            
            if consolidated_deals:  # Only add if there are meaningful offerings
                grouped_deals.append({
                    'title': group_title,
                    'days_of_week': group_data['days_of_week'],
                    'start_time': group_data['start_time'],
                    'end_time': group_data['end_time'],
                    'is_all_day': group_data['is_all_day'],
                    'deals': consolidated_deals,
                    'confidence_score': group_data['highest_confidence'],
                    'source_urls': list(group_data['source_urls']),
                    'deal_count': len(group_data['deals']),
                    'is_schedule_group': False
                })
    
    return grouped_deals


def generate_group_title(days, start_time, end_time, is_all_day):
    """Generate descriptive title for a deal group"""
    if not days:
        if is_all_day:
            return "All Day Special"
        elif start_time and end_time:
            return f"{start_time} - {end_time}"
        else:
            return "Special Offer"
    
    # Format days
    if len(days) == 7:
        day_str = "Daily"
    elif len(days) == 1:
        day_str = days[0].title()
    elif set(days) == {'monday', 'tuesday', 'wednesday', 'thursday', 'friday'}:
        day_str = "Weekday"
    elif set(days) == {'saturday', 'sunday'}:
        day_str = "Weekend"
    else:
        # Multiple specific days
        day_str = ", ".join([day.title() for day in days[:3]])
        if len(days) > 3:
            day_str += f" + {len(days) - 3} more"
    
    # Format time
    if is_all_day:
        time_str = "All Day"
    elif start_time and end_time:
        time_str = f"{start_time} - {end_time}"
    else:
        time_str = ""
    
    # Combine
    if time_str:
        return f"{day_str} {time_str}"
    else:
        return f"{day_str} Special"


def consolidate_deal_descriptions(deals):
    """Consolidate and clean up deal descriptions to avoid redundancy"""
    consolidated = []
    
    for deal in deals:
        description = deal.get('description', '').strip()
        title = deal.get('title', '').strip()
        
        # Skip generic titles that don't add information
        if title.lower() in ['happy hour', 'tuesday special', 'daily special', 'time-based special', 'multi-day happy hour']:
            title = ""
        
        # Clean up description
        if description:
            # Remove redundant day/time info that's already in the group header
            description = clean_description(description)
        
        # For deals with only schedule info and no actual offer details, skip them
        # since the schedule is already shown in the group header
        if not description or description.lower() in ['happy hour', 'special']:
            continue
        
        # Use title if description is empty or not useful
        if not description and title:
            description = title
        elif title and title.lower() not in description.lower() and title:
            # Combine title and description if both are useful
            if description:
                description = f"{title}: {description}"
            else:
                description = title
        
        # Only add if we have meaningful content and it's not a duplicate
        if description and description not in [c.get('description', '') for c in consolidated]:
            consolidated.append({
                'title': title,
                'description': description,
                'price': deal.get('price'),
                'confidence_score': deal.get('confidence_score', 0.0)
            })
    
    # If no meaningful descriptions found, add a generic one
    if not consolidated and deals:
        consolidated.append({
            'title': '',
            'description': 'Happy hour specials available',
            'price': None,
            'confidence_score': max([deal.get('confidence_score', 0.0) for deal in deals])
        })
    
    return consolidated


def clean_description(description):
    """Clean up description by removing redundant schedule information"""
    import re
    
    # Remove patterns like "every tuesday, all day"
    description = re.sub(r'every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday),?\s*all\s+day', '', description, flags=re.IGNORECASE)
    
    # Remove standalone day names at end of description
    description = re.sub(r'\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$', '', description, flags=re.IGNORECASE)
    
    # Remove time patterns that are redundant (like "11am-10pm‍friday")
    description = re.sub(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)[\s\u200d]*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', '', description, flags=re.IGNORECASE)
    
    # Remove standalone time ranges without context
    description = re.sub(r'^\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*$', '', description, flags=re.IGNORECASE)
    
    # Remove any remaining invisible characters or weird spacing
    description = re.sub(r'[\u200d\u200c\u00a0]+', ' ', description)  # Remove zero-width joiners and non-breaking spaces
    description = re.sub(r'\s+', ' ', description)  # Normalize whitespace
    
    return description.strip()


def day_order(day_name):
    """Return numeric order for day of week (Monday = 0)"""
    day_mapping = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    return day_mapping.get(day_name.lower(), 7)


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
    env.filters['domain_name'] = extract_domain_name
    env.filters['cuisine_emoji'] = cuisine_with_emoji
    env.filters['group_deals'] = group_deals_by_schedule
    
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


def extract_domain_name(url):
    """Extract domain name from URL for display"""
    if not url:
        return ""
    
    try:
        # Parse the URL
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    except:
        return url  # Fallback to original if parsing fails


def cuisine_with_emoji(cuisine):
    """Add appropriate emoji to cuisine type"""
    if not cuisine:
        return ""
    
    # Mapping of cuisine types to emojis
    cuisine_emojis = {
        'american': '🇺🇸',
        'asian': '🥢',
        'italian': '🍝',
        'mexican': '🌮',
        'indian': '🍛',
        'chinese': '🥡',
        'japanese': '🍣',
        'thai': '🌶️',
        'mediterranean': '🫒',
        'french': '🥖',
        'seafood': '🦞',
        'steakhouse': '🥩',
        'bbq': '🍖',
        'barbecue': '🍖',
        'pizza': '🍕',
        'sushi': '🍣',
        'burgers': '🍔',
        'sandwich': '🥪',
        'cafe': '☕',
        'bar': '🍸',
        'pub': '🍺',
        'wine': '🍷',
        'cocktails': '🍹',
        'breakfast': '🥞',
        'brunch': '🥐',
        'bakery': '🧁',
        'dessert': '🍰',
        'ice cream': '🍦',
        'vegetarian': '🥗',
        'vegan': '🌱'
    }
    
    # Normalize cuisine name for lookup
    cuisine_lower = cuisine.lower().strip()
    
    # Find matching emoji
    emoji = cuisine_emojis.get(cuisine_lower, '🍽️')  # Default to plate emoji
    
    return f"{emoji} {cuisine}"


if __name__ == "__main__":
    main()