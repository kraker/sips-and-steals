"""
Restaurant Profile Spider

Extracts comprehensive restaurant data from main restaurant pages:
- Contact information (phone, email, social media)
- Business information (hours, status, pricing)
- Service information (reservations, delivery)
- Address verification and enhancement

Uses our proven data-hungry approach with intelligent content analysis.
"""

import scrapy
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse

from ..items import RestaurantProfileItem


class RestaurantProfilerSpider(scrapy.Spider):
    name = 'restaurant_profiler'
    
    # Extraction patterns for comprehensive data
    
    # Phone number patterns (US format)
    PHONE_PATTERNS = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (303) 555-1234, 303-555-1234, 303.555.1234
        r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',        # 3035551234, 303 555 1234
    ]
    
    # Email patterns
    EMAIL_PATTERNS = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    ]
    
    # Social media patterns
    SOCIAL_PATTERNS = {
        'instagram': [
            r'instagram\.com/([^/\s"\']+)',
            r'@([a-zA-Z0-9_.]+)',  # @username format
        ],
        'facebook': [
            r'facebook\.com/([^/\s"\']+)',
            r'fb\.com/([^/\s"\']+)',
        ],
        'twitter': [
            r'twitter\.com/([^/\s"\']+)',
            r'x\.com/([^/\s"\']+)',
        ],
        'tiktok': [
            r'tiktok\.com/@([^/\s"\']+)',
        ]
    }
    
    # Operating hours patterns
    HOURS_PATTERNS = [
        r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)[\s:]*(\d{1,2}):?(\d{2})?\s*(am|pm)\s*[-–]\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',
        r'(mon|tue|wed|thu|fri|sat|sun)[\s:]*(\d{1,2}):?(\d{2})?\s*(am|pm)\s*[-–]\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',
        r'(\d{1,2}):?(\d{2})?\s*(am|pm)\s*[-–]\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',  # General time range
    ]
    
    # Price range indicators
    PRICE_INDICATORS = {
        '$': ['budget', 'cheap', 'under $15', '$5-', '$10-', 'affordable'],
        '$$': ['moderate', '$15-', '$20-', 'mid-range', 'reasonable'],
        '$$$': ['upscale', '$30-', '$40-', 'fine dining', 'expensive'],
        '$$$$': ['luxury', '$60+', '$70+', 'premium', 'high-end']
    }
    
    # Content sections to analyze
    CONTENT_SELECTORS = [
        'main', 'article', 'section', '.content', '#content',
        '.contact', '.hours', '.about', '.location', '.info',
        'header', 'footer', '.restaurant-info', '.contact-info',
        '.social', '.reservations', '.delivery', '.menu-info'
    ]
    
    def __init__(self, input_file='data/restaurants.json', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_file = input_file
        self.restaurants = self._load_restaurants()
        
        # Statistics tracking
        self.stats = {
            'restaurants_processed': 0,
            'profiles_extracted': 0,
            'data_fields_found': 0,
        }
    
    def _load_restaurants(self) -> List[Dict]:
        """Load restaurant data"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            restaurants = []
            restaurant_data = data.get('restaurants', {})
            
            for slug, restaurant in restaurant_data.items():
                if restaurant.get('website'):  # Only process restaurants with websites
                    restaurants.append({
                        'slug': slug,
                        'name': restaurant['name'],
                        'website': restaurant['website'],
                        'district': restaurant.get('district'),
                        'cuisine': restaurant.get('cuisine')
                    })
            
            self.logger.info(f"Loaded {len(restaurants)} restaurants with websites for profiling")
            return restaurants
            
        except FileNotFoundError:
            self.logger.error(f"Restaurant data file not found: {self.input_file}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in restaurant data file: {e}")
            return []
    
    def start_requests(self):
        """Generate requests for restaurant main pages"""
        for restaurant in self.restaurants:
            yield scrapy.Request(
                url=restaurant['website'],
                callback=self.parse_restaurant_profile,
                meta={
                    'restaurant': restaurant
                },
                errback=self.handle_error
            )
    
    def parse_restaurant_profile(self, response):
        """Extract comprehensive restaurant profile from main page"""
        restaurant = response.meta['restaurant']
        
        self.logger.info(f"Extracting profile for {restaurant['name']}: {response.url}")
        self.stats['restaurants_processed'] += 1
        
        # Extract comprehensive profile using data-hungry approach
        profile = self._extract_restaurant_profile(response, restaurant)
        
        if profile:
            self.stats['profiles_extracted'] += 1
            yield profile
        else:
            self.logger.debug(f"No profile data found for {restaurant['name']} at {response.url}")
    
    def _extract_restaurant_profile(self, response, restaurant: Dict) -> Optional[RestaurantProfileItem]:
        """Extract comprehensive restaurant profile using data-hungry approach"""
        
        # Initialize profile item
        profile = RestaurantProfileItem(
            restaurant_slug=restaurant['slug'],
            restaurant_name=restaurant['name'],
            source_url=response.url,
            scraped_at=datetime.now().isoformat(),
            extraction_method='comprehensive_profile_extraction',
            source_text_snippets=[],
            extraction_patterns=[],
            confidence_score=0.0
        )
        
        # Extract all content sections for analysis
        content_sections = self._get_content_sections(response)
        all_text = ' '.join([section[2] for section in content_sections])
        
        # Track what we found for confidence scoring
        fields_found = 0
        total_possible_fields = 25  # Approximate number of extractable fields
        
        # Extract contact information
        fields_found += self._extract_contact_info(profile, all_text, content_sections)
        
        # Extract business information
        fields_found += self._extract_business_info(profile, all_text, content_sections, response)
        
        # Extract service information
        fields_found += self._extract_service_info(profile, all_text, content_sections, response)
        
        # Extract social media
        fields_found += self._extract_social_media(profile, all_text, response)
        
        # Extract address information (to verify/enhance existing)
        fields_found += self._extract_address_info(profile, all_text, content_sections)
        
        # Calculate confidence and completeness scores
        profile['completeness_score'] = fields_found / total_possible_fields
        profile['confidence_score'] = min(0.9, profile['completeness_score'] * 1.2)  # Boost confidence slightly
        profile['data_source_quality'] = self._assess_content_quality(all_text)
        
        self.stats['data_fields_found'] += fields_found
        
        # Only return profile if we found meaningful data
        if fields_found > 0:
            return profile
        
        return None
    
    def _get_content_sections(self, response) -> List[Tuple[str, str, str]]:
        """Extract content sections for analysis"""
        sections = []
        
        for selector in self.CONTENT_SELECTORS:
            elements = response.css(selector)
            for element in elements[:5]:  # Limit to prevent too much data
                html_content = element.get()
                text_content = ' '.join(element.css('::text').getall()).strip()
                
                if text_content and len(text_content) > 20:
                    sections.append((selector, html_content, text_content))
        
        return sections
    
    def _extract_contact_info(self, profile: RestaurantProfileItem, all_text: str, 
                            content_sections: List[Tuple]) -> int:
        """Extract contact information (phone, email)"""
        found_count = 0
        
        # Extract phone numbers
        phones = []
        for pattern in self.PHONE_PATTERNS:
            matches = re.findall(pattern, all_text)
            phones.extend(matches)
        
        if phones:
            # Clean and deduplicate phone numbers
            cleaned_phones = list(set([self._clean_phone(phone) for phone in phones]))
            
            if cleaned_phones:
                profile['primary_phone'] = cleaned_phones[0]
                found_count += 1
                profile['extraction_patterns'].append('phone_extraction')
                
                # Look for reservation-specific phones
                for section_selector, html, text in content_sections:
                    if any(word in text.lower() for word in ['reservation', 'booking', 'table']):
                        reservation_phones = []
                        for pattern in self.PHONE_PATTERNS:
                            reservation_phones.extend(re.findall(pattern, text))
                        if reservation_phones:
                            profile['reservation_phone'] = self._clean_phone(reservation_phones[0])
                            found_count += 1
                            break
        
        # Extract email addresses
        emails = []
        for pattern in self.EMAIL_PATTERNS:
            matches = re.findall(pattern, all_text)
            emails.extend(matches)
        
        if emails:
            cleaned_emails = list(set([email.lower() for email in emails]))
            
            # Categorize emails
            for email in cleaned_emails:
                if any(word in email for word in ['info', 'hello', 'contact', 'general']):
                    profile['general_email'] = email
                    found_count += 1
                elif any(word in email for word in ['reservation', 'booking', 'table']):
                    profile['reservations_email'] = email
                    found_count += 1
                elif any(word in email for word in ['event', 'party', 'private']):
                    profile['events_email'] = email
                    found_count += 1
                elif not profile.get('general_email'):
                    profile['general_email'] = email
                    found_count += 1
                
                profile['extraction_patterns'].append('email_extraction')
        
        return found_count
    
    def _extract_business_info(self, profile: RestaurantProfileItem, all_text: str,
                             content_sections: List[Tuple], response) -> int:
        """Extract business information (hours, status, pricing)"""
        found_count = 0
        
        # Extract operating hours
        hours_data = self._extract_operating_hours(all_text, content_sections)
        if hours_data:
            profile['operating_hours'] = hours_data
            found_count += 1
            profile['extraction_patterns'].append('hours_extraction')
        
        # Detect business status
        status_indicators = {
            'temporarily_closed': ['temporarily closed', 'closed temporarily', 'reopening soon'],
            'permanently_closed': ['permanently closed', 'closed permanently', 'no longer open']
        }
        
        text_lower = all_text.lower()
        for status, indicators in status_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                profile['business_status'] = status
                found_count += 1
                profile['extraction_patterns'].append('business_status_detection')
                break
        else:
            profile['business_status'] = 'operational'  # Default assumption
        
        # Extract price range indicators
        for price_level, indicators in self.PRICE_INDICATORS.items():
            if any(indicator in text_lower for indicator in indicators):
                profile['price_range'] = price_level
                found_count += 1
                profile['extraction_patterns'].append('price_range_detection')
                break
        
        # Extract atmosphere keywords
        atmosphere_keywords = {
            'romantic': ['romantic', 'intimate', 'date night', 'couples'],
            'family_friendly': ['family', 'kids', 'children', 'family-friendly'],
            'lively': ['lively', 'energetic', 'vibrant', 'bustling'],
            'casual': ['casual', 'relaxed', 'laid-back', 'informal'],
            'upscale': ['upscale', 'elegant', 'sophisticated', 'refined']
        }
        
        atmosphere = []
        for mood, keywords in atmosphere_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                atmosphere.append(mood)
        
        if atmosphere:
            profile['atmosphere'] = atmosphere
            found_count += 1
            profile['extraction_patterns'].append('atmosphere_detection')
        
        return found_count
    
    def _extract_service_info(self, profile: RestaurantProfileItem, all_text: str,
                            content_sections: List[Tuple], response) -> int:
        """Extract service information (reservations, delivery)"""
        found_count = 0
        text_lower = all_text.lower()
        
        # Check for reservation services
        reservation_services = {
            'opentable_url': ['opentable.com', 'open table'],
            'resy_url': ['resy.com'],
            'direct_reservation_url': ['reserve', 'booking', 'reservation']
        }
        
        # Look for reservation links in HTML
        reservation_links = response.css('a[href*="opentable"], a[href*="resy"], a[href*="reservation"]')
        for link in reservation_links:
            href = link.attrib.get('href', '')
            if 'opentable' in href:
                profile['opentable_url'] = urljoin(response.url, href)
                profile['accepts_reservations'] = True
                found_count += 2
            elif 'resy' in href:
                profile['resy_url'] = urljoin(response.url, href)
                profile['accepts_reservations'] = True
                found_count += 2
            elif 'reservation' in href or 'booking' in href:
                profile['direct_reservation_url'] = urljoin(response.url, href)
                profile['accepts_reservations'] = True
                found_count += 2
        
        # Check for delivery services
        delivery_services = {
            'doordash_url': ['doordash', 'door dash'],
            'ubereats_url': ['uber eats', 'ubereats'],
            'grubhub_url': ['grubhub', 'grub hub']
        }
        
        # Look for delivery links
        delivery_links = response.css('a[href*="doordash"], a[href*="ubereats"], a[href*="grubhub"]')
        for link in delivery_links:
            href = link.attrib.get('href', '')
            if 'doordash' in href:
                profile['doordash_url'] = href
                profile['offers_delivery'] = True
                found_count += 2
            elif 'uber' in href:
                profile['ubereats_url'] = href
                profile['offers_delivery'] = True
                found_count += 2
            elif 'grubhub' in href:
                profile['grubhub_url'] = href
                profile['offers_delivery'] = True
                found_count += 2
        
        # Check for general service mentions
        if any(word in text_lower for word in ['delivery', 'deliver']):
            if not profile.get('offers_delivery'):
                profile['offers_delivery'] = True
                found_count += 1
        
        if any(word in text_lower for word in ['takeout', 'take out', 'pickup', 'take away']):
            profile['offers_takeout'] = True
            found_count += 1
        
        if any(word in text_lower for word in ['curbside', 'curb side']):
            profile['offers_curbside'] = True
            found_count += 1
        
        if found_count > 0:
            profile['extraction_patterns'].append('service_info_detection')
        
        return found_count
    
    def _extract_social_media(self, profile: RestaurantProfileItem, all_text: str, response) -> int:
        """Extract social media handles and URLs"""
        found_count = 0
        
        # Look for social media links in HTML
        social_links = response.css('a[href*="instagram"], a[href*="facebook"], a[href*="twitter"], a[href*="tiktok"]')
        
        for link in social_links:
            href = link.attrib.get('href', '')
            
            for platform, patterns in self.SOCIAL_PATTERNS.items():
                for pattern in patterns:
                    match = re.search(pattern, href)
                    if match:
                        username = match.group(1) if match.groups() else match.group()
                        # Clean username (remove @ and trailing slashes)
                        username = username.strip('@/').split('?')[0].split('#')[0]
                        if username and not profile.get(platform):
                            profile[platform] = username
                            found_count += 1
                        break
        
        # Also check text content for @mentions
        for platform, patterns in self.SOCIAL_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, all_text)
                if matches and not profile.get(platform):
                    username = matches[0].strip('@/').split('?')[0].split('#')[0]
                    if username:
                        profile[platform] = username
                        found_count += 1
                    break
        
        if found_count > 0:
            profile['extraction_patterns'].append('social_media_extraction')
        
        return found_count
    
    def _extract_address_info(self, profile: RestaurantProfileItem, all_text: str,
                            content_sections: List[Tuple]) -> int:
        """Extract and verify address information"""
        found_count = 0
        
        # Look for address patterns
        address_patterns = [
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Place|Pl)',
            r'\d+\s+[A-Za-z\s]+,\s*Denver',
        ]
        
        addresses = []
        for pattern in address_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            addresses.extend(matches)
        
        if addresses:
            # Take the first/most complete address found
            address = addresses[0].strip()
            profile['street_address'] = address
            found_count += 1
            profile['extraction_patterns'].append('address_extraction')
        
        # Look for city, state, zip
        if 'denver' in all_text.lower():
            profile['city'] = 'Denver'
            found_count += 1
        
        if re.search(r'\bco\b|\bcolorado\b', all_text, re.IGNORECASE):
            profile['state'] = 'CO'
            found_count += 1
        
        zip_matches = re.findall(r'\b80\d{3}\b', all_text)
        if zip_matches:
            profile['zip_code'] = zip_matches[0]
            found_count += 1
        
        return found_count
    
    def _extract_operating_hours(self, all_text: str, content_sections: List[Tuple]) -> Optional[Dict]:
        """Extract operating hours from content"""
        hours_data = {}
        
        # Look for hours in dedicated sections first
        for section_selector, html, text in content_sections:
            if any(word in section_selector.lower() for word in ['hour', 'time']) or \
               any(word in text.lower() for word in ['hours', 'open', 'closed']):
                
                # Try to extract day-specific hours
                day_hours = self._parse_hours_text(text)
                if day_hours:
                    hours_data.update(day_hours)
        
        # If no specific hours found, try general text
        if not hours_data:
            hours_data = self._parse_hours_text(all_text)
        
        return hours_data if hours_data else None
    
    def _parse_hours_text(self, text: str) -> Dict[str, Dict[str, str]]:
        """Parse hours text into structured format"""
        hours = {}
        
        # Simple pattern matching for common formats
        day_mappings = {
            'monday': 'monday', 'mon': 'monday',
            'tuesday': 'tuesday', 'tue': 'tuesday', 'tues': 'tuesday',
            'wednesday': 'wednesday', 'wed': 'wednesday',
            'thursday': 'thursday', 'thu': 'thursday', 'thur': 'thursday', 'thurs': 'thursday',
            'friday': 'friday', 'fri': 'friday',
            'saturday': 'saturday', 'sat': 'saturday',
            'sunday': 'sunday', 'sun': 'sunday'
        }
        
        # Look for patterns like "Monday 11:00 AM - 10:00 PM"
        for pattern in self.HOURS_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                groups = match.groups()
                if len(groups) >= 6:
                    day_text = groups[0].lower()
                    if day_text in day_mappings:
                        day = day_mappings[day_text]
                        
                        # Parse opening time
                        open_hour = int(groups[1])
                        open_min = groups[2] if groups[2] else '00'
                        open_ampm = groups[3].upper()
                        
                        # Parse closing time
                        close_hour = int(groups[4])
                        close_min = groups[5] if groups[5] else '00'
                        close_ampm = groups[6].upper()
                        
                        # Convert to 24-hour format
                        open_24 = self._convert_to_24h(open_hour, open_min, open_ampm)
                        close_24 = self._convert_to_24h(close_hour, close_min, close_ampm)
                        
                        if open_24 and close_24:
                            hours[day] = {
                                'open': open_24,
                                'close': close_24
                            }
        
        return hours
    
    def _convert_to_24h(self, hour: int, minute: str, ampm: str) -> Optional[str]:
        """Convert 12-hour time to 24-hour format"""
        try:
            hour = int(hour)
            minute = int(minute)
            
            if ampm == 'PM' and hour != 12:
                hour += 12
            elif ampm == 'AM' and hour == 12:
                hour = 0
            
            return f"{hour:02d}:{minute:02d}"
        except (ValueError, TypeError):
            return None
    
    def _clean_phone(self, phone: str) -> str:
        """Clean and format phone number"""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Format as (XXX) XXX-XXXX if we have 10 digits
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            # Remove leading 1
            digits = digits[1:]
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        
        return phone  # Return original if we can't format
    
    def _assess_content_quality(self, text: str) -> float:
        """Assess the quality of the source content"""
        if not text:
            return 0.0
        
        # Basic quality indicators
        quality_score = 0.5  # Base score
        
        # Length indicator
        if len(text) > 1000:
            quality_score += 0.2
        
        # Contact info presence
        if re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', text):
            quality_score += 0.1
        
        # Address presence  
        if re.search(r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave)', text, re.IGNORECASE):
            quality_score += 0.1
        
        # Hours presence
        if any(word in text.lower() for word in ['hours', 'open', 'monday', 'tuesday']):
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    
    def handle_error(self, failure):
        """Handle request errors"""
        request = failure.request
        restaurant_slug = request.meta.get('restaurant', {}).get('slug', 'unknown')
        
        self.logger.warning(f"Failed to extract profile from {request.url} for {restaurant_slug}: {failure.value}")
    
    def closed(self, reason):
        """Spider closing callback - log statistics"""
        self.logger.info(f"Restaurant profiler spider closed: {reason}")
        self.logger.info(f"Statistics: {self.stats}")
        
        success_rate = (self.stats['profiles_extracted'] / self.stats['restaurants_processed'] * 100) if self.stats['restaurants_processed'] > 0 else 0
        avg_fields = (self.stats['data_fields_found'] / self.stats['profiles_extracted']) if self.stats['profiles_extracted'] > 0 else 0
        
        self.logger.info(f"Success rate: {success_rate:.1f}%")
        self.logger.info(f"Average fields per profile: {avg_fields:.1f}")