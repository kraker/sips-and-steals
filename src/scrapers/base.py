#!/usr/bin/env python3
"""
Enhanced base scraper with retry logic, circuit breaker, and better error handling
"""

import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import time
import logging
import random
from datetime import datetime, timedelta
from enum import Enum
import json
import re
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse

# Import our models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Restaurant, Deal, DealType, DayOfWeek, ScrapingStatus, DealValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScrapingError(Exception):
    """Base exception for scraping errors"""
    pass


class TemporaryScrapingError(ScrapingError):
    """Temporary error that should be retried"""
    pass


class PermanentScrapingError(ScrapingError):
    """Permanent error that should not be retried"""
    pass


class CircuitBreaker:
    """Simple circuit breaker to avoid hammering failed endpoints"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if we can execute a request"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time and \
               (datetime.now() - self.last_failure_time).seconds > self.timeout:
                self.state = "half-open"
                return True
            return False
        
        # half-open state
        return True
    
    def on_success(self):
        """Called when request succeeds"""
        self.failure_count = 0
        self.state = "closed"
    
    def on_failure(self):
        """Called when request fails"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class BaseScraper(ABC):
    """Enhanced base class for all restaurant scrapers with robust error handling"""
    
    def __init__(self, restaurant: Restaurant):
        self.restaurant = restaurant
        self.circuit_breaker = CircuitBreaker()
        self.session = self._create_session()
        self.start_time = datetime.now()
        
        # Adaptive delays based on website behavior
        self.base_delay = 2.0  # Increased from 1.0
        self.max_delay = 60.0  # Increased from 30.0
        self.current_delay = self.base_delay
        
        # Robots.txt compliance
        self.robots_cache = {}
        
        # More conservative bot detection
        self.failed_attempts = 0
        self.max_failed_attempts = 2
        
    def _create_session(self) -> requests.Session:
        """Create a robust requests session with retries and timeouts"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]  # Updated parameter name
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set polite user agent and headers
        headers = {
            'User-Agent': 'SipsAndStealsBot/1.0 (+https://github.com/sips-and-steals/scraper) - Denver Happy Hour Aggregator',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=300',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Add custom headers from restaurant config
        headers.update(self.restaurant.scraping_config.custom_headers)
        session.headers.update(headers)
        
        return session
    
    def _validate_page_content(self, soup: BeautifulSoup, url: str) -> bool:
        """Validate that the page content is relevant for this restaurant"""
        if not soup:
            return False
            
        page_text = soup.get_text().lower()
        
        # Check content length
        if hasattr(self.restaurant, 'scraping_hints'):
            hints = getattr(self.restaurant, 'scraping_hints', {})
            min_length = hints.get('content_min_length', 300)
            if len(page_text) < min_length:
                logger.info(f"Page content too short ({len(page_text)} chars) for {url}")
                return False
                
            # Check for location-specific keywords
            location_keywords = hints.get('location_check', [])
            if location_keywords:
                found_keywords = [kw for kw in location_keywords if kw in page_text]
                if found_keywords:
                    logger.info(f"Found location keywords {found_keywords} in {url}")
                    return True
                else:
                    logger.info(f"No location keywords found in {url}")
                    return False
        
        # Default validation - just check for reasonable content
        return len(page_text) > 300
    
    def _fetch_single_url(self, url: str, timeout: Optional[int] = None) -> BeautifulSoup:
        """Fetch a single URL with error handling and optional form interaction"""
        timeout = timeout or self.restaurant.scraping_config.timeout_seconds
        
        if not self.circuit_breaker.can_execute():
            raise TemporaryScrapingError("Circuit breaker is open, skipping request")
        
        # Check robots.txt compliance
        if not self._can_fetch_url(url):
            raise PermanentScrapingError(f"Robots.txt disallows fetching {url}")
        
        # Add progressive delay on failures
        if self.failed_attempts > 0:
            delay = min(self.base_delay * (2 ** self.failed_attempts), self.max_delay)
            logger.info(f"Adding {delay}s delay before fetching {url} (attempt after {self.failed_attempts} failures)")
            time.sleep(delay)
        
        logger.info(f"Fetching {url} for {self.restaurant.name}")
        
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        
        # Check for bot detection patterns
        self._check_bot_detection(response)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try location-specific form interaction if needed
        enhanced_soup = self._try_location_form_interaction(soup, url, timeout)
        if enhanced_soup:
            soup = enhanced_soup
        
        self.circuit_breaker.on_success()
        self.failed_attempts = 0  # Reset on success
        
        return soup
    
    def _try_location_form_interaction(self, soup: BeautifulSoup, url: str, timeout: int) -> Optional[BeautifulSoup]:
        """Try to interact with location selection forms for chain restaurants"""
        if not hasattr(self.restaurant, 'scraping_hints'):
            return None
            
        hints = getattr(self.restaurant, 'scraping_hints', {})
        location_keywords = hints.get('location_check', [])
        
        if not location_keywords:
            return None
        
        # Look for location selection forms (like STK)
        selects = soup.find_all('select')
        for select in selects:
            select_name = select.get('name', '').lower()
            if 'location' in select_name:
                # Find matching location option
                options = select.find_all('option')
                for option in options:
                    option_text = option.get_text().strip().lower()
                    option_value = option.get('value', '')
                    
                    # Check if this option matches our location keywords
                    for keyword in location_keywords:
                        if keyword in option_text and option_value:
                            logger.info(f"Found location option '{option_text}' (value={option_value}) for {self.restaurant.name}")
                            
                            # Try form submission
                            try:
                                form_data = {select.get('name', 'location'): option_value}
                                logger.info(f"Submitting location form: {form_data}")
                                
                                response = self.session.post(url, data=form_data, timeout=timeout)
                                response.raise_for_status()
                                
                                new_soup = BeautifulSoup(response.content, 'html.parser')
                                
                                # Validate the new content is significantly better
                                original_length = len(soup.get_text())
                                new_length = len(new_soup.get_text())
                                
                                if new_length > original_length * 2:  # At least 2x more content
                                    logger.info(f"Form submission successful: {original_length} → {new_length} chars")
                                    return new_soup
                                else:
                                    logger.info(f"Form submission didn't improve content significantly")
                                    
                            except Exception as e:
                                logger.warning(f"Form submission failed for {self.restaurant.name}: {e}")
                                continue
        
        return None

    def fetch_page(self, url: Optional[str] = None, timeout: Optional[int] = None) -> BeautifulSoup:
        """Fetch and parse a webpage with multiple URL support and validation"""
        timeout = timeout or self.restaurant.scraping_config.timeout_seconds
        
        # Determine URLs to try
        if url:
            # Single URL provided directly
            urls_to_try = [url]
            logger.info(f"Using provided URL: {url}")
        elif hasattr(self.restaurant, 'scraping_urls') and getattr(self.restaurant, 'scraping_urls'):
            # Multiple URLs configured
            urls_to_try = getattr(self.restaurant, 'scraping_urls')
            logger.info(f"Using scraping_urls: {urls_to_try} for {self.restaurant.name}")
        elif hasattr(self.restaurant, 'websites') and getattr(self.restaurant, 'websites'):
            # Legacy support for 'websites' field
            urls_to_try = getattr(self.restaurant, 'websites')
            logger.info(f"Using legacy websites: {urls_to_try} for {self.restaurant.name}")
        else:
            # Fallback to single website
            urls_to_try = [self.restaurant.website] if self.restaurant.website else []
            logger.info(f"Using fallback website: {urls_to_try} for {self.restaurant.name}")
        
        if not urls_to_try:
            raise PermanentScrapingError("No URLs provided for scraping")
        
        last_exception = None
        
        # Try each URL until we find one with valid content
        for i, try_url in enumerate(urls_to_try):
            try:
                logger.info(f"Attempting URL {i+1}/{len(urls_to_try)}: {try_url}")
                soup = self._fetch_single_url(try_url, timeout)
                
                # Validate page content
                if self._validate_page_content(soup, try_url):
                    logger.info(f"Successfully fetched and validated: {try_url}")
                    return soup
                else:
                    logger.info(f"Content validation failed for: {try_url}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Failed to fetch {try_url}: {e}")
                last_exception = e
                continue
        
        # If we get here, all URLs failed
        if last_exception:
            if isinstance(last_exception, (TemporaryScrapingError, PermanentScrapingError)):
                raise last_exception
            else:
                raise TemporaryScrapingError(f"All URLs failed. Last error: {str(last_exception)}")
        else:
            raise PermanentScrapingError("No valid content found at any URL")

    def fetch_all_pages(self, timeout: Optional[int] = None) -> List[BeautifulSoup]:
        """Fetch and parse all configured webpages, returning list of valid soups"""
        timeout = timeout or self.restaurant.scraping_config.timeout_seconds
        
        # Determine URLs to try
        if hasattr(self.restaurant, 'scraping_urls') and getattr(self.restaurant, 'scraping_urls'):
            urls_to_try = getattr(self.restaurant, 'scraping_urls')
            logger.info(f"Trying all {len(urls_to_try)} URLs for {self.restaurant.name}")
        elif hasattr(self.restaurant, 'websites') and getattr(self.restaurant, 'websites'):
            # Legacy support
            urls_to_try = getattr(self.restaurant, 'websites')
            logger.info(f"Trying all {len(urls_to_try)} URLs for {self.restaurant.name} (legacy)")
        else:
            # Fallback to single website
            urls_to_try = [self.restaurant.website] if self.restaurant.website else []
        
        if not urls_to_try:
            raise PermanentScrapingError("No URLs provided for scraping")
        
        valid_soups = []
        
        # Try each URL and collect all valid content
        for i, try_url in enumerate(urls_to_try):
            try:
                logger.info(f"Attempting URL {i+1}/{len(urls_to_try)}: {try_url}")
                soup = self._fetch_single_url(try_url, timeout)
                
                # Validate page content
                if self._validate_page_content(soup, try_url):
                    logger.info(f"Successfully fetched and validated: {try_url}")
                    valid_soups.append(soup)
                else:
                    logger.info(f"Content validation failed for: {try_url}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Failed to fetch {try_url}: {e}")
                continue
        
        if not valid_soups:
            raise PermanentScrapingError("No valid content found at any URL")
            
        return valid_soups
    
    def _can_fetch_url(self, url: str) -> bool:
        """Check if robots.txt allows fetching this URL"""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if base_url not in self.robots_cache:
                robots_url = urljoin(base_url, '/robots.txt')
                
                try:
                    rp = RobotFileParser()
                    rp.set_url(robots_url)
                    
                    # Set a short timeout for robots.txt fetching
                    old_timeout = self.session.timeout
                    self.session.timeout = 5
                    
                    robots_response = self.session.get(robots_url, timeout=5)
                    if robots_response.status_code == 200:
                        rp.read()
                        self.robots_cache[base_url] = rp
                    else:
                        # If no robots.txt, assume we can fetch
                        self.robots_cache[base_url] = None
                        
                    self.session.timeout = old_timeout
                    
                except Exception:
                    # If we can't fetch robots.txt, assume we can proceed
                    self.robots_cache[base_url] = None
            
            rp = self.robots_cache[base_url]
            if rp is None:
                return True
                
            # Check if our user agent can fetch this URL
            user_agent = self.session.headers.get('User-Agent', '*')
            return rp.can_fetch(user_agent, url)
            
        except Exception:
            # If there's any error with robots.txt checking, allow the fetch
            return True
    
    def _check_bot_detection(self, response: requests.Response):
        """Check if the response indicates bot detection"""
        content = response.text.lower()
        
        # Check response headers first
        if response.status_code == 429:  # Rate limited
            raise TemporaryScrapingError("Rate limited by server")
        
        # More comprehensive bot detection patterns
        bot_indicators = [
            'access denied',
            'blocked',
            'captcha',
            'cloudflare security',
            'security check',
            'bot detection',
            'please enable javascript',
            'automated requests',
            'suspicious activity',
            'verify you are human'
        ]
        
        # Also check for very short responses (often a sign of blocking)
        if len(content) < 500 and any(indicator in content for indicator in bot_indicators):
            raise PermanentScrapingError("Bot detection triggered")
            
        # Check for JavaScript-heavy pages that might be trying to detect bots
        if 'javascript' in content and len(content) < 1000:
            logger.warning(f"Possible JavaScript-heavy page detected for {self.restaurant.name}")
    
    @abstractmethod
    def scrape_deals(self) -> List[Deal]:
        """
        Scrape deals from the restaurant website.
        Should return a list of Deal objects.
        """
        pass
    
    def parse_common_patterns(self, soup: BeautifulSoup) -> List[Deal]:
        """
        Attempt to parse common happy hour patterns automatically
        This serves as a fallback for restaurants without custom scrapers
        """
        deals = []
        
        # Look for JSON-LD structured data
        deals.extend(self._parse_json_ld(soup))
        
        # Look for common happy hour keywords
        deals.extend(self._parse_text_patterns(soup))
        
        # Look for time patterns
        deals.extend(self._parse_time_patterns(soup))
        
        # Apply custom parsing configurations if available
        deals.extend(self._parse_with_custom_config(soup))
        
        return deals
    
    def _parse_json_ld(self, soup: BeautifulSoup) -> List[Deal]:
        """Parse JSON-LD structured data"""
        deals = []
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'Menu':
                    deals.extend(self._extract_deals_from_menu_data(data))
            except (json.JSONDecodeError, TypeError):
                continue
        
        return deals
    
    def _parse_text_patterns(self, soup: BeautifulSoup) -> List[Deal]:
        """Parse common text patterns for happy hour information"""
        deals = []
        text = soup.get_text().lower()
        
        # Enhanced patterns to capture scheduling details
        enhanced_patterns = [
            # Pattern: "11am-10pm‍friday: 11am-10:30pmsaturday: 12pm-10:30pmsunday: 12pm-9pmhappy hour" - multi-day schedule
            r'(\d{1,2}(?::\d{2})?(?:am|pm))\s*-\s*(\d{1,2}(?::\d{2})?(?:am|pm)).*?(?:friday|saturday|sunday|monday|tuesday|wednesday|thursday)',
            # Pattern: "happy hoursmonday-saturday: 11am-6:30pm sunday: all day"
            r'happy\s+hours?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*-\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*:\s*(\d{1,2}(?::\d{2})?(?:am|pm))\s*-?\s*(\d{1,2}(?::\d{2})?(?:am|pm))?',
            # Pattern: "EVERY DAY 3-6PM & 9-10pm" - City O City style
            r'every\s+day\s+(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*pm\s*&\s*(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*pm',
            # Pattern: "3-6PM & 9-10pm" - multiple time ranges
            r'(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*pm\s*&\s*(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*pm',
            # Pattern: "3-6pm every day" or "available 3-6pm every day"
            r'(?:available\s+)?(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*pm\s+every\s+day',
            # Pattern: "EVERY DAY 3-6PM"
            r'every\s+day\s+(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*pm',
            # Pattern: "$3 $6 $9 Happy Hour" - multiple prices with happy hour (STK style)
            r'(\$\d+(?:\s+\$\d+)*)\s+happy\s+hour',
            # Pattern: "9pm-close thurs-sat" or "9pm - close thu-sat"
            r'(\d{1,2}(?::\d{2})?)\s*pm\s*-?\s*close\s+(?:thurs?|thu)\s*-\s*(?:sats?|sat)',
            # Pattern: "25% off something every tuesday, all day" or "half-off something every tuesday, all day"
            r'(?:\d+%\s*off|half-off).*?every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun),?\s*all\s+day',
            # Pattern: "something every tuesday" or "every tuesday all day"
            r'(?:every\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)(?:\s*,?\s*all\s+day|\s*all\s+day)?',
            # Pattern: "happy hour 3pm-6pm monday-friday"
            r'happy\s+hour.*?(\d{1,2}(?::\d{2})?)\s*(?:am|pm)\s*-\s*(\d{1,2}(?::\d{2})?)\s*(?:am|pm).*?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)',
            # Pattern: "discounted drinks 4-7pm weekdays"
            r'(?:discounted|drink|special).*?(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*pm.*?(?:weekdays|weekends)',
            # Pattern: "SUN - SAT - All Day" (Fogo de Chão style)
            r'(sun|sunday)\s*-\s*(sat|saturday)\s*-?\s*all\s+day',
            # Pattern: "happy hour" followed by "SUN - SAT" and "All Day"  
            r'happy\s+hour.*?(sun|sunday)\s*-\s*(sat|saturday).*?all\s+day',
        ]
        
        for pattern in enhanced_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                deal_text = match.group(0)
                deal = self._create_deal_from_text(deal_text, match)
                if deal:
                    deals.append(deal)
        
        # Fallback to simpler patterns if no enhanced patterns found
        if not deals:
            simple_patterns = [
                r'happy hour.*?(\d{1,2}(?::\d{2})?\s*(?:am|pm))',
                r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)).*?happy hour',
                r'drink specials.*?(\d{1,2}(?::\d{2})?\s*(?:am|pm))'
            ]
            
            for pattern in simple_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    deal = Deal(
                        title="Happy Hour",
                        description=match.group(0)[:100],
                        deal_type=DealType.HAPPY_HOUR,
                        is_all_day=True,  # Fallback to all-day for simple patterns
                        confidence_score=0.4
                    )
                    deals.append(deal)
        
        return deals[:3]  # Limit to avoid duplicates
    
    def _create_deal_from_text(self, deal_text: str, match) -> Optional[Deal]:
        """Create a Deal object from parsed text with proper time and day extraction"""
        deal_text_lower = deal_text.lower()
        
        # Extract time ranges
        start_time = None
        end_time = None
        days_of_week = []
        is_all_day = False
        title = "Happy Hour"
        
        # Handle "$3 $6 $9 Happy Hour" style patterns (STK format)
        price_pattern_match = re.search(r'(\$\d+(?:\s+\$\d+)*)\s+happy\s+hour', deal_text_lower)
        if price_pattern_match:
            prices = price_pattern_match.group(1)
            deal = Deal(
                title="Happy Hour",
                description=f"Happy hour with items at {prices} pricing",
                deal_type=DealType.HAPPY_HOUR,
                is_all_day=False,  # Don't assume all-day without timing info
                confidence_score=0.6,  # Lower confidence since we don't have timing details
                source_url=getattr(self.restaurant, 'website', None)
            )
            deal.set_price_from_string(prices)
            return deal
        
        # Pattern: "happy hoursmonday-saturday: 11am-6:30pm"
        day_range_match = re.search(r'happy\s+hours?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*-\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*:\s*(\d{1,2}(?::\d{2})?(?:am|pm))\s*-?\s*(\d{1,2}(?::\d{2})?(?:am|pm))?', deal_text_lower)
        if day_range_match:
            start_day = self._parse_day_name(day_range_match.group(1))
            end_day = self._parse_day_name(day_range_match.group(2))
            start_time = self._normalize_time(day_range_match.group(3))
            end_time = self._normalize_time(day_range_match.group(4)) if day_range_match.group(4) else None
            
            if start_day and end_day:
                # Get days in range
                day_order = list(DayOfWeek)
                start_idx = day_order.index(start_day)
                end_idx = day_order.index(end_day)
                if start_idx <= end_idx:
                    days_of_week = day_order[start_idx:end_idx + 1]
                    title = "Weekly Happy Hour"
        
        # Pattern: "11am-10pm‍friday: 11am-10:30pmsaturday: 12pm-10:30pmsunday: 12pm-9pmhappy hour" - multi-day schedule
        elif re.search(r'(\d{1,2}(?::\d{2})?(?:am|pm))\s*-\s*(\d{1,2}(?::\d{2})?(?:am|pm)).*?(?:friday|saturday|sunday|monday|tuesday|wednesday|thursday)', deal_text_lower):
            # This is a multi-day pattern, but we'll just extract the first one for now
            # The enhanced scraper will create separate deals for each day in _parse_text_patterns
            time_match = re.search(r'(\d{1,2}(?::\d{2})?(?:am|pm))\s*-\s*(\d{1,2}(?::\d{2})?(?:am|pm))', deal_text_lower)
            if time_match:
                start_time = self._normalize_time(time_match.group(1))
                end_time = self._normalize_time(time_match.group(2))
                # Extract mentioned days
                day_names = re.findall(r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', deal_text_lower)
                days_of_week = [self._parse_day_name(day) for day in day_names if self._parse_day_name(day)]
                days_of_week = list(set(days_of_week))  # Remove duplicates
                if days_of_week:
                    if len(days_of_week) == 1:
                        title = f"{days_of_week[0].value.title()} Happy Hour"
                    elif len(days_of_week) <= 3:
                        # Create readable title for small sets
                        day_titles = [day.value.title() for day in days_of_week]
                        title = f"{', '.join(day_titles)} Happy Hour"
                    else:
                        title = "Weekly Happy Hour"
        
        # Pattern: "3-6pm every day" or "available 3-6pm every day"
        time_range_match = re.search(r'(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*pm\s+every\s+day', deal_text_lower)
        if time_range_match:
            start_time = self._normalize_time(time_range_match.group(1) + 'pm')
            end_time = self._normalize_time(time_range_match.group(2) + 'pm')
            days_of_week = list(DayOfWeek)  # All days
            title = "Daily Happy Hour"
        
        # Pattern: "9pm-close thurs-sat" or "9pm - close thu-sat" 
        elif re.search(r'(\d{1,2}(?::\d{2})?)\s*pm\s*-?\s*close\s+(?:thurs?|thu)\s*-\s*(?:sats?|sat)', deal_text_lower):
            time_match = re.search(r'(\d{1,2}(?::\d{2})?)\s*pm', deal_text_lower)
            if time_match:
                start_time = self._normalize_time(time_match.group(1) + 'pm')
                end_time = "Close"
                days_of_week = [DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY]
                title = "Late Night Happy Hour"
        
        # Pattern: "25% off something every tuesday, all day" or "half-off something every tuesday, all day"
        elif re.search(r'(?:\d+%\s*off|half-off).*?every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun),?\s*all\s+day', deal_text_lower):
            day_match = re.search(r'every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)', deal_text_lower)
            discount_match = re.search(r'(\d+%\s*off|half-off)', deal_text_lower)
            if day_match and discount_match:
                day_name = day_match.group(1)
                day_obj = self._parse_day_name(day_name)
                if day_obj:
                    days_of_week = [day_obj]
                    is_all_day = True
                    start_time = None
                    end_time = None
                    if 'vegan' in deal_text_lower and 'maki' in deal_text_lower:
                        title = "Vegan Maki Special"
                    elif 'sake' in deal_text_lower:
                        title = "Sake Special"
                    else:
                        title = f"{discount_match.group(1).title()} Special"
        
        # Pattern: "every tuesday" (fallback for simpler day-specific deals)
        elif re.search(r'every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)', deal_text_lower):
            day_match = re.search(r'every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)', deal_text_lower)
            if day_match:
                day_name = day_match.group(1)
                day_obj = self._parse_day_name(day_name)
                if day_obj:
                    days_of_week = [day_obj]
                    is_all_day = True
                    start_time = None
                    end_time = None
                    title = f"{day_name.title()} Special"
        
        # Pattern: time + weekdays/weekends
        elif 'weekdays' in deal_text_lower:
            time_match = re.search(r'(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*pm', deal_text_lower)
            if time_match:
                start_time = self._normalize_time(time_match.group(1) + 'pm')
                end_time = self._normalize_time(time_match.group(2) + 'pm')
                days_of_week = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
                title = "Weekday Happy Hour"
        
        elif 'weekends' in deal_text_lower:
            time_match = re.search(r'(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*pm', deal_text_lower)
            if time_match:
                start_time = self._normalize_time(time_match.group(1) + 'pm')
                end_time = self._normalize_time(time_match.group(2) + 'pm')
                days_of_week = [DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]
                title = "Weekend Happy Hour"
        
        # Pattern: "SUN - SAT - All Day" (Fogo de Chão style)
        elif re.search(r'(sun|sunday)\s*-\s*(sat|saturday)\s*-?\s*all\s+day', deal_text_lower):
            days_of_week = list(DayOfWeek)  # All days of the week
            is_all_day = True
            start_time = None
            end_time = None
            title = "All Day Happy Hour"
        
        # Create deal if we have proper time/day info OR if it's an all-day special
        if (start_time and end_time and days_of_week) or (is_all_day and days_of_week):
            # Generate a clean, informative description
            clean_description = self._generate_clean_description(deal_text, title, start_time, end_time, days_of_week, is_all_day)
            
            return Deal(
                title=title,
                description=clean_description,
                deal_type=DealType.HAPPY_HOUR,
                days_of_week=days_of_week,
                start_time=start_time,
                end_time=end_time,
                is_all_day=is_all_day,
                confidence_score=0.8,  # Higher confidence for parsed schedules
                source_url=self.restaurant.website
            )
        
        return None
    
    def _normalize_time(self, time_str: str) -> str:
        """Normalize time string to proper format"""
        time_str = time_str.strip().lower()
        
        # Handle cases like "3pm" -> "3:00 PM"
        if re.match(r'^\d{1,2}pm$', time_str):
            hour = time_str.replace('pm', '')
            return f"{hour}:00 PM"
        
        # Handle cases like "3:30pm" -> "3:30 PM"  
        if re.match(r'^\d{1,2}:\d{2}pm$', time_str):
            return time_str.replace('pm', ' PM')
        
        # Handle cases like "3am" -> "3:00 AM"
        if re.match(r'^\d{1,2}am$', time_str):
            hour = time_str.replace('am', '')
            return f"{hour}:00 AM"
            
        # Handle cases like "3:30am" -> "3:30 AM"
        if re.match(r'^\d{1,2}:\d{2}am$', time_str):
            return time_str.replace('am', ' AM')
        
        return time_str
    
    def _parse_day_name(self, day_name: str) -> Optional[DayOfWeek]:
        """Parse a day name string to DayOfWeek enum"""
        day_mapping = {
            'mon': DayOfWeek.MONDAY, 'monday': DayOfWeek.MONDAY,
            'tue': DayOfWeek.TUESDAY, 'tuesday': DayOfWeek.TUESDAY,
            'wed': DayOfWeek.WEDNESDAY, 'wednesday': DayOfWeek.WEDNESDAY,
            'thu': DayOfWeek.THURSDAY, 'thursday': DayOfWeek.THURSDAY,
            'fri': DayOfWeek.FRIDAY, 'friday': DayOfWeek.FRIDAY,
            'sat': DayOfWeek.SATURDAY, 'saturday': DayOfWeek.SATURDAY,
            'sun': DayOfWeek.SUNDAY, 'sunday': DayOfWeek.SUNDAY
        }
        return day_mapping.get(day_name.lower().strip())
    
    def _parse_time_patterns(self, soup: BeautifulSoup) -> List[Deal]:
        """Parse time-based patterns"""
        deals = []
        
        # Look for elements containing time patterns
        time_elements = soup.find_all(text=re.compile(r'\d{1,2}(?::\d{2})?\s*(?:am|pm).*?-.*?\d{1,2}(?::\d{2})?\s*(?:am|pm)', re.IGNORECASE))
        
        for element in time_elements[:5]:  # Limit to first 5 matches
            time_text = element.strip()
            if len(time_text) < 200:  # Reasonable length
                deal = Deal(
                    title="Time-based Special",
                    description=time_text,
                    deal_type=DealType.HAPPY_HOUR,
                    is_all_day=True,  # Set as all-day to pass validation
                    confidence_score=0.4  # Lower confidence for generic patterns
                )
                deals.append(deal)
        
        return deals
    
    def _generate_clean_description(self, original_text: str, title: str, start_time: str, end_time: str, days_of_week: list, is_all_day: bool) -> str:
        """Generate a clean, informative description from raw scraped text"""
        if not original_text:
            return "Happy hour specials available"
        
        # Clean the original text first
        cleaned = original_text.strip()
        
        # Apply custom exclude patterns if available from config
        if hasattr(self.restaurant.scraping_config, 'exclude_patterns') and self.restaurant.scraping_config.exclude_patterns:
            for pattern in self.restaurant.scraping_config.exclude_patterns:
                cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove invisible characters and weird spacing
        cleaned = re.sub(r'[\u200d\u200c\u00a0\u2060]+', ' ', cleaned)  # Remove zero-width joiners, etc.
        
        # Remove excessive newlines and whitespace (especially problematic for City O' City)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)  # Limit to max 2 consecutive newlines
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
        
        # Remove truncated content patterns
        cleaned = re.sub(r'\s+\w{1,5}$', '', cleaned)  # Remove trailing partial words like "spiri"
        
        # Remove redundant time/day patterns that are already in structured data
        if start_time and end_time:
            # Remove patterns like "11am-10pm" when we have structured time
            time_pattern = r'\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)'
            cleaned = re.sub(time_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove redundant day names when we have structured days
        if days_of_week:
            for day in days_of_week:
                day_name = day.value if hasattr(day, 'value') else str(day)
                cleaned = re.sub(rf'\b{day_name}\b', '', cleaned, flags=re.IGNORECASE)
        
        # Remove common filler words more carefully 
        cleaned = re.sub(r'\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(all|available|hour|hours)\b', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra whitespace and punctuation
        cleaned = re.sub(r'[,\s]+', ' ', cleaned).strip()
        cleaned = re.sub(r'^[,\s-]+|[,\s-]+$', '', cleaned)  # Remove leading/trailing punctuation
        
        # Check if what's left is just redundant timing/scheduling info
        timing_only_patterns = [
            r'^\d{1,2}(?::\d{2})?(?:am|pm)?\s*-\s*\d{1,2}(?::\d{2})?(?:am|pm)?\s*(?:close)?\s*(?:thurs?|fri|sat|sun|mon|tue|wed|thu|friday|saturday|sunday|monday|tuesday|wednesday|thursday)?\s*(?:every|day)?$',
            r'^(?:thurs?|fri|sat|sun|mon|tue|wed|thu|friday|saturday|sunday|monday|tuesday|wednesday|thursday)\s*-?\s*(?:thurs?|fri|sat|sun|mon|tue|wed|thu|friday|saturday|sunday|monday|tuesday|wednesday|thursday)?$',
            r'^\d{1,2}(?::\d{2})?(?:am|pm)?\s*-\s*(?:close)\s*(?:thurs?|fri|sat|sun|mon|tue|wed|thu|friday|saturday|sunday|monday|tuesday|wednesday|thursday)?\s*-?\s*(?:thurs?|fri|sat|sun|mon|tue|wed|thu|friday|saturday|sunday|monday|tuesday|wednesday|thursday)?$',
            r'^\d{1,2}(?::\d{2})?(?:am|pm)?\s*-\s*\d{1,2}(?::\d{2})?(?:am|pm)\s+every\s+day$',  # Catches "3-6pm every day"
            r'^(?:close)$',
            r'^(?:every)$'
        ]
        
        is_timing_only = any(re.match(pattern, cleaned, flags=re.IGNORECASE) for pattern in timing_only_patterns)
        
        # If we've cleaned away everything meaningful or only have timing info, generate a context-appropriate description
        if not cleaned or len(cleaned) < 5 or is_timing_only:
            # Try to infer what kind of deals these are based on context
            if 'vegan' in original_text.lower() and 'maki' in original_text.lower():
                return "Discounted vegan maki rolls and plant-based options"
            elif 'sake' in original_text.lower():
                return "Discounted sake and Japanese beverages"
            elif 'sushi' in title.lower() or 'maki' in original_text.lower():
                return "Happy hour sushi and specialty rolls"
            elif any(keyword in original_text.lower() for keyword in ['food', 'appetizer', 'app']):
                return "Discounted appetizers and food specials"
            elif any(keyword in original_text.lower() for keyword in ['drink', 'cocktail', 'beer', 'wine']):
                return "Discounted drinks and beverage specials"
            else:
                # Generate description based on title and timing context
                title_lower = title.lower()
                
                if 'daily' in title_lower and 'happy hour' in title_lower:
                    return "Daily happy hour with discounted food and drinks"
                elif 'late night' in title_lower:
                    return "Late night happy hour specials"
                elif 'weekend' in title_lower:
                    return "Weekend happy hour deals"
                elif any(day in title_lower for day in ['friday', 'saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday']):
                    # Day-specific deals
                    return "Special discounts and happy hour deals"
                elif is_all_day:
                    return "All-day happy hour specials and discounts"
                else:
                    return "Happy hour food and drink specials"
        
        # Capitalize first letter and ensure proper sentence structure
        cleaned = cleaned[0].upper() + cleaned[1:] if cleaned else ""
        
        # Add period if it doesn't end with punctuation
        if cleaned and not cleaned.endswith(('.', '!', '?')):
            cleaned += ""
        
        return cleaned[:150]  # Limit length
    
    def _extract_deals_from_menu_data(self, data: dict) -> List[Deal]:
        """Extract deals from JSON-LD menu data"""
        deals = []
        # Implementation would depend on specific JSON-LD structure
        # This is a placeholder for common patterns
        return deals
    
    def adaptive_delay(self):
        """Implement adaptive delays based on website response"""
        delay = self.current_delay + random.uniform(0, 0.5)  # Add jitter
        time.sleep(delay)
        
        # Adjust delay based on success/failure patterns
        if self.circuit_breaker.failure_count == 0:
            self.current_delay = max(self.base_delay, self.current_delay * 0.9)
        else:
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)
    
    def run(self) -> Tuple[ScrapingStatus, List[Deal], Optional[str]]:
        """
        Main method to run the scraper with comprehensive error handling
        Returns (status, deals, error_message)
        """
        error_message = None
        deals = []
        
        try:
            logger.info(f"Starting scrape for {self.restaurant.name}")
            
            # Update scraping metadata
            self.restaurant.scraping_config.last_scraped = datetime.now()
            
            # Attempt to scrape deals
            deals = self.scrape_deals()
            
            # Validate deals
            valid_deals = []
            for deal in deals:
                issues = DealValidator.validate_deal(deal)
                if not issues:
                    valid_deals.append(deal)
                else:
                    logger.warning(f"Invalid deal for {self.restaurant.name}: {issues}")
            
            if valid_deals:
                # Update restaurant with live deals
                self.restaurant.live_deals = valid_deals
                self.restaurant.deals_last_updated = datetime.now()
                self.restaurant.scraping_config.last_success = datetime.now()
                self.restaurant.scraping_config.consecutive_failures = 0
                
                logger.info(f"Successfully scraped {len(valid_deals)} deals for {self.restaurant.name}")
                return ScrapingStatus.SUCCESS, valid_deals, None
            
            else:
                # Try fallback parsing with all URLs for restaurants with multiple websites
                logger.info(f"No deals found with custom scraper, trying common patterns for {self.restaurant.name}")
                
                # Use all pages if restaurant has multiple URLs configured
                scraping_urls = getattr(self.restaurant, 'scraping_urls', None) or getattr(self.restaurant, 'websites', [])
                if len(scraping_urls) > 1:
                    logger.info(f"Trying fallback parsing on all {len(scraping_urls)} URLs")
                    soups = self.fetch_all_pages()
                    fallback_deals = []
                    for soup in soups:
                        fallback_deals.extend(self.parse_common_patterns(soup))
                else:
                    soup = self.fetch_page()
                    fallback_deals = self.parse_common_patterns(soup)
                
                if fallback_deals:
                    self.restaurant.live_deals = fallback_deals
                    self.restaurant.deals_last_updated = datetime.now()
                    return ScrapingStatus.PARTIAL, fallback_deals, "Used fallback parsing"
                else:
                    return ScrapingStatus.FAILURE, [], "No deals found"
        
        except PermanentScrapingError as e:
            error_message = f"Permanent error: {str(e)}"
            logger.error(f"Permanent scraping error for {self.restaurant.name}: {e}")
            self.restaurant.scraping_config.consecutive_failures += 1
            # Disable scraping if too many permanent failures
            if self.restaurant.scraping_config.consecutive_failures >= 5:
                self.restaurant.scraping_config.enabled = False
                error_message += " (scraping disabled due to repeated failures)"
            return ScrapingStatus.ERROR, [], error_message
        
        except TemporaryScrapingError as e:
            error_message = f"Temporary error: {str(e)}"
            logger.warning(f"Temporary scraping error for {self.restaurant.name}: {e}")
            self.restaurant.scraping_config.consecutive_failures += 1
            return ScrapingStatus.FAILURE, [], error_message
        
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error scraping {self.restaurant.name}: {e}")
            self.restaurant.scraping_config.consecutive_failures += 1
            return ScrapingStatus.ERROR, [], error_message
        
        finally:
            # Always be polite with delays
            self.adaptive_delay()
            
            elapsed = (datetime.now() - self.start_time).total_seconds()
            logger.info(f"Scraping completed for {self.restaurant.name} in {elapsed:.2f}s")
    
    def _parse_with_custom_config(self, soup: BeautifulSoup) -> List[Deal]:
        """Parse content using custom configuration settings"""
        deals = []
        config = self.restaurant.scraping_config
        
        # Return early if no custom config
        if not any([config.custom_selectors, config.time_pattern_regex, 
                   config.day_pattern_regex, config.content_containers]):
            return deals
        
        # Focus on specific content containers if specified
        target_soup = soup
        if config.content_containers:
            target_soup = BeautifulSoup("", "html.parser")
            for container_selector in config.content_containers:
                containers = soup.select(container_selector)
                for container in containers:
                    target_soup.append(container)
        
        # Extract content using custom selectors
        content_text = ""
        if config.custom_selectors:
            for selector_name, selector in config.custom_selectors.items():
                elements = target_soup.select(selector)
                for element in elements:
                    content_text += f" {element.get_text()} "
        else:
            content_text = target_soup.get_text()
        
        # Apply exclude patterns
        for exclude_pattern in config.exclude_patterns:
            content_text = re.sub(exclude_pattern, "", content_text, flags=re.IGNORECASE)
        
        # Extract using custom regex patterns
        deals.extend(self._extract_with_custom_patterns(content_text, config))
        
        return deals
    
    def _extract_with_custom_patterns(self, text: str, config) -> List[Deal]:
        """Extract deals using custom regex patterns"""
        deals = []
        
        # Extract times and days using custom patterns
        times = []
        days = []
        
        if config.time_pattern_regex:
            time_matches = re.finditer(config.time_pattern_regex, text, re.IGNORECASE)
            for match in time_matches:
                times.extend([g for g in match.groups() if g])
        
        if config.day_pattern_regex:
            day_matches = re.finditer(config.day_pattern_regex, text, re.IGNORECASE)
            for match in day_matches:
                days.extend([g for g in match.groups() if g])
        
        # Create deal if we found time and/or day information
        if times or days:
            description_parts = []
            if times:
                description_parts.append(f"Times: {', '.join(times)}")
            if days:
                description_parts.append(f"Days: {', '.join(days)}")
            
            # Extract start and end times (format them properly)
            start_time = None
            end_time = None
            if len(times) >= 4:  # We expect 4 groups: hour1, am/pm1, hour2, am/pm2
                start_time = f"{times[0]} {times[1].upper()}"
                end_time = f"{times[2]} {times[3].upper()}"
            elif len(times) >= 2:
                start_time = times[0]
                end_time = times[1]
            
            # Convert day strings to DayOfWeek enums
            day_enums = []
            is_all_day = False
            
            if days:
                # Special case: Check for "SUN - SAT" pattern (all week)
                days_text = ' '.join(days).lower()
                if ('sun' in days_text and 'sat' in days_text) or 'daily' in days_text or 'every day' in days_text:
                    day_enums = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                                DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]
                # Special case: if we have exactly "Monday" and "Friday", it likely means Monday through Friday
                elif (len(days) == 2 and 
                    'monday' in [d.lower().strip() for d in days] and 
                    'friday' in [d.lower().strip() for d in days]):
                    day_enums = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
                else:
                    # Normal individual day parsing
                    for day in days:
                        day_lower = day.lower().strip()
                        # Map day names to enums
                        day_mapping = {
                            'monday': DayOfWeek.MONDAY,
                            'tuesday': DayOfWeek.TUESDAY, 
                            'wednesday': DayOfWeek.WEDNESDAY,
                            'thursday': DayOfWeek.THURSDAY,
                            'friday': DayOfWeek.FRIDAY,
                            'saturday': DayOfWeek.SATURDAY,
                            'sunday': DayOfWeek.SUNDAY
                        }
                        if day_lower in day_mapping:
                            day_enums.append(day_mapping[day_lower])
            
            # Check for "All Day" patterns in the text
            if 'all day' in text.lower():
                is_all_day = True
            
            deal = Deal(
                title="Happy Hour",
                description=" | ".join(description_parts),
                deal_type=DealType.HAPPY_HOUR,
                days_of_week=day_enums,
                start_time=start_time,
                end_time=end_time,
                is_all_day=is_all_day,
                confidence_score=0.8,  # Higher confidence for custom patterns
                source_url=None
            )
            deals.append(deal)
        
        return deals


# Utility functions for common parsing tasks
class ParsingUtils:
    """Utility functions for common parsing patterns"""
    
    @staticmethod
    def parse_day_range(day_text: str) -> List[DayOfWeek]:
        """Parse day ranges like 'Monday - Friday' or 'Tue, Wed, Thu'"""
        days = []
        day_mapping = {
            'mon': DayOfWeek.MONDAY, 'monday': DayOfWeek.MONDAY,
            'tue': DayOfWeek.TUESDAY, 'tuesday': DayOfWeek.TUESDAY,
            'wed': DayOfWeek.WEDNESDAY, 'wednesday': DayOfWeek.WEDNESDAY,
            'thu': DayOfWeek.THURSDAY, 'thursday': DayOfWeek.THURSDAY,
            'fri': DayOfWeek.FRIDAY, 'friday': DayOfWeek.FRIDAY,
            'sat': DayOfWeek.SATURDAY, 'saturday': DayOfWeek.SATURDAY,
            'sun': DayOfWeek.SUNDAY, 'sunday': DayOfWeek.SUNDAY
        }
        
        day_text = day_text.lower().strip()
        
        # Handle ranges like "monday - friday"
        if ' - ' in day_text or ' to ' in day_text:
            parts = re.split(r' - | to ', day_text)
            if len(parts) == 2:
                start_day = day_mapping.get(parts[0].strip())
                end_day = day_mapping.get(parts[1].strip())
                if start_day and end_day:
                    # Get days in range
                    day_order = list(DayOfWeek)
                    start_idx = day_order.index(start_day)
                    end_idx = day_order.index(end_day)
                    if start_idx <= end_idx:
                        return day_order[start_idx:end_idx + 1]
        
        # Handle comma-separated days - but check for weekday range patterns first
        day_parts = [part.strip() for part in re.split(r'[,&]', day_text)]
        
        # Special case: if we see "monday, friday" it might mean "monday through friday"
        if len(day_parts) == 2:
            first_day = day_mapping.get(day_parts[0])
            second_day = day_mapping.get(day_parts[1])
            
            # If it's Monday and Friday, it's likely Monday through Friday (weekdays)
            if first_day == DayOfWeek.MONDAY and second_day == DayOfWeek.FRIDAY:
                return [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
        
        # Otherwise, treat as individual days
        for day_part in day_parts:
            if day_part in day_mapping:
                days.append(day_mapping[day_part])
        
        return days
    
    @staticmethod
    def normalize_time(time_str: str) -> str:
        """Normalize time strings to consistent format"""
        time_str = time_str.strip()
        
        # Handle common variations
        time_str = re.sub(r'(\d+)([ap]m)', r'\1:00 \2', time_str, flags=re.IGNORECASE)
        time_str = re.sub(r'(\d+):(\d+)([ap]m)', r'\1:\2 \3', time_str, flags=re.IGNORECASE)
        
        # Capitalize AM/PM
        time_str = re.sub(r'([ap])m', lambda m: m.group(0).upper(), time_str, flags=re.IGNORECASE)
        
        return time_str


if __name__ == "__main__":
    # Test parsing utilities
    print("Testing day parsing:")
    print(ParsingUtils.parse_day_range("Monday - Friday"))
    print(ParsingUtils.parse_day_range("Tue, Wed, Thu"))
    
    print("\nTesting time normalization:")
    print(ParsingUtils.normalize_time("3pm"))
    print(ParsingUtils.normalize_time("5:30pm"))
    print(ParsingUtils.normalize_time("11am"))