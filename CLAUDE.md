# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Milestones

### 🎯 **Milestone 3: Production-Ready Scraping Platform** (August 17, 2025)
**Status**: ✅ COMPLETED

**Goals Achieved**:
- **Enhanced NW Denver Coverage**: Fixed American Elm, Bamboo Sushi scrapers (1/19 → 4/19 success rate)
- **Data Quality Systems**: Added source URL tracking, text spacing fixes, robots.txt compliance
- **Documentation Overhaul**: Updated README, created config documentation, milestone tracking
- **UI/UX Polish**: Fixed misleading time indicators, improved deal status badges
- **Architecture Maturity**: Config-based scrapers, modular processing, comprehensive error handling

**Technical Deliverables**:
- 106 restaurants across 11 districts with 34.9% live data coverage
- Robust YAML-driven scraper configuration system
- Production-ready CLI with quality analysis and concurrent processing
- Responsive multi-page website with real-time deal indicators
- Comprehensive backup and archival systems

### 🏗️ **Milestone 2: Enhanced Data Architecture** (August 16, 2025)
**Status**: ✅ COMPLETED

**Goals Achieved**:
- **Single Source Architecture**: Consolidated to `restaurants.json` as master database
- **Live Deal Integration**: Built confidence-scored scraping with 3-tier fallback system
- **Website Generation**: Created responsive static site with individual restaurant profiles
- **Data Quality**: Implemented validation, backup management, and historical archiving

**Technical Deliverables**:
- Unified restaurant database with metadata and static deals
- Live deal aggregation with confidence scoring
- Automated daily archiving and backup management
- Enhanced multi-page website with filtering and search

### 🌱 **Milestone 1: Proof of Concept** (Initial Development)
**Status**: ✅ COMPLETED

**Goals Achieved**:
- **Core Scraping**: Basic restaurant website scraping for happy hour deals
- **Data Storage**: CSV-based storage for immediate usability
- **Initial Coverage**: Successful extraction from key LoDo restaurants

**Technical Deliverables**:
- BeautifulSoup-based web scraping
- CSV data export for Excel compatibility
- Command-line interface for manual execution

---

## Recent Work (Current Sprint)

## Target User

**The Discerning Urban Explorer**: Our target user is a sophisticated food and beverage enthusiast who views happy hour not as budget dining, but as smart luxury. They appreciate:

- **Quality over quantity** - Seeking expertly crafted cocktails, artisanal dishes, and elevated cuisine rather than generic bar food
- **Culinary adventure** - Drawn to diverse, high-caliber cuisines and unique dining experiences  
- **Strategic dining** - Uses happy hour timing to access premium experiences at accessible price points
- **Urban sophistication** - Gravitates toward established neighborhoods with walkable restaurant clusters
- **Experience-focused** - Values atmosphere, craft, and storytelling behind dishes/drinks - not just the discount

This user doesn't want "cheap eats" - they want to discover Denver's culinary gems during their most approachable hours, building a personal map of quality establishments worth returning to at full price.

## Git Commit Style Guide

### Atomic Commit Principles
Following [Aleksandr Hovhannisyan's atomic git commits](https://www.aleksandrhovhannisyan.com/blog/atomic-git-commits/):

**Core Rule**: Each commit should represent "a single, complete unit of work" that can be independently reviewed and reverted.

### Commit Message Format

**Simple Changes** (data fixes, small bug fixes):
```bash
git commit -m "Fix malformed neighborhood names in restaurant data"
git commit -m "Update American Elm scraper time pattern"
git commit -m "Add robots.txt status to restaurant objects"
```

**Feature Commits** (new capabilities, significant changes):
```bash
git commit -m "Add config-based scraper system for rapid restaurant onboarding"
git commit -m "Implement deal confidence scoring and validation"
```

**Milestone/Release Commits** (major completions):
```bash
# Use detailed heredoc format for comprehensive changelog
git commit -m "$(cat <<'EOF'
Complete documentation overhaul and milestone tracking
...detailed changelog...
EOF
)"
```

### Guidelines
- **Present tense verbs**: "Fix", "Add", "Update", "Remove", "Implement"
- **Component focus**: Mention what area/system is changed
- **Atomic scope**: One logical change per commit
- **No fear of many commits**: Better to have 5 focused commits than 1 mixed commit

### Examples by Type
- **Data fixes**: `Fix duplicate neighborhoods in district metadata`
- **Scraper updates**: `Add Bamboo Sushi day pattern validation`
- **Feature additions**: `Implement time-based deal relevance scoring`
- **Documentation**: `Update README with current architecture`
- **Bug fixes**: `Fix missing source URLs in scraped deals`

## Commands

### Core Commands
```bash
# Install dependencies (all pip dependencies managed via requirements.txt)
pip install -r requirements.txt

# Run scraping system for live deals
python scraper_cli.py scrape --district "Central" --workers 2

# Generate multi-page static website with live data
python generate_site.py

# System status and monitoring
python scraper_cli.py status
python scraper_cli.py quality --export
```

### Testing
No formal test framework is configured. Testing is done via direct script execution and manual verification of website output.

## Architecture

### Core Components

**Single Source Data Architecture**: Live scraping-based approach
- **`data/restaurants.json`** - Single source of truth containing all restaurant data, static happy hour data, and scraping metadata
- **`data/deals.json`** - Current live scraped deals with timestamps and confidence scores
- **`data/deals_archive/`** - Historical deal archives for data persistence and analysis
- **`legacy_archive/`** - Archived original Giovanni markdown and parser (legacy)
- 106 restaurants across 11 Denver districts with comprehensive metadata

**Enhanced Scraper Framework**: Production-ready scraping system
- `BaseScraper` class (`src/scrapers/base.py`) with robots.txt compliance
- Built-in circuit breakers, retry logic, and adaptive delays to avoid bot detection
- Individual restaurant scrapers inherit and implement custom scraping logic
- Quality validation and confidence scoring for all scraped deals
- Concurrent execution with configurable worker pools

**Enhanced Deal Data Structure**: Comprehensive deal objects with validation:
```python
@dataclass
class Deal:
    title: str
    description: Optional[str] = None
    deal_type: DealType = DealType.HAPPY_HOUR
    days_of_week: List[DayOfWeek] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    price: Optional[str] = None
    is_all_day: bool = False
    special_notes: List[str] = field(default_factory=list)
    scraped_at: datetime = field(default_factory=datetime.now)
    source_url: Optional[str] = None
    confidence_score: float = 1.0  # 0.0-1.0 confidence rating
```

### Key Workflows

**Adding New Restaurant Scrapers**:
1. Create new file in `src/scrapers/` (e.g., `restaurant_name.py`)
2. Inherit from `BaseScraper`
3. Implement custom `scrape_deals()` method returning List[Deal]
4. Restaurant automatically included based on website URL in `data/restaurants.json`

**Data Processing Flow**:
1. **Live Scraping**: `scraper_cli.py` collects live deals from restaurant websites and stores in `data/deals.json`
2. **Data Merge**: `DataManager` prioritizes live deals over static data (3-tier fallback system)
3. **Website Generation**: `generate_site.py` creates multi-page static website with live deal display
4. **Archival**: Deals automatically archived to `data/deals_archive/` with timestamps

**Data Prioritization** (3-tier fallback system):
1. **Fresh live deals** (< 7 days old) - highest priority
2. **Any live deals** (even if older) - medium priority  
3. **Static happy hour data** from `restaurants.json` - fallback with 0.3 confidence score

### Current Restaurant Scrapers
- **Jax Fish House**: JSON-LD structured data parsing (2 deals with 0.8-0.9 confidence)
- **Tamayo**: Custom HTML parsing (3 deals with 0.8-0.9 confidence)
- **City O' City**: Plant-based happy hour scraping (1 deal with 0.8 confidence)

### Web Output
**Enhanced Multi-page Architecture**: 
- `generate_site.py` creates a static site using Jinja2 templates and Pico CSS
- Dark theme optimized for "The Discerning Urban Explorer" persona  
- Responsive grid layout with restaurant cards and live data indicators
- Individual restaurant profile pages (`docs/restaurants/{slug}.html`) with live deal sections
- Semantic HTML with filtering by day, district, and cuisine
- 106 restaurant pages + main index + statistics page with scraping metrics
- Live vs. static data clearly distinguished with confidence indicators

**Template System**:
- `templates/base.html` - Base template with Pico CSS and dark theme
- `templates/index.html` - Restaurant grid with live data badges and filtering
- `templates/restaurant.html` - Individual restaurant profiles with live deal display
- Custom Jinja2 filters for day range formatting ("Mon - Fri", "Daily", etc.)

## Roadmap & Future Enhancements

### Timezone-Aware Time Handling & Operating Hours
**Priority**: High | **Effort**: Medium | **Impact**: High

Implement comprehensive time and timezone handling to provide accurate "open now" status, timezone-appropriate display for international users, and real-time happy hour tracking.

**Current Limitations**:
- Times stored as display strings ("4:00 PM") without timezone context
- No restaurant operating hours data
- No "open now" or time-until-happy-hour functionality
- Display format not configurable for international users

**Technical Implementation**:
*Schema Normalization:*
- **24-Hour Time Format**: Store all times internally as "HH:MM" (e.g., "16:00", "18:00")
- **Timezone Fields**: Add timezone to restaurants and deals (default: "America/Denver")
- **Operating Hours**: Extend restaurant schema with daily open/close times
- **Dual Time Storage**: Maintain display times for UI, normalized times for calculations

*Library Integration:*
- **Pendulum**: Robust timezone handling and time calculations
- **Time Parsing**: Convert scraped times from various formats to 24-hour
- **Timezone Conversion**: Display times appropriate to user's timezone
- **Business Logic**: "Is restaurant open?", "Time until happy hour starts"

*Enhanced Deal Structure:*
```python
@dataclass
class Deal:
    # Display (user-friendly)
    start_time: Optional[str] = None      # "4:00 PM" 
    end_time: Optional[str] = None        # "6:00 PM"
    # Normalized (for calculations)
    start_time_24h: Optional[str] = None  # "16:00"
    end_time_24h: Optional[str] = None    # "18:00"
    timezone: str = "America/Denver"
```

*Restaurant Operating Hours:*
```json
{
  "operating_hours": {
    "monday": {"open": "11:00", "close": "22:00"},
    "tuesday": {"open": "11:00", "close": "22:00"},
    "sunday": {"open": "10:00", "close": "21:00"}
  },
  "timezone": "America/Denver"
}
```

**Implementation Phases**:
1. **Schema Migration**: Update restaurant and deal data structures with 24-hour times
2. **Scraper Enhancement**: Extend existing scrapers to capture operating hours
3. **Time Utilities**: Implement timezone-aware calculation functions
4. **UI Integration**: Add "Open Now" indicators and countdown timers
5. **User Preferences**: Support for 12/24-hour display format selection

**Success Metrics**:
- Accurate "open now" status for 95%+ of restaurants
- Timezone-appropriate time display for international users
- Real-time happy hour countdown functionality
- Foundation ready for full-stack Flask web application

### Special Event & Holiday Deals Framework
**Priority**: Medium | **Effort**: Medium | **Impact**: Medium

Extend the deal system to handle special events, holidays, and date-specific promotions beyond regular happy hour schedules.

**Enhanced Deal Types**:
- **Special Events**: Convention deals, sports game specials, concert promotions
- **Holiday Deals**: New Year's Eve, Valentine's Day, St. Patrick's Day specials
- **Seasonal Offerings**: Summer patio deals, winter holiday menus
- **Date-Specific**: Limited-time promotions with start/end dates

**Technical Implementation**:
```python
@dataclass
class Deal:
    deal_type: DealType  # HAPPY_HOUR, SPECIAL_EVENT, HOLIDAY, SEASONAL
    event_name: Optional[str] = None        # "Broncos Game Day"
    start_date: Optional[str] = None        # "2025-12-31"
    end_date: Optional[str] = None          # "2025-12-31"
    # ... existing fields
```

**Future Integrations**:
- Holiday APIs for automatic holiday deal detection
- Sports schedule APIs for game day promotions
- Convention center calendars for event-based deals
- Reservation system integration for special event bookings

### Full-Stack Flask Web Application
**Priority**: High | **Effort**: High | **Impact**: High

Transition from static site generator to dynamic Flask web application with real-time features, user accounts, and interactive functionality.

**Core Features**:
- **Real-Time Updates**: Live deal status, countdown timers, open/closed indicators
- **User Accounts**: Preferences, favorites, notification settings
- **Interactive Filtering**: Dynamic search, map integration, real-time filtering
- **Personalization**: Timezone-aware display, cuisine preferences, distance-based recommendations

**Technical Stack**:
- **Backend**: Flask with SQLAlchemy ORM
- **Database**: PostgreSQL for production, SQLite for development
- **Frontend**: Modern JavaScript with responsive design
- **Real-Time**: WebSocket connections for live updates
- **Deployment**: Docker containers with CI/CD pipeline

### Intelligent Happy Hour Content Discovery
**Priority**: Medium | **Effort**: Medium | **Impact**: High

Automatically discover happy hour pages and content across restaurant websites by crawling and analyzing site structure, eliminating the need for manual URL identification and pattern creation.

**Problem**:
- Currently requires manual identification of happy hour URLs for each restaurant
- Many restaurants have happy hour information on non-obvious pages (subpages, PDFs, embedded content)
- Time-intensive process to audit 106+ restaurant websites individually
- Happy hour URLs may change over time, breaking existing scrapers

**Technical Approach**:

*Site Crawling Strategy:*
- **Breadth-First Search**: Start from main restaurant URL and crawl up to 3 levels deep
- **Content-Based Filtering**: Look for pages containing keywords like "happy hour", "specials", "deals", "daily" 
- **URL Pattern Recognition**: Identify common happy hour URL patterns (/happy-hour, /specials, /deals, etc.)
- **PDF Detection**: Scan for linked PDF menus that may contain happy hour information

*Content Analysis Pipeline:*
- **Semantic Analysis**: Use NLP to identify pages with time-based pricing or menu information
- **Schedule Detection**: Automatically identify time ranges and day patterns in content
- **Confidence Scoring**: Rate pages based on happy hour content likelihood
- **Change Detection**: Monitor discovered pages for content updates

*Implementation Architecture:*
- **Crawler Service**: Respectful web crawler with robots.txt compliance and rate limiting
- **Content Analyzer**: ML-based text classification for happy hour content detection
- **URL Repository**: Database of discovered happy hour URLs with confidence scores
- **Auto-Config Generator**: Automatically create scraper configs for discovered content

**Success Metrics**:
- Discover happy hour content for 90%+ of restaurants automatically
- Reduce manual URL identification time from hours to minutes
- Maintain discovery accuracy above 85% (minimize false positives)
- Detect content changes and URL updates within 24 hours

**Implementation Phases**:
1. **Research**: Analyze current restaurant URL patterns and content structures
2. **Crawler Development**: Build respectful, efficient web crawler with content analysis
3. **ML Training**: Train content classifier on existing happy hour pages
4. **Integration**: Connect discovery system to existing scraper architecture
5. **Monitoring**: Implement change detection and notification system

### JavaScript Interactivity Support
**Priority**: Medium | **Effort**: High | **Impact**: High

Many modern restaurant websites (like STK) use JavaScript for dynamic content loading, making them incompatible with our current BeautifulSoup-based static HTML parsing approach.

**Problem**: 
- STK's location dropdown uses JS event handlers for dynamic content loading
- Current form submission only handles server-side processing, not client-side JS
- Estimated 10-15% of restaurants may require JS execution for full data access

**Technical Options for DOM Interaction**:

*Browser Automation Libraries:*
- **Playwright** (Recommended): Modern, fast, supports Chromium/Firefox/Safari, better performance than Selenium
- **Selenium WebDriver**: Mature ecosystem, wider community, slower but more established
- **Pyppeteer**: Lightweight Chrome automation via DevTools Protocol, limited to Chromium

*Implementation Approaches for STK's Dropdown:*
- **Direct Event Simulation**: `await page.select_option('select[name="location"]', value='699')`
- **JavaScript Execution**: Execute actual JS that runs on change events
- **Network Interception**: Capture AJAX calls triggered by dropdown interactions

*Hybrid Detection Strategy:*
1. Try static HTML parsing first (fast, works for 87% of sites)
2. Detect JS requirement indicators (empty content, AJAX loaders, client-side handlers)
3. Fall back to browser automation only when needed

*Performance Optimizations:*
- Browser instance pooling and reuse
- Headless mode for speed
- Resource blocking (images/CSS) for faster loading
- Intelligent timeout management

**Implementation Phases**:
1. **Research**: Evaluate Playwright vs Selenium performance and reliability
2. **Architecture**: Design hybrid scraping system with JS capability detection
3. **Integration**: Add browser automation to BaseScraper with fallback logic
4. **Optimization**: Implement caching and pool management for browser instances

**Success Metrics**:
- Increase scraping success rate from 87.5% to 95%+
- Successfully parse STK and other JS-dependent restaurant sites
- Maintain scraping performance under 30 seconds per restaurant

### PDF Document Parsing Support
**Priority**: Low | **Effort**: Medium | **Impact**: Medium

Some restaurants (like Jovanina's Broken Italian) publish their happy hour menus as PDF documents rather than web pages, which our current HTML-based scraper cannot process.

**Example Case**: 
- Jovanina's PDF menu: `https://jovanina.com/wp-content/uploads/2025/05/Happy-Hour-Menu-Card8.pdf`
- Contains detailed happy hour pricing and timing information
- Current scraper skips PDF URLs and finds no deals

**Technical Approach**:
- **PDF Text Extraction**: Integrate PyPDF2 or pdfplumber for text extraction
- **Content Type Detection**: Identify PDF URLs and route to specialized parser
- **Structured Data Extraction**: Parse menu items, prices, and timing from PDF text
- **Image Processing**: OCR support for image-based PDFs (optional)

**Implementation**:
1. Add PDF content type detection in BaseScraper._fetch_single_url()
2. Create PDFMenuParser class with text extraction and pattern matching
3. Enhance multiple URL architecture to handle mixed content types
4. Add fallback for image-based PDFs using OCR libraries

**Success Metrics**:
- Successfully extract deals from Jovanina's PDF menu
- Support for 5-10 restaurants using PDF menus
- Maintain parsing accuracy above 85% for PDF documents