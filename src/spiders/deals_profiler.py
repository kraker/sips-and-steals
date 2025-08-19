"""
Deals Profile Spider

Extracts ONLY deal-specific content that Google Places API doesn't provide:
- Happy hour deals and promotions
- Menu pricing information
- Special events and seasonal offers
- Reservation links (OpenTable, Resy)
- Atmosphere keywords for user experience

NOTE: Address, phone, hours, business status now come from Google Places API.
This spider focuses exclusively on unique content extraction.
"""

import scrapy
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse

from ..items import RestaurantProfileItem


class DealsProfilerSpider(scrapy.Spider):
    name = 'deals_profiler'
    
    # Focus only on deal-specific extraction patterns
    
    # Reservation service patterns
    RESERVATION_PATTERNS = {
        'opentable': [
            r'opentable\.com/([^/\s"\']+)',
            r'opentable'
        ],
        'resy': [
            r'resy\.com/([^/\s"\']+)',
            r'resy'
        ],
        'tock': [
            r'tock\.com/([^/\s"\']+)',
            r'tock'
        ]
    }
    
    # Price range indicators for menu analysis
    PRICE_INDICATORS = {
        'budget': ['$5', '$6', '$7', '$8', '$9', 'under $10', 'affordable'],
        'moderate': ['$10', '$12', '$15', '$18', '$20', '$25'],
        'upscale': ['$30', '$35', '$40', '$45', '$50', 'market price', 'mp'],
        'luxury': ['$60', '$75', '$100', 'seasonal pricing', 'chef selection']
    }
    
    # Atmosphere keywords for user experience
    ATMOSPHERE_KEYWORDS = {
        'romantic': ['romantic', 'intimate', 'date night', 'couples'],
        'family_friendly': ['family', 'kids', 'children', 'family-friendly'],
        'lively': ['lively', 'energetic', 'vibrant', 'bustling'],
        'casual': ['casual', 'relaxed', 'laid-back', 'informal'],
        'upscale': ['upscale', 'elegant', 'sophisticated', 'refined'],
        'outdoor': ['patio', 'rooftop', 'terrace', 'outdoor', 'garden']
    }

    def start_requests(self):
        """Generate requests for all restaurants"""
        
        # Load restaurant data
        with open('data/restaurants.json', 'r') as f:
            restaurant_data = json.load(f)
        
        restaurants = restaurant_data.get('restaurants', {})
        
        self.logger.info(f"Starting deals profiling for {len(restaurants)} restaurants")
        
        for slug, restaurant in restaurants.items():
            # Use both website sources for comprehensive extraction
            urls_to_try = []
            
            # Primary: Curated website (often has deal-specific pages)
            if restaurant.get('website'):
                urls_to_try.append(restaurant['website'])
            
            # Fallback: Google Places website  
            google_website = restaurant.get('google_places', {}).get('website')
            if google_website and google_website not in urls_to_try:
                urls_to_try.append(google_website)
            
            # Also try scraping URLs if available
            scraping_urls = restaurant.get('scraping_urls', [])
            for url in scraping_urls:
                if url not in urls_to_try:
                    urls_to_try.append(url)
            
            # Generate requests for each URL
            for url in urls_to_try:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_restaurant,
                    meta={
                        'restaurant_slug': slug,
                        'restaurant_data': restaurant,
                        'source_url': url
                    },
                    errback=self.handle_error
                )

    def parse_restaurant(self, response):
        """Extract deals and unique content from restaurant page"""
        
        slug = response.meta['restaurant_slug']
        restaurant_data = response.meta['restaurant_data']
        source_url = response.meta['source_url']
        
        self.logger.info(f"Parsing deals for {restaurant_data.get('name', slug)} from {source_url}")
        
        # Initialize profile item - DEALS ONLY
        profile = RestaurantProfileItem()
        profile['restaurant_slug'] = slug
        profile['restaurant_name'] = restaurant_data.get('name', slug)
        profile['source_url'] = source_url
        profile['scraped_at'] = datetime.now().isoformat()
        profile['extraction_patterns'] = []
        
        # Extract all text content for analysis
        all_text = ' '.join(response.css('*::text').getall())
        content_sections = self._get_content_sections(response)
        
        # Extract ONLY unique content not provided by Google Places
        fields_found = 0
        
        # 1. Menu pricing analysis
        fields_found += self._extract_menu_pricing(profile, all_text, content_sections, response)
        
        # 2. Special events and promotions
        fields_found += self._extract_special_events(profile, all_text, content_sections)
        
        # 3. Reservation service links
        fields_found += self._extract_reservation_services(profile, all_text, response)
        
        # 4. Atmosphere and experience keywords
        fields_found += self._extract_atmosphere(profile, all_text)
        
        # 5. Happy hour specific content (enhanced)
        fields_found += self._extract_happy_hour_details(profile, all_text, content_sections)
        
        profile['fields_extracted'] = fields_found
        profile['extraction_success'] = fields_found > 0
        
        if fields_found > 0:
            self.logger.info(f"✅ Extracted {fields_found} deal fields for {profile['restaurant_name']}")
        else:
            self.logger.warning(f"⚠️ No unique deal content found for {profile['restaurant_name']}")
        
        yield profile

    def _get_content_sections(self, response) -> List[Tuple]:
        """Get content organized by sections for targeted extraction"""
        sections = []
        
        # Look for content in specific containers
        selectors = [
            'main', 'section', 'article', '.content', '.menu', '.specials',
            '.happy-hour', '.deals', '.promotions', '.events', '.pricing'
        ]
        
        for selector in selectors:
            elements = response.css(selector)
            for element in elements:
                html = element.get()
                text = ' '.join(element.css('*::text').getall())
                if text.strip():
                    sections.append((selector, html, text))
        
        return sections

    def _extract_menu_pricing(self, profile: RestaurantProfileItem, all_text: str,
                             content_sections: List[Tuple], response) -> int:
        """Extract menu pricing information"""
        found_count = 0
        text_lower = all_text.lower()
        
        # Look for pricing patterns
        price_data = {}
        
        # Extract dollar amounts and associated items
        price_pattern = r'\$(\d+(?:\.\d{2})?)\s*[–-]?\s*([^$\n]{1,50})'
        price_matches = re.findall(price_pattern, all_text)
        
        if price_matches:
            prices = []
            for price, item in price_matches:
                prices.append({
                    'price': f"${price}",
                    'item': item.strip()
                })
            
            if prices:
                profile['menu_pricing'] = prices[:10]  # Limit to 10 items
                found_count += 1
                profile['extraction_patterns'].append('menu_pricing')
        
        # Detect price range category
        for price_level, indicators in self.PRICE_INDICATORS.items():
            if any(indicator in text_lower for indicator in indicators):
                profile['price_range'] = price_level
                found_count += 1
                profile['extraction_patterns'].append('price_range_detection')
                break
        
        return found_count

    def _extract_special_events(self, profile: RestaurantProfileItem, all_text: str,
                               content_sections: List[Tuple]) -> int:
        """Extract special events and seasonal promotions"""
        found_count = 0
        text_lower = all_text.lower()
        
        # Event keywords
        event_patterns = {
            'seasonal': ['summer', 'winter', 'spring', 'fall', 'holiday', 'christmas', 'thanksgiving'],
            'weekly_specials': ['monday', 'tuesday', 'wednesday', 'thursday', 'taco tuesday', 'wine wednesday'],
            'special_events': ['live music', 'trivia', 'karaoke', 'game day', 'brunch', 'bottomless'],
            'celebrations': ['birthday', 'anniversary', 'private party', 'corporate event']
        }
        
        events_found = {}
        for category, keywords in event_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if category not in events_found:
                        events_found[category] = []
                    events_found[category].append(keyword)
        
        if events_found:
            profile['special_events'] = events_found
            found_count += 1
            profile['extraction_patterns'].append('special_events')
        
        return found_count

    def _extract_reservation_services(self, profile: RestaurantProfileItem, all_text: str,
                                     response) -> int:
        """Extract reservation service links"""
        found_count = 0
        reservation_data = {}
        
        # Look for reservation links in HTML
        for service, patterns in self.RESERVATION_PATTERNS.items():
            # Check links
            links = response.css(f'a[href*="{service}"]')
            for link in links:
                href = link.attrib.get('href', '')
                if href:
                    reservation_data[f'{service}_url'] = href
                    found_count += 1
            
            # Check text content
            for pattern in patterns:
                if re.search(pattern, all_text, re.IGNORECASE):
                    reservation_data[f'{service}_mentioned'] = True
                    found_count += 1
        
        if reservation_data:
            profile['reservation_services'] = reservation_data
            profile['extraction_patterns'].append('reservation_services')
        
        return found_count

    def _extract_atmosphere(self, profile: RestaurantProfileItem, all_text: str) -> int:
        """Extract atmosphere and experience keywords"""
        found_count = 0
        text_lower = all_text.lower()
        
        atmosphere = []
        for mood, keywords in self.ATMOSPHERE_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                atmosphere.append(mood)
        
        if atmosphere:
            profile['atmosphere'] = list(set(atmosphere))  # Remove duplicates
            found_count += 1
            profile['extraction_patterns'].append('atmosphere_detection')
        
        return found_count

    def _extract_happy_hour_details(self, profile: RestaurantProfileItem, all_text: str,
                                   content_sections: List[Tuple]) -> int:
        """Extract enhanced happy hour specific details"""
        found_count = 0
        text_lower = all_text.lower()
        
        happy_hour_data = {}
        
        # Look for happy hour mentions and context
        if 'happy hour' in text_lower:
            happy_hour_data['has_happy_hour'] = True
            found_count += 1
            
            # Extract happy hour specific pricing
            hh_price_pattern = r'happy hour[^$]*\$(\d+(?:\.\d{2})?)'
            hh_prices = re.findall(hh_price_pattern, text_lower)
            if hh_prices:
                happy_hour_data['happy_hour_prices'] = [f"${price}" for price in hh_prices]
            
            # Look for happy hour specific items
            hh_context = []
            sentences = re.split(r'[.!?]+', all_text)
            for sentence in sentences:
                if 'happy hour' in sentence.lower():
                    hh_context.append(sentence.strip())
            
            if hh_context:
                happy_hour_data['happy_hour_context'] = hh_context[:3]  # Limit to 3
        
        # Look for other deal terminology
        deal_terms = ['special', 'discount', 'promotion', 'deal', 'offer']
        for term in deal_terms:
            if term in text_lower:
                if 'deal_types' not in happy_hour_data:
                    happy_hour_data['deal_types'] = []
                happy_hour_data['deal_types'].append(term)
        
        if happy_hour_data:
            profile['happy_hour_details'] = happy_hour_data
            profile['extraction_patterns'].append('happy_hour_details')
            found_count += 1
        
        return found_count

    def handle_error(self, failure):
        """Handle request errors"""
        slug = failure.request.meta.get('restaurant_slug', 'unknown')
        url = failure.request.url
        
        self.logger.error(f"❌ Failed to parse {slug} from {url}: {failure.value}")
        
        # Still yield a minimal profile to track the attempt
        profile = RestaurantProfileItem()
        profile['restaurant_slug'] = slug
        profile['source_url'] = url
        profile['scraped_at'] = datetime.now().isoformat()
        profile['extraction_success'] = False
        profile['error'] = str(failure.value)
        
        yield profile