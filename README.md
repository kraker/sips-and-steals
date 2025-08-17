# Sips and Steals

An intelligent restaurant deal discovery platform that aggregates and curates Denver's best happy hour offerings through automated web scraping and smart data consolidation.

🌐 **Live Site**: [Sips and Steals](https://kraker.github.io/sips-and-steals/)

## Target User

**The Discerning Urban Explorer** - sophisticated food and beverage enthusiasts who view happy hour as smart luxury, not budget dining. They seek expertly crafted cocktails and elevated cuisine at accessible prices, using strategic timing to discover Denver's culinary gems worth returning to at full price.

## Key Features

### 🤖 **Intelligent Scraping System**
- **Live Deal Extraction**: Automated scraping of 106 Denver restaurants across 11 districts
- **Config-Based Architecture**: YAML-driven scraper configurations for rapid restaurant onboarding
- **Quality Validation**: Confidence scoring and deal validation with automatic data quality checks
- **Robots.txt Compliance**: Respectful scraping with built-in robots.txt checking and circuit breakers

### 📊 **Data Management**
- **Single Source Architecture**: `restaurants.json` as unified restaurant metadata and static deal storage
- **Live Data Integration**: Real-time deal aggregation with 3-tier fallback system (live → cached → static)
- **Historical Archives**: Automated daily deal archiving for trend analysis and data persistence
- **Smart Backups**: Automatic backup management during data operations

### 🌐 **Enhanced Website Generation**
- **Multi-Page Static Site**: Responsive website with individual restaurant profiles
- **Live Data Indicators**: Clear distinction between live scraped and static data with confidence badges
- **Advanced Filtering**: Filter by day, district, neighborhood, and cuisine with dynamic neighborhood updates
- **Time-Based Relevance**: Smart deal scoring based on current time and day of week

### 🔧 **Developer Experience**
- **Modular Architecture**: Separated concerns with specialized processors and managers
- **CLI Interface**: Full-featured command-line tool for scraping, quality analysis, and data export
- **Comprehensive Logging**: Detailed logging with performance metrics and error tracking

## Current Coverage

- **106 Restaurants** across 11 Denver districts
- **37 Restaurants** with live deal data (34.9% coverage)
- **4 Working Northwest Denver Scrapers** (American Elm, Bamboo Sushi, Wild Taco, Kumoya)
- **Confidence-Scored Deals** with source URL tracking

## Tech Stack

- **Backend**: Python 3.x with requests, BeautifulSoup4, and Jinja2
- **Data**: JSON-based storage with automatic backup management
- **Frontend**: Static HTML/CSS/JS generated from Jinja2 templates
- **Deployment**: GitHub Pages with automated builds
- **Architecture**: Config-driven scrapers with modular processing pipeline

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run scraping system for Central district
python scraper_cli.py scrape --district "Central" --workers 2

# Generate static website
python generate_site.py

# View system status
python scraper_cli.py status

# Export quality analysis
python scraper_cli.py quality --export
```

## Project Structure

```
sips-and-steals/
├── src/
│   ├── scrapers/              # Modular scraping system
│   │   ├── core/             # Base classes and HTTP client
│   │   ├── processors/       # Text and post-processing
│   │   └── exceptions.py     # Custom error handling
│   ├── config_manager.py     # YAML configuration management
│   ├── data_manager.py       # JSON data operations
│   └── scheduler.py          # Concurrent scraping orchestration
├── config/scrapers/          # YAML scraper configurations
├── data/
│   ├── restaurants.json      # Master restaurant database
│   ├── deals.json           # Current live deals
│   ├── deals_archive/       # Historical deal snapshots
│   └── backups/             # Automatic data backups
├── docs/                    # Generated static website
│   ├── restaurants/         # Individual restaurant pages
│   └── index.html          # Main directory
├── templates/               # Jinja2 website templates
├── scraper_cli.py          # Command-line interface
├── generate_site.py        # Website generation
└── models.py               # Data models and validation
```

## Adding New Restaurants

### Method 1: Config-Based (Recommended)
```yaml
# config/scrapers/restaurant-name.yaml
restaurant_name: "Restaurant Name"
scraper_type: "config_based"
enabled: true
urls:
  - "https://restaurant.com/happy-hour"

scraping_patterns:
  time_patterns:
    - pattern: "Monday - Friday: (\\d{1,2}[ap]m) - (\\d{1,2}[ap]m)"
      groups: [start_time, end_time]
      confidence: 0.9
  
  day_patterns:
    - pattern: "(Monday - Friday)"
      groups: [days]
      confidence: 0.9
```

### Method 2: Custom Scraper
```python
# src/scrapers/restaurant_name.py
from .core.base import BaseScraper

class RestaurantNameScraper(BaseScraper):
    def scrape_deals(self) -> List[Deal]:
        content = self.fetch_page()
        # Custom scraping logic
        return deals
```

## Recent Improvements

- **Enhanced Northwest Denver Coverage**: Fixed American Elm and Bamboo Sushi scrapers
- **Data Quality**: Added source URL tracking and improved text spacing
- **Robots.txt Compliance**: Added blocking status tracking for 5 restaurants
- **UI/UX**: Improved time indicators and deal status badges
- **Performance**: Concurrent scraping with configurable worker pools

## Contributing

1. Add restaurant to `data/restaurants.json`
2. Create scraper config in `config/scrapers/` or custom scraper in `src/scrapers/`
3. Test with `python scraper_cli.py scrape --restaurant "restaurant-slug"`
4. Generate site with `python generate_site.py`

## License

MIT License - see LICENSE file for details.