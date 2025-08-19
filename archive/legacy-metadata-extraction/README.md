# Legacy Metadata Extraction Code

This directory contains the original metadata extraction functionality that was made redundant by Google Places API integration.

## Archived Files

- `restaurant_profiler.py` - Original comprehensive restaurant profiler with metadata extraction

## Why Archived

Google Places API now provides superior data quality for:
- ✅ Addresses (100% coverage vs ~50% scraping accuracy)
- ✅ Phone numbers (99.1% coverage vs ~75% scraping accuracy)  
- ✅ Operating hours (99.1% coverage vs ~60% scraping accuracy)
- ✅ Business status (100% coverage vs unreliable detection)
- ✅ Coordinates (100% coverage vs 0% from scraping)
- ✅ Ratings (100% coverage vs not available from scraping)

## Code Complexity Removed

- ~621 lines of complex regex and parsing logic
- Address extraction with pattern matching
- Phone number normalization and validation
- Operating hours parsing from various formats
- Business status detection from content analysis

## New Architecture

Scrapers now focus exclusively on unique content:
- Happy hour deals and promotions
- Menu pricing information
- Special events and seasonal offers
- Reservation service links
- Atmosphere keywords

This provides a cleaner, more maintainable codebase where Google handles verified metadata and scrapers extract unique deal content.

## Cost Comparison

- Google Places API: $3.60 for 106 restaurants with 99%+ accuracy
- Metadata scraping: Hours of debugging complex parsing logic with 50-75% accuracy

The ROI strongly favors the API approach for metadata while preserving scraper value for unique content extraction.