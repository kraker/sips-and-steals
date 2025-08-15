#!/usr/bin/env python3
"""
Multi-page site generator using Jinja2 templates and Pico CSS
Creates a static site optimized for "The Discerning Urban Explorer"
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from urllib.parse import quote

def main():
    """Generate the complete multi-page restaurant site"""
    
    # Load restaurant data
    with open('data/restaurants.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader('templates'),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # Add custom filters
    env.filters['slugify'] = slugify
    env.filters['dateformat'] = format_date
    env.filters['urlencode'] = quote
    
    # Create output directories
    docs_dir = Path('docs')
    restaurants_dir = docs_dir / 'restaurants'
    docs_dir.mkdir(exist_ok=True)
    restaurants_dir.mkdir(exist_ok=True)
    
    print("🏗️  Generating Sips and Steals website...")
    
    # Generate index page
    generate_index_page(env, data, docs_dir)
    
    # Generate individual restaurant pages
    generate_restaurant_pages(env, data, restaurants_dir)
    
    print(f"✅ Site generated successfully!")
    print(f"📁 Output: {docs_dir}")
    print(f"🏠 Index: {docs_dir}/index.html")
    print(f"📄 Restaurant pages: {len([r for area in data['areas'].values() for r in area.values()])} pages")

def generate_index_page(env, data, output_dir):
    """Generate the main index page with restaurant grid"""
    template = env.get_template('index.html')
    
    html = template.render(
        metadata=data['metadata'],
        areas=data['areas']
    )
    
    output_file = output_dir / 'index.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"📄 Generated index page: {output_file}")

def generate_restaurant_pages(env, data, output_dir):
    """Generate individual restaurant profile pages"""
    template = env.get_template('restaurant.html')
    
    total_restaurants = 0
    
    for area_name, restaurants in data['areas'].items():
        for slug, restaurant in restaurants.items():
            # Add area info to restaurant data
            restaurant_data = restaurant.copy()
            restaurant_data['area'] = area_name
            
            html = template.render(
                restaurant=restaurant_data,
                metadata=data['metadata']
            )
            
            output_file = output_dir / f"{slug}.html"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            total_restaurants += 1
    
    print(f"📄 Generated {total_restaurants} restaurant pages")

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

if __name__ == "__main__":
    main()