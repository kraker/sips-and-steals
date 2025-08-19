# Data Schema Documentation

## Three-Layer Data Architecture

The sips-and-steals project implements a sophisticated three-layer data architecture that separates concerns between raw extraction, refined processing, and user presentation. This architecture enables robust data quality control, debugging capabilities, and clean user experiences.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RAW LAYER     │    │  REFINED LAYER  │    │  PUBLIC LAYER   │
│                 │    │                 │    │                 │
│ • Debugging     │───▶│ • Clean Data    │───▶│ • User-Facing   │
│ • Refinement    │    │ • Validated     │    │ • Presentation  │
│ • All Artifacts │    │ • Normalized    │    │ • Real-time     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Layer 1: Raw Extraction Data

**Purpose**: Preserve all extraction artifacts for debugging and refinement

**Location**: `data/raw/`

### Raw Extraction Items (`extracted_deals_raw.json`)

```json
{
  "migrated_at": "2025-08-19T...",
  "migration_stats": { ... },
  "raw_extractions": [
    {
      "extraction_id": "uuid-string",
      "extracted_at": "2025-08-19T...",
      "restaurant_slug": "restaurant-name",
      "source_url": "https://restaurant.com/happy-hour",
      "extraction_method": "scrapy_html_parser",
      
      // Raw extraction artifacts (debugging)
      "source_text": "Raw text where deal was found...",
      "html_context": "<div class='happy-hour'>...</div>",
      "extraction_patterns": ["time_pattern_1", "day_pattern_2"],
      "raw_matches": {
        "time_matches": ["3pm", "6 PM"],
        "day_matches": ["Mon-Fri", "weekdays"]
      },
      
      // Extracted content (unprocessed)
      "raw_title": "Happy Hour Special",
      "raw_description": "Great drinks and food...",
      "raw_times": ["3pm", "6pm"],
      "raw_days": ["monday", "tuesday", "wednesday"],
      "raw_prices": ["$5 cocktails", "$3 beers"],
      
      // Metadata
      "confidence_score": 0.85,
      "processor_version": "1.0",
      "data_quality": "medium"
    }
  ]
}
```

### Raw Menu Extractions (PDF Processing)

```json
{
  "extraction_id": "pdf_restaurant_20250819",
  "restaurant_slug": "restaurant-name",
  "menu_url": "https://restaurant.com/menu.pdf",
  "menu_format": "pdf",
  "extracted_at": "2025-08-19T...",
  
  // Raw content
  "raw_text": "Full text extracted from PDF...",
  "pdf_metadata": {
    "content_length": 1024000,
    "last_modified": "Wed, 18 Aug 2025 10:00:00 GMT"
  },
  
  // Processing metadata
  "extraction_success": true,
  "processor_version": "1.0"
}
```

## Layer 2: Refined Clean Data

**Purpose**: Clean, validated, and normalized data ready for presentation

**Location**: `data/refined/`

### Deal Schedules (`deal_schedules.json`)

Defines **when** deals happen with normalized timing and recurrence patterns.

```json
{
  "refined_at": "2025-08-19T...",
  "total_schedules": 60,
  "schedules": [
    {
      "id": "restaurant-name-happy_hour-monday-tuesday-wednesday",
      "restaurant_slug": "restaurant-name",
      "deal_type": "happy_hour",
      "name": "Weekday Happy Hour",
      
      // Schedule information (normalized)
      "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
      "start_time": "15:00",  // 24-hour format
      "end_time": "18:00",    // 24-hour format
      "timezone": "America/Denver",
      "is_all_day": false,
      
      // Recurrence and conditions
      "recurrence": "weekly",
      "special_conditions": [],
      "date_range": null,
      
      // Status and metadata
      "active_status": "active",
      "last_verified": "2025-08-19",
      "data_quality": "high",
      "source_urls": ["https://restaurant.com/happy-hour"],
      "confidence_scores": [0.85, 0.90],
      "average_confidence": 0.875
    }
  ]
}
```

### Deal Menus (`deal_menus.json`)

Defines **what** is offered with structured pricing and categorization.

```json
{
  "refined_at": "2025-08-19T...",
  "total_menus": 45,
  "menus": [
    {
      "schedule_id": "restaurant-name-happy_hour-monday-tuesday-wednesday",
      "restaurant_slug": "restaurant-name",
      "menu_type": "combo",  // drinks, food, combo
      
      // Menu items (structured)
      "items": [
        {
          "name": "House Cocktails",
          "category": "cocktails",
          "deal_price": 8.0,
          "regular_price": 12.0,
          "savings": 4.0,
          "discount_percent": 33,
          "description": "Well spirits with fresh mixers",
          "confidence_score": 0.9
        },
        {
          "name": "Draft Beer",
          "category": "beer", 
          "deal_price": 5.0,
          "size": "16oz",
          "confidence_score": 0.85
        }
      ],
      
      // Menu metadata
      "source": "website",
      "menu_url": "https://restaurant.com/menu",
      "last_updated": "2025-08-19",
      "data_quality": "high",
      "price_range": "$5-12",
      "item_count": 8,
      "categories": ["cocktails", "beer", "appetizers"]
    }
  ]
}
```

## Layer 3: Public Presentation Data

**Purpose**: User-facing data optimized for presentation and real-time features

**Location**: `data/public/`

### Active Deals (`active_deals.json`)

Clean, user-friendly deal information ready for web/app display.

```json
{
  "generated_at": "2025-08-19T...",
  "total_deals": 60,
  "deals": [
    {
      "id": "restaurant-name-happy_hour-weekdays",
      "restaurant_slug": "restaurant-name",
      "restaurant_name": "Restaurant Name",
      
      // Deal information (user-friendly)
      "deal_name": "Weekday Happy Hour",
      "deal_type": "happy_hour",
      "when": "Mon-Fri 3:00-6:00 PM",
      
      // Highlights and summary
      "highlights": [
        "$8 House Cocktails",
        "$5 Draft Beer", 
        "$6 Appetizers"
      ],
      "savings_range": "$5-12 savings",
      "description": "Craft cocktails and local beers...",
      
      // Real-time status (calculated)
      "active_now": false,
      "starts_in_minutes": 45,
      "ends_in_minutes": null,
      
      // Quality indicators
      "confidence": "high",
      "last_verified": "2025-08-19",
      
      // Links and actions
      "menu_url": "https://restaurant.com/menu",
      "reservation_url": null
    }
  ]
}
```

### Deal Summary (`deal_summary.json`)

Aggregated statistics and highlights for dashboard displays.

```json
{
  "generated_at": "2025-08-19T...",
  "total_active_deals": 60,
  "total_restaurants": 25,
  
  // Deal type breakdown
  "deal_types_count": {
    "happy_hour": 35,
    "brunch": 8,
    "early_bird": 5,
    "daily_special": 7,
    "weekend": 5
  },
  
  // Highlights (real-time calculated)
  "top_savings": [
    {
      "restaurant_slug": "restaurant-a",
      "deal_name": "Happy Hour",
      "savings_amount": "$8 off cocktails"
    }
  ],
  "starting_soon": [
    {
      "restaurant_slug": "restaurant-b", 
      "starts_in_minutes": 15
    }
  ],
  "active_now": [
    {
      "restaurant_slug": "restaurant-c",
      "ends_in_minutes": 45
    }
  ],
  
  // Data quality metrics
  "data_quality_stats": {
    "high": 45,
    "medium": 12,
    "low": 3
  }
}
```

## Deal Types Supported

The system supports **17 different deal types** beyond traditional happy hours:

| Deal Type | Description | Example |
|-----------|-------------|---------|
| `happy_hour` | Traditional happy hour deals | Mon-Fri 3-6 PM drink specials |
| `brunch` | Brunch specials, bottomless | Weekend bottomless mimosas |
| `bottomless` | Unlimited drinks | Bottomless brunch drinks |
| `early_bird` | Pre-dinner discounts | 5-6 PM dinner specials |
| `late_night` | Post-dinner deals | After 10 PM appetizers |
| `daily_special` | Day-specific deals | Taco Tuesday, Wine Wednesday |
| `prix_fixe` | Fixed price menus | 3-course $35 menu |
| `tasting_menu` | Chef's tasting experiences | 7-course chef selection |
| `game_day` | Sports event specials | Game day wings & beer |
| `industry` | Service industry discounts | Industry night 20% off |
| `trivia` | Trivia with specials | Wednesday trivia + deals |
| `reverse_happy` | Late evening deals | 9-11 PM reverse happy hour |
| `weekend` | Weekend-only deals | Saturday/Sunday specials |
| `seasonal` | Holiday/seasonal menus | Holiday cocktail menu |
| `restaurant_week` | Restaurant week events | Restaurant week prix fixe |
| `live_music` | Music events with specials | Live jazz + drink specials |
| `karaoke` | Karaoke night deals | Karaoke night drink deals |

## Data Quality Framework

### Confidence Scoring
- **High (0.8-1.0)**: Human verified or high-confidence extraction
- **Medium (0.5-0.7)**: Good extraction with minor uncertainties  
- **Low (0.0-0.4)**: Needs manual review or has extraction issues

### Data Quality Levels
- **Verified**: Human reviewed and confirmed
- **High**: High confidence extraction, complete data
- **Medium**: Partial extraction, some missing elements
- **Low**: Significant gaps or extraction issues
- **Inferred**: Guessed from patterns
- **Failed**: Extraction failed

## Schema Benefits

### For Developers
- **Debuggable**: All raw extraction artifacts preserved
- **Maintainable**: Clear separation of concerns
- **Scalable**: Easy to add new deal types and restaurants
- **Testable**: Each layer can be validated independently

### For Users  
- **Clean**: User-friendly names and formatting
- **Real-time**: Active/starting/ending status calculations
- **Comprehensive**: All dining deals, not just happy hours
- **Reliable**: Quality indicators show data confidence

### For Business
- **Professional**: Production-ready data architecture
- **Expandable**: Support for any type of restaurant promotion
- **Measurable**: Quality metrics and coverage statistics
- **Competitive**: Rich deal data beyond basic happy hours

## Processing Pipeline

1. **Raw Extraction**: Scrapers populate raw layer with all artifacts
2. **Refinement**: Pipeline processes raw data into clean, normalized format
3. **Quality Control**: Validation, deduplication, and confidence scoring
4. **Presentation**: Generation of user-friendly public data
5. **Real-time**: Live calculation of active/starting/ending status

## File Organization

```
data/
├── restaurants.json              # Master restaurant database (106 restaurants)
├── discovered_urls.json          # Happy hour page URLs discovered by crawlers
├── discovered_links.json         # All links discovered during crawling
├── temp/                         # Temporary operational files
├── raw/                          # Layer 1: Raw extraction & debugging
│   ├── extracted_deals_raw.json  # All raw extractions with artifacts
│   ├── deals_original_backup.json # Original deals.json backup
│   ├── deals_original_unrefined.json # Pre-migration unrefined data
│   ├── cache/                    # Operational status and district files
│   │   ├── scraping_status.json  # Current scraping status
│   │   └── lodo_union_station_*.json # District-specific cache files
│   └── legacy/                   # Archived test data and proof-of-concept files
│       ├── lodo_dashboard_data.json
│       ├── test_restaurants.json
│       └── *.json               # Historical test files
├── refined/                      # Layer 2: Clean, validated data
│   ├── deal_schedules.json      # When deals happen (normalized)
│   └── deal_menus.json          # What's offered (structured pricing)
└── public/                       # Layer 3: User-facing presentation
    ├── active_deals.json         # Clean deals ready for web/app display
    └── deal_summary.json         # Aggregated statistics and highlights
```

## Migration Results

**Dramatic Quality Improvement**: 525 raw extractions → 60 clean, deduplicated deals

- **10:1 reduction ratio** through intelligent deduplication
- **Smart classification** of deal types beyond happy hours  
- **Time normalization** to 24-hour format with 12-hour display
- **Schedule merging** of multiple extractions into single deals
- **Confidence scoring** for data quality assessment

This architecture provides a robust foundation for expanding deal extraction while maintaining data quality and user experience.

## Restaurant Data Schema

The master restaurant database (`restaurants.json`) contains comprehensive information for all 106 restaurants across 11 Denver districts, enriched with Google Places API data for reliability and completeness.

### Restaurant Database Structure

```json
{
  "metadata": {
    "source": "enhanced_data_pipeline",
    "updated_at": "2025-08-18T20:21:17.273537",
    "districts": ["Central", "North Denver", "Boulder", ...],
    "districts_with_neighborhoods": {
      "Central": ["LoDo", "Union Station", "RiNo", ...],
      "North Denver": ["Berkeley", "Highlands", ...]
    }
  },
  "restaurants": {
    "restaurant-slug": { ... }
  }
}
```

### Individual Restaurant Schema

Each restaurant entry contains the following standardized structure:

```json
{
  "name": "Restaurant Name",
  "slug": "restaurant-slug",
  "district": "Central",
  "neighborhood": "LoDo",
  "address": "1234 Street Name, Denver, CO 80202, USA",
  "cuisine": "Italian",
  "website": "https://restaurant.com",
  
  // Contact Information (Google Places enriched)
  "contact_info": {
    "primary_phone": "(720) 555-1234",
    "reservation_phone": null,
    "general_email": null,
    "reservations_email": null,
    "events_email": null,
    "instagram": "restaurant_handle",
    "facebook": null,
    "twitter": null,
    "tiktok": null,
    "international_phone": "+1 720-555-1234"
  },
  
  // Dining Experience Details
  "dining_info": {
    "price_range": "$$$",           // $, $$, $$$, $$$$
    "dress_code": "Casual",         // Casual, Smart Casual, Business Casual, Formal
    "atmosphere": [
      "Neighborhood Gem",
      "Date Night",
      "Wine Bar"
    ],
    "dining_style": "Casual Fine Dining",
    "total_seats": 85,
    "bar_seats": 12,
    "outdoor_seats": 20
  },
  
  // Service Capabilities
  "service_info": {
    "accepts_reservations": true,
    "opentable_url": "https://www.opentable.com/restaurant",
    "resy_url": null,
    "direct_reservation_url": null,
    "offers_delivery": true,
    "offers_takeout": true,
    "offers_curbside": false,
    "doordash_url": "https://doordash.com/restaurant",
    "ubereats_url": null,
    "grubhub_url": null
  },
  
  // Operating Schedule
  "timezone": "America/Denver",
  "operating_hours": {
    "monday": { "open": "17:00", "close": "22:00" },
    "tuesday": { "open": "17:00", "close": "22:00" },
    "wednesday": { "open": "17:00", "close": "22:00" },
    "thursday": { "open": "17:00", "close": "22:00" },
    "friday": { "open": "17:00", "close": "23:00" },
    "saturday": { "open": "16:00", "close": "23:00" },
    "sunday": { "open": "16:00", "close": "21:00" }
  },
  
  // Static Deal Information (fallback data)
  "static_deals": [
    {
      "title": "Happy Hour",
      "description": "Discounted drinks and appetizers",
      "deal_type": "happy_hour",
      "days_of_week": ["monday", "tuesday", "wednesday", "thursday", "friday"],
      "start_time": "15:00",
      "end_time": "18:00",
      "is_all_day": false,
      "price": "$5-12 drinks",
      "confidence_score": 0.3,
      "source": "manual_entry"
    }
  ]
}
```

### Data Quality & Coverage

**Google Places API Enhancement** (99-100% coverage):

- ✅ **Addresses**: 100% complete, standardized format
- ✅ **Phone Numbers**: 99% coverage with international format
- ✅ **Operating Hours**: 95% coverage with timezone normalization
- ✅ **Business Status**: Active status verification
- ✅ **Coordinates**: Precise latitude/longitude for mapping

**Manual Curation** (restaurant-specific):

- ✅ **Cuisine Types**: Carefully categorized (Italian, Mexican, American, etc.)
- ✅ **Atmosphere Tags**: Experience descriptors (Date Night, Sports Bar, etc.)
- ✅ **Price Ranges**: Economic categorization ($-$$$$)
- ✅ **Service Capabilities**: Reservation systems, delivery options

### District & Neighborhood Organization

**11 Districts Covered**:

- **Central**: LoDo, Union Station, RiNo, Capitol Hill, CBD
- **North Denver**: Berkeley, Highlands, Regis
- **Northwest Denver**: Lakeside, Wheat Ridge
- **West & Southwest Denver**: Lakewood, Edgewater
- **South**: Cherry Creek, Glendale
- **East & Southeast Denver**: Hampden South, Lowry Field
- **Northeast Denver**: Stapleton, Montclair
- **Boulder**: Pearl Street, University Hill
- **Aurora**: Various neighborhoods
- **Greenwood Village, Englewood, Littleton, Centennial**
- **Lakewood/Wheat Ridge/Golden**

### Static Deals (Fallback System)

When live deal extraction is unavailable, the system falls back to static deal information:

**Deal Types Supported**:

- `happy_hour` - Traditional drink/food discounts
- `brunch` - Weekend brunch specials
- `daily_special` - Day-specific deals (Taco Tuesday)
- `early_bird` - Pre-dinner specials
- `late_night` - After-hours deals

**Confidence Scoring**:

- Live scraped deals: 0.6-1.0 confidence
- Static deals: 0.3 confidence (fallback quality)
- Manual verification: 1.0 confidence

### Integration with Deal Extraction

The restaurant database serves as the foundation for the three-layer deal architecture:

1. **Discovery**: Crawlers use restaurant URLs to find happy hour pages
2. **Extraction**: Live deals are linked to restaurants via slug matching
3. **Fallback**: Static deals provide coverage when live extraction fails
4. **Enrichment**: Google Places data enables contact and mapping features

This comprehensive restaurant schema ensures reliable, complete business information while supporting sophisticated deal discovery and presentation features.