# Sips and Steals

A simple web scraper that aggregates local restaurant happy hour deals and specials.

## Target User

**The Discerning Urban Explorer** - sophisticated food and beverage enthusiasts who view happy hour as smart luxury, not budget dining. They seek expertly crafted cocktails and elevated cuisine at accessible prices, using strategic timing to discover Denver's culinary gems worth returning to at full price.

## Proof of Concept Features
- Scrape Denver area restaurant websites for happy hour deals
- Extract real-time pricing and menu items
- Save directly to CSV for immediate use
- Simple command-line interface

## Tech Stack
- Python 3.x
- Requests + BeautifulSoup for web scraping
- Pure CSV storage (no database needed)
- JSON-LD structured data parsing

## Project Structure
```
sips-and-steals/
├── src/
│   ├── scrapers/           # Restaurant-specific scrapers
│   └── csv_manager.py      # Simple CSV data management
├── data/
│   └── happy_hour_deals.csv # Main data file
├── requirements.txt
├── run_scraper.py          # Main script
└── view_deals.py           # Pretty print data
```

## Usage
```bash
# Install dependencies (just 3 packages!)
pip install -r requirements.txt

# Run the scraper
python run_scraper.py

# View the data
python view_deals.py

# Open CSV directly in Excel
open data/happy_hour_deals.csv
```

## Current Data Sources
- **Jax Fish House** (LoDo) - Happy hour + weekly specials
  - Real-time pricing ($2 oysters, $8 cocktails)
  - Accurate timing (Mon all day, Tue-Sat 3-6pm, Sun 2-6pm)
  - Weekly specials (Tostada Tuesday $25, Wine Wednesday 40-50% off)

## Adding New Restaurants
1. Create new scraper in `src/scrapers/`
2. Inherit from `BaseScraper` 
3. Implement `scrape_deals()` method
4. Add to `run_scraper.py`

Simple CSV-only approach = easy to understand, modify, and share!