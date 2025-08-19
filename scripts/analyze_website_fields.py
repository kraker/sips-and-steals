#!/usr/bin/env python3
"""
Analyze Website Field Duplication

Examines the differences between top-level website and service_info.website
to understand data sources and consolidation strategy.
"""

import json
from urllib.parse import urlparse

def analyze_website_fields():
    """Analyze website field patterns and differences"""
    
    with open('data/restaurants.json', 'r') as f:
        data = json.load(f)
    
    restaurants = data['restaurants']
    
    print("🔍 WEBSITE FIELD ANALYSIS")
    print("=" * 50)
    
    # Track patterns
    stats = {
        'total_restaurants': len(restaurants),
        'both_same': 0,
        'both_different': 0,
        'only_top_level': 0,
        'only_service_info': 0,
        'neither': 0,
        'top_more_specific': 0,
        'service_more_general': 0
    }
    
    examples = {
        'different_values': [],
        'same_values': [],
        'top_level_only': [],
        'service_info_only': []
    }
    
    for slug, restaurant in restaurants.items():
        name = restaurant.get('name', slug)
        top_website = restaurant.get('website', '').strip()
        service_website = restaurant.get('service_info', {}).get('website', '').strip()
        
        # Normalize for comparison (remove trailing slashes, http vs https)
        def normalize_url(url):
            if not url:
                return ''
            # Parse URL
            parsed = urlparse(url if url.startswith(('http://', 'https://')) else 'http://' + url)
            # Normalize: remove trailing slash, use https
            normalized = f"https://{parsed.netloc}{parsed.path.rstrip('/')}"
            if parsed.query:
                normalized += f"?{parsed.query}"
            return normalized
        
        top_norm = normalize_url(top_website)
        service_norm = normalize_url(service_website)
        
        if top_website and service_website:
            if top_norm == service_norm:
                stats['both_same'] += 1
                if len(examples['same_values']) < 2:
                    examples['same_values'].append((name, top_website, service_website))
            else:
                stats['both_different'] += 1
                if len(examples['different_values']) < 5:
                    examples['different_values'].append((name, top_website, service_website))
                
                # Check if one is more specific
                if service_website in top_website or top_website.count('/') > service_website.count('/'):
                    stats['top_more_specific'] += 1
                elif top_website in service_website or service_website.count('/') > top_website.count('/'):
                    stats['service_more_general'] += 1
                    
        elif top_website and not service_website:
            stats['only_top_level'] += 1
            if len(examples['top_level_only']) < 2:
                examples['top_level_only'].append((name, top_website))
        elif not top_website and service_website:
            stats['only_service_info'] += 1
            if len(examples['service_info_only']) < 2:
                examples['service_info_only'].append((name, service_website))
        else:
            stats['neither'] += 1
    
    # Print analysis
    print("📊 STATISTICS")
    print("-" * 25)
    for key, value in stats.items():
        if key != 'total_restaurants':
            percentage = (value / stats['total_restaurants']) * 100
            print(f"{key.replace('_', ' ').title()}: {value}/{stats['total_restaurants']} ({percentage:.1f}%)")
    
    print("\n🔍 EXAMPLES OF DIFFERENT VALUES")
    print("-" * 35)
    for name, top, service in examples['different_values']:
        print(f"\n🏪 {name}")
        print(f"   Top-level: {top}")
        print(f"   Service:   {service}")
        
        # Analyze difference type
        if service in top:
            print(f"   📝 Top-level is more specific (location-specific)")
        elif top in service:
            print(f"   📝 Service is more general")
        else:
            print(f"   📝 Completely different URLs")
    
    print(f"\n💡 DATA SOURCE HYPOTHESIS")
    print("-" * 25)
    print("• Top-level website: Original manual data entry or location-specific URLs")
    print("• service_info.website: Google Places API general website URLs")
    print("• Pattern: Top-level often has location-specific paths (/lodo, /colorado)")
    print("• Pattern: Service info has general domain without specific paths")
    
    print(f"\n🎯 CONSOLIDATION STRATEGY")
    print("-" * 25)
    print("1. Keep top-level website as primary (often more specific)")
    print("2. Use service_info.website as fallback if top-level missing")
    print("3. Remove service_info.website to eliminate duplication")
    print("4. Prefer location-specific URLs for better user experience")
    
    return stats, examples

if __name__ == "__main__":
    analyze_website_fields()