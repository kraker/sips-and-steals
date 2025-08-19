#!/usr/bin/env python3
"""
Google Places API (New) Integration

Updated version using the New Places API endpoints for better performance
and future-proofing.
"""

import json
import os
import time
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class NewGooglePlacesEnricher:
    """Enriches restaurant data using Google Places API (New)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
        if not self.api_key:
            raise ValueError("Google Places API key required. Set GOOGLE_PLACES_API_KEY environment variable.")
        
        self.restaurants_file = 'data/restaurants.json'
        
        # New Places API endpoints
        self.search_url = "https://places.googleapis.com/v1/places:searchText"
        self.details_url = "https://places.googleapis.com/v1/places"
        
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
    
    def _make_api_request(self, url: str, data: Dict = None, headers: Dict = None) -> Optional[Dict]:
        """Make rate-limited API request with error handling"""
        self._rate_limit()
        
        default_headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.api_key,
            'X-Goog-FieldMask': '*'  # Get all available fields
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            if data:
                response = requests.post(url, json=data, headers=default_headers)
            else:
                response = requests.get(url, headers=default_headers)
            
            response.raise_for_status()
            
            self.stats['api_requests_made'] += 1
            self.stats['cost_estimate'] += 0.017  # $0.017 per request
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API Request failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return None
    
    def search_restaurant(self, name: str, neighborhood: str, city: str = "Denver") -> Optional[str]:
        """Search for restaurant using New Places API Text Search"""
        query = f"{name} restaurant {neighborhood} {city} Colorado"
        
        data = {
            "textQuery": query,
            "maxResultCount": 1
        }
        
        print(f"🔍 Searching: {query}")
        response_data = self._make_api_request(self.search_url, data=data)
        
        if not response_data or not response_data.get('places'):
            self.stats['failed_searches'] += 1
            return None
        
        # Return the first result's place ID
        place = response_data['places'][0]
        place_id = place.get('id')
        name = place.get('displayName', {}).get('text', 'Unknown')
        address = place.get('formattedAddress', 'No address')
        
        print(f"   ✅ Found: {name} - {address}")
        return place_id
    
    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """Get detailed place information using New Places API"""
        url = f"{self.details_url}/{place_id}"
        
        # Specify the fields we want
        headers = {
            'X-Goog-FieldMask': 'id,displayName,formattedAddress,nationalPhoneNumber,internationalPhoneNumber,websiteUri,rating,userRatingCount,priceLevel,businessStatus,regularOpeningHours,location,addressComponents,photos,reviews'
        }
        
        response_data = self._make_api_request(url, headers=headers)
        return response_data if response_data else None
    
    def process_opening_hours(self, opening_hours: Dict) -> Dict:
        """Convert New Places API opening hours to our format"""
        if not opening_hours:
            return {}
        
        # Handle both legacy and new API formats
        periods = opening_hours.get('periods', [])
        if not periods:
            return {}
        
        day_mapping = {
            0: 'sunday', 1: 'monday', 2: 'tuesday', 3: 'wednesday',
            4: 'thursday', 5: 'friday', 6: 'saturday'
        }
        
        hours = {}
        for period in periods:
            if 'open' not in period:
                continue
            
            try:
                # New API format
                open_info = period['open']
                close_info = period.get('close')
                
                day_num = open_info.get('day')
                if day_num is None:
                    continue
                    
                day_name = day_mapping.get(day_num)
                if not day_name:
                    continue
                
                # Handle different time formats
                if 'time' in open_info and close_info and 'time' in close_info:
                    # HHMM format
                    open_time = open_info['time']
                    close_time = close_info['time']
                    open_formatted = f"{open_time[:2]}:{open_time[2:]}"
                    close_formatted = f"{close_time[:2]}:{close_time[2:]}"
                elif 'hour' in open_info and close_info and 'hour' in close_info:
                    # Hour/minute format
                    open_hour = open_info.get('hour', 0)
                    open_minute = open_info.get('minute', 0)
                    close_hour = close_info.get('hour', 0)
                    close_minute = close_info.get('minute', 0)
                    
                    open_formatted = f"{open_hour:02d}:{open_minute:02d}"
                    close_formatted = f"{close_hour:02d}:{close_minute:02d}"
                else:
                    continue
                
                hours[day_name] = {
                    'open': open_formatted,
                    'close': close_formatted
                }
                
            except (KeyError, ValueError, TypeError) as e:
                # Skip malformed entries
                continue
        
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
        """Update restaurant object with New Places API data"""
        # Update with Google data
        if google_data.get('formattedAddress'):
            restaurant['address'] = google_data['formattedAddress']
        
        # Contact information
        contact_info = restaurant.setdefault('contact_info', {})
        if google_data.get('nationalPhoneNumber'):
            contact_info['primary_phone'] = google_data['nationalPhoneNumber']
        if google_data.get('internationalPhoneNumber'):
            contact_info['international_phone'] = google_data['internationalPhoneNumber']
        
        # Note: websiteUri now stored in google_places section for schema consistency
        
        # Operating hours
        if google_data.get('regularOpeningHours'):
            hours = self.process_opening_hours(google_data['regularOpeningHours'])
            if hours:
                restaurant['operating_hours'] = hours
        
        # Google-specific data
        google_info = restaurant.setdefault('google_places', {})
        google_info.update({
            'place_id': google_data.get('id'),
            'rating': google_data.get('rating'),
            'user_ratings_total': google_data.get('userRatingCount'),
            'price_level': google_data.get('priceLevel'),
            'business_status': google_data.get('businessStatus'),
            'website': google_data.get('websiteUri'),  # Store website in google_places
            'last_updated': datetime.now().isoformat()
        })
        
        # Coordinates
        if google_data.get('location'):
            location = google_data['location']
            restaurant['coordinates'] = {
                'latitude': location['latitude'],
                'longitude': location['longitude']
            }
        
        # Update main timestamp
        restaurant['last_updated'] = datetime.now().isoformat()
    
    def test_single_restaurant(self):
        """Test with a single restaurant"""
        print("🧪 Testing New Places API with Osteria Marco...")
        
        place_id = self.search_restaurant("Osteria Marco", "LoDo", "Denver")
        if place_id:
            details = self.get_place_details(place_id)
            if details:
                print("✅ New Places API test successful!")
                print(f"   Name: {details.get('displayName', {}).get('text', 'N/A')}")
                print(f"   Address: {details.get('formattedAddress', 'N/A')}")
                print(f"   Phone: {details.get('nationalPhoneNumber', 'N/A')}")
                print(f"   Rating: {details.get('rating', 'N/A')}")
                print(f"   Business Status: {details.get('businessStatus', 'N/A')}")
                return True
        
        print("❌ New Places API test failed")
        return False


def main():
    """Test the New Places API"""
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("❌ Error: GOOGLE_PLACES_API_KEY environment variable not set")
        return
    
    enricher = NewGooglePlacesEnricher(api_key)
    success = enricher.test_single_restaurant()
    
    if success:
        print("\n🚀 Ready to use New Places API!")
    else:
        print("\n❌ Please check API setup")


if __name__ == "__main__":
    main()