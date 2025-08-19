"""
Enhanced Deals Data Models

Defines the data structures for the three-layer architecture:
- Raw extraction data (for debugging/refinement)
- Refined clean data (validated and normalized)
- Presentation data (user-facing)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, time


class DealType(Enum):
    """Expanded deal types beyond just happy hours"""
    HAPPY_HOUR = "happy_hour"
    BRUNCH = "brunch"
    BOTTOMLESS = "bottomless"          # Bottomless mimosas/drinks
    EARLY_BIRD = "early_bird"          # Pre-dinner discounts
    LATE_NIGHT = "late_night"          # Post-dinner deals
    DAILY_SPECIAL = "daily_special"    # Taco Tuesday, Wine Wednesday
    PRIX_FIXE = "prix_fixe"           # Fixed price menus
    TASTING_MENU = "tasting_menu"     # Chef's tasting experiences
    GAME_DAY = "game_day"             # Sports event specials
    INDUSTRY_NIGHT = "industry"       # Service industry discounts
    TRIVIA_NIGHT = "trivia"           # Trivia with specials
    REVERSE_HAPPY = "reverse_happy"   # Late evening deals
    WEEKEND_SPECIAL = "weekend"       # Weekend-only deals
    SEASONAL = "seasonal"             # Holiday/seasonal menus
    RESTAURANT_WEEK = "restaurant_week"
    LIVE_MUSIC = "live_music"         # Music events with specials
    KARAOKE = "karaoke"              # Karaoke night deals


class DataQuality(Enum):
    """Data quality indicators for refinement pipeline"""
    VERIFIED = "verified"      # Human reviewed and confirmed
    HIGH = "high"              # High confidence extraction
    MEDIUM = "medium"          # Partial extraction, some issues
    LOW = "low"               # Needs manual review
    INFERRED = "inferred"      # Guessed from patterns
    FAILED = "failed"          # Extraction failed


class MenuFormat(Enum):
    """Source format for menu data"""
    HTML = "html"
    PDF = "pdf"
    JSON_LD = "json_ld"
    IMAGE = "image"
    MANUAL = "manual"


class ItemCategory(Enum):
    """Categories for menu items"""
    COCKTAILS = "cocktails"
    WINE = "wine"
    BEER = "beer"
    SPIRITS = "spirits"
    NON_ALCOHOLIC = "non_alcoholic"
    APPETIZERS = "appetizers"
    ENTREES = "entrees"
    DESSERTS = "desserts"
    SHAREABLES = "shareables"
    OYSTERS = "oysters"
    SUSHI = "sushi"
    PIZZA = "pizza"
    BURGERS = "burgers"
    TACOS = "tacos"


# ===== RAW EXTRACTION DATA MODELS =====

@dataclass
class RawExtractionItem:
    """Raw scraped data with full extraction context"""
    extraction_id: str
    extracted_at: datetime
    restaurant_slug: str
    source_url: str
    extraction_method: str
    
    # Raw extraction artifacts
    source_text: str                    # Raw text where deal was found
    html_context: Optional[str] = None  # HTML section containing deal
    extraction_patterns: List[str] = field(default_factory=list)
    raw_matches: Dict[str, Any] = field(default_factory=dict)
    
    # Extracted content (unprocessed)
    raw_title: Optional[str] = None
    raw_description: Optional[str] = None
    raw_times: List[str] = field(default_factory=list)
    raw_days: List[str] = field(default_factory=list)
    raw_prices: List[str] = field(default_factory=list)
    
    # Metadata
    confidence_score: float = 0.0
    processor_version: str = "1.0"
    error_messages: List[str] = field(default_factory=list)


@dataclass
class RawMenuExtraction:
    """Raw menu data from PDF or HTML"""
    extraction_id: str
    restaurant_slug: str
    menu_url: str
    menu_format: MenuFormat
    extracted_at: datetime
    
    # Raw content
    raw_text: str
    raw_html: Optional[str] = None
    pdf_metadata: Optional[Dict] = None
    
    # File information
    file_size: Optional[int] = None
    cached_path: Optional[str] = None
    last_modified: Optional[datetime] = None
    
    # Processing metadata
    extraction_success: bool = False
    error_messages: List[str] = field(default_factory=list)


# ===== REFINED CLEAN DATA MODELS =====

@dataclass
class DealSchedule:
    """Clean, validated deal schedule information"""
    id: str                            # Unique identifier
    restaurant_slug: str
    deal_type: DealType
    name: str                          # User-friendly name
    
    # Schedule information
    days: List[str]                    # Normalized day names
    start_time: Optional[str] = None   # 24-hour format "HH:MM"
    end_time: Optional[str] = None     # 24-hour format "HH:MM"
    timezone: str = "America/Denver"
    is_all_day: bool = False
    
    # Recurrence and conditions
    recurrence: str = "weekly"         # daily, weekly, monthly, special_event
    special_conditions: List[str] = field(default_factory=list)
    date_range: Optional[Dict] = None  # start_date, end_date for seasonal deals
    
    # Status and metadata
    active_status: str = "active"      # active, inactive, seasonal
    last_verified: Optional[str] = None
    data_quality: DataQuality = DataQuality.MEDIUM
    source_urls: List[str] = field(default_factory=list)


@dataclass
class MenuItem:
    """Individual menu item with pricing"""
    name: str
    category: ItemCategory
    deal_price: float
    
    # Optional pricing info
    regular_price: Optional[float] = None
    savings: Optional[float] = None
    discount_percent: Optional[int] = None
    
    # Item details
    description: Optional[str] = None
    size: Optional[str] = None          # "12oz", "small", "large"
    special_notes: List[str] = field(default_factory=list)
    
    # Metadata
    confidence_score: float = 1.0
    last_verified: Optional[str] = None


@dataclass
class DealMenu:
    """Clean menu associated with a deal schedule"""
    schedule_id: str                   # Links to DealSchedule
    restaurant_slug: str
    menu_type: str                     # "drinks", "food", "combo"
    
    # Menu items
    items: List[MenuItem] = field(default_factory=list)
    
    # Menu metadata
    source: str = "website"            # website, pdf, manual
    menu_url: Optional[str] = None
    last_updated: Optional[str] = None
    data_quality: DataQuality = DataQuality.MEDIUM
    
    # Summary information
    price_range: Optional[str] = None  # "$5-15"
    item_count: int = 0
    categories: List[str] = field(default_factory=list)


@dataclass
class RestaurantMenuLinks:
    """All menu links and documents for a restaurant"""
    restaurant_slug: str
    
    # Categorized menu links
    menu_links: Dict[str, Dict] = field(default_factory=dict)
    discovered_pdfs: List[str] = field(default_factory=list)
    
    # Discovery metadata
    last_discovery: Optional[str] = None
    total_links: int = 0
    pdf_count: int = 0


# ===== PRESENTATION DATA MODELS =====

@dataclass
class PublicDeal:
    """User-facing deal information"""
    id: str
    restaurant_slug: str
    restaurant_name: str
    
    # Deal information
    deal_name: str
    deal_type: str                     # User-friendly type name
    when: str                          # "Mon-Fri 3:00-6:00 PM"
    
    # Highlights and summary
    highlights: List[str] = field(default_factory=list)  # Top 3-4 deal items
    savings_range: Optional[str] = None                  # "$5-15 savings"
    description: Optional[str] = None
    
    # Real-time status
    active_now: bool = False
    starts_in_minutes: Optional[int] = None
    ends_in_minutes: Optional[int] = None
    
    # Quality indicators
    confidence: str = "medium"         # high, medium, low
    last_verified: Optional[str] = None
    
    # Links and actions
    menu_url: Optional[str] = None
    reservation_url: Optional[str] = None


@dataclass
class DealSummary:
    """Aggregated statistics and highlights"""
    total_active_deals: int
    total_restaurants: int
    
    # Deal type breakdown
    deal_types_count: Dict[str, int] = field(default_factory=dict)
    
    # Highlights
    top_savings: List[Dict] = field(default_factory=list)
    starting_soon: List[Dict] = field(default_factory=list)
    active_now: List[Dict] = field(default_factory=list)
    
    # Data quality
    data_quality_stats: Dict[str, int] = field(default_factory=dict)
    last_updated: str = ""


# ===== UTILITY FUNCTIONS =====

def normalize_day_name(day: str) -> str:
    """Normalize day names to lowercase full names"""
    day_mapping = {
        'mon': 'monday', 'tue': 'tuesday', 'wed': 'wednesday',
        'thu': 'thursday', 'fri': 'friday', 'sat': 'saturday', 'sun': 'sunday',
        'monday': 'monday', 'tuesday': 'tuesday', 'wednesday': 'wednesday',
        'thursday': 'thursday', 'friday': 'friday', 'saturday': 'saturday', 'sunday': 'sunday'
    }
    return day_mapping.get(day.lower(), day.lower())


def normalize_time_24h(time_str: str) -> Optional[str]:
    """Convert various time formats to 24-hour HH:MM format"""
    if not time_str:
        return None
    
    # Handle common formats
    time_str = time_str.lower().strip()
    
    # "3pm" or "3 pm" -> "15:00"
    if 'pm' in time_str:
        hour = int(time_str.replace('pm', '').strip())
        if hour != 12:
            hour += 12
        return f"{hour:02d}:00"
    
    # "3am" or "3 am" -> "03:00"
    if 'am' in time_str:
        hour = int(time_str.replace('am', '').strip())
        if hour == 12:
            hour = 0
        return f"{hour:02d}:00"
    
    # "15:00" already in correct format
    if ':' in time_str and len(time_str) == 5:
        return time_str
    
    return None


def classify_deal_type(title: str, description: str, days: List[str], times: List[str]) -> DealType:
    """Intelligently classify deal type based on content"""
    content = f"{title} {description}".lower()
    
    # Specific deal type keywords
    if any(word in content for word in ['bottomless', 'unlimited']):
        return DealType.BOTTOMLESS
    if any(word in content for word in ['brunch', 'breakfast', 'mimosa']):
        return DealType.BRUNCH
    if any(word in content for word in ['prix fixe', 'tasting menu', 'chef']):
        return DealType.PRIX_FIXE
    if any(word in content for word in ['game day', 'football', 'sports']):
        return DealType.GAME_DAY
    if any(word in content for word in ['trivia', 'quiz']):
        return DealType.TRIVIA_NIGHT
    if any(word in content for word in ['industry', 'service']):
        return DealType.INDUSTRY_NIGHT
    if any(word in content for word in ['late night', 'midnight']):
        return DealType.LATE_NIGHT
    if any(word in content for word in ['early bird', 'sunset']):
        return DealType.EARLY_BIRD
    
    # Day-specific specials
    if len(days) == 1:
        day = days[0].lower()
        if 'tuesday' in day and 'taco' in content:
            return DealType.DAILY_SPECIAL
        if 'wednesday' in day and 'wine' in content:
            return DealType.DAILY_SPECIAL
    
    # Weekend specials
    if all(day in ['saturday', 'sunday'] for day in days):
        return DealType.WEEKEND_SPECIAL
    
    # Default to happy hour
    return DealType.HAPPY_HOUR