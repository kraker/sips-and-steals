#!/usr/bin/env python3
"""
Text processing engine for extracting deals from HTML content
Handles pattern matching, content selection, and basic deal creation
"""

import re
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

# Import models (adjust path as needed)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from models import Deal, DealType, DayOfWeek

logger = logging.getLogger(__name__)


class TextProcessor:
    """Extract deals from HTML content using configuration-based patterns"""
    
    def __init__(self, config: Dict[str, Any], restaurant=None):
        self.config = config
        self.scraping_config = config.get('scraping_config', {})
        self.restaurant = restaurant
    
    def extract_deals(self, soup: BeautifulSoup) -> List[Deal]:
        """Extract deals from BeautifulSoup object using configured patterns"""
        deals = []
        
        # Get target content based on configuration
        target_content = self._get_target_content(soup)
        
        # Apply exclude patterns
        filtered_content = self._apply_exclude_patterns(target_content)
        
        # Extract deals using configured patterns
        if self._has_custom_patterns():
            deals.extend(self._extract_with_custom_patterns(filtered_content))
        else:
            deals.extend(self._extract_with_common_patterns(filtered_content))
        
        return deals
    
    def _get_target_content(self, soup: BeautifulSoup) -> str:
        """Extract target content using custom selectors or containers"""
        content_parts = []
        
        # Use custom selectors if specified
        custom_selectors = self.scraping_config.get('custom_selectors', {})
        if custom_selectors:
            for selector_name, selector in custom_selectors.items():
                elements = soup.select(selector)
                for element in elements:
                    content_parts.append(element.get_text())
        
        # Use content containers if specified
        content_containers = self.scraping_config.get('content_containers', [])
        if content_containers:
            for container_selector in content_containers:
                containers = soup.select(container_selector)
                for container in containers:
                    content_parts.append(container.get_text())
        
        # Fallback to full page content
        if not content_parts:
            content_parts.append(soup.get_text())
        
        return ' '.join(content_parts)
    
    def _apply_exclude_patterns(self, content: str) -> str:
        """Apply exclude patterns from configuration"""
        exclude_patterns = self.scraping_config.get('exclude_patterns', [])
        
        filtered_content = content
        for pattern in exclude_patterns:
            filtered_content = re.sub(pattern, '', filtered_content, flags=re.IGNORECASE)
        
        return filtered_content
    
    def _has_custom_patterns(self) -> bool:
        """Check if configuration has custom regex patterns"""
        scraping_patterns = self.config.get('scraping_patterns', {})
        return any([
            scraping_patterns.get('time_patterns'),
            scraping_patterns.get('deal_patterns'),
            scraping_patterns.get('day_patterns')
        ])
    
    def _extract_with_custom_patterns(self, content: str) -> List[Deal]:
        """Extract deals using custom regex patterns from configuration"""
        deals = []
        scraping_patterns = self.config.get('scraping_patterns', {})
        
        
        # Extract time information
        times = []
        time_patterns = scraping_patterns.get('time_patterns', [])
        for pattern_config in time_patterns:
            pattern = pattern_config.get('pattern', '')
            matches = self._extract_pattern_matches_with_groups(content, pattern, pattern_config.get('groups', []))
            times.extend(matches)
        
        # Extract deal information  
        deals_info = []
        deal_patterns = scraping_patterns.get('deal_patterns', [])
        for pattern_config in deal_patterns:
            pattern = pattern_config.get('pattern', '')
            matches = self._extract_pattern_matches_with_groups(content, pattern, pattern_config.get('groups', []))
            deals_info.extend(matches)
        
        # Extract day information
        days = []
        day_patterns = scraping_patterns.get('day_patterns', [])
        for pattern_config in day_patterns:
            pattern = pattern_config.get('pattern', '')
            matches = self._extract_pattern_matches_with_groups(content, pattern, pattern_config.get('groups', []))
            days.extend(matches)
        
        # Create deals from extracted components
        if times or days or deals_info:
            deal = self._create_deal_from_components(
                times=times,
                days=days,
                prices=deals_info,  # Include all deal info as "prices" for now
                source_content=content  # Pass full content for "Every Day" detection
            )
            if deal:
                deals.append(deal)
        
        return deals
    
    def _extract_pattern_matches(self, content: str, pattern_key: str) -> List[str]:
        """Extract matches using a specific pattern from configuration"""
        pattern = self.scraping_config.get(pattern_key)
        if not pattern:
            return []
        
        matches = []
        try:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                # Add all non-None groups from the match
                matches.extend([group for group in match.groups() if group])
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern_key}': {e}")
        
        return matches
    
    def _extract_pattern_matches_with_groups(self, content: str, pattern: str, groups: List[str]) -> List[str]:
        """Extract matches using a pattern and return specific groups"""
        if not pattern:
            return []
        
        matches = []
        try:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                # Extract specified groups or all groups if none specified
                if groups:
                    for i, group_name in enumerate(groups):
                        if i < len(match.groups()) and match.group(i + 1):
                            matches.append(match.group(i + 1))
                else:
                    # Add all non-None groups from the match
                    matches.extend([group for group in match.groups() if group])
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        return matches
    
    def _create_deal_from_components(self, times: List[str], days: List[str], 
                                   prices: List[str], source_content: str) -> Optional[Deal]:
        """Create a Deal object from extracted components"""
        
        # Parse time components
        start_time = None
        end_time = None
        if len(times) >= 2:
            start_time = self._normalize_time(times[0])
            end_time = self._normalize_time(times[1])
        
        # Parse day components
        day_enums = []
        is_all_day = False
        
        if days:
            day_enums = self._parse_days(days)
        
        # Handle "Every Day" case - if we have times but no specific days, assume all days
        if (start_time and end_time) and not day_enums:
            # Check if content mentions "every day" or "daily"
            content_lower = source_content.lower()
            if 'every day' in content_lower or 'daily' in content_lower:
                day_enums = list(DayOfWeek)  # All days of the week
        
        # Check for all-day patterns
        if 'all day' in source_content.lower():
            is_all_day = True
        
        # Create price string with proper spacing
        price_str = None
        if prices:
            # Clean up prices to ensure proper spacing
            cleaned_prices = []
            for price in prices[:3]:
                # Add space after $ if missing
                clean_price = re.sub(r'\$(\d)', r'$ \1', price)
                # Add space before uppercase letters after numbers
                clean_price = re.sub(r'(\d)([A-Z])', r'\1 \2', clean_price)
                cleaned_prices.append(clean_price)
            price_str = ', '.join(cleaned_prices)
        
        # Generate title and description
        title = self._generate_title(day_enums, start_time, end_time, is_all_day)
        description = self._generate_description(source_content[:200], times, days, prices)  # Limit description source
        
        # Only create deal if we have meaningful timing or day information
        if (start_time and end_time and day_enums) or (is_all_day and day_enums) or day_enums or (start_time and end_time):
            deal = Deal(
                title=title,
                description=description,
                deal_type=DealType.HAPPY_HOUR,
                days_of_week=day_enums,
                start_time=start_time,
                end_time=end_time,
                is_all_day=is_all_day,
                confidence_score=0.8,  # High confidence for custom pattern matches
                scraped_at=datetime.now(),
                source_url=self.restaurant.website if self.restaurant else None
            )
            if price_str:
                deal.set_price_from_string(price_str)
            return deal
        
        return None
    
    def _extract_with_common_patterns(self, content: str) -> List[Deal]:
        """Extract deals using common happy hour patterns"""
        deals = []
        content_lower = content.lower()
        
        # Common happy hour patterns
        patterns = [
            r'happy\s+hour.*?(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*-\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))',
            r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*-\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)).*?happy\s+hour',
            r'daily.*?(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*-\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                deal = Deal(
                    title="Happy Hour",
                    description=match.group(0)[:100],  # First 100 chars
                    deal_type=DealType.HAPPY_HOUR,
                    start_time=self._normalize_time(match.group(1)),
                    end_time=self._normalize_time(match.group(2)),
                    confidence_score=0.6,  # Lower confidence for generic patterns
                    scraped_at=datetime.now(),
                    source_url=self.restaurant.website if self.restaurant else None
                )
                deals.append(deal)
                break  # Only take first match to avoid duplicates
        
        return deals[:1]  # Limit to one deal to avoid spam
    
    def _parse_days(self, day_strings: List[str]) -> List[DayOfWeek]:
        """Parse day strings into DayOfWeek enums"""
        day_mapping = {
            'monday': DayOfWeek.MONDAY, 'mon': DayOfWeek.MONDAY,
            'tuesday': DayOfWeek.TUESDAY, 'tue': DayOfWeek.TUESDAY,
            'wednesday': DayOfWeek.WEDNESDAY, 'wed': DayOfWeek.WEDNESDAY,
            'thursday': DayOfWeek.THURSDAY, 'thu': DayOfWeek.THURSDAY,
            'friday': DayOfWeek.FRIDAY, 'fri': DayOfWeek.FRIDAY,
            'saturday': DayOfWeek.SATURDAY, 'sat': DayOfWeek.SATURDAY,
            'sunday': DayOfWeek.SUNDAY, 'sun': DayOfWeek.SUNDAY
        }
        
        days = []
        for day_str in day_strings:
            day_lower = day_str.lower().strip().rstrip(':')  # Remove trailing colon
            
            # Handle range patterns like "Monday - Friday:"
            if ' - ' in day_lower:
                if 'monday - friday' in day_lower:
                    return [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                           DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
                elif 'saturday - sunday' in day_lower:
                    return [DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]
                elif 'sunday - saturday' in day_lower:
                    return list(DayOfWeek)  # All days
            
            # Handle individual days
            if day_lower in day_mapping:
                days.append(day_mapping[day_lower])
        
        # Handle special cases like "MON - FRI" meaning Monday through Friday (legacy)
        if len(day_strings) == 2:
            first_day = day_strings[0].lower().strip()
            second_day = day_strings[1].lower().strip()
            
            if first_day in ['mon', 'monday'] and second_day in ['fri', 'friday']:
                return [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                       DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
            elif first_day in ['sun', 'sunday'] and second_day in ['sat', 'saturday']:
                return list(DayOfWeek)  # All days
        
        return list(set(days))  # Remove duplicates
    
    def _normalize_time(self, time_str: str) -> str:
        """Normalize time string to consistent format"""
        if not time_str:
            return time_str
        
        time_str = time_str.strip()
        
        # Handle cases like "3pm" -> "3:00 PM"
        if re.match(r'^\d{1,2}pm$', time_str, re.IGNORECASE):
            hour = time_str[:-2]
            return f"{hour}:00 PM"
        
        # Handle cases like "3:30pm" -> "3:30 PM"
        if re.match(r'^\d{1,2}:\d{2}pm$', time_str, re.IGNORECASE):
            return time_str[:-2] + ' PM'
        
        # Handle cases like "3am" -> "3:00 AM"
        if re.match(r'^\d{1,2}am$', time_str, re.IGNORECASE):
            hour = time_str[:-2]
            return f"{hour}:00 AM"
        
        # Handle cases like "3:30am" -> "3:30 AM"
        if re.match(r'^\d{1,2}:\d{2}am$', time_str, re.IGNORECASE):
            return time_str[:-2] + ' AM'
        
        # Handle cases like "3:00" or "9:30" (assume PM for dinner hours)
        if re.match(r'^\d{1,2}:\d{2}$', time_str):
            hour = int(time_str.split(':')[0])
            # Assume PM for times 2-11, AM for times 11-1 (late night/early morning)
            if 2 <= hour <= 11:
                return f"{time_str} PM"
            else:
                return f"{time_str} AM"
        
        # Handle cases like "3" or "9" (assume PM for single digits in restaurant context)
        if re.match(r'^\d{1,2}$', time_str):
            hour = int(time_str)
            if 2 <= hour <= 11:
                return f"{hour}:00 PM"
            else:
                return f"{hour}:00 AM"
        
        return time_str
    
    def _generate_title(self, days: List[DayOfWeek], start_time: str, 
                       end_time: str, is_all_day: bool) -> str:
        """Generate an appropriate title for the deal"""
        if is_all_day:
            if len(days) == 7:
                return "All Day Happy Hour"
            elif len(days) == 5 and DayOfWeek.MONDAY in days and DayOfWeek.FRIDAY in days:
                return "Weekday Happy Hour"
            elif len(days) == 1:
                return f"{days[0].value.title()} Special"
            else:
                return "Happy Hour Special"
        else:
            if len(days) == 7:
                return "Daily Happy Hour"
            elif len(days) == 5 and DayOfWeek.MONDAY in days and DayOfWeek.FRIDAY in days:
                return "Weekday Happy Hour"
            elif len(days) == 1:
                return f"{days[0].value.title()} Happy Hour"
            else:
                return "Happy Hour"
    
    def _generate_description(self, source_content: str, times: List[str], 
                            days: List[str], prices: List[str]) -> str:
        """Generate a clean description from extracted components"""
        description_parts = []
        
        # Add time information
        if times and len(times) >= 2:
            description_parts.append(f"Available {times[0]} - {times[1]}")
        
        # Add day information
        if days:
            if len(days) <= 3:
                description_parts.append(f"Days: {', '.join(days)}")
        
        # Add pricing information
        if prices:
            description_parts.append(f"Pricing: {', '.join(prices[:2])}")
        
        # If no structured data, use cleaned source content
        if not description_parts:
            # Clean up the source content
            cleaned = re.sub(r'\s+', ' ', source_content).strip()
            cleaned = cleaned[:100]  # Limit length
            if cleaned:
                description_parts.append(cleaned)
        
        return ' | '.join(description_parts) if description_parts else "Happy hour specials available"