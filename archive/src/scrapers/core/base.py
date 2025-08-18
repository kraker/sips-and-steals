#!/usr/bin/env python3
"""
Simplified base scraper interface focusing on core scraping concerns
HTTP handling, parsing, and post-processing are delegated to specialized classes
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

# Import our models and components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from models import Restaurant, Deal, ScrapingStatus, DealValidator

from .http_client import HttpClient
from ..processors.post_processor import PostProcessor
from ..exceptions import ScrapingError, TemporaryScrapingError, PermanentScrapingError

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Simplified base scraper focusing on core responsibilities:
    1. Define scraping interface
    2. Orchestrate HTTP client, parsers, and post-processors
    3. Handle high-level error management
    """
    
    def __init__(self, restaurant: Restaurant, config: Dict[str, Any] = None):
        self.restaurant = restaurant
        self.config = config or {}
        self.start_time = datetime.now()
        
        # Initialize specialized components
        self.http_client = HttpClient(self._get_http_config())
        self.post_processor = PostProcessor(self.config) if self.config else None
    
    def _get_http_config(self) -> Dict[str, Any]:
        """Extract HTTP-specific configuration"""
        http_config = {}
        
        if hasattr(self.restaurant, 'scraping_config'):
            scraping_config = self.restaurant.scraping_config
            http_config.update({
                'timeout_seconds': getattr(scraping_config, 'timeout_seconds', 30),
                'custom_headers': getattr(scraping_config, 'custom_headers', {}),
                'base_delay': 2.0,
                'max_delay': 60.0
            })
        
        return http_config
    
    @abstractmethod
    def scrape_deals(self) -> List[Deal]:
        """
        Core scraping method to be implemented by subclasses
        Should return raw deals before post-processing
        """
        pass
    
    def fetch_page(self, url: Optional[str] = None) -> str:
        """Fetch and return page content as string"""
        if url:
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
        
        # Try each URL until we get valid content
        for url in urls_to_try:
            try:
                response = self.http_client.fetch_url(url)
                # Basic content validation
                if len(response.text) > 500:  # Minimum content threshold
                    return response.text
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                continue
        
        raise PermanentScrapingError("No valid content found at any URL")
    
    def run(self) -> Tuple[ScrapingStatus, List[Deal], Optional[str]]:
        """
        Main execution method with comprehensive error handling
        Returns (status, deals, error_message)
        """
        error_message = None
        deals = []
        
        try:
            logger.info(f"Starting scrape for {self.restaurant.name}")
            
            # Update scraping metadata
            if hasattr(self.restaurant, 'scraping_config'):
                self.restaurant.scraping_config.last_scraped = datetime.now()
            
            # Scrape raw deals
            raw_deals = self.scrape_deals()
            
            # Apply post-processing if configured
            if self.post_processor:
                deals = self.post_processor.enhance_deals(raw_deals)
                logger.info(f"Post-processing enhanced {len(raw_deals)} deals to {len(deals)} deals")
            else:
                deals = raw_deals
            
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
                
                if hasattr(self.restaurant, 'scraping_config'):
                    self.restaurant.scraping_config.last_success = datetime.now()
                    self.restaurant.scraping_config.consecutive_failures = 0
                
                logger.info(f"Successfully scraped {len(valid_deals)} deals for {self.restaurant.name}")
                return ScrapingStatus.SUCCESS, valid_deals, None
            else:
                return ScrapingStatus.FAILURE, [], "No valid deals found"
        
        except PermanentScrapingError as e:
            error_message = f"Permanent error: {str(e)}"
            logger.error(f"Permanent scraping error for {self.restaurant.name}: {e}")
            
            if hasattr(self.restaurant, 'scraping_config'):
                self.restaurant.scraping_config.consecutive_failures += 1
                # Disable scraping if too many permanent failures
                if self.restaurant.scraping_config.consecutive_failures >= 5:
                    self.restaurant.scraping_config.enabled = False
                    error_message += " (scraping disabled due to repeated failures)"
            
            return ScrapingStatus.ERROR, [], error_message
        
        except TemporaryScrapingError as e:
            error_message = f"Temporary error: {str(e)}"
            logger.warning(f"Temporary scraping error for {self.restaurant.name}: {e}")
            
            if hasattr(self.restaurant, 'scraping_config'):
                self.restaurant.scraping_config.consecutive_failures += 1
            
            return ScrapingStatus.FAILURE, [], error_message
        
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error scraping {self.restaurant.name}: {e}")
            
            if hasattr(self.restaurant, 'scraping_config'):
                self.restaurant.scraping_config.consecutive_failures += 1
            
            return ScrapingStatus.ERROR, [], error_message
        
        finally:
            # Always be polite with delays
            self.http_client.adaptive_delay()
            
            elapsed = (datetime.now() - self.start_time).total_seconds()
            logger.info(f"Scraping completed for {self.restaurant.name} in {elapsed:.2f}s")


class ConfigBasedScraper(BaseScraper):
    """
    Scraper that uses YAML configuration for pattern matching
    This replaces the complex pattern matching logic from the original BaseScraper
    """
    
    def scrape_deals(self) -> List[Deal]:
        """Scrape using configuration-based patterns"""
        from bs4 import BeautifulSoup
        import re
        
        all_deals = []
        
        # Check if restaurant has multiple URLs to try
        if hasattr(self.restaurant, 'scraping_urls') and len(getattr(self.restaurant, 'scraping_urls', [])) > 1:
            # Try all URLs and combine deals
            urls_to_try = getattr(self.restaurant, 'scraping_urls')
            logger.info(f"Trying all {len(urls_to_try)} URLs for {self.restaurant.name}")
            
            for url in urls_to_try:
                try:
                    content = self.fetch_page(url)
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Use direct config-based pattern matching
                    page_deals = self._extract_deals_from_soup(soup)
                    
                    if page_deals:
                        logger.info(f"Found {len(page_deals)} deals from {url}")
                        all_deals.extend(page_deals)
                        
                except Exception as e:
                    logger.warning(f"Failed to process {url}: {e}")
                    continue
        else:
            # Single URL - use original logic
            content = self.fetch_page()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Use direct config-based pattern matching
            all_deals = self._extract_deals_from_soup(soup)
        
        return all_deals
    
    def _extract_deals_from_soup(self, soup) -> List[Deal]:
        """Extract deals from BeautifulSoup using YAML config patterns"""
        from bs4 import BeautifulSoup
        from models import DayOfWeek, Deal, DealType
        import re
        deals = []
        
        # Get scraping config from YAML
        scraping_config = self.config.get('scraping_config', {})
        
        # Focus on specific content containers if specified
        target_soup = soup
        content_containers = scraping_config.get('content_containers', [])
        if content_containers:
            for container_selector in content_containers:
                container = soup.select_one(container_selector)
                if container:
                    target_soup = container
                    logger.debug(f"Using content container: {container_selector}")
                    break
        
        # Get text content for pattern matching
        text = target_soup.get_text(separator=' ', strip=True)
        logger.debug(f"Processing text: {text[:200]}...")
        
        # Apply exclude patterns if specified
        exclude_patterns = scraping_config.get('exclude_patterns', [])
        for exclude_pattern in exclude_patterns:
            if exclude_pattern.lower() in text.lower():
                logger.debug(f"Excluding text matching: {exclude_pattern}")
                # Use regex to handle patterns with wildcards
                text = re.sub(exclude_pattern, '', text, flags=re.IGNORECASE)
            else:
                logger.debug(f"Exclude pattern '{exclude_pattern}' not found in text")
        
        logger.debug(f"Text after exclusions: {text[:200]}...")
        
        # Extract times and days using custom patterns
        times = []
        days = []
        
        # Extract time ranges (multiple ranges possible)
        time_ranges = []
        time_pattern = scraping_config.get('time_pattern_regex')
        if time_pattern:
            time_matches = list(re.finditer(time_pattern, text, re.IGNORECASE))
            for match in time_matches:
                time_ranges.append(match.groups())
            logger.debug(f"Time ranges found: {time_ranges}")
        
        day_pattern = scraping_config.get('day_pattern_regex')
        if day_pattern:
            day_matches = re.finditer(day_pattern, text, re.IGNORECASE)
            for match in day_matches:
                days.extend([g for g in match.groups() if g])
            logger.debug(f"Day matches found: {days}")
        
        # Create deals for each time range found
        if time_ranges or days:
            # If we have time ranges, create a deal for each one
            if time_ranges:
                for time_range in time_ranges:
                    hour1, ampm1, hour2, ampm2 = time_range
                    
                    # Handle shared AM/PM (e.g., "3-6PM" = "3PM-6PM") and missing AM/PM (assume PM for happy hour)
                    if ampm1 is None and ampm2 is None:
                        # No AM/PM specified, assume PM for happy hour times
                        start_time = f"{hour1} PM"
                        end_time = f"{hour2} PM"
                    elif ampm1 is None and ampm2 is not None:
                        start_time = f"{hour1} {ampm2.upper()}"
                        end_time = f"{hour2} {ampm2.upper()}"
                    elif ampm1 is not None and ampm2 is not None:
                        start_time = f"{hour1} {ampm1.upper()}"
                        end_time = f"{hour2} {ampm2.upper()}"
                    else:
                        start_time = f"{hour1} {ampm2.upper() if ampm2 else 'PM'}"
                        end_time = f"{hour2} {ampm2.upper() if ampm2 else 'PM'}"
                    
                    deal = self._create_deal_from_data(start_time, end_time, days)
                    if deal:
                        deals.append(deal)
            
            # If we have days but no time ranges, create a deal with day info only  
            elif days and not time_ranges:
                deal = self._create_deal_from_data(None, None, days)
                if deal:
                    deals.append(deal)
        
        return deals
    
    def _create_deal_from_data(self, start_time, end_time, days):
        """Create a Deal object from extracted time and day data"""
        from models import DayOfWeek, Deal, DealType
        
        # Build description
        description_parts = []
        if start_time and end_time:
            description_parts.append(f"Time: {start_time} - {end_time}")
        if days:
            description_parts.append(f"Days: {', '.join(days)}")
        
        # Convert day strings to DayOfWeek enums
        day_enums = []
        is_all_day = False
        
        if days:
            # Special case: Check for "all day" patterns
            days_text = ' '.join(days).lower()
            if 'every day' in days_text or 'daily' in days_text:
                day_enums = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                           DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]
            elif 'all day' in days_text:
                is_all_day = True
                # If it's "all day" for specific days, still parse those days
                if 'sunday' in days_text and not ('monday' in days_text or 'saturday' in days_text):
                    day_enums = [DayOfWeek.SUNDAY]
                else:
                    day_enums = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                               DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]
            elif 'sunday - thursday' in days_text or 'sunday-thursday' in days_text:
                day_enums = [DayOfWeek.SUNDAY, DayOfWeek.MONDAY, DayOfWeek.TUESDAY, 
                           DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY]
            elif 'monday - friday' in days_text or 'monday-friday' in days_text:
                day_enums = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                           DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
            elif 'tuesday - friday' in days_text or 'tuesday-friday' in days_text:
                day_enums = [DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
            elif 'saturday - sunday' in days_text or 'saturday-sunday' in days_text:
                day_enums = [DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]
            elif 'friday - saturday' in days_text or 'friday-saturday' in days_text:
                day_enums = [DayOfWeek.FRIDAY, DayOfWeek.SATURDAY]
            elif 'monday-saturday' in days_text.replace('-', '').replace(' ', ''):
                day_enums = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                           DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY]
            else:
                # Parse individual days
                day_mapping = {
                    'monday': DayOfWeek.MONDAY, 'mon': DayOfWeek.MONDAY,
                    'tuesday': DayOfWeek.TUESDAY, 'tue': DayOfWeek.TUESDAY,
                    'wednesday': DayOfWeek.WEDNESDAY, 'wed': DayOfWeek.WEDNESDAY,
                    'thursday': DayOfWeek.THURSDAY, 'thu': DayOfWeek.THURSDAY,
                    'friday': DayOfWeek.FRIDAY, 'fri': DayOfWeek.FRIDAY,
                    'saturday': DayOfWeek.SATURDAY, 'sat': DayOfWeek.SATURDAY,
                    'sunday': DayOfWeek.SUNDAY, 'sun': DayOfWeek.SUNDAY
                }
                
                for day in days:
                    day_lower = day.lower().strip()
                    if day_lower in day_mapping:
                        day_enums.append(day_mapping[day_lower])
        
        # Create the deal
        deal = Deal(
            title="Happy Hour",
            description=" | ".join(description_parts) if description_parts else "Happy Hour",
            deal_type=DealType.HAPPY_HOUR,
            days_of_week=day_enums,
            start_time=start_time,
            end_time=end_time,
            is_all_day=is_all_day,
            confidence_score=0.8,  # Higher confidence for custom patterns
            source_url=None
        )
        
        logger.info(f"Created deal: {deal.title} | {start_time}-{end_time} | Days: {[d.value for d in day_enums]} | All day: {is_all_day}")
        return deal
    
    def scrape_restaurant_info(self) -> Dict[str, Any]:
        """Scrape operating hours, contact info, address, and other restaurant details"""
        from ..processors.text_processor import TextProcessor
        from ..processors.contact_extractor import ContactExtractor
        from bs4 import BeautifulSoup
        
        restaurant_info = {
            'operating_hours': {},
            'contact_info': {},
            'dining_info': {},
            'service_info': {},
            'address_info': {},
            'business_status': 'operational',
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            # Use primary URL for restaurant info
            content = self.fetch_page()
            soup = BeautifulSoup(content, 'html.parser')
            text_content = soup.get_text()
            
            # Initialize enhanced contact extractor
            contact_extractor = ContactExtractor(base_url=self.restaurant.website)
            
            # Extract comprehensive contact information
            contact_info = contact_extractor.extract_contact_info(soup, text_content)
            if contact_info:
                restaurant_info['contact_info'] = contact_info.to_dict()
                logger.info(f"Extracted enhanced contact info for {self.restaurant.name}: phone={contact_info.primary_phone}, email={contact_info.general_email}")
            
            # Extract service information (reservations, delivery, etc.)
            service_info = contact_extractor.extract_service_info(soup, text_content)
            if service_info:
                restaurant_info['service_info'] = service_info.to_dict()
                logger.info(f"Extracted service info for {self.restaurant.name}: reservations={service_info.accepts_reservations}, delivery={service_info.offers_delivery}")
            
            # Extract dining experience information
            dining_info = contact_extractor.extract_dining_info(soup, text_content)
            if dining_info:
                restaurant_info['dining_info'] = dining_info.to_dict()
                logger.info(f"Extracted dining info for {self.restaurant.name}: price_range={dining_info.price_range}, atmosphere={dining_info.atmosphere}")
            
            # Extract operating hours using enhanced extractor
            operating_hours = contact_extractor.extract_operating_hours(soup, text_content)
            if operating_hours:
                restaurant_info['operating_hours'] = operating_hours
                logger.info(f"Extracted operating hours for {self.restaurant.name}: {len(operating_hours)} days")
            
            # Fallback to original text processor for additional patterns
            text_processor = TextProcessor(self.config, restaurant=self.restaurant)
            
            # Extract address information using existing address parser
            address_info = text_processor.extract_address_info(soup)
            if address_info:
                restaurant_info['address_info'] = address_info
                logger.info(f"Extracted address info for {self.restaurant.name}: {address_info.get('formatted_address', 'Structured address')}")
                
        except Exception as e:
            logger.error(f"Failed to scrape restaurant info for {self.restaurant.name}: {e}")
            # Re-raise exception so calling code can handle failure tracking
            raise e
        
        return restaurant_info