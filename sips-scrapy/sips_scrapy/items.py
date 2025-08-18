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