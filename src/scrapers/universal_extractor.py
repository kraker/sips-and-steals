"""
Universal Happy Hour Extractor

A scalable approach to extracting happy hour information from any restaurant website
without requiring custom configurations. Uses intelligent heuristics and pattern 
recognition to identify deal content across diverse website structures.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup
from models import Deal, DealType, DayOfWeek


logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of universal extraction with confidence scoring"""
    deals: List[Deal]
    confidence_score: float
    extraction_method: str
    content_sources: List[str]


class UniversalHappyHourExtractor:
    """
    Universal extractor that works across restaurant websites without custom configs.
    Uses intelligent content discovery and pattern recognition.
    """
    
    # Universal content container selectors in priority order
    CONTENT_CONTAINERS = [
        # Happy hour specific selectors (highest priority)
        ".happy-hour-content", ".happy-hour", ".happii-hour", 
        "[class*='happy']", "[id*='happy']", ".specials", ".deals",
        ".bar-specials", ".drink-specials", ".cocktail-hour",
        
        # Generic content areas (medium priority)
        ".main-content", "main", "article", ".content", ".page-content",
        ".menu-content", ".hours-section", ".specials-section",
        
        # Fallback areas (lowest priority)
        ".container", ".wrapper", "body"
    ]
    
    # Universal happy hour indicator keywords
    HAPPY_HOUR_KEYWORDS = [
        'happy hour', 'happii hour', 'drink specials', 'bar specials',
        'cocktail hour', 'wine hour', 'discounted drinks', 'deals',
        'all day happy', 'daily specials'
    ]
    
    # Universal time patterns (flexible regex)
    TIME_PATTERNS = [
        # Standard format: "3 PM - 5 PM", "4:00pm-6:00pm"
        r'(\d{1,2})\s*(?::\d{2})?\s*(?:(am|pm|AM|PM))?\s*[–\-~]\s*(\d{1,2})\s*(?::\d{2})?\s*(pm|am|PM|AM)',
        # Alternative with "to": "3pm to 6pm"
        r'(\d{1,2})\s*(?::\d{2})?\s*(?:(am|pm|AM|PM))?\s*(?:to)\s*(\d{1,2})\s*(?::\d{2})?\s*(pm|am|PM|AM)',
        # Colon format: "3:00 - 6:00"
        r'(\d{1,2}):(\d{2})\s*[–\-~]\s*(\d{1,2}):(\d{2})'
    ]
    
    # Universal day patterns
    DAY_PATTERNS = [
        # Day ranges
        r'(Monday\s*[\-–]\s*Friday|Tuesday\s*[\-–]\s*Friday|Saturday\s*[\-–]\s*Sunday)',
        r'(Sunday\s*[\-–]\s*Thursday|Friday\s*[\-–]\s*Saturday)',
        # Daily patterns
        r'(Every\s+Day|Daily|All\s+Day|everyday|daily)',
        # Individual days
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
        r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)'
    ]
    
    # Universal exclude patterns (content to ignore)
    EXCLUDE_PATTERNS = [
        'copyright', 'privacy policy', 'terms of service', 'footer',
        'navigation', 'header', 'social media', 'follow us', 'newsletter',
        'careers', 'gift cards', 'reservations', 'contact', 'about us',
        'catering', 'private dining', 'events', 'locations'
    ]
    
    # Restaurant operating hours patterns (to distinguish from happy hour)
    OPERATING_HOURS_PATTERNS = [
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[\s:]*\d{1,2}:\d{2}\s*[ap]m\s*[\-–]\s*\d{1,2}:\d{2}\s*[ap]m',
        r'Open\s+\d{1,2}:\d{2}\s*[ap]m\s*[\-–]\s*\d{1,2}:\d{2}\s*[ap]m',
        r'Hours?[\s:]+.*\d{1,2}:\d{2}\s*[ap]m\s*[\-–]\s*\d{1,2}:\d{2}\s*[ap]m',
        r'kitchen\s+hours?[\s:]+.*\d{1,2}:\d{2}\s*[ap]m\s*[\-–]\s*\d{1,2}:\d{2}\s*[ap]m',
        r'dining\s+hours?[\s:]+.*\d{1,2}:\d{2}\s*[ap]m\s*[\-–]\s*\d{1,2}:\d{2}\s*[ap]m',
        r'restaurant\s+hours?[\s:]+.*\d{1,2}:\d{2}\s*[ap]m\s*[\-–]\s*\d{1,2}:\d{2}\s*[ap]m'
    ]
    
    # Restaurant types that typically have higher success rates for happy hour
    HIGH_SUCCESS_RESTAURANT_TYPES = [
        'pub', 'brewery', 'bar', 'grill', 'tavern', 'gastropub', 
        'sports bar', 'wine bar', 'cocktail bar', 'american', 'casual'
    ]
    
    # Time range validation - typical happy hour times (2 PM - 8 PM range)
    VALID_HAPPY_HOUR_RANGE = (14, 20)  # 2 PM to 8 PM in 24-hour format
    
    def __init__(self):
        self.confidence_threshold = 0.5
    
    def validate_restaurant_url(self, url: str, timeout: int = 10) -> Tuple[bool, str]:
        """
        Validate that a restaurant URL is accessible before attempting extraction.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            import httpx
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; SipsAndSteals/1.0; +https://sips-and-steals.com)'
                }
                response = client.head(url, headers=headers)
                
                if response.status_code == 200:
                    return True, "URL is accessible"
                elif response.status_code == 404:
                    return False, "URL returns 404 Not Found"
                elif response.status_code >= 500:
                    return False, f"Server error: HTTP {response.status_code}"
                else:
                    return False, f"HTTP {response.status_code}"
                    
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def calculate_restaurant_type_score(self, restaurant_data: dict) -> float:
        """
        Calculate a score based on restaurant type for happy hour likelihood.
        Higher scores indicate better candidates for universal extraction.
        
        Args:
            restaurant_data: Dictionary containing 'name', 'cuisine', 'type' fields
            
        Returns:
            Float score (0.0 to 1.0) indicating extraction likelihood
        """
        score = 0.5  # Base score
        
        name = restaurant_data.get('name', '').lower()
        cuisine = restaurant_data.get('cuisine', '').lower()
        restaurant_type = restaurant_data.get('type', '').lower()
        
        # High-success type indicators in name
        for success_type in self.HIGH_SUCCESS_RESTAURANT_TYPES:
            if success_type in name:
                score += 0.2
                break
        
        # High-success type indicators in cuisine
        for success_type in self.HIGH_SUCCESS_RESTAURANT_TYPES:
            if success_type in cuisine:
                score += 0.15
                break
                
        # High-success type indicators in restaurant type
        for success_type in self.HIGH_SUCCESS_RESTAURANT_TYPES:
            if success_type in restaurant_type:
                score += 0.1
                break
        
        # Boost for specific patterns that showed success in pilot
        if any(word in name for word in ['jack', 'phantom', 'cooper', 'brother']):
            score += 0.1
        
        # Penalize fine dining (showed lower success in pilot)
        if any(word in name.lower() for word in ['steakhouse', 'fine', 'elegant', 'upscale']) or \
           any(word in cuisine for word in ['french', 'fine dining', 'steakhouse']):
            score -= 0.1
            
        return min(max(score, 0.0), 1.0)
    
    def extract_from_soup(self, soup: BeautifulSoup, url: str = None) -> ExtractionResult:
        """
        Extract happy hour deals from any restaurant website using universal patterns.
        
        Args:
            soup: BeautifulSoup parsed HTML
            url: Optional URL for context
        
        Returns:
            ExtractionResult with deals and confidence scoring
        """
        logger.info("Starting universal happy hour extraction")
        
        # Step 1: Find content sections likely to contain happy hour info
        happy_hour_sections = self._find_happy_hour_sections(soup)
        
        # Step 2: Extract deals from these sections
        deals = []
        extraction_methods = []
        content_sources = []
        
        for section, method in happy_hour_sections:
            section_deals = self._extract_deals_from_section(section)
            deals.extend(section_deals)
            extraction_methods.append(method)
            content_sources.append(self._get_section_identifier(section))
        
        # Step 3: Calculate confidence score
        confidence = self._calculate_confidence(deals, extraction_methods, soup)
        
        # Step 4: Deduplicate and clean deals
        clean_deals = self._deduplicate_deals(deals)
        
        result = ExtractionResult(
            deals=clean_deals,
            confidence_score=confidence,
            extraction_method=', '.join(set(extraction_methods)),
            content_sources=content_sources
        )
        
        logger.info(f"Universal extraction found {len(clean_deals)} deals with {confidence:.2f} confidence")
        return result
    
    def _find_happy_hour_sections(self, soup: BeautifulSoup) -> List[Tuple[BeautifulSoup, str]]:
        """Find sections likely to contain happy hour information"""
        sections = []
        
        # Method 1: Look for sections with happy hour keywords
        for keyword in self.HAPPY_HOUR_KEYWORDS:
            elements = soup.find_all(text=re.compile(keyword, re.IGNORECASE))
            for element in elements:
                section = element.parent
                sections.append((section, f"keyword:{keyword}"))
        
        # Method 2: Look for semantic content containers
        for selector in self.CONTENT_CONTAINERS:
            try:
                elements = soup.select(selector)
                for element in elements:
                    # Check if this section contains happy hour indicators
                    text = element.get_text().lower()
                    if any(keyword in text for keyword in self.HAPPY_HOUR_KEYWORDS):
                        sections.append((element, f"container:{selector}"))
            except Exception as e:
                logger.debug(f"CSS selector {selector} failed: {e}")
                continue
        
        # Method 3: Look for pricing patterns near time patterns
        pricing_elements = soup.find_all(text=re.compile(r'\$\d+', re.IGNORECASE))
        for element in pricing_elements:
            section = element.parent
            section_text = section.get_text()
            # If pricing is near time patterns, likely happy hour
            if any(re.search(pattern, section_text, re.IGNORECASE) for pattern in self.TIME_PATTERNS):
                sections.append((section, "pricing-near-time"))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_sections = []
        for section, method in sections:
            section_id = id(section)
            if section_id not in seen:
                seen.add(section_id)
                unique_sections.append((section, method))
        
        logger.debug(f"Found {len(unique_sections)} potential happy hour sections")
        return unique_sections
    
    def _extract_deals_from_section(self, section: BeautifulSoup) -> List[Deal]:
        """Extract deals from a specific section"""
        deals = []
        
        # Get text content and clean it
        text = section.get_text(separator=' ', strip=True)
        text = self._clean_text(text)
        
        # Extract time ranges
        time_ranges = self._extract_time_ranges(text)
        
        # Extract day patterns  
        day_patterns = self._extract_day_patterns(text)
        
        # Extract pricing information
        prices = self._extract_prices(text)
        
        # Combine into deals
        if time_ranges or day_patterns:
            deals.extend(self._create_deals_from_patterns(time_ranges, day_patterns, prices, text))
        
        return deals
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing noise patterns"""
        for pattern in self.EXCLUDE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove operating hours patterns that might confuse happy hour detection
        for pattern in self.OPERATING_HOURS_PATTERNS:
            # Only remove if it doesn't contain happy hour keywords
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                context = text[max(0, match.start()-50):match.end()+50].lower()
                if not any(keyword in context for keyword in self.HAPPY_HOUR_KEYWORDS):
                    text = text.replace(match.group(), '')
        
        return text.strip()
    
    def _extract_time_ranges(self, text: str) -> List[Tuple]:
        """Extract time ranges using universal patterns with context validation"""
        time_ranges = []
        
        for pattern in self.TIME_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Check context around the time range for happy hour keywords
                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 100)
                context = text[context_start:context_end].lower()
                
                # Only include time ranges that are near happy hour keywords
                has_happy_hour_context = any(keyword in context for keyword in self.HAPPY_HOUR_KEYWORDS)
                
                # Or if they fall within typical happy hour times
                time_range = match.groups()
                is_valid_happy_hour_time = self._is_valid_happy_hour_time(time_range)
                
                if has_happy_hour_context or is_valid_happy_hour_time:
                    time_ranges.append(time_range)
        
        return time_ranges
    
    def _is_valid_happy_hour_time(self, time_range: Tuple) -> bool:
        """Validate if time range falls within typical happy hour window"""
        try:
            if len(time_range) >= 4:
                hour1 = int(time_range[0])
                ampm1 = time_range[1] if len(time_range) > 1 else None
                hour2 = int(time_range[2]) if len(time_range) > 2 else None
                ampm2 = time_range[3] if len(time_range) > 3 else None
                
                # Convert to 24-hour format
                start_hour = self._to_24_hour(hour1, ampm1)
                end_hour = self._to_24_hour(hour2, ampm2) if hour2 else None
                
                if start_hour and end_hour:
                    # Check if times fall within typical happy hour range (2 PM - 8 PM)
                    return (self.VALID_HAPPY_HOUR_RANGE[0] <= start_hour <= self.VALID_HAPPY_HOUR_RANGE[1] or
                            self.VALID_HAPPY_HOUR_RANGE[0] <= end_hour <= self.VALID_HAPPY_HOUR_RANGE[1])
            
            return False
            
        except (ValueError, IndexError):
            return False
    
    def _to_24_hour(self, hour: int, ampm: Optional[str]) -> Optional[int]:
        """Convert hour to 24-hour format"""
        if not hour:
            return None
            
        if ampm and 'pm' in ampm.lower() and hour != 12:
            return hour + 12
        elif ampm and 'am' in ampm.lower() and hour == 12:
            return 0
        elif not ampm:
            # Default assumption for happy hour context
            if hour >= 1 and hour <= 11:
                return hour + 12  # Assume PM for typical happy hour times
            else:
                return hour
        else:
            return hour
    
    def _extract_day_patterns(self, text: str) -> List[str]:
        """Extract day patterns using universal patterns"""
        day_patterns = []
        
        for pattern in self.DAY_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                day_patterns.extend([g for g in match.groups() if g])
        
        return day_patterns
    
    def _extract_prices(self, text: str) -> List[str]:
        """Extract pricing information"""
        price_pattern = r'\$(\d+(?:\.\d{2})?)'
        prices = re.findall(price_pattern, text)
        return prices
    
    def _create_deals_from_patterns(self, time_ranges: List[Tuple], day_patterns: List[str], 
                                   prices: List[str], source_text: str) -> List[Deal]:
        """Create Deal objects from extracted patterns"""
        deals = []
        
        # If we have time ranges, create deals for each one
        if time_ranges:
            for time_range in time_ranges:
                deal = self._create_deal_from_time_range(time_range, day_patterns, prices, source_text)
                if deal:
                    deals.append(deal)
        
        # If we have day patterns but no time ranges, create a generic deal
        elif day_patterns:
            deal = Deal(
                title="Happy Hour",
                description=f"Found happy hour pattern: {', '.join(day_patterns[:2])}",
                deal_type=DealType.HAPPY_HOUR,
                days_of_week=self._parse_days(day_patterns),
                confidence_score=0.6
            )
            deals.append(deal)
        
        return deals
    
    def _create_deal_from_time_range(self, time_range: Tuple, day_patterns: List[str], 
                                   prices: List[str], source_text: str) -> Optional[Deal]:
        """Create a Deal from a time range pattern"""
        try:
            # Handle different time pattern formats
            if len(time_range) == 4:  # Standard format (hour1, ampm1, hour2, ampm2)
                hour1, ampm1, hour2, ampm2 = time_range
                
                # Handle shared AM/PM
                if ampm1 is None and ampm2 is not None:
                    start_time = f"{hour1} {ampm2.upper()}"
                    end_time = f"{hour2} {ampm2.upper()}"
                elif ampm1 is not None and ampm2 is not None:
                    start_time = f"{hour1} {ampm1.upper()}"
                    end_time = f"{hour2} {ampm2.upper()}"
                else:
                    start_time = f"{hour1} PM"  # Default to PM for happy hour
                    end_time = f"{hour2} PM"
            
            elif len(time_range) == 4 and ':' in str(time_range):  # Colon format
                start_time = f"{time_range[0]}:{time_range[1]}"
                end_time = f"{time_range[2]}:{time_range[3]}"
            
            else:
                logger.debug(f"Unhandled time range format: {time_range}")
                return None
            
            # Parse days
            days = self._parse_days(day_patterns) if day_patterns else []
            
            # Create description
            description = f"Time: {start_time}-{end_time}"
            if days:
                day_names = [day.value for day in days]
                description += f" | Days: {', '.join(day_names)}"
            if prices:
                description += f" | Pricing: ${', $'.join(prices[:3])}"
            
            deal = Deal(
                title="Happy Hour",
                description=description,
                deal_type=DealType.HAPPY_HOUR,
                days_of_week=days,
                start_time=start_time,
                end_time=end_time,
                confidence_score=self._calculate_deal_confidence(time_range, day_patterns, prices, source_text)
            )
            
            return deal
            
        except Exception as e:
            logger.debug(f"Error creating deal from time range {time_range}: {e}")
            return None
    
    def _parse_days(self, day_patterns: List[str]) -> List[DayOfWeek]:
        """Parse day patterns into DayOfWeek enums"""
        days = []
        
        for pattern in day_patterns:
            pattern_lower = pattern.lower().replace(' ', '').replace('-', '')
            
            # Handle ranges
            if 'mondayfriday' in pattern_lower:
                days.extend([DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                           DayOfWeek.THURSDAY, DayOfWeek.FRIDAY])
            elif 'tuesdayfriday' in pattern_lower:
                days.extend([DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY])
            elif 'saturdaysunday' in pattern_lower:
                days.extend([DayOfWeek.SATURDAY, DayOfWeek.SUNDAY])
            elif 'everyday' in pattern_lower or 'daily' in pattern_lower:
                days.extend([DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                           DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY, DayOfWeek.SUNDAY])
            
            # Handle individual days
            elif 'monday' in pattern_lower or 'mon' in pattern_lower:
                days.append(DayOfWeek.MONDAY)
            elif 'tuesday' in pattern_lower or 'tue' in pattern_lower:
                days.append(DayOfWeek.TUESDAY)
            elif 'wednesday' in pattern_lower or 'wed' in pattern_lower:
                days.append(DayOfWeek.WEDNESDAY)
            elif 'thursday' in pattern_lower or 'thu' in pattern_lower:
                days.append(DayOfWeek.THURSDAY)
            elif 'friday' in pattern_lower or 'fri' in pattern_lower:
                days.append(DayOfWeek.FRIDAY)
            elif 'saturday' in pattern_lower or 'sat' in pattern_lower:
                days.append(DayOfWeek.SATURDAY)
            elif 'sunday' in pattern_lower or 'sun' in pattern_lower:
                days.append(DayOfWeek.SUNDAY)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_days = []
        for day in days:
            if day not in seen:
                seen.add(day)
                unique_days.append(day)
        
        return unique_days
    
    def _calculate_deal_confidence(self, time_range: Tuple, day_patterns: List[str], 
                                 prices: List[str], source_text: str) -> float:
        """Calculate confidence score for a deal"""
        confidence = 0.5  # Base confidence
        
        # Boost for having time information
        if time_range:
            confidence += 0.2
        
        # Boost for having day information
        if day_patterns:
            confidence += 0.1
        
        # Boost for having pricing information
        if prices:
            confidence += 0.1
        
        # Boost for happy hour keywords in context
        text_lower = source_text.lower()
        for keyword in self.HAPPY_HOUR_KEYWORDS:
            if keyword in text_lower:
                confidence += 0.1
                break
        
        return min(confidence, 1.0)
    
    def _calculate_confidence(self, deals: List[Deal], extraction_methods: List[str], 
                            soup: BeautifulSoup) -> float:
        """Calculate overall confidence for the extraction"""
        if not deals:
            return 0.0
        
        # Base confidence from deals
        avg_deal_confidence = sum(deal.confidence_score for deal in deals) / len(deals)
        
        # Boost for specific extraction methods
        method_boost = 0.0
        if any('keyword:happy hour' in method for method in extraction_methods):
            method_boost += 0.2
        if any('container:.happy-hour' in method for method in extraction_methods):
            method_boost += 0.1
        
        # Boost for multiple deals (indicates structured content)
        if len(deals) > 1:
            method_boost += 0.1
        
        return min(avg_deal_confidence + method_boost, 1.0)
    
    def _deduplicate_deals(self, deals: List[Deal]) -> List[Deal]:
        """Remove duplicate deals"""
        seen = set()
        unique_deals = []
        
        for deal in deals:
            # Create a signature for the deal using string representations
            days_str = tuple(sorted([day.value for day in deal.days_of_week])) if deal.days_of_week else ()
            signature = (
                deal.start_time, 
                deal.end_time, 
                days_str
            )
            
            if signature not in seen:
                seen.add(signature)
                unique_deals.append(deal)
        
        return unique_deals
    
    def _get_section_identifier(self, section: BeautifulSoup) -> str:
        """Get an identifier for a section for debugging"""
        if section.name:
            attrs = []
            if section.get('class'):
                attrs.append(f"class={' '.join(section['class'])}")
            if section.get('id'):
                attrs.append(f"id={section['id']}")
            
            attr_str = f"[{', '.join(attrs)}]" if attrs else ""
            return f"{section.name}{attr_str}"
        
        return "text_node"