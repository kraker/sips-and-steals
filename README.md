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

## Quick Start

### Prerequisites
```bash
# Python 3.8+
python --version

# Install dependencies
pip install -r requirements.txt

# Install Playwright for JavaScript support
playwright install chromium
```

### Environment Setup

⚠️ **NEVER commit API keys to version control!**

```bash
# Set up Google Places API key (required for metadata)
export GOOGLE_PLACES_API_KEY='your-api-key-here'

# Test the setup
python scripts/test_google_places.py
```

### Basic Commands
```bash
# Check system status
python scripts/cli.py status

# Run deal discovery and extraction
python scripts/cli.py pipeline

# Generate website
python scripts/generate_site.py

# View dashboard (if generated)
open docs/index.html
```

## Current Coverage

- **106 Restaurants** across 11 Denver districts
- **JavaScript Extraction**: 8 dynamic content sites successfully automated
- **PDF Processing**: Automated menu extraction (Jovanina's Happy Hour PDF)
- **Multi-Format Support**: HTML scraping, JSON-LD parsing, PDF text extraction
- **Real-Time Demo**: Live LoDo dashboard with 6 premium establishments

## Three-Layer Data Architecture

```
data/
├── raw/           # Extraction artifacts & debugging data
├── refined/       # Clean, validated, normalized data
└── public/        # User-facing presentation data
```

- **Smart Deduplication**: 525 raw extractions → 60 clean deals (10:1 reduction)
- **17+ Deal Types**: Happy hour, brunch, early bird, late night, daily specials, and more
- **Quality Framework**: Confidence scoring and data quality indicators
- **Comprehensive Schema**: Full documentation in `data/README.md`

## API Security

All API keys use environment variables. **Never commit secrets to source code!**

### Google Places API Setup
1. Create API key in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Places API (New)
3. Set environment variable: `export GOOGLE_PLACES_API_KEY='your-key'`
4. Test: `python scripts/test_google_places.py`

Cost: ~$0.017 per restaurant (~$1.80 for full enrichment)

## Project Structure

```
sips-and-steals/
├── src/                   # Scrapy framework
│   ├── spiders/          # Restaurant crawlers & extractors
│   ├── pipelines.py      # Data validation & export
│   └── models/           # Data models & schemas
├── scripts/              # Utility tools & CLI
├── data/                 # Three-layer data architecture
│   ├── raw/             # Raw extraction data
│   ├── refined/         # Clean, validated data
│   └── public/          # User-facing data
├── docs/                 # Documentation & guides
│   ├── guides/          # Development guides
│   └── references/      # Technical references
└── archive/              # Legacy code preservation
```

## Tech Stack

- **Core Framework**: Scrapy 2.x with Python 3.x
- **Browser Automation**: Playwright for JavaScript-heavy sites
- **PDF Processing**: PyPDF2 for menu document extraction
- **Data Storage**: JSON-based with automated backup management
- **Frontend**: Self-contained HTML with embedded data and real-time JavaScript
- **API Integration**: Google Places API for verified business metadata

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - AI context and development guidelines
- **[data/README.md](data/README.md)** - Complete data schema documentation
- **[docs/guides/](docs/guides/)** - Style guide, UX design principles
- **[docs/references/](docs/references/)** - Google Places integration, security procedures

## Contributing

This project uses PEP 8 Python style guidelines and semantic commit messages. See [docs/guides/STYLE_GUIDE.md](docs/guides/STYLE_GUIDE.md) for details.

## License

Private project - All rights reserved
