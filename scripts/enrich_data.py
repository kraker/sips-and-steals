#!/usr/bin/env python3
"""
Restaurant Data Enrichment Script

Enriches LoDo restaurant data with essential contact information:
- Physical addresses
- Phone numbers
- Hours of operation  
- Reservation links
- Social media handles
"""

import json
from typing import Dict, List, Any
from datetime import datetime


class RestaurantDataEnricher:
    """Enrich restaurant data with contact and operational details"""
    
    def __init__(self, restaurant_file: str):
        self.restaurant_file = restaurant_file
        self.restaurants = self._load_restaurants()
        
        # Manual data collection from web research
        self.enrichment_data = {
            'stk': {
                'address': '1550 Market St, Denver, CO 80202',
                'phone': '(303) 318-8888',
                'hours': {
                    'monday': '11:00 AM - 11:00 PM',
                    'tuesday': '11:00 AM - 11:00 PM', 
                    'wednesday': '11:00 AM - 11:00 PM',
                    'thursday': '11:00 AM - 11:00 PM',
                    'friday': '11:00 AM - 12:00 AM',
                    'saturday': '10:00 AM - 12:00 AM',
                    'sunday': '10:00 AM - 11:00 PM'
                },
                'reservations': {
                    'platform': 'OpenTable',
                    'url': 'https://www.opentable.com/r/stk-denver'
                },
                'social': {
                    'facebook': 'https://www.facebook.com/STKDenver/',
                    'instagram': '@stkdenver'
                },
                'price_range': '$$$',
                'coordinates': {
                    'lat': 39.7516,
                    'lng': -104.9969
                }
            },
            'rioja': {
                'address': '1431 Larimer St, Denver, CO 80202',
                'phone': '(303) 820-2282',
                'hours': {
                    'monday': '11:00 AM - 2:30 PM, 4:00 PM - 10:00 PM',
                    'tuesday': '11:00 AM - 2:30 PM, 4:00 PM - 10:00 PM',
                    'wednesday': '11:00 AM - 2:30 PM, 4:00 PM - 10:00 PM',
                    'thursday': '11:00 AM - 2:30 PM, 4:00 PM - 10:00 PM',
                    'friday': '11:00 AM - 2:30 PM, 4:00 PM - 11:00 PM',
                    'saturday': '10:00 AM - 2:30 PM, 4:00 PM - 11:00 PM',
                    'sunday': '10:00 AM - 2:30 PM, 4:00 PM - 10:00 PM'
                },
                'happy_hour_schedule': {
                    'daily': '2:30 PM - 5:00 PM'
                },
                'reservations': {
                    'platform': 'OpenTable',
                    'url': 'https://www.opentable.com/r/rioja-denver'
                },
                'social': {
                    'instagram': '@riojadenver',
                    'website': 'https://www.riojadenver.com/'
                },
                'price_range': '$$$',
                'coordinates': {
                    'lat': 39.7516,
                    'lng': -104.9969
                }
            },
            'jovaninas-broken-italian': {
                'address': '1520 Blake St, Denver, CO 80202',
                'phone': '(303) 997-3700',
                'hours': {
                    'monday': 'Closed',
                    'tuesday': '5:00 PM - 10:00 PM',
                    'wednesday': '5:00 PM - 10:00 PM',
                    'thursday': '5:00 PM - 10:00 PM',
                    'friday': '5:00 PM - 11:00 PM',
                    'saturday': '5:00 PM - 11:00 PM',
                    'sunday': '5:00 PM - 10:00 PM'
                },
                'happy_hour_schedule': {
                    'tuesday_wednesday': '5:00 PM - 6:00 PM',
                    'friday_saturday': '9:00 PM - 10:00 PM',
                    'wednesday_all_day': 'All Day'
                },
                'reservations': {
                    'platform': 'Resy',
                    'url': 'https://resy.com/cities/denver/jovaninas-broken-italian'
                },
                'social': {
                    'instagram': '@jovaninasbrokenitalian',
                    'website': 'https://jovanina.com'
                },
                'price_range': '$$',
                'coordinates': {
                    'lat': 39.7525,
                    'lng': -104.9964
                }
            },
            'corridor-44': {
                'address': '1433 17th St, Denver, CO 80202',
                'phone': '(303) 825-0844',
                'hours': {
                    'monday': '11:00 AM - 12:00 AM',
                    'tuesday': '11:00 AM - 12:00 AM',
                    'wednesday': '11:00 AM - 12:00 AM',
                    'thursday': '11:00 AM - 12:00 AM',
                    'friday': '11:00 AM - 2:00 AM',
                    'saturday': '9:00 AM - 2:00 AM',
                    'sunday': '9:00 AM - 12:00 AM'
                },
                'happy_hour_schedule': {
                    'weekdays': '3:00 PM - 6:00 PM'
                },
                'reservations': {
                    'platform': 'Phone',
                    'url': 'tel:+13038250844'
                },
                'social': {
                    'instagram': '@corridor44',
                    'website': 'https://corridor44.com'
                },
                'price_range': '$$',
                'coordinates': {
                    'lat': 39.7516,
                    'lng': -104.9969
                }
            },
            'urban-farmer': {
                'address': '1659 Wazee St, Denver, CO 80202',
                'phone': '(303) 991-6328',
                'hours': {
                    'monday': '6:30 AM - 10:00 PM',
                    'tuesday': '6:30 AM - 10:00 PM',
                    'wednesday': '6:30 AM - 10:00 PM',
                    'thursday': '6:30 AM - 10:00 PM',
                    'friday': '6:30 AM - 11:00 PM',
                    'saturday': '7:00 AM - 11:00 PM',
                    'sunday': '7:00 AM - 10:00 PM'
                },
                'happy_hour_schedule': {
                    'daily': '3:00 PM - 6:00 PM'
                },
                'reservations': {
                    'platform': 'OpenTable',
                    'url': 'https://www.opentable.com/r/urban-farmer-denver'
                },
                'social': {
                    'instagram': '@urbanfarmerdenver',
                    'website': 'https://www.urbanfarmerdenver.com'
                },
                'price_range': '$$$',
                'coordinates': {
                    'lat': 39.7503,
                    'lng': -104.9942
                }
            },
            'osteria-marco': {
                'address': '1453 Larimer St, Denver, CO 80202',
                'phone': '(303) 534-5855',
                'hours': {
                    'monday': '5:00 PM - 10:00 PM',
                    'tuesday': '5:00 PM - 10:00 PM',
                    'wednesday': '5:00 PM - 10:00 PM',
                    'thursday': '5:00 PM - 10:00 PM',
                    'friday': '5:00 PM - 11:00 PM',
                    'saturday': '5:00 PM - 11:00 PM',
                    'sunday': '5:00 PM - 10:00 PM'
                },
                'happy_hour_schedule': {
                    'daily': '5:00 PM - 6:30 PM'
                },
                'reservations': {
                    'platform': 'Resy',
                    'url': 'https://resy.com/cities/denver/osteria-marco'
                },
                'social': {
                    'instagram': '@osteriamarco',
                    'website': 'https://www.osteriamarco.com'
                },
                'price_range': '$$$',
                'coordinates': {
                    'lat': 39.7517,
                    'lng': -104.9968
                }
            }
        }
    
    def _load_restaurants(self) -> Dict:
        """Load existing restaurant data"""
        with open(self.restaurant_file, 'r') as f:
            return json.load(f)
    
    def enrich_data(self):
        """Enrich restaurant data with contact and operational information"""
        print("🔧 **Enriching LoDo Restaurant Data**")
        print("=" * 50)
        
        enriched_count = 0
        
        for slug, restaurant in self.restaurants['restaurants'].items():
            if slug in self.enrichment_data:
                enrichment = self.enrichment_data[slug]
                
                # Add contact information
                restaurant['contact'] = {
                    'address': enrichment['address'],
                    'phone': enrichment['phone'],
                    'coordinates': enrichment['coordinates']
                }
                
                # Add operational hours
                restaurant['hours'] = enrichment['hours']
                
                # Add happy hour schedule (cleaned)
                if 'happy_hour_schedule' in enrichment:
                    restaurant['happy_hour_schedule'] = enrichment['happy_hour_schedule']
                
                # Add reservation information
                restaurant['reservations'] = enrichment['reservations']
                
                # Add social media
                restaurant['social'] = enrichment['social']
                
                # Add price range
                restaurant['price_range'] = enrichment['price_range']
                
                enriched_count += 1
                print(f"✅ Enhanced {restaurant['name']} with contact info")
            else:
                print(f"⚠️  No enrichment data for {restaurant['name']}")
        
        print(f"\n📊 Successfully enriched {enriched_count}/{len(self.restaurants['restaurants'])} restaurants")
        
        # Update metadata
        self.restaurants['metadata']['enriched_at'] = datetime.now().isoformat()
        self.restaurants['metadata']['enrichment_version'] = '1.0'
        
        return self.restaurants
    
    def save_enriched_data(self, output_file: str = None):
        """Save enriched restaurant data"""
        if output_file is None:
            output_file = self.restaurant_file.replace('.json', '_enriched.json')
        
        with open(output_file, 'w') as f:
            json.dump(self.restaurants, f, indent=2, default=str)
        
        print(f"💾 Enriched data saved to: {output_file}")
        return output_file
    
    def create_user_friendly_summary(self):
        """Create a user-friendly summary of enriched data"""
        summary = {
            'generated_at': datetime.now().isoformat(),
            'district': 'LoDo (Lower Downtown)',
            'total_restaurants': len(self.restaurants['restaurants']),
            'restaurants': {}
        }
        
        for slug, restaurant in self.restaurants['restaurants'].items():
            if 'contact' in restaurant:
                summary['restaurants'][slug] = {
                    'name': restaurant['name'],
                    'cuisine': restaurant['cuisine'],
                    'address': restaurant['contact']['address'],
                    'phone': restaurant['contact']['phone'],
                    'website': restaurant['website'],
                    'price_range': restaurant.get('price_range', '$$'),
                    'hours': restaurant.get('hours', {}),
                    'happy_hour': restaurant.get('happy_hour_schedule', {}),
                    'reservations': restaurant.get('reservations', {}),
                    'social': restaurant.get('social', {})
                }
        
        with open('data/lodo_restaurants_user_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print("📋 User-friendly summary created: data/lodo_restaurants_user_summary.json")
        return summary


def main():
    """Enrich LoDo restaurant data with contact information"""
    print("🏢 **LoDo Restaurant Data Enrichment**")
    print("Adding essential contact and operational information for user dashboard")
    print("=" * 70)
    
    enricher = RestaurantDataEnricher('data/lodo_restaurants.json')
    
    # Enrich the data
    enriched_data = enricher.enrich_data()
    
    # Save enriched data
    output_file = enricher.save_enriched_data()
    
    # Create user-friendly summary
    summary = enricher.create_user_friendly_summary()
    
    print(f"\n✅ **Enrichment Complete**")
    print(f"Enhanced restaurant data ready for user-focused dashboard")
    print(f"Output: {output_file}")


if __name__ == '__main__':
    main()