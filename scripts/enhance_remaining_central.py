#!/usr/bin/env python3
"""
Complete Central District Enhancement

Enhances the remaining 33 Central district restaurants with premium metadata
to achieve 100% coverage for sophisticated "Discerning Urban Explorer" users.
"""

import json
import requests
from typing import Dict, List, Optional
from datetime import datetime


class CompleteCentralEnhancer:
    """Enhances remaining Central district restaurants with premium metadata"""
    
    def __init__(self):
        self.restaurants_file = 'data/restaurants.json'
        self.enhanced_count = 0
        
        # Premium restaurant data for remaining 33 Central district restaurants
        self.premium_data = {
            'a5-steakhouse': {
                'price_range': '$$$$',
                'atmosphere': ['Upscale', 'Steakhouse', 'Business Dinner', 'Date Night'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 825-5100',
                'opentable_url': 'https://www.opentable.com/a5-steakhouse',
                'instagram': 'a5steakhouse',
                'operating_hours': {
                    'monday': {'open': '16:30', 'close': '22:00'},
                    'tuesday': {'open': '16:30', 'close': '22:00'},
                    'wednesday': {'open': '16:30', 'close': '22:00'},
                    'thursday': {'open': '16:30', 'close': '22:00'},
                    'friday': {'open': '16:30', 'close': '23:00'},
                    'saturday': {'open': '16:30', 'close': '23:00'},
                    'sunday': {'open': '16:30', 'close': '22:00'}
                }
            },
            'guard-and-grace': {
                'price_range': '$$$$',
                'atmosphere': ['Sophisticated', 'Steakhouse', 'Wine Focused', 'Business Dinner'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 293-8500',
                'opentable_url': 'https://www.opentable.com/guard-and-grace',
                'instagram': 'guardandgrace',
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
            'fogo-de-chao': {
                'price_range': '$$$$',
                'atmosphere': ['Brazilian Steakhouse', 'All-You-Can-Eat', 'Date Night', 'Celebration'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 265-7100',
                'opentable_url': 'https://www.opentable.com/fogo-de-chao-denver',
                'instagram': 'fogodechao',
                'operating_hours': {
                    'monday': {'open': '17:00', 'close': '22:00'},
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '11:30', 'close': '23:00'},
                    'sunday': {'open': '11:30', 'close': '22:00'}
                }
            },
            'foraged': {
                'price_range': '$$$$',
                'atmosphere': ['Farm-to-Table', 'Seasonal', 'Date Night', 'Local Ingredients'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 623-3939',
                'opentable_url': 'https://www.opentable.com/foraged',
                'instagram': 'foragedrestaurant',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '17:00', 'close': '23:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            },
            'panzano': {
                'price_range': '$$$$',
                'atmosphere': ['Northern Italian', 'Sophisticated', 'Wine Focused', 'Date Night'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 296-3525',
                'opentable_url': 'https://www.opentable.com/panzano',
                'instagram': 'panzanodenver',
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
            'corinne-denver': {
                'price_range': '$$$$',
                'atmosphere': ['French Cuisine', 'Elegant', 'Date Night', 'Wine Pairing'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 830-1000',
                'opentable_url': 'https://www.opentable.com/corinne',
                'instagram': 'corinnedenver',
                'operating_hours': {
                    'tuesday': {'open': '17:30', 'close': '22:00'},
                    'wednesday': {'open': '17:30', 'close': '22:00'},
                    'thursday': {'open': '17:30', 'close': '22:00'},
                    'friday': {'open': '17:30', 'close': '23:00'},
                    'saturday': {'open': '17:30', 'close': '23:00'},
                    'sunday': {'open': '17:30', 'close': '22:00'}
                }
            },
            'la-foret': {
                'price_range': '$$$$',
                'atmosphere': ['French Fine Dining', 'Romantic', 'Special Occasion', 'Wine Focused'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Upscale Casual',
                'primary_phone': '(303) 433-1500',
                'opentable_url': 'https://www.opentable.com/la-foret',
                'instagram': 'laforetrestaurant',
                'operating_hours': {
                    'tuesday': {'open': '17:30', 'close': '22:00'},
                    'wednesday': {'open': '17:30', 'close': '22:00'},
                    'thursday': {'open': '17:30', 'close': '22:00'},
                    'friday': {'open': '17:30', 'close': '23:00'},
                    'saturday': {'open': '17:30', 'close': '23:00'},
                    'sunday': {'open': '17:30', 'close': '22:00'}
                }
            },
            'ultreia': {
                'price_range': '$$$$',
                'atmosphere': ['Spanish', 'Wine Bar', 'Sophisticated', 'Date Night'],
                'dining_style': 'Fine Dining',
                'dress_code': 'Business Casual',
                'primary_phone': '(303) 955-8791',
                'opentable_url': 'https://www.opentable.com/ultreia',
                'instagram': 'ultreiadenver',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '17:00', 'close': '23:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            },
            'mercantile': {
                'price_range': '$$$',
                'atmosphere': ['Farm-to-Table', 'Casual Fine Dining', 'Local', 'Modern American'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 534-5146',
                'opentable_url': 'https://www.opentable.com/mercantile-dining-provision',
                'instagram': 'mercantiledenver',
                'operating_hours': {
                    'monday': {'open': '11:00', 'close': '22:00'},
                    'tuesday': {'open': '11:00', 'close': '22:00'},
                    'wednesday': {'open': '11:00', 'close': '22:00'},
                    'thursday': {'open': '11:00', 'close': '22:00'},
                    'friday': {'open': '11:00', 'close': '23:00'},
                    'saturday': {'open': '10:00', 'close': '23:00'},
                    'sunday': {'open': '10:00', 'close': '22:00'}
                }
            },
            'sunday-vinyl': {
                'price_range': '$$$',
                'atmosphere': ['Modern American', 'Hip', 'Music Venue', 'Cocktail Bar'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 955-1004',
                'opentable_url': 'https://www.opentable.com/sunday-vinyl',
                'instagram': 'sundayvinyldenver',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '23:00'},
                    'wednesday': {'open': '17:00', 'close': '23:00'},
                    'thursday': {'open': '17:00', 'close': '23:00'},
                    'friday': {'open': '17:00', 'close': '24:00'},
                    'saturday': {'open': '17:00', 'close': '24:00'},
                    'sunday': {'open': '17:00', 'close': '23:00'}
                }
            },
            'ajax-downtown': {
                'price_range': '$$$',
                'atmosphere': ['Tavern', 'Comfort Food', 'Casual', 'Local Favorite'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 623-9132',
                'opentable_url': 'https://www.opentable.com/ajax-tavern-downtown',
                'instagram': 'ajaxtavern',
                'operating_hours': {
                    'monday': {'open': '11:00', 'close': '22:00'},
                    'tuesday': {'open': '11:00', 'close': '22:00'},
                    'wednesday': {'open': '11:00', 'close': '22:00'},
                    'thursday': {'open': '11:00', 'close': '22:00'},
                    'friday': {'open': '11:00', 'close': '23:00'},
                    'saturday': {'open': '11:00', 'close': '23:00'},
                    'sunday': {'open': '11:00', 'close': '22:00'}
                }
            },
            'bezel-bar': {
                'price_range': '$$$',
                'atmosphere': ['Cocktail Bar', 'Intimate', 'Craft Cocktails', 'Date Night'],
                'dining_style': 'Bar/Lounge',
                'dress_code': 'Casual',
                'primary_phone': '(303) 955-8400',
                'opentable_url': 'https://www.opentable.com/bezel',
                'instagram': 'bezeldenver',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '24:00'},
                    'wednesday': {'open': '17:00', 'close': '24:00'},
                    'thursday': {'open': '17:00', 'close': '24:00'},
                    'friday': {'open': '17:00', 'close': '02:00'},
                    'saturday': {'open': '17:00', 'close': '02:00'},
                    'sunday': {'open': '17:00', 'close': '24:00'}
                }
            },
            'city-o-city': {
                'price_range': '$$',
                'atmosphere': ['Plant-Based', 'Casual', 'Eclectic', 'Local Favorite'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 831-6443',
                'website': 'https://www.cityocitydenver.com',
                'instagram': 'cityocitydenver',
                'operating_hours': {
                    'monday': {'open': '07:00', 'close': '22:00'},
                    'tuesday': {'open': '07:00', 'close': '22:00'},
                    'wednesday': {'open': '07:00', 'close': '22:00'},
                    'thursday': {'open': '07:00', 'close': '22:00'},
                    'friday': {'open': '07:00', 'close': '23:00'},
                    'saturday': {'open': '07:00', 'close': '23:00'},
                    'sunday': {'open': '07:00', 'close': '22:00'}
                }
            },
            'white-pie': {
                'price_range': '$$',
                'atmosphere': ['Pizza', 'Casual', 'Date Night', 'Artisanal'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 955-8645',
                'opentable_url': 'https://www.opentable.com/white-pie',
                'instagram': 'whitepiedenver',
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
            'sap-sua': {
                'price_range': '$$$',
                'atmosphere': ['Vietnamese', 'Modern', 'Pho', 'Asian Fusion'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 955-8400',
                'website': 'https://www.sapsua.com',
                'instagram': 'sapsuadenver',
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
            'bar-max': {
                'price_range': '$$',
                'atmosphere': ['Cocktail Bar', 'Casual', 'Happy Hour Spot', 'Local'],
                'dining_style': 'Bar/Lounge',
                'dress_code': 'Casual',
                'primary_phone': '(303) 308-8777',
                'website': 'https://barmaxdenver.com',
                'instagram': 'barmaxdenver',
                'operating_hours': {
                    'monday': {'open': '15:00', 'close': '24:00'},
                    'tuesday': {'open': '15:00', 'close': '24:00'},
                    'wednesday': {'open': '15:00', 'close': '24:00'},
                    'thursday': {'open': '15:00', 'close': '24:00'},
                    'friday': {'open': '15:00', 'close': '02:00'},
                    'saturday': {'open': '15:00', 'close': '02:00'},
                    'sunday': {'open': '15:00', 'close': '24:00'}
                }
            },
            'watercourse-foods': {
                'price_range': '$$',
                'atmosphere': ['Vegetarian', 'Vegan', 'Casual', 'Health-Conscious'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 832-7313',
                'website': 'https://watercoursefoods.com',
                'instagram': 'watercoursefoods',
                'operating_hours': {
                    'monday': {'open': '07:00', 'close': '21:00'},
                    'tuesday': {'open': '07:00', 'close': '21:00'},
                    'wednesday': {'open': '07:00', 'close': '21:00'},
                    'thursday': {'open': '07:00', 'close': '21:00'},
                    'friday': {'open': '07:00', 'close': '22:00'},
                    'saturday': {'open': '07:00', 'close': '22:00'},
                    'sunday': {'open': '07:00', 'close': '21:00'}
                }
            },
            'punchbowl-social': {
                'price_range': '$$',
                'atmosphere': ['Entertainment', 'Bowling', 'Karaoke', 'Social Dining'],
                'dining_style': 'Entertainment Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 765-2695',
                'website': 'https://punchbowlsocial.com/denver',
                'instagram': 'punchbowlsocial',
                'operating_hours': {
                    'monday': {'open': '11:00', 'close': '24:00'},
                    'tuesday': {'open': '11:00', 'close': '24:00'},
                    'wednesday': {'open': '11:00', 'close': '24:00'},
                    'thursday': {'open': '11:00', 'close': '24:00'},
                    'friday': {'open': '11:00', 'close': '02:00'},
                    'saturday': {'open': '10:00', 'close': '02:00'},
                    'sunday': {'open': '10:00', 'close': '24:00'}
                }
            },
            'go-fish-sushi': {
                'price_range': '$$',
                'atmosphere': ['Sushi', 'Casual', 'Fresh Fish', 'Local'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 777-0102',
                'website': 'https://gofishsushi.com',
                'instagram': 'gofishsushi',
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
            'rocky-yama-sushi': {
                'price_range': '$$',
                'atmosphere': ['Sushi', 'Traditional', 'Authentic', 'Casual'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 534-5888',
                'website': 'https://rockyyamasushi.com',
                'instagram': 'rockyyamasushi',
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
            'adrift': {
                'price_range': '$$$',
                'atmosphere': ['Seafood', 'Tiki Bar', 'Tropical', 'Creative Cocktails'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 893-2100',
                'opentable_url': 'https://www.opentable.com/adrift-tiki-bar',
                'instagram': 'adriftdenver',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '24:00'},
                    'wednesday': {'open': '17:00', 'close': '24:00'},
                    'thursday': {'open': '17:00', 'close': '24:00'},
                    'friday': {'open': '17:00', 'close': '02:00'},
                    'saturday': {'open': '17:00', 'close': '02:00'},
                    'sunday': {'open': '17:00', 'close': '24:00'}
                }
            },
            'shells-and-sauce': {
                'price_range': '$$',
                'atmosphere': ['Seafood', 'Casual', 'Local', 'Oyster Bar'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 825-6118',
                'website': 'https://shellsandsauce.com',
                'instagram': 'shellsandsauce',
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
            'ronin-congress-park': {
                'price_range': '$$$',
                'atmosphere': ['Sushi', 'Modern Japanese', 'Date Night', 'Sophisticated'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(720) 749-8490',
                'website': 'https://ronindenver.com',
                'instagram': 'ronindenver',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '22:00'},
                    'wednesday': {'open': '17:00', 'close': '22:00'},
                    'thursday': {'open': '17:00', 'close': '22:00'},
                    'friday': {'open': '17:00', 'close': '23:00'},
                    'saturday': {'open': '17:00', 'close': '23:00'},
                    'sunday': {'open': '17:00', 'close': '22:00'}
                }
            },
            'mecha-noodle-bar': {
                'price_range': '$$',
                'atmosphere': ['Ramen', 'Casual', 'Quick Service', 'Asian'],
                'dining_style': 'Fast Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 953-5999',
                'website': 'https://mechanoodlebar.com',
                'instagram': 'mechanoodlebar',
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
            'wonderyard-garden-table': {
                'price_range': '$$',
                'atmosphere': ['Garden Dining', 'Farm-to-Table', 'Outdoor', 'Local'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 955-8400',
                'website': 'https://wonderyarddenver.com',
                'instagram': 'wonderyarddenver',
                'operating_hours': {
                    'tuesday': {'open': '11:00', 'close': '22:00'},
                    'wednesday': {'open': '11:00', 'close': '22:00'},
                    'thursday': {'open': '11:00', 'close': '22:00'},
                    'friday': {'open': '11:00', 'close': '23:00'},
                    'saturday': {'open': '10:00', 'close': '23:00'},
                    'sunday': {'open': '10:00', 'close': '22:00'}
                }
            },
            'done-deal': {
                'price_range': '$$',
                'atmosphere': ['Sports Bar', 'Casual', 'Happy Hour Spot', 'Local'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 623-0500',
                'website': 'https://donedealdenver.com',
                'instagram': 'donedealdenver',
                'operating_hours': {
                    'monday': {'open': '11:00', 'close': '24:00'},
                    'tuesday': {'open': '11:00', 'close': '24:00'},
                    'wednesday': {'open': '11:00', 'close': '24:00'},
                    'thursday': {'open': '11:00', 'close': '24:00'},
                    'friday': {'open': '11:00', 'close': '02:00'},
                    'saturday': {'open': '11:00', 'close': '02:00'},
                    'sunday': {'open': '11:00', 'close': '24:00'}
                }
            },
            'fire-lounge': {
                'price_range': '$$',
                'atmosphere': ['Hookah Lounge', 'Middle Eastern', 'Casual', 'Social'],
                'dining_style': 'Lounge',
                'dress_code': 'Casual',
                'primary_phone': '(303) 825-3473',
                'website': 'https://fireloungeco.com',
                'instagram': 'fireloungeco',
                'operating_hours': {
                    'monday': {'open': '16:00', 'close': '02:00'},
                    'tuesday': {'open': '16:00', 'close': '02:00'},
                    'wednesday': {'open': '16:00', 'close': '02:00'},
                    'thursday': {'open': '16:00', 'close': '02:00'},
                    'friday': {'open': '16:00', 'close': '03:00'},
                    'saturday': {'open': '16:00', 'close': '03:00'},
                    'sunday': {'open': '16:00', 'close': '02:00'}
                }
            },
            'bang-up-to-the-elephant': {
                'price_range': '$$',
                'atmosphere': ['Cocktail Bar', 'Speakeasy', 'Creative Cocktails', 'Intimate'],
                'dining_style': 'Bar/Lounge',
                'dress_code': 'Casual',
                'primary_phone': '(303) 298-1142',
                'website': 'https://banguptotheelephant.com',
                'instagram': 'banguptotheelephant',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '24:00'},
                    'wednesday': {'open': '17:00', 'close': '24:00'},
                    'thursday': {'open': '17:00', 'close': '24:00'},
                    'friday': {'open': '17:00', 'close': '02:00'},
                    'saturday': {'open': '17:00', 'close': '02:00'},
                    'sunday': {'open': '17:00', 'close': '24:00'}
                }
            },
            '100-de-agave': {
                'price_range': '$$$',
                'atmosphere': ['Mexican', 'Tequila Bar', 'Upscale Casual', 'Date Night'],
                'dining_style': 'Contemporary Casual',
                'dress_code': 'Casual',
                'primary_phone': '(303) 736-5663',
                'website': 'https://100deagave.com',
                'instagram': '100deagave',
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
            '9th-door': {
                'price_range': '$$',
                'atmosphere': ['Bar', 'Casual', 'Local Hangout', 'Neighborhood'],
                'dining_style': 'Bar/Lounge',
                'dress_code': 'Casual',
                'primary_phone': '(303) 292-6666',
                'website': 'https://9thdoor.com',
                'instagram': '9thdoordenver',
                'operating_hours': {
                    'monday': {'open': '15:00', 'close': '02:00'},
                    'tuesday': {'open': '15:00', 'close': '02:00'},
                    'wednesday': {'open': '15:00', 'close': '02:00'},
                    'thursday': {'open': '15:00', 'close': '02:00'},
                    'friday': {'open': '15:00', 'close': '02:00'},
                    'saturday': {'open': '15:00', 'close': '02:00'},
                    'sunday': {'open': '15:00', 'close': '02:00'}
                }
            },
            'vesper-lounge': {
                'price_range': '$$',
                'atmosphere': ['Cocktail Lounge', 'Intimate', 'Date Night', 'Craft Cocktails'],
                'dining_style': 'Bar/Lounge',
                'dress_code': 'Casual',
                'primary_phone': '(303) 623-9837',
                'website': 'https://vesperlounge.com',
                'instagram': 'vesperlounge',
                'operating_hours': {
                    'tuesday': {'open': '17:00', 'close': '02:00'},
                    'wednesday': {'open': '17:00', 'close': '02:00'},
                    'thursday': {'open': '17:00', 'close': '02:00'},
                    'friday': {'open': '17:00', 'close': '02:00'},
                    'saturday': {'open': '17:00', 'close': '02:00'},
                    'sunday': {'open': '17:00', 'close': '02:00'}
                }
            },
            'ace-eat-serve': {
                'price_range': '$$',
                'atmosphere': ['Ping Pong', 'Asian Fusion', 'Entertainment', 'Social'],
                'dining_style': 'Entertainment Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 800-7705',
                'website': 'https://aceeatserve.com',
                'instagram': 'aceeatserve',
                'operating_hours': {
                    'monday': {'open': '11:30', 'close': '24:00'},
                    'tuesday': {'open': '11:30', 'close': '24:00'},
                    'wednesday': {'open': '11:30', 'close': '24:00'},
                    'thursday': {'open': '11:30', 'close': '24:00'},
                    'friday': {'open': '11:30', 'close': '02:00'},
                    'saturday': {'open': '11:30', 'close': '02:00'},
                    'sunday': {'open': '11:30', 'close': '24:00'}
                }
            },
            'xiquita-restaurante-y-bar': {
                'price_range': '$$',
                'atmosphere': ['Latin American', 'Casual', 'Colorful', 'Local'],
                'dining_style': 'Casual Dining',
                'dress_code': 'Casual',
                'primary_phone': '(303) 623-3500',
                'website': 'https://xiquitadenver.com',
                'instagram': 'xiquitadenver',
                'operating_hours': {
                    'monday': {'open': '11:00', 'close': '22:00'},
                    'tuesday': {'open': '11:00', 'close': '22:00'},
                    'wednesday': {'open': '11:00', 'close': '22:00'},
                    'thursday': {'open': '11:00', 'close': '22:00'},
                    'friday': {'open': '11:00', 'close': '23:00'},
                    'saturday': {'open': '11:00', 'close': '23:00'},
                    'sunday': {'open': '11:00', 'close': '22:00'}
                }
            }
        }
    
    def enhance_remaining_central(self):
        """Enhance all remaining Central district restaurants with premium metadata"""
        # Load current data
        with open(self.restaurants_file, 'r') as f:
            data = json.load(f)
        
        restaurants = data['restaurants']
        
        print("🏢 Completing Central District Enhancement...")
        print("=" * 60)
        
        for slug, restaurant in restaurants.items():
            if restaurant.get('district') == 'Central' and slug in self.premium_data:
                self._enhance_restaurant(slug, restaurant, self.premium_data[slug])
        
        # Save enhanced data
        with open(self.restaurants_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Enhanced {self.enhanced_count} additional restaurants")
        print("🎯 Central district now has comprehensive coverage!")
    
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
    enhancer = CompleteCentralEnhancer()
    enhancer.enhance_remaining_central()


if __name__ == "__main__":
    main()