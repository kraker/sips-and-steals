"""
Happy Hour Deal Extraction Spider

Extracts deal information from discovered pages using our proven data-hungry approach.
Captures rich extraction context for semantic analysis and intelligent deduplication.
"""

import scrapy
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin

from ..items import DealItem


class ExtractionSpider(scrapy.Spider):
    name = 'extractor'
    
    # Time extraction patterns (proven from our PoC)
    TIME_PATTERNS = [
        # Standard ranges: "3 PM - 6 PM", "3:00 PM - 6:00 PM"
        r'(\d{1,2})\s*(?::\d{2})?\s*(am|pm|AM|PM)\s*[–\-~]\s*(\d{1,2})\s*(?::\d{2})?\s*(am|pm|AM|PM)',
        
        # Compact ranges: "3-6 PM", "3-6PM"
        r'(\d{1,2})\s*[–\-~]\s*(\d{1,2})\s*(pm|am|PM|AM)',
        
        # Time to close: "9 PM-Close", "9PM-Close"
        r'(\d{1,2})\s*(?::\d{2})?\s*(pm|am|PM|AM)\s*[–\-~]\s*(close|Close|CLOSE)',
        
        # Compact close format: "9PM-Close"
        r'(\d{1,2})(PM|AM|pm|am)[–\-~](close|Close|CLOSE)',
        
        # All day patterns
        r'all\s+day',
        r'daily',
    ]
    
    # Day extraction patterns (proven from our PoC) 
    DAY_PATTERNS = [
        # Day ranges
        r'monday\s*[–\-~]\s*friday',
        r'mon\s*[–\-~]\s*fri', 
        r'weekdays?',
        r'every\s+day',
        r'daily',
        r'thurs?\s*[–\-~]\s*sat',
        r'thursday\s*[–\-~]\s*saturday',
        
        # Individual days
        r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\b(?:mon|tue|wed|thu|fri|sat|sun)\b',
        
        # Special patterns
        r'weekends?',
        r'week\s*ends?',
    ]
    
    # Content sections to analyze (where deals are typically found)
    CONTENT_SELECTORS = [
        'main', 'article', 'section', '.content', '#content',
        '.menu', '.specials', '.happy-hour', '.deals',
        '.hours', '.dining', '.bar', '.restaurant-info',
        'p', 'div', 'span', 'li'
    ]
    
    def __init__(self, input_file='data/discovered_pages.json', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_file = input_file
        self.discovered_pages = self._load_discovered_pages()
        
        # Statistics tracking
        self.stats = {
            'pages_processed': 0,
            'deals_extracted': 0,
            'restaurants_with_deals': set(),
        }
    
    def _load_discovered_pages(self) -> List[Dict]:
        """Load discovered pages from discovery spider output"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Handle different formats
                if isinstance(data, list):
                    # Direct array format
                    return data
                elif isinstance(data, dict) and 'pages' in data:
                    # Object format with 'pages' key (our current format)
                    return data['pages']
                else:
                    # Try JSONL format - one item per line
                    content = f.read().strip()
                    pages = []
                    for line in content.split('\n'):
                        if line.strip():
                            pages.append(json.loads(line))
                    return pages
        except FileNotFoundError:
            self.logger.error(f"Discovered pages file not found: {self.input_file}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in discovered pages file: {e}")
            return []
    
    def start_requests(self):
        """Generate requests for discovered pages with high happy hour likelihood"""
        # Sort by likelihood score, process highest-scoring pages first
        sorted_pages = sorted(
            self.discovered_pages, 
            key=lambda x: x.get('happy_hour_likelihood', 0), 
            reverse=True
        )
        
        for page in sorted_pages:
            likelihood = page.get('happy_hour_likelihood', 0)
            
            # Only process pages with decent likelihood scores
            if likelihood > 0.3:
                yield scrapy.Request(
                    url=page['url'],
                    callback=self.parse_deals,
                    meta={
                        'restaurant_slug': page['restaurant_slug'],
                        'restaurant_name': page['restaurant_name'],
                        'discovery_likelihood': likelihood,
                        'discovered_keywords': page.get('content_keywords', [])
                    },
                    errback=self.handle_error
                )
    
    def parse_deals(self, response):
        """Extract deals from a page using data-hungry approach"""
        restaurant_slug = response.meta['restaurant_slug']
        restaurant_name = response.meta['restaurant_name']
        discovery_likelihood = response.meta.get('discovery_likelihood', 0)
        
        self.logger.info(f"Extracting deals from {restaurant_name}: {response.url}")
        self.stats['pages_processed'] += 1
        
        # Apply our proven universal extraction approach
        deals = self._extract_deals_from_page(response, restaurant_slug, restaurant_name)
        
        if deals:
            self.stats['restaurants_with_deals'].add(restaurant_slug)
            self.stats['deals_extracted'] += len(deals)
            self.logger.info(f"Found {len(deals)} deals for {restaurant_name}")
            
            for deal in deals:
                yield deal
        else:
            self.logger.debug(f"No deals found for {restaurant_name} at {response.url}")
    
    def _extract_deals_from_page(self, response, restaurant_slug: str, restaurant_name: str) -> List[DealItem]:
        """Extract deals using our proven data-hungry approach"""
        deals = []
        
        # Extract all content sections for analysis
        content_sections = self._get_content_sections(response)
        
        for section_selector, section_html, section_text in content_sections:
            # Look for time and day patterns in this section
            time_matches = self._find_time_patterns(section_text)
            day_matches = self._find_day_patterns(section_text)
            
            # If we found relevant patterns, create deals (data-hungry approach)
            if time_matches or day_matches or self._contains_happy_hour_indicators(section_text):
                section_deals = self._create_deals_from_section(
                    section_text, section_html, section_selector,
                    time_matches, day_matches, 
                    restaurant_slug, restaurant_name, response.url
                )
                deals.extend(section_deals)
        
        return deals
    
    def _get_content_sections(self, response) -> List[Tuple[str, str, str]]:
        """Extract content sections for analysis"""
        sections = []
        
        for selector in self.CONTENT_SELECTORS:
            elements = response.css(selector)
            for element in elements:
                # Get both HTML and text content
                html_content = element.get()
                text_content = ' '.join(element.css('::text').getall()).strip()
                
                # Only include sections with substantial content
                if text_content and len(text_content) > 20:
                    sections.append((selector, html_content, text_content))
        
        return sections
    
    def _find_time_patterns(self, text: str) -> List[Dict]:
        """Find time patterns in text"""
        matches = []
        
        for i, pattern in enumerate(self.TIME_PATTERNS):
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append({
                    'pattern_index': i,
                    'match_text': match.group(),
                    'groups': match.groups(),
                    'start_pos': match.start(),
                    'end_pos': match.end()
                })
        
        return matches
    
    def _find_day_patterns(self, text: str) -> List[Dict]:
        """Find day patterns in text"""
        matches = []
        
        for i, pattern in enumerate(self.DAY_PATTERNS):
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append({
                    'pattern_index': i,
                    'match_text': match.group(),
                    'groups': match.groups(),
                    'start_pos': match.start(),
                    'end_pos': match.end()
                })
        
        return matches
    
    def _contains_happy_hour_indicators(self, text: str) -> bool:
        """Check if text contains happy hour indicators"""
        indicators = [
            'happy hour', 'happy-hour', 'happyhour',
            'specials', 'deals', 'après', 'apres',
            'early bird', 'late night'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in indicators)
    
    def _create_deals_from_section(self, section_text: str, section_html: str, 
                                 section_selector: str, time_matches: List[Dict], 
                                 day_matches: List[Dict], restaurant_slug: str, 
                                 restaurant_name: str, source_url: str) -> List[DealItem]:
        """Create deal items from section using data-hungry approach"""
        deals = []
        
        # Data-hungry approach: create separate deals for each significant pattern match
        
        # Create deals from time patterns
        for time_match in time_matches:
            start_time, end_time = self._parse_time_match(time_match)
            
            deal = DealItem(
                title='Happy Hour',
                description=self._create_time_description(time_match, day_matches),
                start_time=start_time,
                end_time=end_time,
                days_of_week=self._extract_days_from_matches(day_matches),
                confidence_score=self._calculate_confidence_score(time_match, day_matches, section_text),
                
                # Rich extraction context (our proven approach)
                extraction_method='universal_html_section',
                source_text=section_text[:500],  # First 500 chars
                html_context=section_html[:1000],  # First 1000 chars of HTML
                extraction_patterns=[f"time_pattern_{time_match['pattern_index']}"],
                raw_time_matches=[str(time_match['groups'])],
                raw_day_matches=[dm['match_text'] for dm in day_matches],
                
                # Metadata
                restaurant_slug=restaurant_slug,
                restaurant_name=restaurant_name,
                source_url=source_url,
                scraped_at=datetime.now().isoformat()
            )
            
            deals.append(deal)
        
        # Create deals from day patterns (even without specific times)
        if day_matches and not time_matches:
            deal = DealItem(
                title='Happy Hour',
                description=self._create_day_description(day_matches),
                days_of_week=self._extract_days_from_matches(day_matches),
                confidence_score=self._calculate_confidence_score(None, day_matches, section_text),
                
                # Rich extraction context
                extraction_method='universal_html_section',
                source_text=section_text[:500],
                html_context=section_html[:1000],
                extraction_patterns=[f"day_pattern_{dm['pattern_index']}" for dm in day_matches],
                raw_day_matches=[dm['match_text'] for dm in day_matches],
                raw_time_matches=[],
                
                # Metadata
                restaurant_slug=restaurant_slug,
                restaurant_name=restaurant_name,
                source_url=source_url,
                scraped_at=datetime.now().isoformat()
            )
            
            deals.append(deal)
        
        # Create deals from happy hour indicators (even without times/days)
        if not time_matches and not day_matches and self._contains_happy_hour_indicators(section_text):
            deal = DealItem(
                title='Happy Hour',
                description=self._create_generic_description(section_text),
                confidence_score=0.5,  # Lower confidence for generic matches
                
                # Rich extraction context
                extraction_method='universal_html_section',
                source_text=section_text[:500],
                html_context=section_html[:1000],
                extraction_patterns=['happy_hour_indicator'],
                raw_day_matches=[],
                raw_time_matches=[],
                
                # Metadata
                restaurant_slug=restaurant_slug,
                restaurant_name=restaurant_name,
                source_url=source_url,
                scraped_at=datetime.now().isoformat()
            )
            
            deals.append(deal)
        
        return deals
    
    def _parse_time_match(self, time_match: Dict) -> Tuple[Optional[str], Optional[str]]:
        """Parse time match into start and end times"""
        groups = time_match['groups']
        pattern_index = time_match['pattern_index']
        
        if pattern_index == 0:  # "3 PM - 6 PM"
            return f"{groups[0]} {groups[1]}", f"{groups[2]} {groups[3]}"
        elif pattern_index == 1:  # "3-6 PM"
            return f"{groups[0]} {groups[2]}", f"{groups[1]} {groups[2]}"
        elif pattern_index in [2, 3]:  # "9 PM-Close"
            return f"{groups[0]} {groups[1]}", "Close"
        elif pattern_index in [4, 5]:  # "all day", "daily"
            return "All Day", "All Day"
        
        return None, None
    
    def _extract_days_from_matches(self, day_matches: List[Dict]) -> List[str]:
        """Extract normalized day names from day matches"""
        days = set()
        
        for match in day_matches:
            match_text = match['match_text'].lower()
            
            # Handle day ranges
            if 'monday' in match_text and 'friday' in match_text:
                days.update(['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
            elif 'mon' in match_text and 'fri' in match_text:
                days.update(['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
            elif 'weekday' in match_text:
                days.update(['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
            elif 'every day' in match_text or 'daily' in match_text:
                days.update(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'])
            elif 'thurs' in match_text and 'sat' in match_text:
                days.update(['thursday', 'friday', 'saturday'])
            elif 'weekend' in match_text:
                days.update(['saturday', 'sunday'])
            else:
                # Individual days
                day_mapping = {
                    'monday': 'monday', 'mon': 'monday',
                    'tuesday': 'tuesday', 'tue': 'tuesday',
                    'wednesday': 'wednesday', 'wed': 'wednesday',
                    'thursday': 'thursday', 'thu': 'thursday',
                    'friday': 'friday', 'fri': 'friday',
                    'saturday': 'saturday', 'sat': 'saturday',
                    'sunday': 'sunday', 'sun': 'sunday'
                }
                
                for day_abbr, day_full in day_mapping.items():
                    if day_abbr in match_text:
                        days.add(day_full)
        
        return list(days)
    
    def _calculate_confidence_score(self, time_match: Optional[Dict], 
                                  day_matches: List[Dict], section_text: str) -> float:
        """Calculate confidence score for extracted deal"""
        score = 0.5  # Base score
        
        # Boost for time patterns
        if time_match:
            score += 0.3
        
        # Boost for day patterns
        if day_matches:
            score += 0.2
        
        # Boost for explicit happy hour mentions
        if 'happy hour' in section_text.lower():
            score += 0.3
        
        # Boost for pricing information
        if re.search(r'\$\d+', section_text):
            score += 0.1
        
        return min(score, 1.0)
    
    def _create_time_description(self, time_match: Dict, day_matches: List[Dict]) -> str:
        """Create description from time and day matches"""
        time_text = time_match['match_text']
        
        if day_matches:
            day_texts = [dm['match_text'] for dm in day_matches]
            return f"Time: {time_text} | Days: {', '.join(day_texts)}"
        else:
            return f"Time: {time_text}"
    
    def _create_day_description(self, day_matches: List[Dict]) -> str:
        """Create description from day matches"""
        day_texts = [dm['match_text'] for dm in day_matches]
        return f"Days: {', '.join(day_texts)}"
    
    def _create_generic_description(self, section_text: str) -> str:
        """Create description from generic happy hour indicators"""
        # Extract a snippet around happy hour mentions
        text_lower = section_text.lower()
        for indicator in ['happy hour', 'specials', 'deals']:
            if indicator in text_lower:
                start = max(0, text_lower.find(indicator) - 50)
                end = min(len(section_text), text_lower.find(indicator) + 100)
                return section_text[start:end].strip()
        
        return "Happy Hour mentioned"
    
    def handle_error(self, failure):
        """Handle request errors"""
        request = failure.request
        restaurant_slug = request.meta.get('restaurant_slug', 'unknown')
        
        self.logger.warning(f"Failed to extract from {request.url} for {restaurant_slug}: {failure.value}")
    
    def closed(self, reason):
        """Spider closing callback - log statistics"""
        self.logger.info(f"Extraction spider closed: {reason}")
        self.logger.info(f"Statistics: {self.stats}")
        
        # Log summary
        self.logger.info(f"Processed {self.stats['pages_processed']} pages")
        self.logger.info(f"Extracted {self.stats['deals_extracted']} deals")
        self.logger.info(f"Found deals for {len(self.stats['restaurants_with_deals'])} restaurants")