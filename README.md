# Sips and Steals

A web scraper that aggregates local restaurant happy hour deals and specials.

## Target User
Budget-conscious but social, tech-savvy deal hunters who make spontaneous "right now" decisions about where to grab drinks and food.

## MVP Features
- Scrape Denver area restaurant websites for happy hour deals
- Store deals in SQLite database
- Export to CSV for easy sharing and analysis
- Command-line interface for manual runs

## Tech Stack
- Python 3.x
- Requests + BeautifulSoup for web scraping
- SQLite for data storage
- Pandas for CSV export
- Schedule for automated runs

## Project Structure
```
sips-and-steals/
├── src/
│   ├── scrapers/
│   ├── database/
│   └── exporters/
├── data/
├── requirements.txt
└── README.md
```

## Usage
```bash
# Install dependencies
pip install -r requirements.txt

# Run scrapers
python -m src.scrapers.run_all

# Export to CSV
python -m src.exporters.csv_export
```