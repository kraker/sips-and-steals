# Sips and Steals

An advanced restaurant data mining platform powered by Scrapy that discovers and aggregates Denver's premium happy hour offerings through intelligent web scraping and real-time status detection.

🌐 **Live Demo**: [LoDo Happy Hours](https://kraker.github.io/sips-and-steals/) - Interactive dashboard showcasing Lower Downtown restaurants

## Target User

**The Value-Driven Culinary Adventurer** - spontaneous foodies who seek authentic culinary experiences and "smart luxury" through strategic timing. They're passionate about exploring Denver's diverse food scene, using happy hour to access premium experiences and discover both accessible gems and elevated cuisine. They make on-the-go dining decisions based on current deals that offer maximum experience value.

## Key Features

### 🕷️ **Scrapy-Powered Data Mining**
- **Enterprise-Grade Framework**: Production-ready Scrapy spiders with respectful crawling
- **JavaScript Support**: Playwright integration for dynamic content sites (Urban Farmer, Ginger Pig, etc.)
- **Multi-Format Processing**: HTML, PDF, and JSON-LD structured data extraction
- **106 Restaurants**: Comprehensive coverage across 11 Denver districts
- **Quality Validation**: Confidence scoring and automated data validation pipelines

### 🌟 **Google Places API Integration** ✅ *COMPLETED*
- **Perfect Data Quality**: 99-100% coverage for addresses, phones, hours, and business status
- **Cost-Effective Success**: $3.60 for 106 restaurants vs hours of debugging scraping logic
- **Smart Hybrid Architecture**: Google's verified metadata + focused deal extraction
- **Real-Time Business Data**: Operational status, ratings, and precise geocoding
- **Architectural Cleanup**: Removed 1,857+ lines of redundant metadata extraction code

### 📊 **Intelligent Data Architecture**
- **Discovery Pipeline**: Automated happy hour page discovery and content analysis
- **Real-Time Processing**: Live deal extraction with timestamp tracking and archival
- **Smart Fallback**: 3-tier data prioritization (fresh live → cached live → static)
- **Historical Archives**: Automated deal snapshots for trend analysis
- **Backup Management**: Comprehensive data protection and recovery systems

### 🎯 **Live Dashboard Experience**
- **Real-Time Status**: 🟢 Active Now, 🟡 Starting Soon, 🔴 Closed indicators
- **Time Intelligence**: Current time awareness with "starts in X minutes" alerts
- **Contact Integration**: One-click calling, reservations, directions, website access
- **Mobile-Responsive**: Touch-optimized interface for on-the-go discovery
- **Smart Filtering**: Filter by active status, upcoming deals, or browse all

### 🛠️ **Developer Experience**
- **Modular CLI**: Comprehensive command-line interface for all operations
- **Scrapy Integration**: Direct spider execution with `python -m scrapy crawl`
- **Data Enhancement**: Contact enrichment, time parsing, and URL discovery tools
- **Quality Analysis**: Coverage metrics, extraction success rates, and performance monitoring

## Current Coverage

- **106 Restaurants** across 11 Denver districts
- **JavaScript Extraction**: 8 dynamic content sites successfully automated
- **PDF Processing**: Automated menu extraction (Jovanina's Happy Hour PDF)
- **Multi-Format Support**: HTML scraping, JSON-LD parsing, PDF text extraction
- **Real-Time Demo**: Live LoDo dashboard with 6 premium establishments

## Tech Stack

- **Core Framework**: Scrapy 2.x with Python 3.x
- **Browser Automation**: Playwright for JavaScript-heavy sites
- **PDF Processing**: PyPDF2 for menu document extraction
- **Data Storage**: JSON-based with automated backup management
- **Frontend**: Self-contained HTML with embedded data and real-time JavaScript
- **Deployment**: GitHub Pages for public demonstration

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium  # Required for JavaScript support

# System status and monitoring
python scripts/cli.py status

# Run full discovery and extraction pipeline
python scripts/cli.py comprehensive

# Core operations
python scripts/cli.py discover                   # Discover happy hour pages
python scripts/cli.py extract                    # Extract deals from pages
python scripts/cli.py profile                    # Extract restaurant profiles
python scripts/cli.py pipeline                   # Discovery + extraction (deals only)
python scripts/cli.py analyze                    # Analyze extraction results
python scripts/cli.py pricing                    # Extract menu pricing data

# Data utilities (unified CLI interface)
python scripts/cli.py enrich                     # Add contact information
python scripts/cli.py fix-times                  # Clean time parsing issues
python scripts/cli.py fix-urls                   # Discover and fix broken URLs
python scripts/cli.py district                   # Generate district reports
python scripts/cli.py schema                     # Show data architecture
python scripts/cli.py profiles                   # Generate restaurant profiles

# Google Places API integration (enhanced data quality)
python scripts/cli.py fix-addresses              # Fix malformed address formats
python scripts/cli.py google-enrich              # Enrich with Google Places API data
python scripts/cli.py google-update daily        # Update business status & hours
python scripts/cli.py google-update weekly       # Update contact info & hours
python scripts/cli.py google-update monthly      # Update ratings & metadata
python scripts/cli.py google-update report       # Show data quality report

# Direct Scrapy execution (advanced)
python -m scrapy list                            # List available spiders
python -m scrapy crawl discovery                 # Run discovery spider
python -m scrapy crawl happy_hour_deals          # Extract happy hour deals
```

## Project Structure

```
sips-and-steals/
├── src/                      # Main Scrapy framework
│   ├── spiders/             # Restaurant crawlers and extractors
│   │   ├── discovery.py     # Happy hour page discovery
│   │   ├── happy_hour_deals.py  # Deal extraction
│   │   └── restaurant_profiler.py  # Profile extraction
│   ├── pipelines.py         # Data validation and processing
│   ├── items.py            # Data models and structures
│   └── settings.py         # Scrapy configuration
├── scripts/                 # Utility tools and unified CLI
│   ├── cli.py              # Main command interface (all operations)
│   ├── enrich_data.py      # Contact data enhancement
│   ├── fix_times.py        # Time parsing cleanup
│   ├── fix_urls.py         # URL discovery and repair
│   ├── district_analysis.py # District-level analysis
│   ├── data_schema_summary.py # Data architecture documentation
│   └── restaurant_profiles.py # Individual restaurant profiles
├── config/scrapers/         # YAML scraper configurations
├── data/
│   ├── restaurants.json     # Master restaurant database
│   ├── deals.json          # Current live deals
│   └── archives/           # Historical deal snapshots
├── docs/                   # GitHub Pages public demo
│   ├── index.html          # Interactive LoDo dashboard
│   └── assets/             # CSS, JS, and embedded data
├── archive/                # Preserved legacy systems
│   ├── src/                # Original scraper architecture
│   ├── site-generation/    # Previous Jinja2 site generator
│   ├── scripts/            # One-time migration/demo scripts
│   └── data/               # Historical data archives
└── scrapy.cfg              # Scrapy project configuration
```

## Adding New Restaurants

### Method 1: YAML Configuration (Recommended)
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
```

### Method 2: Custom Scrapy Spider
```python
# src/spiders/restaurant_name.py
from scrapy import Spider
from ..items import HappyHourDeal

class RestaurantNameSpider(Spider):
    name = 'restaurant_name'
    
    def parse(self, response):
        # Custom extraction logic
        yield HappyHourDeal(
            title=deal_title,
            description=deal_description,
            # ... other fields
        )
```

### Method 3: Add to Restaurant Database
```bash
# Add restaurant to data/restaurants.json
# Test extraction
python scripts/cli.py extract --restaurant "restaurant-slug"
```

## Recent Milestones

### 🏗️ **Milestone 5: Repository Reorganization** (August 18, 2025)
- **Scrapy-First Architecture**: Promoted Scrapy to primary framework (`src/`)
- **Public Demo**: Created interactive LoDo dashboard for GitHub Pages
- **Legacy Preservation**: Archived all original systems while maintaining clean structure
- **Professional Organization**: Implemented concise, consistent naming conventions

### 🚀 **Milestone 4: JavaScript & Advanced Discovery** (August 17, 2025)
- **Browser Automation**: Playwright integration for dynamic content sites
- **URL Discovery**: Automated restaurant URL repair and discovery
- **Coverage Breakthrough**: Achieved 44.3% live data coverage

### 🎯 **Previous Milestones**: Production platform, enhanced data architecture, and proof of concept
- See [CLAUDE.md](CLAUDE.md) for complete milestone history and technical details

## Contributing

1. **Add Restaurant**: Update `data/restaurants.json` with restaurant metadata
2. **Configure Scraper**: Create YAML config in `config/scrapers/` or custom spider in `src/spiders/`
3. **Test Extraction**: Run `python scripts/cli.py extract --restaurant "restaurant-slug"`
4. **Validate Quality**: Use `python scripts/cli.py analyze` for quality metrics

## Public Demo

Visit our **[Live LoDo Dashboard](https://kraker.github.io/sips-and-steals/)** to see the platform in action:
- Real-time happy hour status detection
- Interactive restaurant filtering
- Mobile-responsive design
- One-click contact integration

## License

MIT License - see LICENSE file for details.