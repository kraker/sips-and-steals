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


def get_current_relevant_deals(deals, current_time=None):
    """Get the most relevant deals happening right now"""
    if not deals:
        return []
    
    if current_time is None:
        current_time = datetime.now()
    
    current_day = current_time.strftime('%A').lower()  # monday, tuesday, etc.
    current_hour = current_time.hour
    current_minute = current_time.minute
    current_time_minutes = current_hour * 60 + current_minute
    
    relevant_deals = []
    
    for deal in deals:
        deal_score = 0
        relevance_reasons = []
        
        # Skip very low confidence deals for main page display, but allow static deals (0.3) as fallback
        if deal.get('confidence_score', 0) < 0.25:
            continue
            
        days_of_week = deal.get('days_of_week', [])
        start_time = deal.get('start_time')
        end_time = deal.get('end_time')
        is_all_day = deal.get('is_all_day', False)
        
        # Check if deal is active today
        is_today = current_day in [day.lower() for day in days_of_week] if days_of_week else True
        
        # For static deals (low confidence), show them even when not active today as fallback content
        if not is_today and deal.get('confidence_score', 0) >= 0.5:
            continue  # Skip high-confidence deals that aren't active today, but keep static deals
        
        # Deal is active today, start scoring
        deal_score += 100
        relevance_reasons.append('active_today')
        
        # Check time relevance
        if is_all_day:
            deal_score += 50
            relevance_reasons.append('all_day')
        elif start_time and end_time:
            # Parse time strings (e.g., "3:00 PM" -> 15:00)
            try:
                start_minutes = parse_time_to_minutes(start_time)
                end_minutes = parse_time_to_minutes(end_time)
                
                # Handle overnight deals (end time < start time)
                if end_minutes < start_minutes:
                    end_minutes += 24 * 60  # Add 24 hours
                
                # Check if current time is within deal hours
                if start_minutes <= current_time_minutes <= end_minutes:
                    deal_score += 150
                    relevance_reasons.append('happening_now')
                elif current_time_minutes < start_minutes:
                    # Deal starts later today
                    time_until_start = start_minutes - current_time_minutes
                    if time_until_start <= 120:  # Within 2 hours
                        deal_score += 75
                        relevance_reasons.append('starting_soon')
                    elif time_until_start <= 360:  # Within 6 hours
                        deal_score += 25
                        relevance_reasons.append('later_today')
                        
            except (ValueError, AttributeError):
                # If we can't parse time, give moderate score
                deal_score += 30
                relevance_reasons.append('unknown_time')
        
        # Boost score for deals with specific offerings (prices, discounts)
        title = deal.get('title', '').lower()
        description = deal.get('description', '').lower()
        if any(keyword in (title + ' ' + description) for keyword in [
            '$', '%', 'off', 'price', 'special', 'discount', 'maki', 'sake', 'cocktail', 'beer', 'wine'
        ]):
            deal_score += 25
            relevance_reasons.append('specific_offer')
        
        # Boost score based on confidence
        confidence_score = deal.get('confidence_score', 0)
        deal_score += confidence_score * 20
        
        if deal_score > 0:
            deal_copy = deal.copy()
            deal_copy['relevance_score'] = deal_score
            deal_copy['relevance_reasons'] = relevance_reasons
            relevant_deals.append(deal_copy)
    
    # Sort by relevance score (highest first) and return top deals
    relevant_deals.sort(key=lambda x: x['relevance_score'], reverse=True)
    return relevant_deals[:3]  # Return top 3 most relevant deals


def parse_time_to_minutes(time_str):
    """Convert time string like '3:00 PM' to minutes since midnight"""
    if not time_str:
        return 0
        
    # Handle various time formats
    time_str = time_str.strip().upper()
    
    # Remove common suffixes
    time_str = time_str.replace(' PM', 'PM').replace(' AM', 'AM')
    
    try:
        if 'PM' in time_str:
            time_part = time_str.replace('PM', '').strip()
            if ':' in time_part:
                hour, minute = map(int, time_part.split(':'))
            else:
                hour, minute = int(time_part), 0
            
            if hour != 12:
                hour += 12
            elif hour == 12:
                hour = 12  # 12 PM stays as 12
                
        elif 'AM' in time_str:
            time_part = time_str.replace('AM', '').strip()
            if ':' in time_part:
                hour, minute = map(int, time_part.split(':'))
            else:
                hour, minute = int(time_part), 0
                
            if hour == 12:
                hour = 0  # 12 AM becomes 0 (midnight)
        else:
            # 24-hour format or just hour
            if ':' in time_str:
                hour, minute = map(int, time_str.split(':'))
            else:
                hour, minute = int(time_str), 0
                
        return hour * 60 + minute
        
    except (ValueError, IndexError):
        return 0


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
        # But treat pricing in the 'prices' field differently - if it's the main deal with schedule, don't separate it
        has_price_field = bool(deal.get('prices'))
        has_schedule = bool(deal.get('days_of_week') or deal.get('start_time') or deal.get('is_all_day'))
        
        # If it's the main deal with both schedule and pricing, don't separate into offerings
        if has_price_field and has_schedule and len(deals) == 1:
            has_specific_offerings = False
        else:
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
                day_str = format_day_range(days)
                
                if is_all_day:
                    time_str = "All Day"
                elif start_time and end_time:
                    time_str = f"{start_time} - {end_time}"
                else:
                    time_str = "Happy Hour"
                
                # Include location context from deal title if meaningful
                deal_title = deal.get('title', '')
                location_context = ''
                if 'at the bar' in deal_title.lower():
                    location_context = ' (Bar)'
                elif 'at tables' in deal_title.lower():
                    location_context = ' (Tables)'
                elif 'at bar' in deal_title.lower():
                    location_context = ' (Bar)'
                elif 'bar' in deal_title.lower() and 'happy hour' in deal_title.lower() and len(deals) > 1:
                    location_context = ' (Bar)'
                elif 'table' in deal_title.lower() and 'happy hour' in deal_title.lower() and len(deals) > 1:
                    location_context = ' (Tables)'
                
                # Include pricing information in schedule if available
                price_info = format_deal_prices(deal)
                if price_info:
                    schedule_entry = f"{day_str}: {time_str}{location_context} - {price_info}"
                else:
                    schedule_entry = f"{day_str}: {time_str}{location_context}"
                    
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
                'price': format_deal_prices(deal),
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
    env.filters['deal_status_badge'] = deal_status_badge
    env.filters['format_deal_time'] = format_deal_time
    env.filters['group_by_district'] = group_restaurants_by_district
    env.filters['group_by_metro_area'] = group_restaurants_by_metro_area
    
    # Create output directories
    docs_dir = Path('docs')
    restaurants_dir = docs_dir / 'restaurants'
    docs_dir.mkdir(exist_ok=True)
    restaurants_dir.mkdir(exist_ok=True)
    
    # Generate index page with enhanced features and current deals
    generate_enhanced_index_page(env, enhanced_data, docs_dir, dm)
    
    # Generate individual restaurant pages with live data
    generate_enhanced_restaurant_pages(env, enhanced_data, restaurants_dir, dm)
    
    # Generate additional pages
    generate_stats_page(env, enhanced_data, docs_dir)
    
    print(f"✅ Enhanced site generated successfully!")
    print(f"📁 Output: {docs_dir}")
    print(f"🏠 Index: {docs_dir}/index.html")
    print(f"📊 Stats: {docs_dir}/stats.html")
    print(f"📄 Restaurant pages: {len(enhanced_data['restaurants'])} pages")


def generate_enhanced_index_page(env, data, output_dir, dm):
    """Generate the main index page with enhanced features and current deals"""
    template = env.get_template('index.html')
    
    # Extract unique neighborhoods and cuisines for filters
    neighborhoods = set()
    cuisines = set()
    
    # Enhance each restaurant with current relevant deals
    current_time = datetime.now()
    
    for slug, restaurant in data['restaurants'].items():
        if restaurant.get('neighborhood'):
            neighborhoods.add(restaurant['neighborhood'])
            if restaurant.get('cuisine'):
                cuisines.add(restaurant['cuisine'])
            
            # Get live deals for this restaurant and find most relevant ones
            restaurant_obj = dm.get_restaurant(slug)
            current_deals = []
            
            if restaurant_obj:
                current_deals_objects = restaurant_obj.get_current_deals()
                if current_deals_objects:
                    # Convert Deal objects to dicts for processing
                    deals_data = []
                    for deal in current_deals_objects:
                        deals_data.append({
                            'title': deal.title,
                            'description': deal.description,
                            'deal_type': deal.deal_type.value,
                            'days_of_week': [day.value for day in deal.days_of_week],
                            'start_time': deal.start_time,
                            'end_time': deal.end_time,
                            'price': format_deal_prices(deal),
                            'is_all_day': deal.is_all_day,
                            'confidence_score': deal.confidence_score,
                            'scraped_at': deal.scraped_at.isoformat(),
                            'source_url': deal.source_url
                        })
                    
                    # Get most relevant deals for right now
                    current_deals = get_current_relevant_deals(deals_data, current_time)
            
            # Add current deals to restaurant data
            restaurant['current_deals'] = current_deals
            restaurant['has_current_deals'] = len(current_deals) > 0
    
    # Sort alphabetically
    neighborhoods = sorted(list(neighborhoods))
    cuisines = sorted(list(cuisines))
    
    # Add data freshness indicators
    fresh_data_count = 0
    total_with_live_data = 0
    restaurants_with_current_deals = 0
    
    for restaurant in data['restaurants'].values():
        if restaurant.get('live_data_available'):
            total_with_live_data += 1
            if restaurant.get('last_updated'):
                try:
                    updated = datetime.fromisoformat(restaurant['last_updated'])
                    if (datetime.now() - updated).days < 2:
                        fresh_data_count += 1
                except:
                        pass
            
            if restaurant.get('has_current_deals'):
                restaurants_with_current_deals += 1
    
    # Convert structured addresses to strings for template compatibility
    restaurants_for_template = {}
    for slug, restaurant_data in data['restaurants'].items():
        restaurant_copy = restaurant_data.copy()
        
        # Convert structured address to string for template compatibility
        if restaurant_copy.get('address') and isinstance(restaurant_copy['address'], dict):
            # Extract formatted address or create from components
            formatted_address = restaurant_copy['address'].get('formatted_address')
            if not formatted_address:
                # Generate from components
                street_num = restaurant_copy['address'].get('street_number', '')
                street_name = restaurant_copy['address'].get('street_name', '')
                unit = restaurant_copy['address'].get('unit', '')
                city = restaurant_copy['address'].get('city', 'Denver')
                state = restaurant_copy['address'].get('state', 'CO')
                zip_code = restaurant_copy['address'].get('zip_code', '')
                
                parts = []
                if street_num and street_name:
                    street_addr = f"{street_num} {street_name}"
                    if unit:
                        street_addr += f" {unit}"
                    parts.append(street_addr)
                
                if city and state:
                    location = f"{city}, {state}"
                    if zip_code:
                        location += f" {zip_code}"
                    parts.append(location)
                
                formatted_address = ', '.join(parts) if parts else None
            
            restaurant_copy['address'] = str(formatted_address or '')
        elif restaurant_copy.get('address') is None:
            restaurant_copy['address'] = ''
        else:
            # Ensure any remaining addresses are strings
            restaurant_copy['address'] = str(restaurant_copy.get('address', ''))
        
        restaurants_for_template[slug] = restaurant_copy
    
    html = template.render(
        metadata=data['metadata'],
        restaurants=restaurants_for_template,
        neighborhoods=neighborhoods,
        cuisines=cuisines,
        current_time=current_time,
        data_freshness={
            'total_with_live_data': total_with_live_data,
            'fresh_data_count': fresh_data_count,
            'live_data_percentage': round(total_with_live_data / data['metadata']['total_restaurants'] * 100, 1) if data['metadata']['total_restaurants'] > 0 else 0,
            'restaurants_with_current_deals': restaurants_with_current_deals
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
    
    for slug, restaurant_data in data['restaurants'].items():
        # Get enhanced restaurant object for live deals
        restaurant_obj = dm.get_restaurant(slug)
        
        # Enhance restaurant data with live deals if available
        enhanced_restaurant_data = restaurant_data.copy()
        
        # Convert structured address to string for template compatibility
        if enhanced_restaurant_data.get('address') and isinstance(enhanced_restaurant_data['address'], dict):
            # Extract formatted address or create from components
            formatted_address = enhanced_restaurant_data['address'].get('formatted_address')
            if not formatted_address:
                # Generate from components
                street_num = enhanced_restaurant_data['address'].get('street_number', '')
                street_name = enhanced_restaurant_data['address'].get('street_name', '')
                unit = enhanced_restaurant_data['address'].get('unit', '')
                city = enhanced_restaurant_data['address'].get('city', 'Denver')
                state = enhanced_restaurant_data['address'].get('state', 'CO')
                zip_code = enhanced_restaurant_data['address'].get('zip_code', '')
                
                parts = []
                if street_num and street_name:
                    street_addr = f"{street_num} {street_name}"
                    if unit:
                        street_addr += f" {unit}"
                    parts.append(street_addr)
                
                if city and state:
                    location = f"{city}, {state}"
                    if zip_code:
                        location += f" {zip_code}"
                    parts.append(location)
                
                formatted_address = ', '.join(parts) if parts else None
            
            enhanced_restaurant_data['address'] = str(formatted_address or '')
            
            # Also store the structured address data for potential future use
            enhanced_restaurant_data['address_structured'] = restaurant_data['address']
        elif enhanced_restaurant_data.get('address') is None:
            enhanced_restaurant_data['address'] = ''
        else:
            # Ensure any remaining addresses are strings
            enhanced_restaurant_data['address'] = str(enhanced_restaurant_data.get('address', ''))
        
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
                    'prices': deal.prices if hasattr(deal, 'prices') else [],
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
    # Group restaurants by district for counting
    districts = {}
    for restaurant in data['restaurants'].values():
        district = restaurant['district']
        if district not in districts:
            districts[district] = []
        districts[district].append(restaurant)
    
    # Calculate district restaurant counts  
    area_restaurant_counts = {}
    for district_name, restaurants in districts.items():
        area_restaurant_counts[district_name] = len(restaurants)
    
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
    """Format a list of days into compact ranges using numeric day detection"""
    if not days:
        return ""
    
    # Define day mappings
    day_to_num = {
        'monday': 1, 'tuesday': 2, 'wednesday': 3, 'thursday': 4,
        'friday': 5, 'saturday': 6, 'sunday': 7
    }
    
    num_to_abbrev = {
        1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu',
        5: 'Fri', 6: 'Sat', 7: 'Sun'
    }
    
    # Convert days to numbers, normalize, and remove duplicates
    day_numbers = []
    for day in days:
        day_lower = day.lower().strip()
        if day_lower in day_to_num:
            day_numbers.append(day_to_num[day_lower])
    
    if not day_numbers:
        return ", ".join(days)  # Fallback if we can't parse
    
    # Remove duplicates and sort
    unique_numbers = sorted(set(day_numbers))
    
    # Special case: all 7 days
    if len(unique_numbers) == 7:
        return "Daily"
    
    # Handle week wraparound by checking for Sunday-Monday sequences
    # For cases like [1,2,3,7] (Mon,Tue,Wed,Sun) or [6,7,1,2] (Sat,Sun,Mon,Tue)
    ranges = []
    wraparound_handled = False
    if 7 in unique_numbers and 1 in unique_numbers:
        # Check if we have a sequence that wraps around (like Sun-Thu)
        # Find Sunday and see if it connects to a sequence starting with Monday
        sunday_idx = unique_numbers.index(7)
        monday_idx = unique_numbers.index(1)
        
        # If Sunday is at the end and Monday is at the beginning, and they're part of consecutive sequences
        if sunday_idx == len(unique_numbers) - 1 and monday_idx == 0:
            # Check if we have a sequence like [1,2,3,4,7] (Mon-Thu,Sun)
            # This should be displayed as "Sun - Thu"
            consecutive_from_monday = 0
            while (consecutive_from_monday + 1 < len(unique_numbers) and 
                   unique_numbers[consecutive_from_monday + 1] == unique_numbers[consecutive_from_monday] + 1 and
                   unique_numbers[consecutive_from_monday] < 7):
                consecutive_from_monday += 1
            
            # If we have Monday through some weekday, then Sunday, it's a wraparound
            if consecutive_from_monday > 0 and unique_numbers[consecutive_from_monday + 1] == 7:
                ranges.append(f"Sun - {num_to_abbrev[unique_numbers[consecutive_from_monday]]}")
                wraparound_handled = True
    
    if not wraparound_handled:
        # Standard consecutive range detection
        i = 0
        
        while i < len(unique_numbers):
            start = i
            
            # Find consecutive sequence
            while (i + 1 < len(unique_numbers) and 
                   unique_numbers[i + 1] == unique_numbers[i] + 1):
                i += 1
            
            # Format the range
            if i == start:
                # Single day
                ranges.append(num_to_abbrev[unique_numbers[start]])
            elif i == start + 1:
                # Two consecutive days, show as range for brevity
                ranges.append(f"{num_to_abbrev[unique_numbers[start]]} - {num_to_abbrev[unique_numbers[i]]}")
            else:
                # Three or more consecutive days, definitely a range
                ranges.append(f"{num_to_abbrev[unique_numbers[start]]} - {num_to_abbrev[unique_numbers[i]]}")
            
            i += 1
    
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


def deal_status_badge(deal):
    """Return appropriate status badge for a deal based on relevance"""
    if not deal or not deal.get('relevance_reasons'):
        return ""
    
    reasons = deal.get('relevance_reasons', [])
    
    if 'happening_now' in reasons:
        return "🔥 Live Now"
    elif 'starting_soon' in reasons:
        return "⏰ Starting Soon"
    elif 'all_day' in reasons and 'active_today' in reasons:
        return "📅 All Day Today"
    elif 'active_today' in reasons:
        return "✅ Today"
    elif 'later_today' in reasons:
        return "🔜 Later Today"
    else:
        return ""


def format_deal_time(deal):
    """Format deal timing information for display"""
    if not deal:
        return ""
    
    start_time = deal.get('start_time')
    end_time = deal.get('end_time')
    is_all_day = deal.get('is_all_day', False)
    days_of_week = deal.get('days_of_week', [])
    
    time_parts = []
    
    # Smart formatting: combine days and time to avoid redundancy
    if days_of_week:
        formatted_days = format_day_range(days_of_week)
        if formatted_days == "Daily" and is_all_day:
            # For daily all-day deals, just say "Daily" (don't add "All Day" later)
            time_parts.append("Daily")
        else:
            time_parts.append(formatted_days)
    
    # Format time (but avoid redundancy with daily all-day)
    if is_all_day and len(days_of_week) != 7:
        # Only add "All Day" if it's not already covered by "Daily"
        time_parts.append("All Day")
    elif start_time and end_time:
        time_parts.append(f"{start_time} - {end_time}")
    elif start_time:
        time_parts.append(f"From {start_time}")
    
    result = " • ".join(time_parts)
    
    # Add pricing information if available - this is key for budget-conscious culinary adventurers!
    price_info = format_deal_prices(deal)
    if price_info:
        result += f" • {price_info}"
    
    return result


def group_restaurants_by_district(restaurants_dict):
    """Group restaurants by district for template rendering"""
    districts = {}
    for slug, restaurant in restaurants_dict.items():
        district = restaurant['district']
        if district not in districts:
            districts[district] = {}
        districts[district][slug] = restaurant
    return districts.items()

def group_restaurants_by_metro_area(restaurants_dict):
    """Group restaurants by metro area for template rendering"""
    metro_areas = {}
    for slug, restaurant in restaurants_dict.items():
        metro_area = restaurant.get('metro_area', 'Denver Metro')
        if metro_area not in metro_areas:
            metro_areas[metro_area] = {}
        metro_areas[metro_area][slug] = restaurant
    
    # Sort metro areas (Denver Metro first, then Boulder)
    sorted_areas = []
    if 'Denver Metro' in metro_areas:
        sorted_areas.append(('Denver Metro', metro_areas['Denver Metro']))
    if 'Boulder' in metro_areas:
        sorted_areas.append(('Boulder', metro_areas['Boulder']))
    
    return sorted_areas


def format_deal_prices(deal) -> str:
    """Format deal pricing information using structured prices list"""
    if not deal:
        return ""
    
    # For object instances with prices attribute
    if hasattr(deal, 'prices') and deal.prices:
        return ", ".join(deal.prices)
    
    # For dict-like objects (JSON data)
    if isinstance(deal, dict):
        prices = deal.get('prices', [])
        if prices:
            return ", ".join(prices)
    
    return ""


def improve_deal_title(deal):
    """Generate better, more descriptive titles for deals"""
    original_title = deal.get('title', '')
    start_time = deal.get('start_time')
    end_time = deal.get('end_time')
    is_all_day = deal.get('is_all_day', False)
    days_of_week = deal.get('days_of_week', [])
    description = deal.get('description', '')
    
    # If title is generic, create a better one
    if original_title.lower() in ['multi-day happy hour', 'time-based special', 'happy hour']:
        
        # Check if we can infer the type from description
        desc_lower = description.lower()
        
        # Look for specific deal types in description
        if any(word in desc_lower for word in ['maki', 'sushi', 'roll']):
            return "Sushi Specials"
        elif any(word in desc_lower for word in ['sake', 'wine', 'beer', 'cocktail', 'drink']):
            return "Drink Specials" 
        elif any(word in desc_lower for word in ['food', 'appetizer', 'app']):
            return "Food Specials"
        elif '25% off' in desc_lower or 'half off' in desc_lower or 'half-off' in desc_lower:
            return "Discount Specials"
        
        # Create title based on timing
        if is_all_day:
            if len(days_of_week) == 1:
                return f"{days_of_week[0].title()} All-Day Special"
            else:
                return "All-Day Happy Hour"
        elif start_time and end_time:
            if len(days_of_week) == 1:
                return f"{days_of_week[0].title()} Happy Hour"
            elif len(days_of_week) == 7:
                return "Daily Happy Hour"
            elif set([d.lower() for d in days_of_week]) == {'saturday', 'sunday'}:
                return "Weekend Happy Hour"
            elif set([d.lower() for d in days_of_week]) == {'monday', 'tuesday', 'wednesday', 'thursday', 'friday'}:
                return "Weekday Happy Hour"
            else:
                return "Happy Hour"
        else:
            return "Special Offers"
    
    return original_title


if __name__ == "__main__":
    main()