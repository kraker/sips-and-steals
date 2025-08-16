# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Recent Work (August 16, 2025)
- **Repository Cleanup**: Consolidated to single data source architecture
- **Enhanced Scraping**: Built live deal scraping system with confidence scoring
- **Live Data Integration**: Successfully scraped and integrated 6 high-quality deals from 3 restaurants
- **Data Consolidation**: Unified all restaurant data into `restaurants.json` as single source of truth
- **Website Enhancement**: Generated enhanced site with live deal display and proper day formatting
- **Backslash Fix**: Resolved escape character issues in restaurant names and data

## Target User

**The Discerning Urban Explorer**: Our target user is a sophisticated food and beverage enthusiast who views happy hour not as budget dining, but as smart luxury. They appreciate:

- **Quality over quantity** - Seeking expertly crafted cocktails, artisanal dishes, and elevated cuisine rather than generic bar food
- **Culinary adventure** - Drawn to diverse, high-caliber cuisines and unique dining experiences  
- **Strategic dining** - Uses happy hour timing to access premium experiences at accessible price points
- **Urban sophistication** - Gravitates toward established neighborhoods with walkable restaurant clusters
- **Experience-focused** - Values atmosphere, craft, and storytelling behind dishes/drinks - not just the discount

This user doesn't want "cheap eats" - they want to discover Denver's culinary gems during their most approachable hours, building a personal map of quality establishments worth returning to at full price.

## Commands

### Core Commands
```bash
# Install dependencies (all pip dependencies managed via requirements.txt)
pip install -r requirements.txt

# Parse Giovanni's markdown into structured JSON data (updates restaurants.json)
python parse_giovanni.py

# Run scraping system for live deals
python scraper_cli.py scrape --district "Central" --workers 2

# Generate multi-page static website with live data
python generate_site.py
```

### Testing
No formal test framework is configured. Testing is done via direct script execution and manual verification of website output.

## Architecture

### Core Components

**Single Source Data Architecture**: Consolidated JSON-based approach
- **`data/restaurants.json`** - Single source of truth containing all restaurant data and live data metadata
- **`data/live_deals.json`** - Current live scraped deals with timestamps and confidence scores
- **`data/deals_archive/`** - Historical deal archives for data persistence and analysis
- Static data parsed from `data/giovanni_happy_hours.md` using `parse_giovanni.py`
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
1. **Static Data**: `parse_giovanni.py` parses markdown source into `data/restaurants.json`
2. **Live Scraping**: `scraper_cli.py` collects live deals and stores in `data/live_deals.json`
3. **Data Merge**: `DataManager` prioritizes live deals over static data (3-tier fallback system)
4. **Website Generation**: `generate_site.py` creates multi-page static website with live deal display
5. **Archival**: Deals automatically archived to `data/deals_archive/` with timestamps

**Data Prioritization** (3-tier fallback system):
1. **Fresh live deals** (< 7 days old) - highest priority
2. **Any live deals** (even if older) - medium priority  
3. **Static Giovanni's data** - fallback with 0.3 confidence score

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