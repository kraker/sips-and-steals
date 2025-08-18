"""
Restaurant Happy Hour Discovery Spider

Automatically discovers happy hour pages across restaurant websites.
Uses intelligent link following and content analysis to find relevant pages.
"""

import scrapy
import json
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime
from typing import List, Dict, Optional

from ..items import RestaurantPageItem, DiscoveredLinkItem


class DiscoverySpider(scrapy.Spider):
    name = 'discovery'
    allowed_domains = []  # Will be populated from restaurant data
    
    # Happy hour indicators for link and content analysis
    HAPPY_HOUR_PATTERNS = [
        r'\bhappy\s*hour\b',
        r'\bspecials?\b',
        r'\bdeals?\b',
        r'\bapr[eè]s\b',
        r'\bearly\s*bird\b',
        r'\blate\s*night\b',
        r'\bdrink\s*specials?\b',
        r'\bfood\s*specials?\b',
        r'\bdaily\s*specials?\b',
    ]
    
    # URL patterns that often contain happy hour info and menu/pricing data
    URL_PATTERNS = [
        r'happy.*hour',
        r'specials?',
        r'deals?',
        r'menu',
        r'food',
        r'dining',
        r'eat',
        r'drink',
        r'apr[eè]s',
        r'bar',
        r'lounge',
        r'brunch',
        r'lunch',
        r'dinner',
        r'prix.*fixe',
        r'tasting.*menu',
        r'chef.*menu',
    ]
    
    # Menu-specific patterns for enhanced menu discovery
    MENU_PATTERNS = [
        r'\bmenu\b',
        r'\bfood\b',
        r'\bdining\b',
        r'\beat\b',
        r'\bbrunch\b',
        r'\blunch\b',
        r'\bdinner\b',
        r'\bappetizers?\b',
        r'\bentr[eé]es?\b',
        r'\bmains?\b',
        r'\bdesserts?\b',
        r'\bbeverage\b',
        r'\bcocktails?\b',
        r'\bwine\s*list\b',
        r'\bprix\s*fixe\b',
        r'\btasting\s*menu\b',
        r'\bchef.*menu\b',
        r'\bseasonal\s*menu\b',
    ]
    
    # Pricing indicators for content analysis  
    PRICING_INDICATORS = [
        r'\$\d+',           # $15
        r'\$\d+\.\d{2}',    # $15.99
        r'\$\d+\s*[-–]\s*\$?\d+',  # $10-15, $10-$15
        r'market\s*price',
        r'seasonal\s*price',
        r'mp\b',            # Market Price abbreviation
    ]
    
    def __init__(self, restaurant_file='data/restaurants.json', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.restaurant_file = restaurant_file
        self.restaurants = self._load_restaurants()
        
        # Set allowed domains from restaurant websites
        self.allowed_domains = self._extract_domains()
        
        # Statistics tracking
        self.stats = {
            'pages_discovered': 0,
            'links_found': 0,
            'restaurants_processed': 0,
        }
    
    def _load_restaurants(self) -> Dict[str, Dict]:
        """Load restaurant data from JSON file"""
        try:
            with open(self.restaurant_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both old nested format and new flat format
            if 'restaurants' in data:
                return data['restaurants']
            elif 'areas' in data:
                # Legacy format - flatten
                restaurants = {}
                for area_name, area_restaurants in data.get('areas', {}).items():
                    restaurants.update(area_restaurants)
                return restaurants
            else:
                self.logger.warning("Unexpected restaurant data format")
                return {}
                
        except FileNotFoundError:
            self.logger.error(f"Restaurant file not found: {self.restaurant_file}")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in restaurant file: {e}")
            return {}
    
    def _extract_domains(self) -> List[str]:
        """Extract allowed domains from restaurant websites"""
        domains = set()
        for slug, restaurant in self.restaurants.items():
            website = restaurant.get('website')
            if website:
                try:
                    parsed = urlparse(website)
                    domain = parsed.netloc.lower()
                    if domain:
                        domains.add(domain)
                        # Also add without www
                        if domain.startswith('www.'):
                            domains.add(domain[4:])
                except:
                    self.logger.warning(f"Invalid website URL for {slug}: {website}")
        
        return list(domains)
    
    def start_requests(self):
        """Generate initial requests for all restaurant websites"""
        for slug, restaurant in self.restaurants.items():
            website = restaurant.get('website')
            if not website:
                self.logger.debug(f"No website for restaurant: {slug}")
                continue
            
            # Ensure URL has scheme
            if not website.startswith(('http://', 'https://')):
                website = 'https://' + website
            
            yield scrapy.Request(
                url=website,
                callback=self.parse_restaurant_homepage,
                meta={
                    'restaurant_slug': slug,
                    'restaurant_name': restaurant.get('name', slug),
                    'depth': 0
                },
                errback=self.handle_error
            )
    
    def parse_restaurant_homepage(self, response):
        """Parse restaurant homepage and discover potential happy hour pages"""
        restaurant_slug = response.meta['restaurant_slug']
        restaurant_name = response.meta['restaurant_name']
        depth = response.meta.get('depth', 0)
        
        self.logger.info(f"Discovering pages for {restaurant_name} ({restaurant_slug})")
        self.stats['restaurants_processed'] += 1
        
        # Analyze current page for happy hour content
        page_item = self._analyze_page_content(response, restaurant_slug, restaurant_name)
        if page_item:
            self.stats['pages_discovered'] += 1
            yield page_item
        
        # Find and follow relevant links (up to max depth)
        max_depth = self.settings.getint('MAX_CRAWL_DEPTH', 3)
        if depth < max_depth:
            yield from self._discover_links(response, restaurant_slug, restaurant_name, depth)
    
    def parse_discovered_page(self, response):
        """Parse a discovered page that might contain happy hour information"""
        restaurant_slug = response.meta['restaurant_slug']
        restaurant_name = response.meta['restaurant_name']
        depth = response.meta.get('depth', 0)
        
        # Analyze page content
        page_item = self._analyze_page_content(response, restaurant_slug, restaurant_name)
        if page_item:
            self.stats['pages_discovered'] += 1
            yield page_item
        
        # Continue discovering links if we haven't reached max depth
        max_depth = self.settings.getint('MAX_CRAWL_DEPTH', 3)
        if depth < max_depth:
            yield from self._discover_links(response, restaurant_slug, restaurant_name, depth)
    
    def _analyze_page_content(self, response, restaurant_slug: str, restaurant_name: str) -> Optional[RestaurantPageItem]:
        """Analyze page content for happy hour relevance"""
        # Extract text content for analysis
        text_content = ' '.join(response.css('*::text').getall()).lower()
        title = response.css('title::text').get('').strip()
        
        # Calculate happy hour likelihood score
        likelihood_score = self._calculate_happy_hour_likelihood(text_content, response.url, title)
        
        # Only create item if there's some potential for happy hour content
        if likelihood_score > 0.1:  # Minimum threshold
            content_preview = text_content[:500] if text_content else ''
            
            return RestaurantPageItem(
                url=response.url,
                title=title,
                restaurant_slug=restaurant_slug,
                restaurant_name=restaurant_name,
                happy_hour_likelihood=likelihood_score,
                content_keywords=self._extract_keywords(text_content),
                discovered_at=datetime.now().isoformat(),
                content_type=response.headers.get('content-type', b'').decode('utf-8'),
                status_code=response.status,
                content_preview=content_preview
            )
        
        return None
    
    def _calculate_happy_hour_likelihood(self, text_content: str, url: str, title: str) -> float:
        """Calculate likelihood that this page contains happy hour information and menu/pricing data"""
        score = 0.0
        
        # Check content for happy hour patterns
        for pattern in self.HAPPY_HOUR_PATTERNS:
            matches = len(re.findall(pattern, text_content, re.IGNORECASE))
            score += matches * 0.2  # Each match adds 0.2
        
        # Check content for menu patterns (NEW: menu discovery enhancement)
        for pattern in self.MENU_PATTERNS:
            matches = len(re.findall(pattern, text_content, re.IGNORECASE))
            score += matches * 0.15  # Menu content is valuable for pricing
        
        # Check content for pricing indicators (NEW: pricing detection)
        for pattern in self.PRICING_INDICATORS:
            matches = len(re.findall(pattern, text_content, re.IGNORECASE))
            score += matches * 0.25  # Pricing content is highly valuable
        
        # Check URL for relevant patterns
        url_lower = url.lower()
        for pattern in self.URL_PATTERNS:
            if re.search(pattern, url_lower):
                score += 0.3
        
        # Check title for relevant terms
        title_lower = title.lower()
        for pattern in self.HAPPY_HOUR_PATTERNS + self.MENU_PATTERNS:
            if re.search(pattern, title_lower):
                score += 0.4
        
        # Look for time patterns (strong indicator)
        time_patterns = [
            r'\d{1,2}\s*(?::\d{2})?\s*(?:am|pm)',  # Time mentions
            r'monday|tuesday|wednesday|thursday|friday|saturday|sunday',  # Days
        ]
        for pattern in time_patterns:
            matches = len(re.findall(pattern, text_content, re.IGNORECASE))
            score += matches * 0.1
        
        # Boost for PDF files (often contain menus with pricing)
        if url_lower.endswith('.pdf'):
            score += 0.5
            
        # Normalize score to 0-1 range
        return min(score, 1.0)
    
    def _extract_keywords(self, text_content: str) -> List[str]:
        """Extract relevant keywords from content"""
        keywords = set()
        
        # Find all happy hour related terms
        for pattern in self.HAPPY_HOUR_PATTERNS:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            keywords.update(match.lower().strip() for match in matches)
        
        # Find time patterns
        time_matches = re.findall(r'\d{1,2}\s*(?::\d{2})?\s*(?:am|pm)', text_content, re.IGNORECASE)
        keywords.update(match.lower().strip() for match in time_matches[:5])  # Limit to 5
        
        # Find day patterns
        day_matches = re.findall(r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekday|weekend|daily)\b', 
                                text_content, re.IGNORECASE)
        keywords.update(match.lower().strip() for match in day_matches[:5])  # Limit to 5
        
        return list(keywords)[:20]  # Return max 20 keywords
    
    def _discover_links(self, response, restaurant_slug: str, restaurant_name: str, current_depth: int):
        """Discover and follow relevant links"""
        # Extract all links
        links = response.css('a[href]')
        
        for link in links:
            href = link.css('::attr(href)').get()
            anchor_text = ' '.join(link.css('::text').getall()).strip().lower()
            
            if not href:
                continue
            
            # Resolve relative URLs
            full_url = urljoin(response.url, href)
            
            # Skip non-HTTP links and external domains
            if not full_url.startswith(('http://', 'https://')):
                continue
            
            parsed_url = urlparse(full_url)
            if parsed_url.netloc.lower() not in self.allowed_domains:
                continue
            
            # Calculate relevance score for this link
            relevance_score = self._calculate_link_relevance(href, anchor_text)
            
            # Only follow links with decent relevance
            if relevance_score > 0.3:
                self.stats['links_found'] += 1
                
                # Yield discovered link item for tracking
                yield DiscoveredLinkItem(
                    url=full_url,
                    anchor_text=anchor_text,
                    source_url=response.url,
                    restaurant_slug=restaurant_slug,
                    happy_hour_relevance_score=relevance_score,
                    discovered_at=datetime.now().isoformat()
                )
                
                # Follow the link
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_discovered_page,
                    meta={
                        'restaurant_slug': restaurant_slug,
                        'restaurant_name': restaurant_name,
                        'depth': current_depth + 1,
                        'found_via': response.url,
                        'link_text': anchor_text
                    },
                    errback=self.handle_error
                )
    
    def _calculate_link_relevance(self, href: str, anchor_text: str) -> float:
        """Calculate how relevant a link is for happy hour discovery and menu/pricing content"""
        score = 0.0
        
        # Check anchor text for happy hour indicators
        for pattern in self.HAPPY_HOUR_PATTERNS:
            if re.search(pattern, anchor_text, re.IGNORECASE):
                score += 0.4
        
        # Check anchor text for menu patterns (NEW: enhanced menu discovery)
        for pattern in self.MENU_PATTERNS:
            if re.search(pattern, anchor_text, re.IGNORECASE):
                score += 0.35  # Menu content is valuable for pricing
        
        # Check URL for relevant patterns
        href_lower = href.lower()
        for pattern in self.URL_PATTERNS:
            if re.search(pattern, href_lower):
                score += 0.3
        
        # Boost score for specific high-value terms
        high_value_terms = ['happy hour', 'specials', 'deals', 'menu']
        for term in high_value_terms:
            if term in anchor_text:
                score += 0.5
            if term in href_lower:
                score += 0.3
        
        # ENHANCED: Boost for menu-specific high-value terms
        menu_high_value_terms = ['food menu', 'dinner menu', 'lunch menu', 'brunch menu', 
                                'drink menu', 'cocktail menu', 'wine list', 'prix fixe', 
                                'tasting menu', 'chef menu', 'seasonal menu']
        for term in menu_high_value_terms:
            if term in anchor_text:
                score += 0.6  # Higher boost for specific menu types
            if term in href_lower:
                score += 0.4
        
        # ENHANCED: Boost for pricing-related terms
        pricing_terms = ['prices', 'pricing', 'cost', '$', 'price list']
        for term in pricing_terms:
            if term in anchor_text:
                score += 0.4
            if term in href_lower:
                score += 0.3
        
        # ENHANCED: Boost for PDF files (often contain menus with pricing)
        if href_lower.endswith('.pdf'):
            score += 0.5
            # Extra boost if PDF has menu-related keywords
            if any(keyword in href_lower for keyword in ['menu', 'food', 'drink', 'price']):
                score += 0.3
        
        return min(score, 1.0)
    
    def handle_error(self, failure):
        """Handle request errors"""
        request = failure.request
        restaurant_slug = request.meta.get('restaurant_slug', 'unknown')
        
        self.logger.warning(f"Failed to crawl {request.url} for {restaurant_slug}: {failure.value}")
    
    def closed(self, reason):
        """Spider closing callback - log statistics"""
        self.logger.info(f"Discovery spider closed: {reason}")
        self.logger.info(f"Statistics: {self.stats}")
        
        # Log summary
        self.logger.info(f"Processed {self.stats['restaurants_processed']} restaurants")
        self.logger.info(f"Discovered {self.stats['pages_discovered']} relevant pages")
        self.logger.info(f"Found {self.stats['links_found']} promising links")