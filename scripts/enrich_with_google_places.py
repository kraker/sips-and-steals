#!/usr/bin/env python3
"""
Google Places API Integration

Enriches restaurant data with high-quality metadata from Google Places API.
This hybrid approach combines our unique happy hour data with Google's reliable
business information (addresses, hours, contact info, ratings).
"""

import json
import os
import time
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class GooglePlacesEnricher:
    """Enriches restaurant data using Google Places API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
        if not self.api_key:
            raise ValueError("Google Places API key required. Set GOOGLE_PLACES_API_KEY environment variable.")
        
        self.restaurants_file = 'data/restaurants.json'
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        
        # API endpoints
        self.search_url = f"{self.base_url}/textsearch/json"
        self.details_url = f"{self.base_url}/details/json"
        
        # Rate limiting
        self.requests_made = 0
        self.last_request_time = 0
        self.min_request_interval = 0.02  # 50 requests/second max
        
        # Statistics
        self.stats = {
            'restaurants_processed': 0,
            'api_requests_made': 0,
            'successful_enrichments': 0,
            'failed_searches': 0,
            'cost_estimate': 0.0
        }
    
    def _rate_limit(self):
        """Enforce rate limiting for API requests"""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _make_api_request(self, url: str, params: Dict) -> Optional[Dict]:
        """Make rate-limited API request with error handling"""
        self._rate_limit()
        
        params['key'] = self.api_key
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            self.stats['api_requests_made'] += 1
            self.stats['cost_estimate'] += 0.017  # $0.017 per request for Place Details
            
            data = response.json()
            if data['status'] != 'OK':
                print(f"⚠️ API Warning: {data['status']} - {data.get('error_message', '')}")
                return None
            
            return data
        except requests.exceptions.RequestException as e:
            print(f"❌ API Request failed: {e}")
            return None
    
    def search_restaurant(self, name: str, neighborhood: str, city: str = "Denver") -> Optional[str]:
        """Search for restaurant and return place_id"""
        query = f"{name} {neighborhood} {city} restaurant"
        
        params = {
            'query': query,
            'fields': 'place_id,name,formatted_address,rating'
        }
        
        print(f"🔍 Searching: {query}")
        data = self._make_api_request(self.search_url, params)
        
        if not data or not data.get('results'):
            self.stats['failed_searches'] += 1
            return None
        
        # Return the first result's place_id
        result = data['results'][0]
        print(f"   ✅ Found: {result['name']} - {result.get('formatted_address', 'No address')}")
        return result['place_id']
    
    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """Get detailed place information from Google Places"""
        fields = [
            'place_id', 'name', 'formatted_address', 'formatted_phone_number',
            'international_phone_number', 'website', 'rating', 'user_ratings_total',
            'price_level', 'business_status', 'opening_hours', 'geometry',
            'address_components', 'photos', 'reviews'
        ]
        
        params = {
            'place_id': place_id,
            'fields': ','.join(fields)
        }
        
        data = self._make_api_request(self.details_url, params)
        return data.get('result') if data else None
    
    def process_opening_hours(self, opening_hours: Dict) -> Dict:
        """Convert Google's opening hours to our format"""
        if not opening_hours or 'periods' not in opening_hours:
            return {}
        
        day_mapping = {
            0: 'sunday', 1: 'monday', 2: 'tuesday', 3: 'wednesday',
            4: 'thursday', 5: 'friday', 6: 'saturday'
        }
        
        hours = {}
        for period in opening_hours['periods']:
            if 'open' not in period:
                continue
                
            day_num = period['open']['day']
            day_name = day_mapping.get(day_num)
            
            if day_name and 'open' in period and 'close' in period:
                open_time = period['open']['time']
                close_time = period['close']['time']
                
                # Convert from HHMM to HH:MM format
                open_formatted = f"{open_time[:2]}:{open_time[2:]}"
                close_formatted = f"{close_time[:2]}:{close_time[2:]}"
                
                hours[day_name] = {
                    'open': open_formatted,
                    'close': close_formatted
                }
        
        return hours
    
    def enrich_restaurant(self, slug: str, restaurant: Dict) -> bool:
        """Enrich a single restaurant with Google Places data"""
        name = restaurant.get('name', slug)
        neighborhood = restaurant.get('neighborhood', '')
        
        print(f"\n🔧 Enriching: {name}")
        
        # Step 1: Search for the restaurant
        place_id = self.search_restaurant(name, neighborhood)
        if not place_id:
            print(f"   ❌ Could not find {name} in Google Places")
            return False
        
        # Step 2: Get detailed information
        details = self.get_place_details(place_id)
        if not details:
            print(f"   ❌ Could not get details for {name}")
            return False
        
        # Step 3: Update restaurant data
        self._update_restaurant_data(restaurant, details)
        print(f"   ✅ Enhanced {name} with Google Places data")
        return True
    
    def _update_restaurant_data(self, restaurant: Dict, google_data: Dict):
        """Update restaurant object with Google Places data"""
        # Fix address format (convert from object to string if needed)
        current_address = restaurant.get('address')
        if isinstance(current_address, dict):
            # Use formatted_address if available, otherwise construct from parts
            formatted = current_address.get('formatted_address')
            if formatted:
                restaurant['address'] = formatted
            else:
                # Fallback: construct from parts
                parts = []
                if current_address.get('street_number') and current_address.get('street_name'):
                    parts.append(f"{current_address['street_number']} {current_address['street_name']}")
                if current_address.get('city'):
                    parts.append(current_address['city'])
                if current_address.get('state'):
                    parts.append(current_address['state'])
                if current_address.get('zip_code'):
                    parts.append(current_address['zip_code'])
                restaurant['address'] = ', '.join(parts) if parts else 'Address not available'
        
        # Update with Google data
        if google_data.get('formatted_address'):
            restaurant['address'] = google_data['formatted_address']
        
        # Contact information
        contact_info = restaurant.setdefault('contact_info', {})
        if google_data.get('formatted_phone_number'):
            contact_info['primary_phone'] = google_data['formatted_phone_number']
        if google_data.get('international_phone_number'):
            contact_info['international_phone'] = google_data['international_phone_number']
        
        # Note: website now stored in google_places section for schema consistency
        
        # Operating hours
        if google_data.get('opening_hours'):
            hours = self.process_opening_hours(google_data['opening_hours'])
            if hours:
                restaurant['operating_hours'] = hours
        
        # Google-specific data
        google_info = restaurant.setdefault('google_places', {})
        google_info.update({
            'place_id': google_data.get('place_id'),
            'rating': google_data.get('rating'),
            'user_ratings_total': google_data.get('user_ratings_total'),
            'price_level': google_data.get('price_level'),  # 1-4 scale
            'business_status': google_data.get('business_status'),
            'website': google_data.get('website'),  # Store website in google_places
            'last_updated': datetime.now().isoformat()
        })
        
        # Coordinates
        if google_data.get('geometry', {}).get('location'):
            location = google_data['geometry']['location']
            restaurant['coordinates'] = {
                'latitude': location['lat'],
                'longitude': location['lng']
            }
        
        # Update main timestamp
        restaurant['last_updated'] = datetime.now().isoformat()
    
    def enrich_all_restaurants(self, limit: Optional[int] = None):
        """Enrich all restaurants with Google Places data"""
        # Load current data
        with open(self.restaurants_file, 'r') as f:
            data = json.load(f)
        
        restaurants = data['restaurants']
        
        print("🌟 Google Places API Enrichment Starting...")
        print("=" * 60)
        
        count = 0
        for slug, restaurant in restaurants.items():
            if limit and count >= limit:
                break
                
            success = self.enrich_restaurant(slug, restaurant)
            if success:
                self.stats['successful_enrichments'] += 1
            
            self.stats['restaurants_processed'] += 1
            count += 1
            
            # Save progress every 10 restaurants
            if count % 10 == 0:
                with open(self.restaurants_file, 'w') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"\n💾 Progress saved: {count} restaurants processed")
        
        # Final save
        with open(self.restaurants_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self._print_final_stats()
    
    def _print_final_stats(self):
        """Print final enrichment statistics"""
        print("\n" + "=" * 60)
        print("🏆 GOOGLE PLACES ENRICHMENT COMPLETE")
        print("=" * 60)
        
        for key, value in self.stats.items():
            if key == 'cost_estimate':
                print(f"💰 {key.replace('_', ' ').title()}: ${value:.2f}")
            else:
                print(f"📊 {key.replace('_', ' ').title()}: {value}")
        
        success_rate = (self.stats['successful_enrichments'] / self.stats['restaurants_processed'] * 100) if self.stats['restaurants_processed'] > 0 else 0
        print(f"✅ Success Rate: {success_rate:.1f}%")


def main():
    """Main execution function"""
    # Check for API key
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("❌ Error: GOOGLE_PLACES_API_KEY environment variable not set")
        print("\nTo set up Google Places API:")
        print("1. Go to Google Cloud Console")
        print("2. Enable Places API")
        print("3. Create API key")
        print("4. Export GOOGLE_PLACES_API_KEY=your_api_key")
        return
    
    enricher = GooglePlacesEnricher(api_key)
    
    # Start with a small test (first 5 restaurants)
    print("🧪 Starting with test run (5 restaurants)")
    enricher.enrich_all_restaurants(limit=5)


if __name__ == "__main__":
    main()