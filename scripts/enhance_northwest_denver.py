#!/usr/bin/env python3
"""
Northwest Denver Enhancement

Enhances all 19 Northwest Denver restaurants with premium metadata
optimized for Value-Driven Culinary Adventurers seeking diverse experiences.
"""

import json
import requests
from typing import Dict, List, Optional
from datetime import datetime


class NorthwestDenverEnhancer:
    """Enhances Northwest Denver restaurants with curated metadata"""
    
    def __init__(self):
        self.restaurants_file = 'data/restaurants.json'
        self.enhanced_count = 0
        
        # Premium restaurant data for Northwest Denver (Highland, Berkeley, LoHi neighborhoods)
        self.premium_data = {
            'linger': {
                'price_range': '$$$',
                'atmosphere': ['Rooftop', 'Global Cuisine', 'Trendy', 'Date Night', 'City Views'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 993-3120',
                'opentable_url': 'https://www.opentable.com/linger',
                'instagram': 'lingerdenver',
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
            'root-down': {
                'price_range': '$$$',
                'atmosphere': ['Farm-to-Table', 'Sustainable', 'Local Ingredients', 'Modern American'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 993-4200',
                'opentable_url': 'https://www.opentable.com/root-down',
                'instagram': 'rootdowndenver',
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
            'el-five': {
                'price_range': '$$$',
                'atmosphere': ['Mediterranean', 'Rooftop', 'City Views', 'Date Night', 'Tapas'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 993-3000',
                'opentable_url': 'https://www.opentable.com/el-five',
                'instagram': 'elfivedenver',
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
            'ginger-pig': {
                'price_range': '$$',
                'atmosphere': ['Asian Fusion', 'Creative', 'Local Favorite', 'Casual'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 954-3804',
                'website': 'https://www.gingerpig.com',
                'instagram': 'gingerpigdenver',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '17:00', 'close': '23:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            },
            'bar-dough': {
                'price_range': '$$',
                'atmosphere': ['Italian', 'Pizza', 'Casual', 'Family-Friendly', 'Local'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 323-7777',
                'website': 'https://www.bardoughdenver.com',
                'instagram': 'bardoughdenver',
                'operating_hours': {
                    'monday': {'open': '16:00', 'close': '22:00'},
                    'tuesday': {'open': '16:00', 'close': '22:00'},
                    'wednesday': {'open': '16:00', 'close': '22:00'},
                    'thursday': {'open': '16:00', 'close': '22:00'},
                    'friday': {'open': '16:00', 'close': '23:00'},
                    'saturday': {'open': '16:00', 'close': '23:00'},
                    'sunday': {'open': '16:00', 'close': '22:00'}
                }
            },
            'alma-fonda-fina': {
                'price_range': '$$',
                'atmosphere': ['Mexican', 'Authentic', 'Casual', 'Local Favorite'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 997-8111',
                'website': 'https://almafondafina.com',
                'instagram': 'almafondafina',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '17:00', 'close': '23:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            },
            'bamboo-sushi': {
                'price_range': '$$',
                'atmosphere': ['Sushi', 'Sustainable', 'Modern', 'Casual'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 477-6556',
                'website': 'https://bamboosushi.com/locations/denver-highland',
                'instagram': 'bamboosushi',
                'operating_hours': {
                    'monday': {'open': '11:30', 'close': '21:00'},
                    'tuesday': {'open': '11:30', 'close': '21:00'},
                    'wednesday': {'open': '11:30', 'close': '21:00'},
                    'thursday': {'open': '11:30', 'close': '21:00'},
                    'friday': {'open': '11:30', 'close': '22:00'},
                    'saturday': {'open': '11:30', 'close': '22:00'},
                    'sunday': {'open': '11:30', 'close': '21:00'}
                }
            },
            'american-elm': {
                'price_range': '$$$',
                'atmosphere': ['Modern American', 'Craft Cocktails', 'Date Night', 'Sophisticated'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 998-9292',
                'website': 'https://www.amelm.com',
                'instagram': 'americanelmdenver',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '17:00', 'close': '23:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            },
            'necio-mexican-kitchen': {
                'price_range': '$$',
                'atmosphere': ['Mexican', 'Neighborhood Gem', 'Authentic', 'Casual'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 477-4100',
                'website': 'https://neciomexicankitchen.com',
                'instagram': 'neciomexicankitchen',
                'operating_hours': {
                    'monday': {'open': '16:00', 'close': '22:00'},
                    'tuesday': {'open': '16:00', 'close': '22:00'},
                    'wednesday': {'open': '16:00', 'close': '22:00'},
                    'thursday': {'open': '16:00', 'close': '22:00'},
                    'friday': {'open': '16:00', 'close': '23:00'},
                    'saturday': {'open': '16:00', 'close': '23:00'},
                    'sunday': {'open': '16:00', 'close': '22:00'}
                }
            },
            'senor-bear': {
                'price_range': '$$',
                'atmosphere': ['Mexican', 'Creative', 'Hip', 'Local Favorite'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 433-8787',
                'website': 'https://www.senorbeardenver.com',
                'instagram': 'senorbeardenver',
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
            'ashkara': {
                'price_range': '$$$',
                'atmosphere': ['Mediterranean', 'Middle Eastern', 'Date Night', 'Sophisticated'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 485-9400',
                'website': 'https://www.ashkaradenver.com',
                'instagram': 'ashkaradenver',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '17:00', 'close': '23:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            },
            'kawa-ni': {
                'price_range': '$$',
                'atmosphere': ['Japanese', 'Casual', 'Authentic', 'Local'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 455-2233',
                'website': 'https://kawanidenver.com',
                'instagram': 'kawanidenver',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '21:00'},
                    'wednesday': {'open': '17:00', 'close': '21:00'},
                    'thursday': {'open': '17:00', 'close': '21:00'},
                    'friday': {'open': '17:00', 'close': '22:00'},
                    'saturday': {'open': '17:00', 'close': '22:00'},
                    'sunday': {'open': '17:00', 'close': '21:00'}
                }
            },
            'kumoya-denver': {
                'price_range': '$$$',
                'atmosphere': ['Japanese', 'Sushi', 'Modern', 'Date Night'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 955-3230',
                'website': 'https://www.kumoyadenver.com',
                'instagram': 'kumoyadenver',
                'operating_hours': {
                    'tuesday': {'open': '17:30', 'close': '22:00'},
                    'wednesday': {'open': '17:30', 'close': '22:00'},
                    'thursday': {'open': '17:30', 'close': '22:00'},
                    'friday': {'open': '17:30', 'close': '23:00'},
                    'saturday': {'open': '17:30', 'close': '23:00'},
                    'sunday': {'open': '17:30', 'close': '22:00'}
                }
            },
            'vital-root': {
                'price_range': '$$',
                'atmosphere': ['Plant-Based', 'Health-Conscious', 'Casual', 'Local'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 474-4131',
                'website': 'https://vitalroot.net',
                'instagram': 'vitalroot',
                'operating_hours': {
                    'monday': {'open': '11:00', 'close': '21:00'},
                    'tuesday': {'open': '11:00', 'close': '21:00'},
                    'wednesday': {'open': '11:00', 'close': '21:00'},
                    'thursday': {'open': '11:00', 'close': '21:00'},
                    'friday': {'open': '11:00', 'close': '22:00'},
                    'saturday': {'open': '11:00', 'close': '22:00'},
                    'sunday': {'open': '11:00', 'close': '21:00'}
                }
            },
            'the-bindery': {
                'price_range': '$$$',
                'atmosphere': ['Global Cuisine', 'Creative', 'Date Night', 'Modern'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 993-3300',
                'website': 'https://thebinderydenver.com',
                'instagram': 'thebinderydenver',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '17:00', 'close': '23:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            },
            'gaetanos-eccellente-cucina-cocktails': {
                'price_range': '$$',
                'atmosphere': ['Italian', 'Family-Friendly', 'Traditional', 'Casual'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 433-6500',
                'website': 'https://gaetanosdenver.com',
                'instagram': 'gaetanosdenver',
                'operating_hours': {
                    'monday': {'open': '16:00', 'close': '21:00'},
                    'tuesday': {'open': '16:00', 'close': '21:00'},
                    'wednesday': {'open': '16:00', 'close': '21:00'},
                    'thursday': {'open': '16:00', 'close': '21:00'},
                    'friday': {'open': '16:00', 'close': '22:00'},
                    'saturday': {'open': '16:00', 'close': '22:00'},
                    'sunday': {'open': '16:00', 'close': '21:00'}
                }
            },
            'wild-taco': {
                'price_range': '$',
                'atmosphere': ['Mexican', 'Casual', 'Quick Service', 'Local'],
                'dining_style': 'Fast Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 955-5995',
                'website': 'https://wildtacodenver.com',
                'instagram': 'wildtacodenver',
                'operating_hours': {
                    'monday': {'open': '11:00', 'close': '21:00'},
                    'tuesday': {'open': '11:00', 'close': '21:00'},
                    'wednesday': {'open': '11:00', 'close': '21:00'},
                    'thursday': {'open': '11:00', 'close': '21:00'},
                    'friday': {'open': '11:00', 'close': '22:00'},
                    'saturday': {'open': '11:00', 'close': '22:00'},
                    'sunday': {'open': '11:00', 'close': '21:00'}
                }
            },
            'tacos-tequila-whiskey': {
                'price_range': '$$',
                'atmosphere': ['Mexican', 'Tequila Bar', 'Lively', 'Happy Hour Spot'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 997-3999',
                'website': 'https://tacostequilawhiskey.com',
                'instagram': 'tacostequilawhiskey',
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
            'glo-noodle-house': {
                'price_range': '$',
                'atmosphere': ['Asian', 'Noodles', 'Casual', 'Quick Service'],
                'dining_style': 'Fast Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 477-3786',
                'website': 'https://glonoodlehouse.com',
                'instagram': 'glonoodlehouse',
                'operating_hours': {
                    'monday': {'open': '11:00', 'close': '21:00'},
                    'tuesday': {'open': '11:00', 'close': '21:00'},
                    'wednesday': {'open': '11:00', 'close': '21:00'},
                    'thursday': {'open': '11:00', 'close': '21:00'},
                    'friday': {'open': '11:00', 'close': '22:00'},
                    'saturday': {'open': '11:00', 'close': '22:00'},
                    'sunday': {'open': '11:00', 'close': '21:00'}
                }
            }
        }
    
    def enhance_northwest_denver(self):
        """Enhance all Northwest Denver restaurants with premium metadata"""
        # Load current data
        with open(self.restaurants_file, 'r') as f:
            data = json.load(f)
        
        restaurants = data['restaurants']
        
        print("🏔️ Enhancing Northwest Denver Restaurants...")
        print("=" * 60)
        
        for slug, restaurant in restaurants.items():
            if restaurant.get('district') == 'Northwest Denver' and slug in self.premium_data:
                self._enhance_restaurant(slug, restaurant, self.premium_data[slug])
        
        # Save enhanced data
        with open(self.restaurants_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Enhanced {self.enhanced_count} restaurants")
        print("🎯 Northwest Denver now optimized for Value-Driven Culinary Adventurers!")
    
    def _enhance_restaurant(self, slug: str, restaurant: Dict, enhancements: Dict):
        """Apply enhancements to a single restaurant"""
        name = restaurant.get('name', slug)
        print(f"🔧 Enhancing {name}...")
        
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
        if 'website' in enhancements:
            service_info['website'] = enhancements['website']
        
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
    enhancer = NorthwestDenverEnhancer()
    enhancer.enhance_northwest_denver()


if __name__ == "__main__":
    main()