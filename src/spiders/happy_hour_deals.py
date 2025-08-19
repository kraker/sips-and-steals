"""
Happy Hour Deals Spider

Specialized spider for extracting structured happy hour deals from restaurant PDFs and web pages.
Focuses on timeframes, days, prices, and deal specifics rather than general menu pricing.
"""

import scrapy
import json
import re
import pypdf as PyPDF2
import io
from urllib.parse import urlparse
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from ..items import HappyHourDealsItem


@dataclass
class HappyHourDeal:
    """Structured happy hour deal data"""
    title: str
    description: Optional[str] = None
    price: Optional[str] = None
    deal_type: str = 'unknown'  # food, drink, cocktail, wine, beer
    timeframes: List[str] = field(default_factory=list)
    days_of_week: List[str] = field(default_factory=list)
    special_conditions: List[str] = field(default_factory=list)
    category: Optional[str] = None  # appetizers, cocktails, wine, beer
    raw_text: Optional[str] = None
    confidence_score: float = 1.0



class HappyHourDealsSpider(scrapy.Spider):
    name = 'happy_hour_deals'
    allowed_domains = []
    
    # Enhanced patterns for happy hour deal extraction (optimized for premium experiences)
    DEAL_PATTERNS = [
        # Premium format: "$X craft cocktails" / "$X artisanal drinks"
        r'\$(\d+(?:\.\d{2})?)\s+(craft\s+cocktails?|artisanal\s+drinks?|signature\s+cocktails?|house\s+cocktails?)',
        # Percentage off format: "X% off wine" / "Half off appetizers"
        r'(\d+%|Half|50%)\s+off\s+([a-z\s]{3,30})',
        # Premium wine format: "$X wine" / "$X glasses of wine"
        r'\$(\d+(?:\.\d{2})?)\s+(wine|glasses?\s+of\s+wine|wine\s+flights?|by\s+the\s+glass)',
        # Specific drink pricing: "$X [drink name]"
        r'\$(\d+(?:\.\d{2})?)\s+([A-Z][A-Za-z\s&\'-]{3,30}(?:cocktails?|martinis?|negronis?|spritzs?|mules?))',
        # Food specials: "$X [food item]" 
        r'\$(\d+(?:\.\d{2})?)\s+([a-z][a-z\s&\'-]{3,30}(?:appetizers?|plates?|oysters?|shareables?))',
        # Range pricing: "$X-$Y [item]"
        r'\$(\d+(?:\.\d{2})?)-\$(\d+(?:\.\d{2})?)\s+([a-z\s]{3,30})',
        # Jovanina's format: "ITEM NAME description   price" (space-separated, no $)
        r'([A-Z][A-Z\s&\'-]{3,30})\s+([a-z][^0-9\n]*?)\s{2,}(\d{1,2})(?:\s|$)',
        # "ITEM NAME description — $price" format 
        r'([A-Z][A-Z\s&\'-]{3,30})\s+([a-z][^$—]*?)\s*—\s*\$(\d+(?:\.\d{2})?)',
        # "ITEM NAME — $price" format (simple)
        r'([A-Z][A-Z\s&\'-]{3,30})\s*—\s*\$(\d+(?:\.\d{2})?)',
        # "$price each" format for special pricing
        r'\$(\d+(?:\.\d{2})?)\s+each',
        # Item followed by price on same line
        r'([A-Z][A-Z\s&\'-]{3,30})\s+([a-z][^$\n]*?)\s+\$(\d+(?:\.\d{2})?)',
        # Price followed by item name  
        r'\$(\d+(?:\.\d{2})?)\s+([A-Z][A-Za-z\s&\'-]{3,30})',
        # Simple format: "ITEM NAME   price" (for items without description)
        r'([A-Z][A-Z\s&\'-]{3,30})\s{2,}(\d{1,2})(?:\s|$)',
        # Premium descriptive format: "Expertly crafted [item] for $X"
        r'(expertly\s+crafted|artfully\s+prepared|chef\'s\s+selection)\s+([a-z\s]{3,30})\s+for\s+\$(\d+(?:\.\d{2})?)',
    ]
    
    # Time patterns for extracting happy hour schedules
    TIME_PATTERNS = [
        # "5 - 6" or "5-6" format
        r'(\d{1,2})\s*[-–]\s*(\d{1,2})',
        # "5:00 - 6:00" or "5:00-6:00" format  
        r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})',
        # "All Day" format
        r'All\s+Day',
        # Time with AM/PM
        r'(\d{1,2}(?::\d{2})?)\s*(AM|PM)',
    ]
    
    # Day patterns for extracting day ranges
    DAY_PATTERNS = [
        # Full day names
        r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
        # Day abbreviations
        r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b',
        # "Weekday" and "Weekend" terms
        r'\b(Weekday|Weekend|Daily)\b',
    ]
    
    # Category classification patterns (enhanced for premium experiences)
    CATEGORY_PATTERNS = {
        'craft_cocktails': ['craft cocktail', 'artisanal drink', 'signature cocktail', 'house cocktail', 'mixologist special'],
        'premium_cocktails': ['negroni', 'martini', 'old fashioned', 'manhattan', 'sazerac', 'boulevardier'],
        'wine': ['wine', 'chardonnay', 'pinot', 'cabernet', 'merlot', 'rosé', 'wine flight', 'by the glass'],
        'beer': ['beer', 'pilsner', 'stout', 'lager', 'ale', 'brewing', 'craft beer', 'local beer'],
        'premium_spirits': ['whiskey', 'bourbon', 'rye', 'scotch', 'vodka', 'gin', 'rum', 'tequila', 'mezcal'],
        'appetizers': ['appetizer', 'small plate', 'starter', 'shareables', 'bites', 'amuse bouche'],
        'oysters': ['oyster', 'raw bar', 'shellfish', 'bivalve'],
        'charcuterie': ['charcuterie', 'cheese board', 'cured meat', 'artisanal cheese'],
        'elevated_food': ['chef selection', 'seasonal special', 'artfully prepared', 'expertly crafted'],
        'international': ['panino', 'pizza', 'pasta', 'sushi', 'tapas', 'dim sum'],
        'seafood': ['crudo', 'ceviche', 'seafood', 'fish', 'salmon', 'tuna']
    }
    
    # Location/restriction patterns
    LOCATION_PATTERNS = [
        r'(?:available\s+)?only\s+at\s+the\s+(bar|patio|dining\s+room)',
        r'bar\s+only',
        r'(dining\s+room|restaurant)\s+only',
        r'(minimum\s+\d+.*?order)',
        r'(limited\s+time|while\s+supplies\s+last)',
    ]
    
    def __init__(self, discovered_pages_file='data/discovered_urls.json', 
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
            'deals_extracted': 0,
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
        """Generate requests for happy hour content discovery"""
        
        # Process discovered pages with high likelihood of happy hour content
        for page in self.discovered_pages:
            likelihood = page.get('happy_hour_likelihood', 0)
            if likelihood >= 0.7:  # Higher threshold for happy hour focus
                url = page.get('url', '')
                if url and 'happy' in url.lower():  # Prioritize happy hour URLs
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_happy_hour_page,
                        meta={
                            'restaurant_slug': page.get('restaurant_slug'),
                            'restaurant_name': page.get('restaurant_name'),
                            'page_data': page
                        },
                        errback=self.handle_error
                    )
        
        # Process discovered links with high happy hour relevance
        for link in self.discovered_links:
            relevance = link.get('happy_hour_relevance_score', 0)
            url = link.get('url', '')
            anchor_text = link.get('anchor_text', '').lower()
            
            # Focus on happy hour specific content
            should_process = (
                relevance >= 0.7 or  # High relevance score
                'happy hour' in anchor_text or  # Happy hour anchor text
                'happy' in url.lower() or  # Happy hour in URL
                (url.lower().endswith('.pdf') and 'happy' in url.lower())  # Happy hour PDFs
            )
            
            if should_process and url:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_happy_hour_page,
                    meta={
                        'restaurant_slug': link.get('restaurant_slug'),
                        'restaurant_name': link.get('restaurant_slug'),  # Use slug as fallback
                        'page_data': link,
                        'is_discovered_link': True
                    },
                    errback=self.handle_error
                )
    
    def parse_happy_hour_page(self, response):
        """Parse page for happy hour deals"""
        restaurant_slug = response.meta['restaurant_slug']
        restaurant_name = response.meta['restaurant_name']
        page_data = response.meta['page_data']
        
        self.logger.info(f"Extracting happy hour deals from {response.url} for {restaurant_name}")
        self.stats['pages_processed'] += 1
        self.stats['restaurants_processed'].add(restaurant_slug)
        
        # Determine content type
        content_type = response.headers.get('content-type', b'').decode('utf-8').lower()
        
        if 'pdf' in content_type or response.url.lower().endswith('.pdf'):
            yield from self._process_pdf_content(response, restaurant_slug, restaurant_name)
        else:
            yield from self._process_html_content(response, restaurant_slug, restaurant_name)
    
    def _process_html_content(self, response, restaurant_slug: str, restaurant_name: str):
        """Process HTML content for happy hour deals"""
        # Extract text content
        text_content = ' '.join(response.css('*::text').getall())
        
        # Extract happy hour deals
        deals = self._extract_happy_hour_deals(text_content)
        
        if deals:
            # Extract timeframes and days from content
            timeframes = self._extract_timeframes(text_content)
            days = self._extract_days(text_content)
            location_restrictions = self._extract_location_restrictions(text_content)
            
            self.stats['deals_extracted'] += len(deals)
            
            yield HappyHourDealsItem(
                url=response.url,
                restaurant_slug=restaurant_slug,
                restaurant_name=restaurant_name,
                happy_hour_deals=[deal.__dict__ for deal in deals],
                timeframes_found=timeframes,
                days_found=days,
                location_restrictions=location_restrictions,
                content_type='text/html',
                scraped_at=datetime.now().isoformat(),
                confidence_score=self._calculate_confidence_score(deals, text_content),
                raw_content_preview=text_content[:1000]
            )
    
    def _process_pdf_content(self, response, restaurant_slug: str, restaurant_name: str):
        """Process PDF content for happy hour deals"""
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
            
            # DEBUG: Log PDF content for analysis
            self.logger.info(f"PDF content preview for {response.url[:50]}...: {text_content[:300]}...")
            
            # Extract happy hour deals from PDF text
            deals = self._extract_happy_hour_deals(text_content)
            
            if deals:
                # Extract timeframes and days from content
                timeframes = self._extract_timeframes(text_content)
                days = self._extract_days(text_content)
                location_restrictions = self._extract_location_restrictions(text_content)
                
                self.stats['deals_extracted'] += len(deals)
                
                yield HappyHourDealsItem(
                    url=response.url,
                    restaurant_slug=restaurant_slug,
                    restaurant_name=restaurant_name,
                    happy_hour_deals=[deal.__dict__ for deal in deals],
                    timeframes_found=timeframes,
                    days_found=days,
                    location_restrictions=location_restrictions,
                    content_type='application/pdf',
                    scraped_at=datetime.now().isoformat(),
                    confidence_score=self._calculate_confidence_score(deals, text_content),
                    raw_content_preview=text_content[:1000]
                )
                
        except Exception as e:
            self.logger.error(f"Error processing PDF {response.url}: {e}")
    
    def _extract_happy_hour_deals(self, text_content: str) -> List[HappyHourDeal]:
        """Extract structured happy hour deals from text content"""
        deals = []
        
        # Split content into sections and lines for better parsing
        sections = self._split_content_into_sections(text_content)
        
        for section_name, section_content in sections.items():
            lines = section_content.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or len(line) < 5:
                    continue
                
                # Try to extract deals from this line
                line_deals = self._extract_deals_from_line(line, section_name)
                deals.extend(line_deals)
        
        return deals
    
    def _split_content_into_sections(self, text_content: str) -> Dict[str, str]:
        """Split content into logical sections (FROM THE KITCHEN, FROM THE BAR, etc.)"""
        sections = {'general': ''}
        current_section = 'general'
        
        lines = text_content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check if this line starts a new section
            if re.search(r'^FROM\s+THE\s+(KITCHEN|BAR|TAP):', line, re.IGNORECASE):
                if 'kitchen' in line.lower():
                    current_section = 'food'
                elif 'bar' in line.lower():
                    current_section = 'cocktails'
                elif 'tap' in line.lower():
                    current_section = 'beer_wine'
                else:
                    current_section = 'drinks'
                sections[current_section] = ''
            else:
                sections[current_section] += line + '\n'
        
        return sections
    
    def _extract_deals_from_line(self, line: str, section_type: str) -> List[HappyHourDeal]:
        """Extract deals from a single line of text"""
        deals = []
        
        # Try each deal pattern
        for pattern in self.DEAL_PATTERNS:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                deal = self._create_deal_from_match(match, pattern, line, section_type)
                if deal:
                    deals.append(deal)
        
        return deals
    
    def _create_deal_from_match(self, match: tuple, pattern: str, line: str, section_type: str) -> Optional[HappyHourDeal]:
        """Create a HappyHourDeal object from a regex match"""
        try:
            # Handle different pattern formats
            if len(match) == 4:  # Range pricing: (price1, price2, item)
                price1, price2, item = match[0], match[1], match[2]
                title = item.strip()
                description = f"{price1}-{price2} pricing"
                price = f"${price1}-${price2}"
            elif len(match) == 3:
                # Check if first element is percentage off
                if 'off' in pattern and ('%' in match[0] or 'Half' in match[0]):
                    # Percentage off format: (percentage, item)
                    percentage, item = match[0], match[1]
                    title = item.strip()
                    description = f"{percentage} off"
                    price = percentage
                else:
                    # Standard (title, description, price) format
                    title, description, price = match
                    title = title.strip()
                    description = description.strip() if description else None
                    # Add $ if not present
                    if not price.startswith('$'):
                        price = f"${price}"
            elif len(match) == 2:  # (title, price) or (price, title)
                if match[0].replace('.', '').replace('$', '').isdigit():  # price first
                    price, title = match
                    if not price.startswith('$'):
                        price = f"${price}"
                    title = title.strip()
                    description = None
                else:  # title first
                    title, price = match
                    title = title.strip()
                    if not price.startswith('$'):
                        price = f"${price}"
                    description = None
            else:
                return None
            
            # Skip if title is too short or contains problematic terms
            if len(title) < 3 or any(term in title.lower() for term in ['minimum', 'each', 'order']):
                return None
            
            # Determine deal type and category
            deal_type, category = self._classify_deal(title, description, section_type)
            
            # Validate price range (reasonable happy hour pricing)
            try:
                # Handle percentage-based deals
                if '%' in price or 'Half' in price:
                    # Percentage deals are always valid
                    pass  
                elif '-' in price:
                    # Range pricing - validate both ends
                    price_parts = price.replace('$', '').split('-')
                    if len(price_parts) == 2:
                        low, high = float(price_parts[0]), float(price_parts[1])
                        if low < 3 or high > 50:  # Reasonable happy hour range
                            return None
                else:
                    # Single price validation
                    price_float = float(price.replace('$', ''))
                    if price_float < 3 or price_float > 50:  # Reasonable happy hour range
                        return None
            except ValueError:
                # If we can't parse price, skip validation for percentage deals
                if not ('%' in price or 'Half' in price or 'off' in price):
                    return None
            
            return HappyHourDeal(
                title=title,
                description=description,
                price=price,
                deal_type=deal_type,
                category=category,
                raw_text=line,
                confidence_score=0.9  # High confidence for pattern matches
            )
            
        except Exception as e:
            self.logger.debug(f"Error creating deal from match {match}: {e}")
            return None
    
    def _classify_deal(self, title: str, description: str, section_type: str) -> Tuple[str, str]:
        """Classify deal type and category based on content"""
        title_lower = title.lower()
        desc_lower = (description or '').lower()
        combined = f"{title_lower} {desc_lower}"
        
        # Use section type as primary indicator
        if section_type == 'food':
            deal_type = 'food'
        elif section_type in ['cocktails', 'drinks']:
            deal_type = 'drink'
        elif section_type == 'beer_wine':
            deal_type = 'drink'
        else:
            # Auto-detect based on keywords
            if any(keyword in combined for keyword in ['cocktail', 'spritz', 'negroni', 'martini']):
                deal_type = 'drink'
            elif any(keyword in combined for keyword in ['wine', 'chardonnay', 'rosé', 'pinot']):
                deal_type = 'drink'
            elif any(keyword in combined for keyword in ['beer', 'pilsner', 'stout', 'brewing']):
                deal_type = 'drink'
            elif any(keyword in combined for keyword in ['food', 'panino', 'pizza', 'oyster']):
                deal_type = 'food'
            else:
                deal_type = 'unknown'
        
        # Determine specific category
        category = None
        for cat, keywords in self.CATEGORY_PATTERNS.items():
            if any(keyword in combined for keyword in keywords):
                category = cat
                break
        
        return deal_type, category
    
    def _extract_timeframes(self, text_content: str) -> List[str]:
        """Extract happy hour timeframes from content"""
        timeframes = []
        
        for pattern in self.TIME_PATTERNS:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 2 and match[0].isdigit() and match[1].isdigit():
                        # "5 - 6" format
                        timeframes.append(f"{match[0]}:00 PM - {match[1]}:00 PM")
                    elif len(match) == 2 and ':' in match[0]:
                        # "5:00 - 6:00" format
                        timeframes.append(f"{match[0]} - {match[1]}")
                    elif len(match) == 2 and match[1] in ['AM', 'PM']:
                        # "5 PM" format
                        timeframes.append(f"{match[0]} {match[1]}")
                else:
                    # "All Day" format
                    timeframes.append(match)
        
        return list(set(timeframes))  # Remove duplicates
    
    def _extract_days(self, text_content: str) -> List[str]:
        """Extract days of week from content"""
        days = []
        
        for pattern in self.DAY_PATTERNS:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            days.extend([day.title() for day in matches])
        
        return list(set(days))  # Remove duplicates
    
    def _extract_location_restrictions(self, text_content: str) -> List[str]:
        """Extract location restrictions and special conditions"""
        restrictions = []
        
        for pattern in self.LOCATION_PATTERNS:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    restrictions.append(' '.join(match).strip())
                else:
                    restrictions.append(match.strip())
        
        return restrictions
    
    def _calculate_confidence_score(self, deals: List[HappyHourDeal], content: str) -> float:
        """Calculate confidence score for extracted deals (enhanced for premium experiences)"""
        if not deals:
            return 0.0
        
        score = 0.0
        
        # Base score for having deals
        score += min(len(deals) * 0.1, 0.5)  # Max 0.5 for quantity
        
        # Boost for happy hour context
        if 'happy hour' in content.lower():
            score += 0.3
        
        # Boost for having prices
        deals_with_prices = [d for d in deals if d.price]
        if deals_with_prices:
            score += 0.2
        
        # Premium experience bonuses
        premium_keywords = ['craft', 'artisanal', 'signature', 'house', 'expertly', 'artfully', 'chef']
        for deal in deals:
            combined_text = f"{deal.title} {deal.description or ''}".lower()
            
            # Bonus for premium language
            if any(keyword in combined_text for keyword in premium_keywords):
                score += 0.1
            
            # Bonus for specific pricing (vs generic "Happy Hour")
            if deal.price and ('$' in deal.price or '%' in deal.price):
                score += 0.1
            
            # Bonus for category classification
            if deal.category:
                score += 0.05
        
        return min(score, 1.0)
    
    def handle_error(self, failure):
        """Handle request errors"""
        request = failure.request
        restaurant_slug = request.meta.get('restaurant_slug', 'unknown')
        self.logger.warning(f"Failed to process {request.url} for {restaurant_slug}: {failure.value}")
    
    def closed(self, reason):
        """Spider closing callback"""
        self.logger.info(f"Happy hour deals spider closed: {reason}")
        self.logger.info(f"Statistics: {dict(self.stats)}")
        self.logger.info(f"Processed {self.stats['pages_processed']} pages")
        self.logger.info(f"Processed {self.stats['pdfs_processed']} PDFs")
        self.logger.info(f"Extracted {self.stats['deals_extracted']} happy hour deals")
        self.logger.info(f"Covered {len(self.stats['restaurants_processed'])} restaurants")