"""
Scrapy Items for Sips and Steals

Data models for deals and restaurants with rich extraction context
for semantic analysis and deduplication.
"""

import scrapy
from itemloaders.processors import TakeFirst, Compose, MapCompose
from datetime import datetime


class DealItem(scrapy.Item):
    """
    Happy hour deal with rich extraction context for semantic analysis.
    
    Based on our proven data-hungry approach that captures everything
    for post-processing analysis and intelligent deduplication.
    """
    
    # Core deal information
    title = scrapy.Field()
    description = scrapy.Field()
    deal_type = scrapy.Field(default='happy_hour')
    
    # Time information
    start_time = scrapy.Field()
    end_time = scrapy.Field()
    start_time_24h = scrapy.Field()
    end_time_24h = scrapy.Field()
    timezone = scrapy.Field(default='America/Denver')
    is_all_day = scrapy.Field(default=False)
    
    # Day information
    days_of_week = scrapy.Field(default=[])
    
    # Pricing and notes
    prices = scrapy.Field(default=[])
    special_notes = scrapy.Field(default=[])
    
    # Metadata
    scraped_at = scrapy.Field()
    source_url = scrapy.Field()
    confidence_score = scrapy.Field(default=1.0)
    
    # Data-hungry extraction context (our proven approach)
    extraction_method = scrapy.Field()
    source_text = scrapy.Field()  # Raw text where deal was found
    html_context = scrapy.Field()  # HTML section containing deal
    extraction_patterns = scrapy.Field(default=[])  # Which patterns matched
    raw_time_matches = scrapy.Field(default=[])  # Original regex matches
    raw_day_matches = scrapy.Field(default=[])  # Original day patterns
    
    # Restaurant association
    restaurant_slug = scrapy.Field()
    restaurant_name = scrapy.Field()


class RestaurantPageItem(scrapy.Item):
    """
    Restaurant page discovered during crawling.
    
    Used by discovery spider to track potential happy hour pages
    and content quality for further processing.
    """
    
    # Page identification
    url = scrapy.Field()
    title = scrapy.Field()
    
    # Restaurant association
    restaurant_slug = scrapy.Field()
    restaurant_name = scrapy.Field()
    
    # Content analysis
    happy_hour_likelihood = scrapy.Field()  # 0.0-1.0 score
    content_keywords = scrapy.Field(default=[])
    
    # Link relationships
    found_via_url = scrapy.Field()  # Parent page that linked here
    link_text = scrapy.Field()  # Anchor text of link
    
    # Technical metadata
    discovered_at = scrapy.Field()
    content_type = scrapy.Field()
    status_code = scrapy.Field()
    
    # Content preview for analysis
    content_preview = scrapy.Field()  # First 500 chars
    
    
class DiscoveredLinkItem(scrapy.Item):
    """
    Link discovered during crawling that might lead to happy hour content.
    
    Used for building a map of restaurant website structure
    and prioritizing crawling targets.
    """
    
    # Link details
    url = scrapy.Field()
    anchor_text = scrapy.Field()
    
    # Source information  
    source_url = scrapy.Field()
    restaurant_slug = scrapy.Field()
    
    # Analysis scores
    happy_hour_relevance_score = scrapy.Field()  # Based on anchor text, URL patterns
    
    # Metadata
    discovered_at = scrapy.Field()
    processed = scrapy.Field(default=False)


class RestaurantProfileItem(scrapy.Item):
    """
    Comprehensive restaurant profile data extracted from restaurant websites.
    
    Captures all data needed to populate our complete restaurant schema:
    contact info, dining info, service info, business hours, etc.
    """
    
    # Restaurant identification
    restaurant_slug = scrapy.Field()
    restaurant_name = scrapy.Field()
    source_url = scrapy.Field()
    
    # Business Information
    business_status = scrapy.Field()  # operational, temporarily_closed, permanently_closed
    operating_hours = scrapy.Field(default={})  # {"monday": {"open": "11:00", "close": "22:00"}}
    
    # Contact Information
    primary_phone = scrapy.Field()
    reservation_phone = scrapy.Field()
    general_email = scrapy.Field()
    reservations_email = scrapy.Field()
    events_email = scrapy.Field()
    
    # Social Media (without @ prefix)
    instagram = scrapy.Field()
    facebook = scrapy.Field()
    twitter = scrapy.Field()
    tiktok = scrapy.Field()
    
    # Dining Information
    price_range = scrapy.Field()  # $, $$, $$$, $$$$
    dress_code = scrapy.Field()  # casual, business_casual, upscale, formal
    atmosphere = scrapy.Field(default=[])  # romantic, family_friendly, lively, etc.
    dining_style = scrapy.Field()  # full_service, fast_casual, bar, food_truck
    total_seats = scrapy.Field()
    bar_seats = scrapy.Field()
    outdoor_seats = scrapy.Field()
    
    # Service Information
    accepts_reservations = scrapy.Field(default=False)
    opentable_url = scrapy.Field()
    resy_url = scrapy.Field()
    direct_reservation_url = scrapy.Field()
    offers_delivery = scrapy.Field(default=False)
    offers_takeout = scrapy.Field(default=True)
    offers_curbside = scrapy.Field(default=False)
    doordash_url = scrapy.Field()
    ubereats_url = scrapy.Field()
    grubhub_url = scrapy.Field()
    
    # Address Enhancement (to validate/enhance existing data)
    street_address = scrapy.Field()
    city = scrapy.Field()
    state = scrapy.Field()
    zip_code = scrapy.Field()
    
    # Extraction Context (data-hungry approach)
    extraction_method = scrapy.Field()
    source_text_snippets = scrapy.Field(default=[])  # Text where data was found
    html_context = scrapy.Field()
    extraction_patterns = scrapy.Field(default=[])
    confidence_score = scrapy.Field(default=0.7)
    
    # Metadata
    scraped_at = scrapy.Field()
    content_language = scrapy.Field()
    
    # Quality Metrics
    completeness_score = scrapy.Field()  # How much of the profile was filled
    data_source_quality = scrapy.Field()  # Quality of source content


class MenuPricingItem(scrapy.Item):
    """
    Menu pricing data extracted from restaurant websites and PDFs.
    
    Contains structured pricing information for menu items with 
    categorization and price range analysis.
    """
    
    # Page identification
    url = scrapy.Field()
    restaurant_slug = scrapy.Field()
    restaurant_name = scrapy.Field()
    
    # Menu classification
    menu_type = scrapy.Field()  # dinner, lunch, happy_hour, wine, etc.
    
    # Pricing data
    price_items = scrapy.Field()  # List of extracted price items
    price_range_detected = scrapy.Field()  # $, $$, $$$, $$$$
    average_price = scrapy.Field()
    min_price = scrapy.Field()
    max_price = scrapy.Field()
    
    # Technical metadata
    content_type = scrapy.Field()  # text/html or application/pdf
    scraped_at = scrapy.Field()
    confidence_score = scrapy.Field()
    
    # Content context
    raw_content_preview = scrapy.Field()  # First 1000 chars for analysis


class HappyHourDealsItem(scrapy.Item):
    """
    Happy hour deals data extracted from restaurant websites and PDFs.
    
    Focuses on structured happy hour deal information including timeframes,
    days, prices, and deal specifics for value-conscious dining decisions.
    """
    
    # Page identification
    url = scrapy.Field()
    restaurant_slug = scrapy.Field()
    restaurant_name = scrapy.Field()
    
    # Happy hour deals data
    happy_hour_deals = scrapy.Field()  # List of structured deal objects
    timeframes_found = scrapy.Field()  # List of all timeframes discovered
    days_found = scrapy.Field()  # List of all days discovered
    location_restrictions = scrapy.Field()  # Location-specific restrictions
    
    # Technical metadata
    content_type = scrapy.Field()  # text/html or application/pdf
    scraped_at = scrapy.Field()
    confidence_score = scrapy.Field()
    
    # Content context
    raw_content_preview = scrapy.Field()  # First 1000 chars for analysis