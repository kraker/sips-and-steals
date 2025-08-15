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
# Install dependencies
pip install -r requirements.txt

# Run the main scraper
python run_scraper.py

# View scraped data in pretty format
python view_deals.py

# Generate static HTML website
python generate_website.py

# Run individual test files
python test_jax_website.py
python test_jax_location_page.py
```

### Testing
No formal test framework is configured. Testing is done via individual test files like `test_jax_website.py` and `enhanced_jax_test.py` that can be run directly with `python filename.py`.

## Architecture

### Core Components

**Data Storage**: Pure CSV approach using `CSVManager` class (`src/csv_manager.py`)
- Single CSV file at `data/happy_hour_deals.csv`
- No database - designed for simplicity and Excel compatibility
- Automatic deduplication by restaurant name on each scrape

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
1. `run_scraper.py` orchestrates all scrapers
2. Each scraper clears old data for its restaurant
3. New deals scraped and saved to CSV
4. `view_deals.py` provides formatted output
5. `generate_website.py` creates static HTML from CSV data

### Current Restaurant Scrapers
- **Jax Fish House**: JSON-LD structured data parsing
- **Hapa Sushi**: HTML parsing for menu items
- **Tamayo**: Standard scraping implementation

### Web Output
`generate_website.py` creates a static HTML site in `docs/index.html` with dark theme styling and mobile responsiveness, grouping deals by area (currently Union Station focus).