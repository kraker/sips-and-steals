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
import pendulum


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


class BusinessStatus(Enum):
    """Restaurant business operational status"""
    OPERATIONAL = "operational"
    TEMPORARILY_CLOSED = "temporarily_closed"
    PERMANENTLY_CLOSED = "permanently_closed"
    UNKNOWN = "unknown"


class PriceRange(Enum):
    """Restaurant price range indicator"""
    BUDGET = "$"           # Under $15 per person
    MODERATE = "$$"        # $15-30 per person  
    UPSCALE = "$$$"        # $30-60 per person
    FINE_DINING = "$$$$"   # $60+ per person


@dataclass
class Deal:
    """
    Represents a single happy hour deal or special
    """
    title: str
    description: Optional[str] = None
    deal_type: DealType = DealType.HAPPY_HOUR
    days_of_week: List[DayOfWeek] = field(default_factory=list)
    
    # Time fields - dual storage for display and calculations
    start_time: Optional[str] = None      # Display format: "3:00 PM" or "All Day"
    end_time: Optional[str] = None        # Display format: "6:00 PM" or "Close"
    start_time_24h: Optional[str] = None  # 24-hour format: "15:00" (for calculations)
    end_time_24h: Optional[str] = None    # 24-hour format: "18:00" (for calculations)
    timezone: str = "America/Denver"      # IANA timezone identifier
    
    prices: List[str] = field(default_factory=list)  # Format: ["$5 Beers", "$8 Wines", "$10 Cocktails"]
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
            'start_time_24h': self.start_time_24h,
            'end_time_24h': self.end_time_24h,
            'timezone': self.timezone,
            'prices': self.prices,
            'is_all_day': self.is_all_day,
            'special_notes': self.special_notes,
            'scraped_at': self.scraped_at.isoformat(),
            'source_url': self.source_url,
            'confidence_score': self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Deal':
        """Create Deal from dictionary, handling both legacy and new formats"""
        # Handle legacy price field by converting to new prices format
        prices = data.get('prices', [])
        legacy_price = data.get('price')
        
        # If no prices list but legacy price exists, convert it
        if not prices and legacy_price:
            # Use the existing parsing logic to convert legacy price to prices list
            deal = cls(
                title=data['title'],
                description=data.get('description'),
                deal_type=DealType(data.get('deal_type', 'happy_hour')),
                days_of_week=[DayOfWeek(day) for day in data.get('days_of_week', [])],
                start_time=data.get('start_time'),
                end_time=data.get('end_time'),
                start_time_24h=data.get('start_time_24h'),
                end_time_24h=data.get('end_time_24h'),
                timezone=data.get('timezone', 'America/Denver'),
                prices=[],  # Will be set below
                is_all_day=data.get('is_all_day', False),
                special_notes=data.get('special_notes', []),
                scraped_at=datetime.fromisoformat(data.get('scraped_at', datetime.now().isoformat())),
                source_url=data.get('source_url'),
                confidence_score=data.get('confidence_score', 1.0)
            )
            # Convert legacy price to new format
            deal.set_price_from_string(legacy_price)
            # Auto-normalize times if 24-hour format is missing
            deal._normalize_times()
            return deal
        
        deal = cls(
            title=data['title'],
            description=data.get('description'),
            deal_type=DealType(data.get('deal_type', 'happy_hour')),
            days_of_week=[DayOfWeek(day) for day in data.get('days_of_week', [])],
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            start_time_24h=data.get('start_time_24h'),
            end_time_24h=data.get('end_time_24h'),
            timezone=data.get('timezone', 'America/Denver'),
            prices=prices,
            is_all_day=data.get('is_all_day', False),
            special_notes=data.get('special_notes', []),
            scraped_at=datetime.fromisoformat(data.get('scraped_at', datetime.now().isoformat())),
            source_url=data.get('source_url'),
            confidence_score=data.get('confidence_score', 1.0)
        )
        
        # Auto-normalize times if 24-hour format is missing
        deal._normalize_times()
        return deal
    
    def parse_price_string(self, price_string: str) -> List[str]:
        """Parse a price string into structured price list
        
        Examples:
        "$5 Beers, $8 Wines, $10 Cocktails" -> ["$5 Beers", "$8 Wines", "$10 Cocktails"]
        "$5 Beers, $8 South American Wines and $10 Brazilian-Inspired Cocktails" -> ["$5 Beers", "$8 South American Wines", "$10 Brazilian-Inspired Cocktails"]
        """
        if not price_string:
            return []
        
        import re
        
        # Pattern to match price items: $amount + description
        # Handles various separators: comma, "and", "&"
        price_pattern = r'\$\d+(?:\.\d{2})?\s*[^,$&]+?(?=\s*(?:,|and|&|\$|$))'
        
        matches = re.findall(price_pattern, price_string, re.IGNORECASE)
        
        # Clean up each match
        cleaned_prices = []
        for match in matches:
            # Remove trailing punctuation and extra whitespace
            cleaned = re.sub(r'[,&]+$', '', match.strip())
            cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
            if cleaned:
                cleaned_prices.append(cleaned)
        
        return cleaned_prices
    
    def set_price_from_string(self, price_string: str):
        """Set structured prices field from price string"""
        self.prices = self.parse_price_string(price_string)
    
    def set_time_from_string(self, start_time_str: Optional[str], end_time_str: Optional[str]):
        """Parse and set both display and 24-hour time formats"""
        self.start_time = start_time_str
        self.end_time = end_time_str
        
        # Convert to 24-hour format for calculations
        if start_time_str and start_time_str.lower() not in ['all day', 'close', 'open']:
            self.start_time_24h = self._parse_time_to_24h(start_time_str)
        
        if end_time_str and end_time_str.lower() not in ['all day', 'close', 'open']:
            self.end_time_24h = self._parse_time_to_24h(end_time_str)
    
    def _parse_time_to_24h(self, time_str: str) -> Optional[str]:
        """Convert various time formats to 24-hour format (HH:MM)"""
        if not time_str:
            return None
            
        import re
        
        # Clean the input
        time_str = time_str.strip()
        
        # Skip pendulum for ambiguous short inputs that could be dates
        use_pendulum = True
        if re.match(r'^\d{1,2}$', time_str):
            # Don't use pendulum for single numbers (could be interpreted as dates)
            use_pendulum = False
        
        if use_pendulum:
            try:
                # Try parsing with pendulum for complex time formats
                parsed_time = pendulum.parse(time_str, strict=False)
                # Verify it's actually a time, not a date interpretation
                if parsed_time.hour != 0 or parsed_time.minute != 0 or 'PM' in time_str.upper() or 'AM' in time_str.upper():
                    return parsed_time.format('HH:mm')
            except:
                pass
        
        # Use regex-based parsing for better control
        # Handle patterns like "3:00 PM", "15:00", "3 PM", etc.
        patterns = [
            r'(\d{1,2}):(\d{2})\s*(AM|PM)',  # 3:00 PM
            r'(\d{1,2})\s*(AM|PM)',          # 3 PM
            r'(\d{1,2}):(\d{2})',            # 15:00 or 3:00
            r'(\d{1,2})\.(\d{2})',           # 15.30
        ]
        
        for pattern in patterns:
            match = re.search(pattern, time_str.upper())
            if match:
                if len(match.groups()) == 3:  # Has AM/PM
                    hour, minute, ampm = match.groups()
                    hour = int(hour)
                    minute = int(minute)
                    
                    if ampm == 'PM' and hour != 12:
                        hour += 12
                    elif ampm == 'AM' and hour == 12:
                        hour = 0
                        
                    return f"{hour:02d}:{minute:02d}"
                
                elif len(match.groups()) == 2:  # Just hour:minute
                    hour, minute = match.groups()
                    return f"{int(hour):02d}:{int(minute):02d}"
                
                elif len(match.groups()) == 2 and 'AM' in time_str.upper() or 'PM' in time_str.upper():
                    # Handle cases like "3 PM"
                    hour = int(match.groups()[0])
                    ampm = match.groups()[1]
                    
                    if ampm == 'PM' and hour != 12:
                        hour += 12
                    elif ampm == 'AM' and hour == 12:
                        hour = 0
                        
                    return f"{hour:02d}:00"
        
        # Handle single numbers (restaurant context)
        if re.match(r'^\d{1,2}$', time_str):
            hour = int(time_str)
            # For restaurant hours, assume PM for common dinner hours, AM for late night/early morning
            if 3 <= hour <= 11:
                # Convert to PM (add 12 for 24-hour format)
                return f"{hour + 12:02d}:00"
            elif hour == 12:
                return "12:00"  # 12 = 12 PM (noon) 
            elif hour == 1 or hour == 2:
                return f"{hour:02d}:00"  # 1-2 AM (late night)
            else:
                return None  # Ambiguous times like 0
        
        return None
    
    def _normalize_times(self):
        """Auto-populate 24-hour time fields if they're missing"""
        if self.start_time and not self.start_time_24h:
            self.start_time_24h = self._parse_time_to_24h(self.start_time)
        
        if self.end_time and not self.end_time_24h:
            self.end_time_24h = self._parse_time_to_24h(self.end_time)


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
    last_failure_reason: Optional[str] = None  # "robots_txt", "timeout", "404", "no_content", etc.
    
    # Custom parsing configurations
    custom_selectors: Dict[str, str] = field(default_factory=dict)  # CSS selectors for specific content
    time_pattern_regex: Optional[str] = None  # Regex for extracting time ranges
    day_pattern_regex: Optional[str] = None   # Regex for extracting days of week
    price_pattern_regex: Optional[str] = None # Regex for extracting prices
    exclude_patterns: List[str] = field(default_factory=list)  # Text patterns to exclude
    content_containers: List[str] = field(default_factory=list)  # Specific containers to focus on


@dataclass
class Address:
    """
    Structured address data with validation and geocoding support
    """
    # Core address components
    street_number: Optional[str] = None    # "1550"
    street_name: Optional[str] = None      # "Market St"
    unit: Optional[str] = None             # "Suite 100", "#2A", "Apt 5B"
    city: str = "Denver"                   # Default to Denver
    state: str = "CO"                      # Default to Colorado
    zip_code: Optional[str] = None         # "80202"
    
    # Additional metadata
    formatted_address: Optional[str] = None  # Full formatted string: "1550 Market St, Denver, CO 80202"
    google_maps_url: Optional[str] = None    # Auto-generated maps link
    confidence_score: float = 1.0            # 0.0-1.0 confidence in address accuracy
    
    def __post_init__(self):
        """Auto-generate formatted address and maps URL after initialization"""
        if not self.formatted_address and self.street_number and self.street_name:
            self._generate_formatted_address()
        if not self.google_maps_url and self.formatted_address:
            self._generate_maps_url()
    
    def _generate_formatted_address(self):
        """Generate a formatted address string from components"""
        parts = []
        
        # Street address
        if self.street_number and self.street_name:
            street_addr = f"{self.street_number} {self.street_name}"
            if self.unit:
                street_addr += f" {self.unit}"
            parts.append(street_addr)
        
        # City, State ZIP
        location_parts = []
        if self.city:
            location_parts.append(self.city)
        if self.state:
            location_parts.append(self.state)
        if self.zip_code:
            location_parts.append(self.zip_code)
        
        if location_parts:
            if len(location_parts) >= 2:
                # "Denver, CO 80202"
                parts.append(f"{location_parts[0]}, {' '.join(location_parts[1:])}")
            else:
                parts.append(' '.join(location_parts))
        
        self.formatted_address = ', '.join(parts) if parts else None
    
    def _generate_maps_url(self):
        """Generate Google Maps URL from formatted address"""
        if self.formatted_address:
            import urllib.parse
            encoded_addr = urllib.parse.quote_plus(self.formatted_address)
            self.google_maps_url = f"https://maps.google.com/?q={encoded_addr}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'street_number': self.street_number,
            'street_name': self.street_name,
            'unit': self.unit,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'formatted_address': self.formatted_address,
            'google_maps_url': self.google_maps_url,
            'confidence_score': self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Address':
        """Create Address from dictionary"""
        return cls(
            street_number=data.get('street_number'),
            street_name=data.get('street_name'),
            unit=data.get('unit'),
            city=data.get('city', 'Denver'),
            state=data.get('state', 'CO'),
            zip_code=data.get('zip_code'),
            formatted_address=data.get('formatted_address'),
            google_maps_url=data.get('google_maps_url'),
            confidence_score=data.get('confidence_score', 1.0)
        )
    
    @classmethod
    def from_string(cls, address_string: str, confidence_score: float = 0.7) -> 'Address':
        """
        Parse address string into structured components
        Used for backward compatibility with existing address strings
        """
        if not address_string:
            return cls(confidence_score=0.0)
        
        # Store the original as formatted_address for now
        # More sophisticated parsing will be added in address utilities
        address = cls(
            formatted_address=address_string.strip(),
            confidence_score=confidence_score
        )
        
        # Try basic parsing for street number and name
        import re
        
        # Pattern: "1550 Market St" or "123 Main Street #100"
        street_match = re.match(r'^(\d+)\s+([^,#]+?)(?:\s*(#\w+|Suite\s+\w+|Apt\s+\w+))?\s*(?:,|$)', address_string.strip())
        if street_match:
            address.street_number = street_match.group(1)
            address.street_name = street_match.group(2).strip()
            if street_match.group(3):
                address.unit = street_match.group(3).strip()
        
        # Generate maps URL
        address._generate_maps_url()
        
        return address
    
    def is_complete(self) -> bool:
        """Check if address has minimum required components"""
        return bool(self.street_number and self.street_name)


@dataclass 
class ContactInfo:
    """Enhanced contact information for restaurants"""
    # Phone numbers
    primary_phone: Optional[str] = None
    reservation_phone: Optional[str] = None
    
    # Email addresses
    general_email: Optional[str] = None
    reservations_email: Optional[str] = None
    events_email: Optional[str] = None
    
    # Social media handles (without @ prefix for flexibility)
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    tiktok: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'primary_phone': self.primary_phone,
            'reservation_phone': self.reservation_phone,
            'general_email': self.general_email,
            'reservations_email': self.reservations_email,
            'events_email': self.events_email,
            'instagram': self.instagram,
            'facebook': self.facebook,
            'twitter': self.twitter,
            'tiktok': self.tiktok
        }


@dataclass
class DiningInfo:
    """Restaurant dining experience information"""
    price_range: Optional[PriceRange] = None
    dress_code: Optional[str] = None  # casual, business_casual, upscale, formal
    atmosphere: List[str] = field(default_factory=list)  # romantic, family_friendly, etc.
    dining_style: Optional[str] = None  # full_service, fast_casual, bar, food_truck
    
    # Capacity information
    total_seats: Optional[int] = None
    bar_seats: Optional[int] = None
    outdoor_seats: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'price_range': self.price_range.value if hasattr(self.price_range, 'value') else self.price_range,
            'dress_code': self.dress_code,
            'atmosphere': self.atmosphere,
            'dining_style': self.dining_style,
            'total_seats': self.total_seats,
            'bar_seats': self.bar_seats,
            'outdoor_seats': self.outdoor_seats
        }


@dataclass
class ServiceInfo:
    """Restaurant service and booking options"""
    # Reservations
    accepts_reservations: bool = False
    opentable_url: Optional[str] = None
    resy_url: Optional[str] = None
    direct_reservation_url: Optional[str] = None
    
    # Ordering and delivery
    offers_delivery: bool = False
    offers_takeout: bool = True
    offers_curbside: bool = False
    doordash_url: Optional[str] = None
    ubereats_url: Optional[str] = None
    grubhub_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'accepts_reservations': self.accepts_reservations,
            'opentable_url': self.opentable_url,
            'resy_url': self.resy_url,
            'direct_reservation_url': self.direct_reservation_url,
            'offers_delivery': self.offers_delivery,
            'offers_takeout': self.offers_takeout,
            'offers_curbside': self.offers_curbside,
            'doordash_url': self.doordash_url,
            'ubereats_url': self.ubereats_url,
            'grubhub_url': self.grubhub_url
        }


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
    address: Optional[Address] = None  # Structured address object
    cuisine: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None  # Legacy field - use contact_info.primary_phone for new data
    
    # Enhanced business information
    business_status: BusinessStatus = BusinessStatus.UNKNOWN
    contact_info: ContactInfo = field(default_factory=ContactInfo)
    dining_info: DiningInfo = field(default_factory=DiningInfo)
    service_info: ServiceInfo = field(default_factory=ServiceInfo)
    
    # Timezone and operating hours
    timezone: str = "America/Denver"
    operating_hours: Dict[str, Dict[str, str]] = field(default_factory=dict)  # {"monday": {"open": "11:00", "close": "22:00"}}
    
    # Static deals info (fallback) - unified format
    static_deals: List[Dict[str, Any]] = field(default_factory=list)
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
            'address': self.address.to_dict() if self.address else None,
            'cuisine': self.cuisine,
            'website': self.website,
            'phone': self.phone,
            'business_status': self.business_status.value,
            'contact_info': self.contact_info.to_dict(),
            'dining_info': self.dining_info.to_dict(),
            'service_info': self.service_info.to_dict(),
            'timezone': self.timezone,
            'operating_hours': self.operating_hours,
            'static_deals': self.static_deals,
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
                'consecutive_failures': self.scraping_config.consecutive_failures,
                'last_failure_reason': self.scraping_config.last_failure_reason,
                'custom_selectors': self.scraping_config.custom_selectors,
                'time_pattern_regex': self.scraping_config.time_pattern_regex,
                'day_pattern_regex': self.scraping_config.day_pattern_regex,
                'price_pattern_regex': self.scraping_config.price_pattern_regex,
                'exclude_patterns': self.scraping_config.exclude_patterns,
                'content_containers': self.scraping_config.content_containers
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
            consecutive_failures=scraping_config_data.get('consecutive_failures', 0),
            last_failure_reason=scraping_config_data.get('last_failure_reason'),
            custom_selectors=scraping_config_data.get('custom_selectors', {}),
            time_pattern_regex=scraping_config_data.get('time_pattern_regex'),
            day_pattern_regex=scraping_config_data.get('day_pattern_regex'),
            price_pattern_regex=scraping_config_data.get('price_pattern_regex'),
            exclude_patterns=scraping_config_data.get('exclude_patterns', []),
            content_containers=scraping_config_data.get('content_containers', [])
        )
        
        # Handle address data with backward compatibility
        address_data = data.get('address')
        address = None
        if address_data:
            if isinstance(address_data, dict):
                # New structured format
                address = Address.from_dict(address_data)
            elif isinstance(address_data, str):
                # Legacy string format - convert to structured
                address = Address.from_string(address_data, confidence_score=0.5)
        
        # Handle new contact info structure
        contact_info_data = data.get('contact_info', {})
        contact_info = ContactInfo(
            primary_phone=contact_info_data.get('primary_phone'),
            reservation_phone=contact_info_data.get('reservation_phone'),
            general_email=contact_info_data.get('general_email'),
            reservations_email=contact_info_data.get('reservations_email'),
            events_email=contact_info_data.get('events_email'),
            instagram=contact_info_data.get('instagram'),
            facebook=contact_info_data.get('facebook'),
            twitter=contact_info_data.get('twitter'),
            tiktok=contact_info_data.get('tiktok')
        )
        
        # Handle dining info structure
        dining_info_data = data.get('dining_info', {})
        dining_info = DiningInfo(
            price_range=PriceRange(dining_info_data['price_range']) if dining_info_data.get('price_range') else None,
            dress_code=dining_info_data.get('dress_code'),
            atmosphere=dining_info_data.get('atmosphere', []),
            dining_style=dining_info_data.get('dining_style'),
            total_seats=dining_info_data.get('total_seats'),
            bar_seats=dining_info_data.get('bar_seats'),
            outdoor_seats=dining_info_data.get('outdoor_seats')
        )
        
        # Handle service info structure  
        service_info_data = data.get('service_info', {})
        service_info = ServiceInfo(
            accepts_reservations=service_info_data.get('accepts_reservations', False),
            opentable_url=service_info_data.get('opentable_url'),
            resy_url=service_info_data.get('resy_url'),
            direct_reservation_url=service_info_data.get('direct_reservation_url'),
            offers_delivery=service_info_data.get('offers_delivery', False),
            offers_takeout=service_info_data.get('offers_takeout', True),
            offers_curbside=service_info_data.get('offers_curbside', False),
            doordash_url=service_info_data.get('doordash_url'),
            ubereats_url=service_info_data.get('ubereats_url'),
            grubhub_url=service_info_data.get('grubhub_url')
        )
        
        return cls(
            name=data['name'],
            slug=data['slug'],
            district=data['district'],
            neighborhood=data.get('neighborhood'),
            address=address,
            cuisine=data.get('cuisine'),
            website=data.get('website'),
            phone=data.get('phone'),
            business_status=BusinessStatus(data.get('business_status', 'unknown')),
            contact_info=contact_info,
            dining_info=dining_info,
            service_info=service_info,
            timezone=data.get('timezone', 'America/Denver'),
            operating_hours=data.get('operating_hours', {}),
            static_deals=data.get('static_deals', []),
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
        
        # Priority 3: Fall back to static deals (new format)
        if self.static_deals:
            static_deals = []
            for deal_data in self.static_deals:
                try:
                    # Convert dict back to Deal object
                    deal = Deal(
                        title=deal_data.get('title', 'Happy Hour'),
                        description=deal_data.get('description', ''),
                        deal_type=DealType(deal_data.get('deal_type', 'happy_hour')),
                        days_of_week=[DayOfWeek(day) for day in deal_data.get('days_of_week', [])],
                        start_time=deal_data.get('start_time'),
                        end_time=deal_data.get('end_time'),
                        prices=deal_data.get('prices', []),
                        is_all_day=deal_data.get('is_all_day', False),
                        special_notes=deal_data.get('special_notes', []),
                        confidence_score=deal_data.get('confidence_score', 0.3),
                        source_url=deal_data.get('source_url')
                    )
                    static_deals.append(deal)
                except (ValueError, KeyError) as e:
                    # Handle malformed static deal data
                    continue
            return static_deals
        
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
    
    def is_open_now(self, user_timezone: str = "America/Denver") -> bool:
        """Check if restaurant is currently open based on operating hours"""
        if not self.operating_hours:
            return True  # Assume open if no hours specified
        
        # Get current time in restaurant's timezone
        restaurant_tz = pendulum.now(self.timezone)
        current_day = restaurant_tz.format('dddd').lower()  # 'monday', 'tuesday', etc.
        current_time = restaurant_tz.format('HH:mm')
        
        # Check if we have hours for today
        today_hours = self.operating_hours.get(current_day)
        if not today_hours:
            return False  # Closed if no hours specified for today
        
        # Handle special cases
        if today_hours.get('closed'):
            return False
            
        open_time = today_hours.get('open')
        close_time = today_hours.get('close')
        
        if not open_time or not close_time:
            return True  # Assume open if hours are incomplete
        
        # Compare times
        return open_time <= current_time <= close_time
    
    def time_until_opens(self, user_timezone: str = "America/Denver") -> Optional[str]:
        """Get human-readable time until restaurant opens"""
        if self.is_open_now(user_timezone):
            return None  # Already open
        
        if not self.operating_hours:
            return None  # No hours data
        
        restaurant_tz = pendulum.now(self.timezone)
        current_day = restaurant_tz.format('dddd').lower()
        
        # Look for next opening time
        days_to_check = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        current_day_index = days_to_check.index(current_day)
        
        for i in range(7):  # Check next 7 days
            check_day_index = (current_day_index + i) % 7
            check_day = days_to_check[check_day_index]
            day_hours = self.operating_hours.get(check_day)
            
            if day_hours and not day_hours.get('closed') and day_hours.get('open'):
                open_time = day_hours['open']
                
                # Calculate target datetime
                if i == 0:  # Today
                    target_time = restaurant_tz.replace(
                        hour=int(open_time.split(':')[0]),
                        minute=int(open_time.split(':')[1]),
                        second=0, microsecond=0
                    )
                    if target_time > restaurant_tz:
                        diff = target_time - restaurant_tz
                        hours = int(diff.total_seconds() // 3600)
                        minutes = int((diff.total_seconds() % 3600) // 60)
                        return f"Opens in {hours}h {minutes}m"
                else:  # Future day
                    target_date = restaurant_tz.add(days=i)
                    target_time = target_date.replace(
                        hour=int(open_time.split(':')[0]),
                        minute=int(open_time.split(':')[1]),
                        second=0, microsecond=0
                    )
                    diff = target_time - restaurant_tz
                    days = diff.days
                    if days == 1:
                        return f"Opens tomorrow at {open_time}"
                    else:
                        return f"Opens {check_day.title()} at {open_time}"
        
        return None  # No opening found in next 7 days


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
        for price in deal.prices:
            if price and not cls._is_valid_price(price):
                issues.append(f"Invalid price format: {price}")
        
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
        prices=["$5 Cocktails"]
    )
    
    print("Deal validation:", DealValidator.validate_deal(deal))
    print("Deal JSON:", json.dumps(deal.to_dict(), indent=2, default=str))