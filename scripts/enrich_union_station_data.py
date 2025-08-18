#!/usr/bin/env python3
"""
Enrich Union Station Restaurant Data
Add missing contact info, pricing, and reservation details for quality demo.
"""

import json
from pathlib import Path
from datetime import datetime


def enrich_union_station_data():
    """Add missing metadata for Union Station restaurants to match LoDo quality"""
    
    # Load Union Station dataset
    with open('data/cache/lodo_union_station_restaurants.json') as f:
        data = json.load(f)
    
    # Key Union Station restaurant enhancements
    # Based on restaurant websites and public information
    enrichments = {
        'tavernetta': {
            'price_range': '$$$',
            'contact': {
                'phone': '(720) 605-1390',
                'address': '1889 16th St, Denver, CO 80202',
                'formatted_address': '1889 16th St, Denver, CO 80202'
            },
            'reservations': {
                'platform': 'Resy',
                'url': 'https://resy.com/cities/denver/tavernetta'
            },
            'social': {
                'website': 'https://www.tavernettadenver.com'
            }
        },
        'uchi': {
            'price_range': '$$$$',
            'contact': {
                'phone': '(720) 420-9926',
                'address': '2500 Lawrence St, Denver, CO 80205',
                'formatted_address': '2500 Lawrence St, Denver, CO 80205'
            },
            'reservations': {
                'platform': 'Resy',
                'url': 'https://resy.com/cities/denver/uchi-denver'
            },
            'social': {
                'website': 'https://uchi.uchirestaurants.com/location/denver/'
            }
        },
        'work-class': {
            'price_range': '$$',
            'contact': {
                'phone': '(303) 292-0700',
                'address': '2500 Larimer St, Suite 101, Denver, CO 80205',
                'formatted_address': '2500 Larimer St, Denver, CO 80205'
            },
            'reservations': {
                'platform': 'OpenTable',
                'url': 'https://www.opentable.com/r/work-and-class-denver'
            },
            'social': {
                'website': 'https://workandclassdenver.com'
            }
        },
        'fogo-de-chão': {
            'price_range': '$$$$',
            'contact': {
                'phone': '(303) 623-4623',
                'address': '1513 Wynkoop St, Denver, CO 80202',
                'formatted_address': '1513 Wynkoop St, Denver, CO 80202'
            },
            'reservations': {
                'platform': 'OpenTable',
                'url': 'https://www.opentable.com/r/fogo-de-chao-denver'
            },
            'social': {
                'website': 'https://fogodechao.com/location/denver/'
            }
        },
        'mercantile': {
            'price_range': '$$',
            'contact': {
                'phone': '(720) 460-3733',
                'address': '1701 Wynkoop St, Denver, CO 80202',
                'formatted_address': '1701 Wynkoop St, Denver, CO 80202'
            },
            'reservations': {
                'platform': 'OpenTable',
                'url': 'https://www.opentable.com/r/mercantile-denver'
            },
            'social': {
                'website': 'https://www.mercantiledenver.com'
            }
        },
        'ultreia': {
            'price_range': '$$$',
            'contact': {
                'phone': '(303) 993-9933',
                'address': '1970 17th St, Denver, CO 80202',
                'formatted_address': '1970 17th St, Denver, CO 80202'
            },
            'reservations': {
                'platform': 'Resy',
                'url': 'https://resy.com/cities/denver/ultreia'
            },
            'social': {
                'website': 'https://ultreiadenver.com'
            }
        },
        'sunday-vinyl': {
            'cuisine': 'Cocktail Bar',
            'price_range': '$$',
            'contact': {
                'phone': '(303) 955-1515',
                'address': '1803 16th St, Denver, CO 80202',
                'formatted_address': '1803 16th St, Denver, CO 80202'
            },
            'social': {
                'website': 'https://www.sundayvinyl.com'
            }
        },
        'sushi-rama': {
            'price_range': '$$',
            'contact': {
                'phone': '(303) 295-1292',
                'address': '2615 Larimer St, Denver, CO 80205',
                'formatted_address': '2615 Larimer St, Denver, CO 80205'
            },
            'reservations': {
                'platform': 'OpenTable',
                'url': 'https://www.opentable.com/r/sushi-rama-rino-denver'
            },
            'social': {
                'website': 'https://sushi-rama.com'
            }
        },
        'a5-steakhouse': {
            'cuisine': 'Steakhouse',
            'price_range': '$$$$',
            'contact': {
                'phone': '(303) 623-2999',
                'address': '1600 15th St, Denver, CO 80202',
                'formatted_address': '1600 15th St, Denver, CO 80202'
            },
            'reservations': {
                'platform': 'OpenTable',
                'url': 'https://www.opentable.com/r/a5-prime-steakhouse'
            },
            'social': {
                'website': 'https://www.a5denver.com'
            }
        },
        'thirsty-lion': {
            'cuisine': 'American',
            'price_range': '$$',
            'contact': {
                'phone': '(720) 524-3030',
                'address': '1605 Wynkoop St, Denver, CO 80202',
                'formatted_address': '1605 Wynkoop St, Denver, CO 80202'
            },
            'reservations': {
                'platform': 'OpenTable',
                'url': 'https://www.opentable.com/r/thirsty-lion-denver'
            },
            'social': {
                'website': 'https://www.thirstylionrestaurant.com/colorado'
            }
        }
    }
    
    # Apply enrichments
    enriched_count = 0
    for slug, enrichment in enrichments.items():
        if slug in data['restaurants']:
            restaurant = data['restaurants'][slug]
            
            # Merge enrichment data
            for key, value in enrichment.items():
                if key == 'contact':
                    # Merge contact info
                    if 'contact' not in restaurant:
                        restaurant['contact'] = {}
                    restaurant['contact'].update(value)
                elif key == 'address':
                    # Update address if not present
                    if not restaurant.get('address'):
                        restaurant['address'] = value
                else:
                    # Update other fields
                    restaurant[key] = value
            
            enriched_count += 1
            print(f"✅ Enriched {restaurant['name']} ({slug})")
    
    # Update metadata
    data['metadata']['enriched_at'] = datetime.now().isoformat()
    data['metadata']['enrichment_summary'] = {
        'restaurants_enriched': enriched_count,
        'data_added': ['contact_info', 'price_ranges', 'reservation_links', 'phone_numbers']
    }
    
    # Save enriched dataset
    output_file = 'data/cache/lodo_union_station_enriched.json'
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"\n💾 Saved enriched dataset: {output_file}")
    print(f"📊 Enrichment Summary:")
    print(f"   • Restaurants enriched: {enriched_count}/14 Union Station restaurants")
    
    # Analyze final data quality
    total_restaurants = len(data['restaurants'])
    with_phone = len([r for r in data['restaurants'].values() if r.get('contact', {}).get('phone')])
    with_reservations = len([r for r in data['restaurants'].values() if r.get('reservations', {}).get('url')])
    with_price_range = len([r for r in data['restaurants'].values() if r.get('price_range')])
    
    print(f"\n📋 Final Data Quality:")
    print(f"   • Restaurants with phone numbers: {with_phone}/{total_restaurants} ({with_phone/total_restaurants*100:.1f}%)")
    print(f"   • Restaurants with reservations: {with_reservations}/{total_restaurants} ({with_reservations/total_restaurants*100:.1f}%)")
    print(f"   • Restaurants with price ranges: {with_price_range}/{total_restaurants} ({with_price_range/total_restaurants*100:.1f}%)")
    
    print(f"\n🎯 Ready for discovery and demo creation!")
    
    return output_file


if __name__ == '__main__':
    enrich_union_station_data()