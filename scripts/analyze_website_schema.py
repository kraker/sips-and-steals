#!/usr/bin/env python3
"""
Analyze Website Data Schema Organization

Examines current website field placement and proposes optimal data schema
for multiple website sources.
"""

import json

def analyze_website_schema():
    """Analyze and propose optimal website data organization"""
    
    with open('data/restaurants.json', 'r') as f:
        data = json.load(f)
    
    sample_restaurant = next(iter(data['restaurants'].values()))
    
    print("🏗️ CURRENT WEBSITE DATA SCHEMA ANALYSIS")
    print("=" * 50)
    
    print("\n📋 CURRENT STRUCTURE:")
    print("• Top-level 'website': Manual/curated URLs (often location-specific)")
    print("• service_info.website: Google Places API websiteUri")
    print("• google_places.*: Other Google Places data (rating, business_status, etc.)")
    
    print(f"\n🔍 SAMPLE DATA:")
    name = sample_restaurant.get('name', 'Unknown')
    print(f"Restaurant: {name}")
    print(f"• website: {sample_restaurant.get('website', 'N/A')}")
    print(f"• service_info.website: {sample_restaurant.get('service_info', {}).get('website', 'N/A')}")
    print(f"• google_places keys: {list(sample_restaurant.get('google_places', {}).keys())}")
    
    print(f"\n💡 SCHEMA INCONSISTENCY ISSUE:")
    print("❌ Google Places website data is scattered:")
    print("   • websiteUri → service_info.website")
    print("   • rating → google_places.rating")
    print("   • business_status → google_places.business_status")
    print("   • place_id → google_places.place_id")
    
    print(f"\n🎯 PROPOSED OPTIMAL SCHEMA:")
    print("✅ Consolidate all Google Places data in google_places object:")
    print("""
{
  "website": "https://manual-curated-url.com/denver/happy-hour",  // Manual/curated
  "google_places": {
    "place_id": "ChIJ...",
    "rating": 4.3,
    "business_status": "OPERATIONAL",
    "website": "https://general-domain.com",  // Google Places websiteUri
    "last_updated": "2025-08-18T20:07:00"
  },
  "service_info": {
    // Other service-related data (delivery, reservations, etc.)
    // No website field
  }
}
""")
    
    print(f"\n🚀 BENEFITS OF PROPOSED SCHEMA:")
    print("1. 🗂️  Data Source Clarity: All Google data grouped together")
    print("2. 🔄 Scraping Strategy: Two website sources for comprehensive coverage")
    print("3. 📱 User Experience: Primary website (curated) + fallback (Google)")
    print("4. 🏗️  Maintainability: Clear separation of manual vs API data")
    print("5. 🔧 Future-Proof: Easy to add more Google Places fields")
    
    print(f"\n🎯 SCRAPING STRATEGY WITH DUAL WEBSITES:")
    print("• Primary: Use curated 'website' (often has happy hour pages)")
    print("• Fallback: Use 'google_places.website' if primary fails")
    print("• Discovery: Try both URLs for comprehensive deal extraction")
    
    print(f"\n📝 MIGRATION STEPS:")
    print("1. Move service_info.website → google_places.website")
    print("2. Update Google Places enrichment script to store consistently")
    print("3. Update scrapers to try both website sources")
    print("4. Clean up empty service_info sections if no other data")

if __name__ == "__main__":
    analyze_website_schema()