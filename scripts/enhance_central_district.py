#!/usr/bin/env python3
"""
Central District Restaurant Enhancement

Enhances restaurant data for Central district establishments with premium metadata
that appeals to the "Discerning Urban Explorer" target user.
"""

import json
import requests
from typing import Dict, List, Optional
from datetime import datetime


class CentralDistrictEnhancer:
    """Enhances Central district restaurant data with premium metadata"""
    
    def __init__(self):
        self.restaurants_file = 'data/restaurants.json'
        self.enhanced_count = 0
        
        # Premium restaurant data for Central district (manually curated for quality)
        self.premium_data = {
            'osteria-marco': {
                'price_range': '$$$$',
                'atmosphere': ['Upscale', 'Date Night', 'Business Dinner', 'Intimate'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 534-5855',
                'opentable_url': 'https://www.opentable.com/osteria-marco',
                'instagram': 'osteriamarco',
                'operating_hours': {
                    'monday': {'open': '17:00', 'close': '22:00'},
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '17:00', 'close': '23:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            },
            'blue-sushi-sake-grill': {
                'price_range': '$$$',
                'atmosphere': ['Modern', 'Lively', 'Sake Bar', 'Happy Hour Spot'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 539-5259',
                'opentable_url': 'https://www.opentable.com/blue-sushi-sake-grill-lodo',
                'instagram': 'bluesushisakegrill',
                'operating_hours': {
                    'monday': {'open': '11:30', 'close': '22:00'},
                    'tuesday': {'open': '11:30', 'close': '22:00'},
                    'wednesday': {'open': '11:30', 'close': '22:00'},
                    'thursday': {'open': '11:30', 'close': '22:00'},
                    'friday': {'open': '11:30', 'close': '23:00'},
                    'saturday': {'open': '11:30', 'close': '23:00'},
                    'sunday': {'open': '11:30', 'close': '22:00'}
                }
            },
            'tavernetta': {
                'price_range': '$$$$',
                'atmosphere': ['Sophisticated', 'Date Night', 'Wine Focused', 'Intimate'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 472-9463',
                'opentable_url': 'https://www.opentable.com/tavernetta',
                'instagram': 'tavernettadenver',
                'operating_hours': {
                    'monday': {'open': '17:00', 'close': '22:00'},
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '17:00', 'close': '23:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            },
            'thirsty-lion': {
                'cuisine': 'American Gastropub',
                'price_range': '$$$',
                'atmosphere': ['Gastropub', 'Sports Bar', 'Happy Hour Spot', 'Lively'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 623-0316',
                'opentable_url': 'https://www.opentable.com/thirsty-lion-gastropub-grill-denver',
                'instagram': 'thirstylionrestaurant',
                'operating_hours': {
                    'monday': {'open': '11:00', 'close': '23:00'},
                    'tuesday': {'open': '11:00', 'close': '23:00'},
                    'wednesday': {'open': '11:00', 'close': '23:00'},
                    'thursday': {'open': '11:00', 'close': '23:00'},
                    'friday': {'open': '11:00', 'close': '24:00'},
                    'saturday': {'open': '10:00', 'close': '24:00'},
                    'sunday': {'open': '10:00', 'close': '23:00'}
                }
            },
            'jovaninas-broken-italian': {
                'price_range': '$$$',
                'atmosphere': ['Neighborhood Gem', 'Intimate', 'Wine Bar', 'Date Night'],
                'dining_style': 'Casual Fine Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 991-1946',
                'opentable_url': 'https://www.opentable.com/jovaninas-broken-italian',
                'instagram': 'jovaninasbrokenitalian',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '22:00'},
                    'saturday': {'open': '17:00', 'close': '22:00'},
                    'sunday': {'open': '17:00', 'close': '21:00'}
                }
            },
            'urban-farmer': {
                'price_range': '$$$$',
                'atmosphere': ['Upscale', 'Business Dinner', 'Steakhouse', 'Date Night'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 623-4844',
                'opentable_url': 'https://www.opentable.com/urban-farmer-denver',
                'instagram': 'urbanfarmerdenver',
                'operating_hours': {
                    'monday': {'open': '06:30', 'close': '22:00'},
                    'tuesday': {'open': '06:30', 'close': '22:00'},
                    'wednesday': {'open': '06:30', 'close': '22:00'},
                    'thursday': {'open': '06:30', 'close': '22:00'},
                    'friday': {'open': '06:30', 'close': '23:00'},
                    'saturday': {'open': '07:00', 'close': '23:00'},
                    'sunday': {'open': '07:00', 'close': '22:00'}
                }
            },
            'rioja': {
                'price_range': '$$$$',
                'atmosphere': ['Sophisticated', 'Wine Focused', 'Date Night', 'Mediterranean'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 820-2282',
                'opentable_url': 'https://www.opentable.com/rioja',
                'instagram': 'riojadenver',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '17:00', 'close': '23:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            },
            'corridor-44': {
                'price_range': '$$$$',
                'atmosphere': ['French Bistro', 'Wine Bar', 'Intimate', 'Date Night'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 893-0013',
                'resy_url': 'https://resy.com/cities/denver/corridor-44',
                'instagram': 'corridor44denver',
                'operating_hours': {
                    'wednesday': {'open': '17:30', 'close': '22:00'},
                    'thursday': {'open': '17:30', 'close': '22:00'},
                    'friday': {'open': '17:30', 'close': '23:00'},
                    'saturday': {'open': '17:30', 'close': '23:00'},
                    'sunday': {'open': '17:30', 'close': '22:00'}
                }
            },
            'tamayo': {
                'price_range': '$$$',
                'atmosphere': ['Rooftop', 'Lively', 'Mexican', 'Happy Hour Spot'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 623-5518',
                'opentable_url': 'https://www.opentable.com/tamayo',
                'instagram': 'tamayodenver',
                'operating_hours': {
                    'monday': {'open': '16:00', 'close': '22:00'},
                    'tuesday': {'open': '16:00', 'close': '22:00'},
                    'wednesday': {'open': '16:00', 'close': '22:00'},
                    'thursday': {'open': '16:00', 'close': '22:00'},
                    'friday': {'open': '16:00', 'close': '23:00'},
                    'saturday': {'open': '11:00', 'close': '23:00'},
                    'sunday': {'open': '11:00', 'close': '22:00'}
                }
            },
            'stk': {
                'price_range': '$$$$',
                'atmosphere': ['Upscale', 'Trendy', 'Steakhouse', 'Nightlife'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Upscale Casual',
                'primary_phone': '(303) 594-3300',
                'opentable_url': 'https://www.opentable.com/stk-denver',
                'instagram': 'stksteakhouse',
                'operating_hours': {
                    'monday': {'open': '17:00', 'close': '22:00'},
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '23:00'},
                    'friday': {'open': '17:00', 'close': '24:00'},
                    'saturday': {'open': '17:00', 'close': '24:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            }
        }
    
    def enhance_central_district(self):
        """Enhance all Central district restaurants with premium metadata"""
        # Load current data
        with open(self.restaurants_file, 'r') as f:
            data = json.load(f)
        
        restaurants = data['restaurants']
        
        print("🏢 Enhancing Central District Restaurants...")
        print("=" * 50)
        
        for slug, restaurant in restaurants.items():
            if restaurant.get('district') == 'Central' and slug in self.premium_data:
                self._enhance_restaurant(slug, restaurant, self.premium_data[slug])
        
        # Save enhanced data
        with open(self.restaurants_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Enhanced {self.enhanced_count} restaurants")
        print("🎯 All Central district restaurants now have premium metadata!")
    
    def _enhance_restaurant(self, slug: str, restaurant: Dict, enhancements: Dict):
        """Apply enhancements to a single restaurant"""
        name = restaurant.get('name', slug)
        print(f"🔧 Enhancing {name}...")
        
        # Update cuisine if provided
        if 'cuisine' in enhancements:
            restaurant['cuisine'] = enhancements['cuisine']
        
        # Update dining info
        dining_info = restaurant.setdefault('dining_info', {})
        if 'price_range' in enhancements:
            dining_info['price_range'] = enhancements['price_range']
        if 'atmosphere' in enhancements:
            dining_info['atmosphere'] = enhancements['atmosphere']
        if 'dining_style' in enhancements:
            dining_info['dining_style'] = enhancements['dining_style']
        if 'dress_code' in enhancements:
            dining_info['dress_code'] = enhancements['dress_code']
        
        # Update contact info
        contact_info = restaurant.setdefault('contact_info', {})
        if 'primary_phone' in enhancements:
            contact_info['primary_phone'] = enhancements['primary_phone']
        if 'instagram' in enhancements:
            contact_info['instagram'] = enhancements['instagram']
        
        # Update service info
        service_info = restaurant.setdefault('service_info', {})
        if 'opentable_url' in enhancements:
            service_info['opentable_url'] = enhancements['opentable_url']
        if 'resy_url' in enhancements:
            service_info['resy_url'] = enhancements['resy_url']
        
        # Update operating hours
        if 'operating_hours' in enhancements:
            restaurant['operating_hours'] = enhancements['operating_hours']
        
        # Update timestamp
        restaurant['last_updated'] = datetime.now().isoformat()
        
        self.enhanced_count += 1
        
        improvements = []
        if 'price_range' in enhancements:
            improvements.append(f"Price: {enhancements['price_range']}")
        if 'atmosphere' in enhancements:
            improvements.append(f"Atmosphere: {', '.join(enhancements['atmosphere'][:2])}...")
        if 'operating_hours' in enhancements:
            improvements.append("Hours")
        
        print(f"   ✅ Added: {', '.join(improvements)}")


def main():
    """Main execution function"""
    enhancer = CentralDistrictEnhancer()
    enhancer.enhance_central_district()


if __name__ == "__main__":
    main()