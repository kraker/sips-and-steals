#!/usr/bin/env python3
"""
Analyze Google Places Enrichment Results

Evaluates the data quality improvements from Google Places API enrichment.
"""

import json
from typing import Dict, List, Tuple

def analyze_data_quality():
    """Analyze the current data quality after Google Places enrichment"""
    
    with open('data/restaurants.json', 'r') as f:
        data = json.load(f)
    
    restaurants = data['restaurants']
    total_restaurants = len(restaurants)
    
    print("🔍 GOOGLE PLACES ENRICHMENT ANALYSIS")
    print("=" * 50)
    print(f"Total restaurants: {total_restaurants}")
    print()
    
    # Track completeness metrics
    metrics = {
        'complete_addresses': 0,
        'has_phone': 0,
        'has_operating_hours': 0,
        'has_google_places_id': 0,
        'has_rating': 0,
        'has_coordinates': 0,
        'has_business_status': 0,
        'malformed_addresses': 0,
        'enriched_restaurants': 0
    }
    
    failed_enrichments = []
    sample_enriched = []
    
    for slug, restaurant in restaurants.items():
        name = restaurant.get('name', slug)
        
        # Check for Google Places enrichment
        google_places = restaurant.get('google_places', {})
        if google_places.get('place_id'):
            metrics['enriched_restaurants'] += 1
            if len(sample_enriched) < 3:
                sample_enriched.append((name, google_places))
        else:
            failed_enrichments.append(name)
        
        # Address quality
        address = restaurant.get('address', '')
        if isinstance(address, str) and len(address) > 10:
            metrics['complete_addresses'] += 1
        elif isinstance(address, dict):
            metrics['malformed_addresses'] += 1
        
        # Contact information
        contact_info = restaurant.get('contact_info', {})
        if contact_info.get('primary_phone'):
            metrics['has_phone'] += 1
        
        # Operating hours
        if restaurant.get('operating_hours'):
            metrics['has_operating_hours'] += 1
        
        # Google-specific fields
        if google_places.get('place_id'):
            metrics['has_google_places_id'] += 1
        if google_places.get('rating'):
            metrics['has_rating'] += 1
        if google_places.get('business_status'):
            metrics['has_business_status'] += 1
        
        # Coordinates
        if restaurant.get('coordinates'):
            metrics['has_coordinates'] += 1
    
    # Calculate percentages
    print("📊 DATA QUALITY METRICS")
    print("-" * 30)
    for metric, count in metrics.items():
        percentage = (count / total_restaurants) * 100
        print(f"{metric.replace('_', ' ').title()}: {count}/{total_restaurants} ({percentage:.1f}%)")
    
    print("\n🎯 ENRICHMENT SUCCESS")
    print("-" * 25)
    success_rate = (metrics['enriched_restaurants'] / total_restaurants) * 100
    print(f"Successfully enriched: {metrics['enriched_restaurants']}/{total_restaurants} ({success_rate:.1f}%)")
    
    if failed_enrichments:
        print(f"\n❌ FAILED ENRICHMENTS ({len(failed_enrichments)}):")
        for restaurant in failed_enrichments:
            print(f"   • {restaurant}")
    
    print("\n✅ SAMPLE ENRICHED DATA:")
    for name, google_data in sample_enriched:
        print(f"\n🏪 {name}")
        print(f"   Place ID: {google_data.get('place_id', 'N/A')[:20]}...")
        print(f"   Rating: {google_data.get('rating', 'N/A')}")
        print(f"   Status: {google_data.get('business_status', 'N/A')}")
        print(f"   Last Updated: {google_data.get('last_updated', 'N/A')[:10]}")
    
    # Cost analysis
    total_requests = metrics['enriched_restaurants'] * 2  # Search + Details
    estimated_cost = total_requests * 0.017
    print(f"\n💰 COST ANALYSIS")
    print("-" * 15)
    print(f"API Requests: ~{total_requests} (search + details)")
    print(f"Estimated Cost: ${estimated_cost:.2f}")
    
    return metrics, failed_enrichments

if __name__ == "__main__":
    analyze_data_quality()