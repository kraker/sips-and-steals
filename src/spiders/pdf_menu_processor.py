"""
PDF Menu Processing Spider

Processes discovered PDF menu URLs to extract structured menu data,
pricing information, and special deals. Supports the expanded deals
architecture beyond just happy hours.
"""

import scrapy
import json
import re
import pypdf
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

from ..items import DealItem
from ..models.deals import (
    DealType, MenuFormat, ItemCategory, DataQuality,
    RawMenuExtraction, MenuItem, DealMenu,
    classify_deal_type
)


class PDFMenuProcessorSpider(scrapy.Spider):
    name = 'pdf_menu_processor'
    
    # PDF menu keywords for deal identification
    DEAL_KEYWORDS = {
        'happy_hour': ['happy hour', 'hh special', 'cocktail hour', 'drink special'],
        'brunch': ['brunch', 'bottomless', 'unlimited mimosa', 'breakfast'],
        'early_bird': ['early bird', 'early dinner', 'sunset menu'],
        'late_night': ['late night', 'after hours', 'midnight menu'],
        'daily_special': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'taco tuesday', 'wine wednesday'],
        'prix_fixe': ['prix fixe', 'tasting menu', 'chef selection', 'fixed price'],
        'seasonal': ['seasonal', 'holiday', 'winter', 'summer', 'spring', 'fall']
    }
    
    # Pricing patterns for menu extraction
    PRICING_PATTERNS = [
        # Standard "$12.95" or "$12" format
        r'\$(\d+(?:\.\d{2})?)',
        # "12.95" without dollar sign
        r'(\d+\.\d{2})(?!\d)',
        # Range pricing "$8-12"
        r'\$(\d+)-\$?(\d+)',
        # "Market Price" or "MP" indicators
        r'(market\s+price|mp|seasonal\s+pricing)',
    ]
    
    # Menu item patterns
    ITEM_PATTERNS = [
        # "ITEM NAME description $price"
        r'([A-Z][A-Z\s&\'-]{3,50})\s+([a-z][^$\n]*?)\s+\$(\d+(?:\.\d{2})?)',
        # "ITEM NAME $price"
        r'([A-Z][A-Z\s&\'-]{3,50})\s+\$(\d+(?:\.\d{2})?)',
        # "$price ITEM NAME"
        r'\$(\d+(?:\.\d{2})?)\s+([A-Z][A-Za-z\s&\'-]{3,50})',
    ]

    def start_requests(self):
        """Generate requests for discovered PDF menu URLs"""
        
        # Load discovered URLs
        with open('data/discovered_urls.json', 'r') as f:
            discovered_data = json.load(f)
        
        pdf_urls = []
        for page in discovered_data.get('pages', []):
            if page.get('content_type') == 'application/pdf':
                url = page.get('url', '')
                restaurant_slug = page.get('restaurant_slug', '')
                
                # Filter for menu-related PDFs
                if self._is_menu_pdf(url):
                    pdf_urls.append((url, restaurant_slug))
        
        self.logger.info(f"Found {len(pdf_urls)} PDF menu URLs to process")
        
        for url, restaurant_slug in pdf_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_pdf_menu,
                meta={
                    'restaurant_slug': restaurant_slug,
                    'pdf_url': url
                },
                errback=self.handle_pdf_error
            )

    def _is_menu_pdf(self, url: str) -> bool:
        """Check if PDF URL appears to be a menu"""
        url_lower = url.lower()
        menu_indicators = [
            'menu', 'happy-hour', 'brunch', 'dinner', 'lunch', 
            'specials', 'drinks', 'cocktails', 'food', 'prix',
            'tasting', 'seasonal'
        ]
        
        return any(indicator in url_lower for indicator in menu_indicators)

    def parse_pdf_menu(self, response):
        """Extract and process PDF menu content"""
        
        restaurant_slug = response.meta['restaurant_slug']
        pdf_url = response.meta['pdf_url']
        
        self.logger.info(f"Processing PDF menu for {restaurant_slug}: {pdf_url}")
        
        try:
            # Extract text from PDF
            pdf_text = self._extract_pdf_text(response.body)
            if not pdf_text:
                self.logger.warning(f"No text extracted from PDF: {pdf_url}")
                return
            
            # Create raw menu extraction record
            raw_extraction = self._create_raw_extraction(
                restaurant_slug, pdf_url, pdf_text, response
            )
            
            # Process for deals and menu items
            deals_found = self._extract_deals_from_pdf(
                pdf_text, restaurant_slug, pdf_url
            )
            
            # Yield raw extraction record
            yield self._create_raw_menu_item(raw_extraction)
            
            # Yield discovered deals
            for deal in deals_found:
                yield deal
                
        except Exception as e:
            self.logger.error(f"Error processing PDF {pdf_url}: {e}")
            yield self._create_error_item(restaurant_slug, pdf_url, str(e))

    def _extract_pdf_text(self, pdf_bytes: bytes) -> Optional[str]:
        """Extract text from PDF bytes using pypdf"""
        try:
            pdf_file = BytesIO(pdf_bytes)
            reader = pypdf.PdfReader(pdf_file)
            
            text = ""
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                except Exception as e:
                    self.logger.warning(f"Could not extract text from page {page_num + 1}: {e}")
                    continue
            
            return text.strip() if text.strip() else None
            
        except Exception as e:
            self.logger.error(f"PDF text extraction failed: {e}")
            return None

    def _create_raw_extraction(self, restaurant_slug: str, pdf_url: str, 
                               pdf_text: str, response) -> Dict:
        """Create raw menu extraction record"""
        
        # Get PDF metadata
        pdf_metadata = {
            'content_length': len(response.body),
            'content_type': response.headers.get('Content-Type', b'').decode(),
            'last_modified': response.headers.get('Last-Modified', b'').decode(),
            'url_parsed': urlparse(pdf_url)._asdict()
        }
        
        return {
            'extraction_id': f"pdf_{restaurant_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'restaurant_slug': restaurant_slug,
            'menu_url': pdf_url,
            'menu_format': MenuFormat.PDF.value,
            'extracted_at': datetime.now().isoformat(),
            'raw_text': pdf_text,
            'pdf_metadata': pdf_metadata,
            'file_size': len(response.body),
            'extraction_success': True,
            'processor_version': '1.0'
        }

    def _extract_deals_from_pdf(self, pdf_text: str, restaurant_slug: str, 
                                pdf_url: str) -> List[DealItem]:
        """Extract deals and menu items from PDF text"""
        
        deals = []
        text_lower = pdf_text.lower()
        
        # Look for sections containing deal keywords
        for deal_type, keywords in self.DEAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Extract section around keyword
                    section_text = self._extract_section_around_keyword(
                        pdf_text, keyword
                    )
                    
                    if section_text:
                        deal = self._create_deal_from_section(
                            section_text, deal_type, restaurant_slug, pdf_url
                        )
                        if deal:
                            deals.append(deal)
        
        # If no specific deals found, try to extract general menu items
        if not deals:
            general_items = self._extract_general_menu_items(pdf_text)
            if general_items:
                deal = self._create_general_menu_deal(
                    general_items, restaurant_slug, pdf_url
                )
                if deal:
                    deals.append(deal)
        
        return deals

    def _extract_section_around_keyword(self, text: str, keyword: str, 
                                        context_lines: int = 5) -> str:
        """Extract text section around a keyword"""
        lines = text.split('\n')
        keyword_lower = keyword.lower()
        
        for i, line in enumerate(lines):
            if keyword_lower in line.lower():
                # Extract context around the keyword
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                return '\n'.join(lines[start:end])
        
        return ""

    def _create_deal_from_section(self, section_text: str, deal_type: str,
                                  restaurant_slug: str, pdf_url: str) -> Optional[DealItem]:
        """Create a deal item from a text section"""
        
        # Extract pricing information
        prices = self._extract_prices_from_text(section_text)
        
        # Extract times (basic patterns)
        times = self._extract_times_from_text(section_text)
        
        # Extract days
        days = self._extract_days_from_text(section_text)
        
        # Create deal item
        deal = DealItem()
        deal['title'] = f"{deal_type.replace('_', ' ').title()} Menu"
        deal['description'] = f"From PDF menu: {section_text[:200]}..."
        deal['deal_type'] = deal_type
        deal['prices'] = prices
        deal['days_of_week'] = days
        
        if times:
            deal['start_time'] = times.get('start_time')
            deal['end_time'] = times.get('end_time')
        
        # Metadata
        deal['restaurant_slug'] = restaurant_slug
        deal['source_url'] = pdf_url
        deal['extraction_method'] = 'pdf_section_analysis'
        deal['confidence_score'] = 0.7  # Medium confidence for PDF extraction
        deal['scraped_at'] = datetime.now().isoformat()
        deal['source_text'] = section_text
        
        return deal

    def _extract_prices_from_text(self, text: str) -> List[Dict]:
        """Extract pricing information from text"""
        prices = []
        
        for pattern in self.PRICING_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Range pricing
                    if len(match) == 2:
                        prices.append({
                            'type': 'range',
                            'min_price': float(match[0]),
                            'max_price': float(match[1])
                        })
                else:
                    # Single price
                    try:
                        price_value = float(match.replace('$', ''))
                        prices.append({
                            'type': 'fixed',
                            'price': price_value
                        })
                    except ValueError:
                        continue
        
        return prices[:10]  # Limit to 10 prices

    def _extract_times_from_text(self, text: str) -> Dict:
        """Extract time information from text"""
        time_patterns = [
            r'(\d{1,2}):?(\d{2})?\s*(am|pm)\s*-\s*(\d{1,2}):?(\d{2})?\s*(am|pm)',
            r'(\d{1,2})\s*(am|pm)\s*-\s*(\d{1,2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    'start_time': match.group(1),
                    'end_time': match.group(3) if len(match.groups()) >= 3 else None,
                    'raw_match': match.group(0)
                }
        
        return {}

    def _extract_days_from_text(self, text: str) -> List[str]:
        """Extract day information from text"""
        days = []
        day_patterns = [
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(mon|tue|wed|thu|fri|sat|sun)\b',
            r'\b(weekday|weekend|daily)\b'
        ]
        
        for pattern in day_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.lower() == 'weekday':
                    days.extend(['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
                elif match.lower() == 'weekend':
                    days.extend(['saturday', 'sunday'])
                elif match.lower() == 'daily':
                    days.extend(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'])
                else:
                    # Map abbreviations
                    day_map = {
                        'mon': 'monday', 'tue': 'tuesday', 'wed': 'wednesday',
                        'thu': 'thursday', 'fri': 'friday', 'sat': 'saturday', 'sun': 'sunday'
                    }
                    full_day = day_map.get(match.lower(), match.lower())
                    if full_day not in days:
                        days.append(full_day)
        
        return days

    def _extract_general_menu_items(self, text: str) -> List[Dict]:
        """Extract general menu items with pricing"""
        items = []
        
        for pattern in self.ITEM_PATTERNS:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                if len(match) == 3:
                    # Name, description, price
                    items.append({
                        'name': match[0].strip(),
                        'description': match[1].strip(),
                        'price': float(match[2])
                    })
                elif len(match) == 2:
                    # Name and price
                    items.append({
                        'name': match[0].strip() if match[0].replace('$', '').replace('.', '').isdigit() == False else match[1].strip(),
                        'price': float(match[1] if match[0].replace('$', '').replace('.', '').isdigit() == False else match[0])
                    })
        
        return items[:20]  # Limit to 20 items

    def _create_general_menu_deal(self, items: List[Dict], restaurant_slug: str,
                                  pdf_url: str) -> Optional[DealItem]:
        """Create a general menu deal from extracted items"""
        
        if not items:
            return None
        
        deal = DealItem()
        deal['title'] = "Menu Items"
        deal['description'] = f"Extracted {len(items)} menu items from PDF"
        deal['deal_type'] = 'menu_items'
        deal['prices'] = [{'item': item['name'], 'price': item['price']} for item in items]
        
        # Metadata
        deal['restaurant_slug'] = restaurant_slug
        deal['source_url'] = pdf_url
        deal['extraction_method'] = 'pdf_menu_parsing'
        deal['confidence_score'] = 0.6  # Lower confidence for general extraction
        deal['scraped_at'] = datetime.now().isoformat()
        
        return deal

    def _create_raw_menu_item(self, raw_extraction: Dict):
        """Create scrapy item for raw menu extraction"""
        from ..items import RestaurantPageItem
        
        item = RestaurantPageItem()
        item['url'] = raw_extraction['menu_url']
        item['title'] = f"PDF Menu: {raw_extraction['restaurant_slug']}"
        item['restaurant_slug'] = raw_extraction['restaurant_slug']
        item['content_type'] = 'application/pdf'
        item['extracted_at'] = raw_extraction['extracted_at']
        item['extraction_success'] = raw_extraction['extraction_success']
        item['raw_content'] = raw_extraction['raw_text'][:1000]  # First 1000 chars
        
        return item

    def _create_error_item(self, restaurant_slug: str, pdf_url: str, error: str):
        """Create error record for failed PDF processing"""
        from ..items import RestaurantPageItem
        
        item = RestaurantPageItem()
        item['url'] = pdf_url
        item['title'] = f"PDF Error: {restaurant_slug}"
        item['restaurant_slug'] = restaurant_slug
        item['extraction_success'] = False
        item['error_message'] = error
        item['extracted_at'] = datetime.now().isoformat()
        
        return item

    def handle_pdf_error(self, failure):
        """Handle PDF processing errors"""
        restaurant_slug = failure.request.meta.get('restaurant_slug', 'unknown')
        pdf_url = failure.request.url
        
        self.logger.error(f"Failed to process PDF {pdf_url} for {restaurant_slug}: {failure.value}")
        
        return self._create_error_item(restaurant_slug, pdf_url, str(failure.value))