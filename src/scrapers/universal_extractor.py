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
        r'(\d{1,2}):(\d{2})\s*[–\-~]\s*(\d{1,2}):(\d{2})',
        # Time to close: "9PM-Close", "9 PM-Close"
        r'(\d{1,2})\s*(?::\d{2})?\s*(pm|am|PM|AM)\s*[–\-~]\s*(close|Close|CLOSE)',
        # Compact format: "9PM-Close" without spaces
        r'(\d{1,2})(PM|AM|pm|am)[–\-~](close|Close|CLOSE)'
    ]
    
    # Universal day patterns
    DAY_PATTERNS = [
        # Day ranges (full names)
        r'(Monday\s*[\-–]\s*Friday|Tuesday\s*[\-–]\s*Friday|Saturday\s*[\-–]\s*Sunday)',
        r'(Sunday\s*[\-–]\s*Thursday|Friday\s*[\-–]\s*Saturday)',
        r'(Thursday\s*[\-–]\s*Saturday|Thursday\s*[\-–]\s*Sunday)',
        # Day ranges (abbreviated)
        r'(Mon\s*[\-–]\s*Fri|Tue\s*[\-–]\s*Fri|Sat\s*[\-–]\s*Sun)',
        r'(Sun\s*[\-–]\s*Thu|Fri\s*[\-–]\s*Sat|Thurs\s*[\-–]\s*Sat)',
        r'(Thu\s*[\-–]\s*Sat|Thu\s*[\-–]\s*Sun)',
        # Daily patterns
        r'(Every\s+Day|Daily|All\s+Day|everyday|daily)',
        # Individual days (full names)
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
        # Individual days (abbreviated)
        r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Thurs)'
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
        
        # Use enhanced parsing logic for better deal creation
        deals.extend(self._extract_deals_from_text_section(text))
        
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
            parsed_days = self._parse_days(day_patterns)
            if parsed_days:
                # Create a more descriptive description based on the days
                if len(parsed_days) == 7:
                    day_description = "Daily"
                elif len(parsed_days) >= 5 and DayOfWeek.MONDAY in parsed_days and DayOfWeek.FRIDAY in parsed_days:
                    day_description = "Monday-Friday"
                elif len(parsed_days) == 2 and DayOfWeek.SATURDAY in parsed_days and DayOfWeek.SUNDAY in parsed_days:
                    day_description = "Weekends"
                else:
                    day_names = [day.value.title() for day in parsed_days]
                    day_description = ", ".join(day_names)
                
                deal = Deal(
                    title="Happy Hour",
                    description=f"Happy hour available {day_description}",
                    deal_type=DealType.HAPPY_HOUR,
                    days_of_week=parsed_days,
                    confidence_score=0.5  # Lower confidence without time info
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
            
            elif len(time_range) == 3 and 'close' in str(time_range).lower():  # "9PM-Close" format
                hour, ampm, close_word = time_range
                start_time = f"{hour} {ampm.upper()}"
                end_time = "Close"
            
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
            if 'mondayfriday' in pattern_lower or 'monfri' in pattern_lower:
                days.extend([DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                           DayOfWeek.THURSDAY, DayOfWeek.FRIDAY])
            elif 'tuesdayfriday' in pattern_lower or 'tuefri' in pattern_lower:
                days.extend([DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY])
            elif 'thursdaysaturday' in pattern_lower or 'thurssat' in pattern_lower or 'thusat' in pattern_lower:
                days.extend([DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY])
            elif 'fridaysaturday' in pattern_lower or 'frisat' in pattern_lower:
                days.extend([DayOfWeek.FRIDAY, DayOfWeek.SATURDAY])
            elif 'saturdaysunday' in pattern_lower or 'satsun' in pattern_lower:
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
            elif 'thursday' in pattern_lower or 'thu' in pattern_lower or 'thurs' in pattern_lower:
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
        """Remove duplicate and overlapping deals"""
        if not deals:
            return deals
        
        # Sort deals by confidence score (highest first) and completeness
        sorted_deals = sorted(deals, key=lambda d: (
            d.confidence_score,
            bool(d.start_time and d.end_time),  # Prefer deals with time info
            len(d.days_of_week),  # Prefer deals with more specific day info
            len(d.description or "")  # Prefer deals with more description
        ), reverse=True)
        
        unique_deals = []
        seen_signatures = set()
        
        for deal in sorted_deals:
            # Create a signature for exact duplicates
            days_str = tuple(sorted([day.value for day in deal.days_of_week])) if deal.days_of_week else ()
            exact_signature = (
                deal.start_time, 
                deal.end_time, 
                days_str
            )
            
            # Skip exact duplicates
            if exact_signature in seen_signatures:
                continue
            
            # Check for overlapping deals
            is_redundant = False
            for existing_deal in unique_deals:
                deal_days = set(deal.days_of_week) if deal.days_of_week else set()
                existing_days = set(existing_deal.days_of_week) if existing_deal.days_of_week else set()
                
                # Check for subset relationships (one deal is contained within another)
                if deal_days and existing_days:
                    if deal_days.issubset(existing_days):
                        # Current deal is subset of existing deal - skip it
                        if (existing_deal.start_time and existing_deal.end_time) or existing_deal.confidence_score >= deal.confidence_score:
                            is_redundant = True
                            break
                    elif existing_days.issubset(deal_days):
                        # Existing deal is subset of current deal - remove existing and add current
                        if (deal.start_time and deal.end_time) or deal.confidence_score > existing_deal.confidence_score:
                            unique_deals.remove(existing_deal)
                            break
                
                # Check for deals with same times
                if (deal.start_time == existing_deal.start_time and 
                    deal.end_time == existing_deal.end_time):
                    
                    # If one deal covers all days and another is more specific, keep the better one
                    if (len(existing_deal.days_of_week) == 7 and 
                        len(deal.days_of_week) < 7 and 
                        deal.days_of_week):
                        # Remove the "daily" deal in favor of more specific one
                        unique_deals.remove(existing_deal)
                        break
                    elif (len(deal.days_of_week) == 7 and 
                          len(existing_deal.days_of_week) < 7 and 
                          existing_deal.days_of_week):
                        # Skip this "daily" deal, keep the more specific one
                        is_redundant = True
                        break
                        
                    # If days overlap significantly (>= 50%), keep the better one
                    if deal_days and existing_days:
                        overlap = len(deal_days & existing_days)
                        overlap_ratio = overlap / min(len(deal_days), len(existing_days))
                        if overlap_ratio >= 0.5:
                            # Keep the one with better confidence or more complete info
                            if existing_deal.confidence_score >= deal.confidence_score:
                                is_redundant = True
                                break
                            else:
                                unique_deals.remove(existing_deal)
                                break
            
            if not is_redundant:
                seen_signatures.add(exact_signature)
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
    
    def _remove_duplicate_deals(self, deals: List[Deal]) -> List[Deal]:
        """
        Remove duplicate deals based on title, time, and days.
        
        Args:
            deals: List of deals to deduplicate
            
        Returns:
            List of unique deals
        """
        if not deals:
            return deals
        
        unique_deals = []
        seen_deals = set()
        
        for deal in deals:
            # Create a signature for the deal
            days_signature = tuple(sorted([day.value for day in deal.days_of_week]))
            deal_signature = (
                deal.title.lower().strip(),
                deal.start_time,
                deal.end_time,
                days_signature
            )
            
            if deal_signature not in seen_deals:
                seen_deals.add(deal_signature)
                unique_deals.append(deal)
        
        return unique_deals
    
    def extract_from_text(self, text: str, source_url: str = None) -> ExtractionResult:
        """
        Extract happy hour deals from plain text (e.g., from PDF extraction).
        
        Args:
            text: Plain text content to analyze
            source_url: Optional source URL for context
        
        Returns:
            ExtractionResult with deals and confidence scoring
        """
        logger.info("Starting universal happy hour extraction from plain text")
        
        if not text or not text.strip():
            logger.warning("Empty text provided for extraction")
            return ExtractionResult(deals=[], confidence_score=0.0, 
                                  extraction_method="text_extraction", 
                                  content_sources=["empty_text"])
        
        # Create a simple wrapper to make text compatible with existing methods
        # We'll treat the entire text as one "section" for analysis
        deals = self._extract_deals_from_text_content(text)
        
        # Calculate confidence score based on extraction quality
        confidence_score = self._calculate_text_confidence(text, deals)
        
        # Determine extraction method
        extraction_method = "text_pattern_matching"
        if source_url and source_url.endswith('.pdf'):
            extraction_method = "pdf_text_extraction"
        
        content_sources = [source_url or "plain_text"]
        
        logger.info(f"Universal extraction found {len(deals)} deals with {confidence_score:.2f} confidence")
        
        return ExtractionResult(
            deals=deals,
            confidence_score=confidence_score,
            extraction_method=extraction_method,
            content_sources=content_sources
        )
    
    def _extract_deals_from_text_content(self, text: str) -> List[Deal]:
        """
        Extract deals from plain text using pattern recognition.
        
        Args:
            text: Plain text content
            
        Returns:
            List of extracted deals
        """
        deals = []
        
        # Split text into lines for analysis
        lines = text.split('\n')
        
        # Look for happy hour indicators in the text
        happy_hour_sections = []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in self.HAPPY_HOUR_KEYWORDS):
                # Include this line and surrounding context
                start_idx = max(0, i - 2)
                end_idx = min(len(lines), i + 3)
                context = '\n'.join(lines[start_idx:end_idx])
                happy_hour_sections.append(context)
        
        # If no specific happy hour sections found, analyze the entire text
        if not happy_hour_sections:
            happy_hour_sections = [text]
        
        # Extract deals from each section
        for section_text in happy_hour_sections:
            section_deals = self._extract_deals_from_text_section(section_text)
            deals.extend(section_deals)
        
        # Remove duplicates
        unique_deals = self._remove_duplicate_deals(deals)
        
        return unique_deals
    
    def _extract_deals_from_text_section(self, section_text: str) -> List[Deal]:
        """
        Extract deals from a section of plain text.
        
        Args:
            section_text: Text section to analyze
            
        Returns:
            List of extracted deals
        """
        deals = []
        
        # Extract time patterns
        time_matches = []
        for pattern in self.TIME_PATTERNS:
            matches = re.findall(pattern, section_text, re.IGNORECASE)
            time_matches.extend(matches)
        
        # Extract day patterns
        day_matches = []
        for pattern in self.DAY_PATTERNS:
            matches = re.findall(pattern, section_text, re.IGNORECASE)
            day_matches.extend(matches)
        
        # Deduplicate time matches to avoid creating duplicate deals
        unique_time_matches = []
        seen_time_strings = set()
        
        for time_match in time_matches:
            # Create a unique signature for this time match (case-insensitive)
            if len(time_match) >= 2:
                time_sig = f"{time_match[0]}-{time_match[-1]}".lower()  # First and last elements, lowercase
            else:
                time_sig = str(time_match[0]).lower()
            
            if time_sig not in seen_time_strings:
                seen_time_strings.add(time_sig)
                unique_time_matches.append(time_match)
        
        # Create separate deals for each unique time pattern found
        if unique_time_matches:
            for time_match in unique_time_matches:
                try:
                    start_time, end_time = self._parse_time_match(time_match)
                    if not start_time or not end_time:
                        continue
                    
                    # Find the most relevant day pattern for this time
                    relevant_days = self._find_relevant_days_for_time(time_match, day_matches, section_text)
                    
                    # Create description
                    description_parts = [f"Time: {start_time} - {end_time}"]
                    if relevant_days:
                        day_str = ", ".join([day.title() for day in relevant_days])
                        description_parts.append(f"Days: {day_str}")
                    
                    description = " | ".join(description_parts)
                    
                    # Create the deal
                    deal = Deal(
                        title="Happy Hour",
                        description=description,
                        deal_type=DealType.HAPPY_HOUR,
                        days_of_week=[DayOfWeek(day) for day in relevant_days if day in [d.value for d in DayOfWeek]],
                        start_time=start_time,
                        end_time=end_time,
                        is_all_day=False
                    )
                    deals.append(deal)
                except Exception as e:
                    continue
        
        # If no time patterns but we have day patterns, create a generic deal
        elif day_matches:
            days_of_week = []
            for match in day_matches:
                try:
                    match_days = self._parse_day_match(match[0] if isinstance(match, tuple) else match)
                    days_of_week.extend(match_days)
                except:
                    continue
            
            # Remove duplicates from days
            days_of_week = list(set(days_of_week))
            
            if days_of_week:
                day_str = ", ".join([day.title() for day in days_of_week])
                description = f"Days: {day_str}"
                
                deal = Deal(
                    title="Happy Hour",
                    description=description,
                    deal_type=DealType.HAPPY_HOUR,
                    days_of_week=[DayOfWeek(day) for day in days_of_week if day in [d.value for d in DayOfWeek]],
                    start_time=None,
                    end_time=None,
                    is_all_day=False
                )
                deals.append(deal)
        
        return deals
    
    def _parse_time_match(self, time_match):
        """Parse a time match into start_time and end_time strings"""
        if len(time_match) == 4:  # Standard format (hour1, ampm1, hour2, ampm2)
            hour1, ampm1, hour2, ampm2 = time_match
            if ampm1 == '':
                ampm1 = ampm2  # Use same AM/PM for both
            start_time = f"{hour1} {ampm1 or 'PM'}".strip()
            end_time = f"{hour2} {ampm2}".strip()
            return start_time, end_time
        elif len(time_match) == 3 and 'close' in str(time_match).lower():  # "9PM-Close" format
            hour, ampm, close_word = time_match
            start_time = f"{hour} {ampm}".strip()
            end_time = "Close"
            return start_time, end_time
        return None, None
    
    def _parse_day_match(self, day_match):
        """Parse a day match into a list of day strings"""
        day_match_str = day_match.lower() if isinstance(day_match, str) else str(day_match).lower()
        
        # Handle ranges
        if 'daily' in day_match_str:
            return ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        elif 'thurs-sat' in day_match_str or 'thu-sat' in day_match_str:
            return ['thursday', 'friday', 'saturday']
        elif 'mon-fri' in day_match_str:
            return ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        
        # Individual days
        day_mapping = {
            'monday': 'monday', 'mon': 'monday',
            'tuesday': 'tuesday', 'tue': 'tuesday', 
            'wednesday': 'wednesday', 'wed': 'wednesday',
            'thursday': 'thursday', 'thu': 'thursday', 'thurs': 'thursday',
            'friday': 'friday', 'fri': 'friday',
            'saturday': 'saturday', 'sat': 'saturday',
            'sunday': 'sunday', 'sun': 'sunday'
        }
        
        for day_variant, day_name in day_mapping.items():
            if day_variant in day_match_str:
                return [day_name]
        
        return []
    
    def _find_relevant_days_for_time(self, time_match, day_matches, section_text):
        """Find the most relevant day pattern for a specific time pattern"""
        # Convert time_match to string for proximity analysis
        if len(time_match) >= 2:
            time_str = f"{time_match[0]}{time_match[1] if time_match[1] else ''}"
        else:
            time_str = str(time_match[0])
        
        # Special handling for patterns like "Daily 3-6 PM & Thurs-Sat 9PM-Close"
        # Look for patterns where day immediately precedes time
        section_lower = section_text.lower()
        
        # Find time position
        time_pos = section_lower.find(time_str.lower())
        
        # Look for day patterns that directly precede this time (within 20 chars)
        for day_match in day_matches:
            day_str = day_match[0] if isinstance(day_match, tuple) else day_match
            day_pos = section_lower.find(day_str.lower())
            
            if day_pos >= 0 and time_pos >= 0:
                distance = time_pos - day_pos  # Positive if day comes before time
                
                # If day comes right before time (1-20 chars before), it's likely the right match
                if 1 <= distance <= 20:
                    return self._parse_day_match(day_str)
        
        # Fallback: look for closest day pattern within reasonable distance
        best_days = []
        best_distance = float('inf')
        
        for day_match in day_matches:
            day_str = day_match[0] if isinstance(day_match, tuple) else day_match
            day_pos = section_lower.find(day_str.lower())
            
            if day_pos >= 0 and time_pos >= 0:
                distance = abs(day_pos - time_pos)
                if distance < best_distance and distance <= 30:  # Within 30 chars
                    best_distance = distance
                    best_days = self._parse_day_match(day_str)
        
        # If no nearby day pattern found, use 'daily' if present, otherwise empty
        if not best_days:
            for day_match in day_matches:
                day_str = day_match[0] if isinstance(day_match, tuple) else day_match
                if 'daily' in day_str.lower():
                    best_days = self._parse_day_match(day_str)
                    break
        
        return best_days
    
    def _calculate_text_confidence(self, text: str, deals: List[Deal]) -> float:
        """
        Calculate confidence score for text-based extraction.
        
        Args:
            text: Original text content
            deals: Extracted deals
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not deals:
            return 0.0
        
        score = 0.0
        
        # Base score for finding deals
        score += 0.5
        
        # Bonus for happy hour keywords
        text_lower = text.lower()
        keyword_count = sum(1 for keyword in self.HAPPY_HOUR_KEYWORDS if keyword in text_lower)
        score += min(keyword_count * 0.1, 0.3)
        
        # Bonus for time patterns
        time_pattern_count = 0
        for pattern in self.TIME_PATTERNS:
            time_pattern_count += len(re.findall(pattern, text, re.IGNORECASE))
        score += min(time_pattern_count * 0.05, 0.2)
        
        # Bonus for day patterns
        day_pattern_count = 0
        for pattern in self.DAY_PATTERNS:
            day_pattern_count += len(re.findall(pattern, text, re.IGNORECASE))
        score += min(day_pattern_count * 0.05, 0.2)
        
        # Penalty for very short text (might be incomplete extraction)
        if len(text) < 100:
            score *= 0.8
        
        return min(score, 1.0)