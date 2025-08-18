"""
Menu Pricing Spider

Extracts pricing information from discovered menu pages and PDFs.
Focuses on building comprehensive pricing intelligence for restaurants.
"""

import scrapy
import json
import re
import PyPDF2
import io
from urllib.parse import urlparse
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from ..items import RestaurantPageItem


@dataclass
class PriceItem:
    """Structured price data extracted from menus"""
    item_name: str
    price: str
    category: Optional[str] = None
    description: Optional[str] = None
    raw_text: Optional[str] = None


# Import MenuPricingItem from items module
from ..items import MenuPricingItem


class MenuPricingSpider(scrapy.Spider):
    name = 'menu_pricing'
    allowed_domains = []
    
    # Comprehensive price extraction patterns
    PRICE_PATTERNS = [
        # Standard pricing: $12, $15.99, $8.50
        r'\$(\d+(?:\.\d{2})?)',
        # Price ranges: $10-15, $12-$18, $10 - $15
        r'\$(\d+)\s*[-–]\s*\$?(\d+)',
        # Market price variations
        r'market\s*price|mp\b|seasonal\s*price',
        # Multiple prices: $12/$15 (lunch/dinner)
        r'\$(\d+)/\$(\d+)',
    ]
    
    # Menu category patterns for better organization
    CATEGORY_PATTERNS = {
        'appetizers': r'appetizers?|starters?|small\s*plates?|shareables?',
        'entrees': r'entr[eé]es?|mains?|large\s*plates?|dinner|entree',
        'salads': r'salads?|greens?',
        'desserts': r'desserts?|sweets?|dolci',
        'beverages': r'beverages?|drinks?|cocktails?|wines?|beers?',
        'happy_hour': r'happy\s*hour|specials?|deals?|après',
        'brunch': r'brunch|breakfast|morning',
        'lunch': r'lunch|midday',
        'pizza': r'pizza|flatbread',
        'pasta': r'pasta|noodles?'
    }
    
    # Enhanced menu item patterns for better extraction
    MENU_ITEM_PATTERNS = [
        # Item with price at end: "Margherita Pizza ... $16"
        r'([A-Z][A-Za-z\s&\'-]{4,40})\s*\.{2,}\s*\$(\d+(?:\.\d{2})?)',
        # Item with price nearby: "Caesar Salad $14"
        r'([A-Z][A-Za-z\s&\'-]{3,35})\s+\$(\d+(?:\.\d{2})?)',
        # Price at start: "$12 - Pasta Carbonara"
        r'\$(\d+(?:\.\d{2})?)\s*[-–]\s*([A-Z][A-Za-z\s&\'-]{3,35})',
        # Price with optional cents: "Bruschetta $12.50"
        r'([A-Z][A-Za-z\s&\'-]{3,35})\s*[:\-]?\s*\$(\d+(?:\.\d{2})?)',
        # Multiple line format: "PASTA\nCarbonara $18"
        r'([A-Z][A-Z\s]{3,25})\s*\n.*?\$(\d+(?:\.\d{2})?)',
        # Specific Italian menu format from PDFs
        r'([A-Z][A-Z\s]{3,30})(?:\n[a-z].*?)*?\s*\$(\d+(?:\.\d{2})?)',
        # Happy hour format: "MOZZARELLA BOCCONCINI House Pomodoro   11"
        r'([A-Z][A-Z\s]{3,30})\s+[A-Za-z\s]+\s+(\d{1,3})',
        # Simple format: "ITEM NAME description   price"
        r'([A-Z][A-Z\s&\'-]{3,30})\s+[a-z][a-z\s,&\'-]+\s+(\d{1,3})',
        # PDF format without dollar sign: "Item Name   15"
        r'([A-Z][A-Za-z\s&\'-]{4,35})\s{2,}(\d{1,3})(?:\s|$)',
    ]
    
    def __init__(self, discovered_pages_file='data/discovered_pages.json', 
                 discovered_links_file='data/discovered_links.json', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.discovered_pages_file = discovered_pages_file
        self.discovered_links_file = discovered_links_file
        self.discovered_pages = self._load_discovered_pages()
        self.discovered_links = self._load_discovered_links()
        
        # Extract domains for filtering
        self.allowed_domains = self._extract_domains()
        
        # Statistics
        self.stats = {
            'pages_processed': 0,
            'pdfs_processed': 0,
            'prices_extracted': 0,
            'restaurants_processed': set(),
        }
    
    def _load_discovered_pages(self) -> List[Dict]:
        """Load discovered pages from JSON file"""
        try:
            with open(self.discovered_pages_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('pages', [])
        except FileNotFoundError:
            self.logger.error(f"Discovered pages file not found: {self.discovered_pages_file}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in discovered pages file: {e}")
            return []
    
    def _load_discovered_links(self) -> List[Dict]:
        """Load discovered links from JSON file"""
        try:
            with open(self.discovered_links_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('links', [])
        except FileNotFoundError:
            self.logger.error(f"Discovered links file not found: {self.discovered_links_file}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in discovered links file: {e}")
            return []
    
    def _extract_domains(self) -> List[str]:
        """Extract allowed domains from discovered pages and links"""
        domains = set()
        
        # Extract domains from pages
        for page in self.discovered_pages:
            url = page.get('url', '')
            if url:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                    if domain:
                        domains.add(domain)
                        if domain.startswith('www.'):
                            domains.add(domain[4:])
                except:
                    pass
        
        # Extract domains from links
        for link in self.discovered_links:
            url = link.get('url', '')
            if url:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                    if domain:
                        domains.add(domain)
                        if domain.startswith('www.'):
                            domains.add(domain[4:])
                except:
                    pass
                    
        return list(domains)
    
    def start_requests(self):
        """Generate requests for discovered pages and links with menu/pricing potential"""
        
        # Process discovered pages with high likelihood
        for page in self.discovered_pages:
            likelihood = page.get('happy_hour_likelihood', 0)
            if likelihood >= 0.5:  # Only process high-likelihood pages
                url = page.get('url', '')
                if url:
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_menu_page,
                        meta={
                            'restaurant_slug': page.get('restaurant_slug'),
                            'restaurant_name': page.get('restaurant_name'),
                            'page_data': page
                        },
                        errback=self.handle_error
                    )
        
        # Process discovered links with high menu/pricing relevance
        for link in self.discovered_links:
            relevance = link.get('happy_hour_relevance_score', 0)
            url = link.get('url', '')
            anchor_text = link.get('anchor_text', '').lower()
            
            # Focus on high-value links: PDFs, menu pages, pricing content
            should_process = (
                relevance >= 0.5 or  # High relevance score
                url.lower().endswith('.pdf') or  # PDF files often contain menus
                'menu' in anchor_text or  # Menu-related anchor text
                'price' in anchor_text or  # Price-related anchor text
                'wine' in anchor_text or  # Wine lists often have pricing
                'happy hour' in anchor_text  # Happy hour content
            )
            
            if should_process and url:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_menu_page,
                    meta={
                        'restaurant_slug': link.get('restaurant_slug'),
                        'restaurant_name': link.get('restaurant_slug'),  # Use slug as fallback
                        'page_data': link,
                        'is_discovered_link': True
                    },
                    errback=self.handle_error
                )
    
    def parse_menu_page(self, response):
        """Parse menu page for pricing information"""
        restaurant_slug = response.meta['restaurant_slug']
        restaurant_name = response.meta['restaurant_name']
        page_data = response.meta['page_data']
        
        self.logger.info(f"Extracting pricing from {response.url} for {restaurant_name}")
        self.stats['pages_processed'] += 1
        self.stats['restaurants_processed'].add(restaurant_slug)
        
        # Determine content type
        content_type = response.headers.get('content-type', b'').decode('utf-8').lower()
        
        if 'pdf' in content_type or response.url.lower().endswith('.pdf'):
            yield from self._process_pdf_content(response, restaurant_slug, restaurant_name)
        else:
            yield from self._process_html_content(response, restaurant_slug, restaurant_name)
    
    def _process_html_content(self, response, restaurant_slug: str, restaurant_name: str):
        """Process HTML content for pricing information"""
        # Extract text content
        text_content = ' '.join(response.css('*::text').getall())
        
        # Extract pricing items
        price_items = self._extract_price_items(text_content)
        
        if price_items:
            # Determine menu type from URL and content
            menu_type = self._determine_menu_type(response.url, text_content)
            
            # Calculate pricing statistics
            pricing_stats = self._calculate_pricing_stats(price_items)
            
            self.stats['prices_extracted'] += len(price_items)
            
            yield MenuPricingItem(
                url=response.url,
                restaurant_slug=restaurant_slug,
                restaurant_name=restaurant_name,
                menu_type=menu_type,
                price_items=[item.__dict__ for item in price_items],
                price_range_detected=pricing_stats['price_range'],
                average_price=pricing_stats['average_price'],
                min_price=pricing_stats['min_price'],
                max_price=pricing_stats['max_price'],
                content_type='text/html',
                scraped_at=datetime.now().isoformat(),
                confidence_score=self._calculate_confidence_score(price_items, text_content),
                raw_content_preview=text_content[:1000]
            )
    
    def _process_pdf_content(self, response, restaurant_slug: str, restaurant_name: str):
        """Process PDF content for pricing information"""
        try:
            self.stats['pdfs_processed'] += 1
            
            # Read PDF content
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(response.body))
            text_content = ""
            
            for page in pdf_reader.pages:
                try:
                    text_content += page.extract_text() + "\n"
                except:
                    continue
            
            if not text_content.strip():
                self.logger.warning(f"No text extracted from PDF: {response.url}")
                return
            
            # DEBUG: Log PDF content preview for analysis
            self.logger.info(f"PDF content preview for {response.url[:50]}...: {text_content[:200]}...")
            
            # Extract pricing items from PDF text
            price_items = self._extract_price_items(text_content)
            
            if price_items:
                # Determine menu type from URL and content
                menu_type = self._determine_menu_type(response.url, text_content)
                
                # Calculate pricing statistics
                pricing_stats = self._calculate_pricing_stats(price_items)
                
                self.stats['prices_extracted'] += len(price_items)
                
                yield MenuPricingItem(
                    url=response.url,
                    restaurant_slug=restaurant_slug,
                    restaurant_name=restaurant_name,
                    menu_type=menu_type,
                    price_items=[item.__dict__ for item in price_items],
                    price_range_detected=pricing_stats['price_range'],
                    average_price=pricing_stats['average_price'],
                    min_price=pricing_stats['min_price'],
                    max_price=pricing_stats['max_price'],
                    content_type='application/pdf',
                    scraped_at=datetime.now().isoformat(),
                    confidence_score=self._calculate_confidence_score(price_items, text_content),
                    raw_content_preview=text_content[:1000]
                )
                
        except Exception as e:
            self.logger.error(f"Error processing PDF {response.url}: {e}")
    
    def _extract_price_items(self, text_content: str) -> List[PriceItem]:
        """Extract structured price items from text content"""
        price_items = []
        
        # Split content into lines for better parsing
        lines = text_content.split('\n')
        current_category = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # DEBUG: Log lines from Happy Hour PDF for analysis
            if 'HAPPY HOUR' in text_content.upper() and ('MOZZARELLA' in line.upper() or 'MORTADELL' in line.upper()):
                self.logger.info(f"DEBUG Happy Hour line: '{line}'")
            
            # Check if this line indicates a menu category
            detected_category = self._detect_category(line)
            if detected_category:
                current_category = detected_category
                continue
            
            # Try to extract menu items with prices from this line
            items = self._extract_items_from_line(line, current_category)
            price_items.extend(items)
        
        return price_items
    
    def _extract_items_from_line(self, line: str, category: Optional[str] = None) -> List[PriceItem]:
        """Extract price items from a single line of text"""
        items = []
        
        # Skip lines that contain group/catering/event indicators
        line_lower = line.lower()
        skip_indicators = [
            'per person', 'family style', 'group', 'catering', 'event', 
            'party', 'buyout', 'minimum', 'service charge', 'gratuity',
            'tax', 'beo', 'capacity', 'contact', 'reservation'
        ]
        
        if any(indicator in line_lower for indicator in skip_indicators):
            return items
        
        # Skip very long lines (likely descriptions rather than menu items)
        if len(line) > 200:
            return items
        
        # Try each menu item pattern
        for i, pattern in enumerate(self.MENU_ITEM_PATTERNS):
            matches = re.findall(pattern, line, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if matches:
                self.logger.debug(f"Pattern {i} matched on line: {line[:100]}... -> {matches}")
            for match in matches:
                if len(match) == 2:  # (item_name, price)
                    item_name, price = match
                    
                    # Clean item name
                    item_name = item_name.strip()
                    
                    # Skip if item name is too short or too long
                    if len(item_name) < 3 or len(item_name) > 50:
                        continue
                    
                    # Handle different pattern orders
                    if price.replace('.', '').replace(' ', '').isdigit():  # price is numeric
                        # Filter out unrealistic prices (more permissive range)
                        price_float = float(price.replace(' ', ''))
                        if 3 <= price_float <= 200:  # Broader range for menu items
                            items.append(PriceItem(
                                item_name=item_name,
                                price=f"${price}",
                                category=category,
                                raw_text=line.strip()
                            ))
                    elif item_name.replace('.', '').replace(' ', '').isdigit():  # item_name is actually price
                        price_float = float(item_name.replace(' ', ''))
                        if 3 <= price_float <= 200:  # Broader range for menu items
                            items.append(PriceItem(
                                item_name=price.strip(),
                                price=f"${item_name}",
                                category=category,
                                raw_text=line.strip()
                            ))
        
        return items
    
    def _detect_category(self, line: str) -> Optional[str]:
        """Detect if a line represents a menu category"""
        line_lower = line.lower()
        for category, pattern in self.CATEGORY_PATTERNS.items():
            if re.search(pattern, line_lower) and len(line) < 50:  # Categories are usually short
                return category
        return None
    
    def _determine_menu_type(self, url: str, content: str) -> str:
        """Determine the type of menu from URL and content"""
        url_lower = url.lower()
        content_lower = content.lower()
        
        # Check URL for menu type indicators
        if 'happy' in url_lower or 'hour' in url_lower:
            return 'happy_hour'
        elif 'wine' in url_lower:
            return 'wine'
        elif 'brunch' in url_lower:
            return 'brunch'
        elif 'lunch' in url_lower:
            return 'lunch'
        elif 'dinner' in url_lower:
            return 'dinner'
        
        # Check content for menu type indicators
        if 'happy hour' in content_lower:
            return 'happy_hour'
        elif content_lower.count('wine') > 10:
            return 'wine'
        elif 'brunch' in content_lower:
            return 'brunch'
        elif 'lunch' in content_lower and content_lower.count('lunch') > 3:
            return 'lunch'
        else:
            return 'dinner'  # Default
    
    def _calculate_pricing_stats(self, price_items: List[PriceItem]) -> Dict:
        """Calculate pricing statistics from extracted items"""
        if not price_items:
            return {
                'price_range': '$',
                'average_price': 0,
                'min_price': 0,
                'max_price': 0
            }
        
        # Extract numeric prices
        prices = []
        for item in price_items:
            price_str = item.price.replace('$', '').replace(',', '')
            try:
                price = float(price_str)
                if 0 < price < 1000:  # Reasonable price range
                    prices.append(price)
            except ValueError:
                continue
        
        if not prices:
            return {
                'price_range': '$',
                'average_price': 0,
                'min_price': 0,
                'max_price': 0
            }
        
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        # Determine price range based on average
        if avg_price < 15:
            price_range = '$'
        elif avg_price < 25:
            price_range = '$$'
        elif avg_price < 40:
            price_range = '$$$'
        else:
            price_range = '$$$$'
        
        return {
            'price_range': price_range,
            'average_price': round(avg_price, 2),
            'min_price': round(min_price, 2),
            'max_price': round(max_price, 2)
        }
    
    def _calculate_confidence_score(self, price_items: List[PriceItem], content: str) -> float:
        """Calculate confidence score for extracted pricing data"""
        if not price_items:
            return 0.0
        
        score = 0.0
        
        # Base score for having price items
        score += min(len(price_items) * 0.1, 0.5)  # Max 0.5 for quantity
        
        # Boost for having categories
        categorized_items = [item for item in price_items if item.category]
        if categorized_items:
            score += 0.2
        
        # Boost for realistic price distribution
        prices = []
        for item in price_items:
            try:
                price = float(item.price.replace('$', '').replace(',', ''))
                if 0 < price < 1000:
                    prices.append(price)
            except:
                continue
        
        if len(prices) >= 3:  # Good number of valid prices
            score += 0.2
            
            # Check for reasonable price distribution
            if len(set(prices)) > 1:  # Not all the same price
                score += 0.1
        
        return min(score, 1.0)
    
    def handle_error(self, failure):
        """Handle request errors"""
        request = failure.request
        restaurant_slug = request.meta.get('restaurant_slug', 'unknown')
        self.logger.warning(f"Failed to process {request.url} for {restaurant_slug}: {failure.value}")
    
    def closed(self, reason):
        """Spider closing callback"""
        self.logger.info(f"Menu pricing spider closed: {reason}")
        self.logger.info(f"Statistics: {dict(self.stats)}")
        self.logger.info(f"Processed {self.stats['pages_processed']} pages")
        self.logger.info(f"Processed {self.stats['pdfs_processed']} PDFs")
        self.logger.info(f"Extracted {self.stats['prices_extracted']} price items")
        self.logger.info(f"Covered {len(self.stats['restaurants_processed'])} restaurants")