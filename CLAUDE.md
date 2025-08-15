# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

# Run the main scraper
python run_scraper.py

# View scraped data in pretty format
python view_deals.py

# Parse Giovanni's markdown into structured JSON data
python parse_giovanni.py

# Generate multi-page static website with Jinja2 templates
python generate_site.py

# Legacy single-page generator (deprecated)
python generate_website.py

# Run individual test files
python test_jax_website.py
python test_jax_location_page.py
```

### Testing
No formal test framework is configured. Testing is done via individual test files like `test_jax_website.py` and `enhanced_jax_test.py` that can be run directly with `python filename.py`.

## Architecture

### Core Components

**Data Storage**: JSON-based approach organized by Denver areas
- Restaurant data parsed from `data/giovanni_happy_hours.md` using `parse_giovanni.py`
- Structured data stored in `data/restaurants.json` (single source of truth)
- Location-based organization optimized for "The Discerning Urban Explorer"
- 117 restaurants across 12 Denver areas with comprehensive metadata

**Scraper Framework**: Object-oriented scraper system
- `BaseScraper` abstract class (`src/scrapers/base.py`) provides common functionality
- Individual restaurant scrapers inherit from `BaseScraper`
- Each scraper implements `scrape_deals()` method returning standardized deal dictionaries
- Built-in rate limiting and polite crawling headers

**Deal Data Structure**: Standardized dictionary format for all deals:
```python
{
    'title': str,           # Required
    'description': str,     # Optional
    'day_of_week': str,     # Optional, comma-separated
    'start_time': str,      # Optional
    'end_time': str,        # Optional  
    'deal_type': str,       # 'happy_hour', 'daily_special', 'food', 'drink'
    'price': str           # Optional
}
```

### Key Workflows

**Adding New Restaurant Scrapers**:
1. Create new file in `src/scrapers/`
2. Inherit from `BaseScraper`
3. Implement `scrape_deals()` method
4. Add to scraper list in `run_scraper.py`

**Data Processing Flow**:
1. `parse_giovanni.py` parses markdown source into `data/restaurants.json`
2. `generate_site.py` creates multi-page static website from JSON data using Jinja2 templates
3. Legacy scrapers: `run_scraper.py` orchestrates individual restaurant scrapers (CSV-based)
4. `view_deals.py` provides formatted output for legacy CSV data

### Current Restaurant Scrapers
- **Jax Fish House**: JSON-LD structured data parsing
- **Hapa Sushi**: HTML parsing for menu items
- **Tamayo**: Standard scraping implementation

### Web Output
**Multi-page Architecture**: 
- `generate_site.py` creates a static site using Jinja2 templates and Pico CSS
- Dark theme optimized for "The Discerning Urban Explorer" persona  
- Responsive grid layout with restaurant cards displaying left-to-right
- Individual restaurant profile pages (`docs/restaurants/{slug}.html`)
- Semantic HTML with filtering by day, area, and cuisine
- 117 restaurant pages + main index with location-based organization

**Template System**:
- `templates/base.html` - Base template with Pico CSS and dark theme
- `templates/index.html` - Restaurant grid with filtering functionality  
- `templates/restaurant.html` - Individual restaurant profile pages