#!/usr/bin/env python3
"""
Data models and schemas for Sips and Steals
Enhanced models for restaurant data and deal validation
"""

from datetime import datetime, time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import re
import json


class DealType(Enum):
    """Types of deals we track"""
    HAPPY_HOUR = "happy_hour"
    DAILY_SPECIAL = "daily_special"
    FOOD_SPECIAL = "food_special"
    DRINK_SPECIAL = "drink_special"
    WEEKLY_SPECIAL = "weekly_special"
    BRUNCH_SPECIAL = "brunch_special"


class DayOfWeek(Enum):
    """Days of the week"""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class ScrapingStatus(Enum):
    """Status of scraping attempts"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class Deal:
    """
    Represents a single happy hour deal or special
    """
    title: str
    description: Optional[str] = None
    deal_type: DealType = DealType.HAPPY_HOUR
    days_of_week: List[DayOfWeek] = field(default_factory=list)
    start_time: Optional[str] = None  # Format: "3:00 PM" or "All Day"
    end_time: Optional[str] = None    # Format: "6:00 PM" or "Close"
    price: Optional[str] = None       # Format: "$5" or "$2-4"
    is_all_day: bool = False
    special_notes: List[str] = field(default_factory=list)
    
    # Metadata
    scraped_at: datetime = field(default_factory=datetime.now)
    source_url: Optional[str] = None
    confidence_score: float = 1.0  # 0.0-1.0, how confident we are in this data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'title': self.title,
            'description': self.description,
            'deal_type': self.deal_type.value,
            'days_of_week': [day.value for day in self.days_of_week],
            'start_time': self.start_time,
            'end_time': self.end_time,
            'price': self.price,
            'is_all_day': self.is_all_day,
            'special_notes': self.special_notes,
            'scraped_at': self.scraped_at.isoformat(),
            'source_url': self.source_url,
            'confidence_score': self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Deal':
        """Create Deal from dictionary"""
        return cls(
            title=data['title'],
            description=data.get('description'),
            deal_type=DealType(data.get('deal_type', 'happy_hour')),
            days_of_week=[DayOfWeek(day) for day in data.get('days_of_week', [])],
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            price=data.get('price'),
            is_all_day=data.get('is_all_day', False),
            special_notes=data.get('special_notes', []),
            scraped_at=datetime.fromisoformat(data.get('scraped_at', datetime.now().isoformat())),
            source_url=data.get('source_url'),
            confidence_score=data.get('confidence_score', 1.0)
        )


@dataclass
class ScrapingConfig:
    """Configuration for scraping a specific restaurant"""
    enabled: bool = True
    scraping_frequency_hours: int = 24  # How often to scrape (in hours)
    max_retries: int = 3
    timeout_seconds: int = 30
    custom_headers: Dict[str, str] = field(default_factory=dict)
    requires_javascript: bool = False
    scraper_class: Optional[str] = None  # Name of specific scraper class
    fallback_to_static: bool = True      # Fall back to Giovanni's data if scraping fails
    last_scraped: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0


@dataclass
class Restaurant:
    """
    Enhanced restaurant model combining static data with scraping config
    """
    # Static data (from Giovanni's markdown)
    name: str
    slug: str
    district: str
    neighborhood: Optional[str] = None
    address: Optional[str] = None
    cuisine: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    
    # Static happy hour info (fallback)
    static_happy_hour_times: List[str] = field(default_factory=list)
    special_notes: List[str] = field(default_factory=list)
    
    # Live scraping config and status
    scraping_config: ScrapingConfig = field(default_factory=ScrapingConfig)
    
    # Live deals (scraped data)
    live_deals: List[Deal] = field(default_factory=list)
    deals_last_updated: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'slug': self.slug,
            'district': self.district,
            'neighborhood': self.neighborhood,
            'address': self.address,
            'cuisine': self.cuisine,
            'website': self.website,
            'phone': self.phone,
            'static_happy_hour_times': self.static_happy_hour_times,
            'special_notes': self.special_notes,
            'scraping_config': {
                'enabled': self.scraping_config.enabled,
                'scraping_frequency_hours': self.scraping_config.scraping_frequency_hours,
                'max_retries': self.scraping_config.max_retries,
                'timeout_seconds': self.scraping_config.timeout_seconds,
                'custom_headers': self.scraping_config.custom_headers,
                'requires_javascript': self.scraping_config.requires_javascript,
                'scraper_class': self.scraping_config.scraper_class,
                'fallback_to_static': self.scraping_config.fallback_to_static,
                'last_scraped': self.scraping_config.last_scraped.isoformat() if self.scraping_config.last_scraped else None,
                'last_success': self.scraping_config.last_success.isoformat() if self.scraping_config.last_success else None,
                'consecutive_failures': self.scraping_config.consecutive_failures
            },
            'live_deals': [deal.to_dict() for deal in self.live_deals],
            'deals_last_updated': self.deals_last_updated.isoformat() if self.deals_last_updated else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Restaurant':
        """Create Restaurant from dictionary"""
        scraping_config_data = data.get('scraping_config', {})
        scraping_config = ScrapingConfig(
            enabled=scraping_config_data.get('enabled', True),
            scraping_frequency_hours=scraping_config_data.get('scraping_frequency_hours', 24),
            max_retries=scraping_config_data.get('max_retries', 3),
            timeout_seconds=scraping_config_data.get('timeout_seconds', 30),
            custom_headers=scraping_config_data.get('custom_headers', {}),
            requires_javascript=scraping_config_data.get('requires_javascript', False),
            scraper_class=scraping_config_data.get('scraper_class'),
            fallback_to_static=scraping_config_data.get('fallback_to_static', True),
            last_scraped=datetime.fromisoformat(scraping_config_data['last_scraped']) if scraping_config_data.get('last_scraped') else None,
            last_success=datetime.fromisoformat(scraping_config_data['last_success']) if scraping_config_data.get('last_success') else None,
            consecutive_failures=scraping_config_data.get('consecutive_failures', 0)
        )
        
        return cls(
            name=data['name'],
            slug=data['slug'],
            district=data['district'],
            neighborhood=data.get('neighborhood'),
            address=data.get('address'),
            cuisine=data.get('cuisine'),
            website=data.get('website'),
            phone=data.get('phone'),
            static_happy_hour_times=data.get('static_happy_hour_times', []),
            special_notes=data.get('special_notes', []),
            scraping_config=scraping_config,
            live_deals=[Deal.from_dict(deal_data) for deal_data in data.get('live_deals', [])],
            deals_last_updated=datetime.fromisoformat(data['deals_last_updated']) if data.get('deals_last_updated') else None
        )
    
    def needs_scraping(self) -> bool:
        """Check if this restaurant needs to be scraped"""
        if not self.scraping_config.enabled or not self.website:
            return False
        
        if not self.scraping_config.last_scraped:
            return True
        
        hours_since_last_scrape = (datetime.now() - self.scraping_config.last_scraped).total_seconds() / 3600
        return hours_since_last_scrape >= self.scraping_config.scraping_frequency_hours
    
    def get_current_deals(self) -> List[Deal]:
        """
        Get the best available deals with clear prioritization:
        1. Fresh live scraped data (< 7 days old) - highest priority
        2. Any live scraped data (even if older) - medium priority  
        3. Static Giovanni's data - lowest priority (fallback only)
        """
        # Priority 1: Fresh live deals (less than 7 days old)
        if (self.live_deals and 
            self.deals_last_updated and 
            (datetime.now() - self.deals_last_updated).days < 7):
            return self.live_deals
        
        # Priority 2: Any live deals (even if older than 7 days)
        # Live scraped data is still more accurate than static data
        if self.live_deals:
            return self.live_deals
        
        # Priority 3: Fall back to static Giovanni's data only if no live data exists
        if self.static_happy_hour_times:
            fallback_deals = []
            for time_str in self.static_happy_hour_times:
                # Parse and reformat the static data for better display
                formatted_description = self._format_static_happy_hour(time_str)
                fallback_deals.append(Deal(
                    title="Happy Hour (from Giovanni's data)",
                    description=formatted_description,
                    deal_type=DealType.HAPPY_HOUR,
                    confidence_score=0.3,  # Lower confidence for static data
                    source_url=None  # No source URL for static data
                ))
            return fallback_deals
        
        return []
    
    def _format_static_happy_hour(self, time_str: str) -> str:
        """Format static Giovanni's data with compact day ranges"""
        import re
        
        # Define day patterns and their compact replacements
        # ORDER MATTERS: Check longer patterns first!
        day_replacements = [
            # Full week patterns FIRST (before weekday patterns)
            (r'\bMon,\s*Tue,\s*Wed,\s*Thu,\s*Fri,\s*Sat,\s*Sun\b', 'Daily'),
            (r'\bMonday,\s*Tuesday,\s*Wednesday,\s*Thursday,\s*Friday,\s*Saturday,\s*Sunday\b', 'Daily'),
            
            # Full weekday sequences
            (r'\bMon,\s*Tue,\s*Wed,\s*Thu,\s*Fri\b', 'Mon - Fri'),
            (r'\bMonday,\s*Tuesday,\s*Wednesday,\s*Thursday,\s*Friday\b', 'Mon - Fri'),
            
            # Weekend patterns
            (r'\bSat,\s*Sun\b', 'Sat - Sun'),
            (r'\bSaturday,\s*Sunday\b', 'Sat - Sun'),
            
            # Other common consecutive ranges
            (r'\bMon,\s*Tue,\s*Wed\b', 'Mon - Wed'),
            (r'\bThu,\s*Fri,\s*Sat\b', 'Thu - Sat'),
            (r'\bFri,\s*Sat\b', 'Fri - Sat'),
            (r'\bTue,\s*Wed,\s*Thu\b', 'Tue - Thu'),
            
            # Individual day abbreviations (keep as-is, but standardize)
            (r'\bMonday\b', 'Mon'),
            (r'\bTuesday\b', 'Tue'),
            (r'\bWednesday\b', 'Wed'),
            (r'\bThursday\b', 'Thu'),
            (r'\bFriday\b', 'Fri'),
            (r'\bSaturday\b', 'Sat'),
            (r'\bSunday\b', 'Sun'),
        ]
        
        formatted = time_str
        
        # Apply day replacements
        for pattern, replacement in day_replacements:
            formatted = re.sub(pattern, replacement, formatted, flags=re.IGNORECASE)
        
        # Clean up extra spaces and standardize formatting
        formatted = re.sub(r'\s+', ' ', formatted)  # Multiple spaces to single
        formatted = re.sub(r'\s*-\s*', ' - ', formatted)  # Standardize dashes
        formatted = re.sub(r'\s*\|\s*', ' | ', formatted)  # Standardize pipes
        
        return formatted.strip()


class DealValidator:
    """Validates deal data for quality and consistency"""
    
    TIME_PATTERNS = [
        r'\d{1,2}:\d{2}\s*(AM|PM)',  # 3:00 PM
        r'\d{1,2}\s*(AM|PM)',        # 3 PM
        r'All Day',
        r'Close',
        r'Open'
    ]
    
    PRICE_PATTERNS = [
        r'\$\d+(\.\d{2})?',          # $5.00
        r'\$\d+-\d+',                # $5-8
        r'\d+¢',                     # 50¢
        r'[Ff]ree'                   # Free
    ]
    
    @classmethod
    def validate_deal(cls, deal: Deal) -> List[str]:
        """Validate a deal and return list of issues found"""
        issues = []
        
        # Title validation
        if not deal.title or len(deal.title.strip()) < 3:
            issues.append("Title is too short or empty")
        
        # Time validation
        if deal.start_time and not cls._is_valid_time(deal.start_time):
            issues.append(f"Invalid start time format: {deal.start_time}")
        
        if deal.end_time and not cls._is_valid_time(deal.end_time):
            issues.append(f"Invalid end time format: {deal.end_time}")
        
        # Price validation
        if deal.price and not cls._is_valid_price(deal.price):
            issues.append(f"Invalid price format: {deal.price}")
        
        # Day validation
        if not deal.days_of_week and not deal.is_all_day:
            issues.append("No days specified and not marked as all day")
        
        # Confidence score validation
        if not 0.0 <= deal.confidence_score <= 1.0:
            issues.append(f"Confidence score out of range: {deal.confidence_score}")
        
        return issues
    
    @classmethod
    def _is_valid_time(cls, time_str: str) -> bool:
        """Check if time string matches expected patterns"""
        if not time_str:
            return False
        return any(re.search(pattern, time_str, re.IGNORECASE) for pattern in cls.TIME_PATTERNS)
    
    @classmethod
    def _is_valid_price(cls, price_str: str) -> bool:
        """Check if price string matches expected patterns"""
        if not price_str:
            return False
        return any(re.search(pattern, price_str, re.IGNORECASE) for pattern in cls.PRICE_PATTERNS)


if __name__ == "__main__":
    # Test the models
    deal = Deal(
        title="Happy Hour Drinks",
        description="$5 craft cocktails",
        deal_type=DealType.HAPPY_HOUR,
        days_of_week=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY],
        start_time="3:00 PM",
        end_time="6:00 PM",
        price="$5"
    )
    
    print("Deal validation:", DealValidator.validate_deal(deal))
    print("Deal JSON:", json.dumps(deal.to_dict(), indent=2, default=str))