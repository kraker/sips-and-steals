# Google Places API Setup Guide

This guide walks through setting up Google Places API integration to enhance restaurant data quality.

## Why Google Places API?

Our analysis revealed significant data quality issues:
- **91.5% of restaurants** had malformed address formats
- **25.5% missing phone numbers**
- **39.6% missing operating hours**
- **4.7% have corrupted addresses** (mixed with menu content)

Google Places API provides:
✅ **Consistent, high-quality data** - Standardized format, verified information  
✅ **Real-time accuracy** - Operating hours, business status (open/closed)  
✅ **Rich metadata** - Price levels, ratings, reviews, coordinates  
✅ **Reliable updates** - Google maintains and verifies data continuously  

## Setup Steps

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the **Places API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Places API"
   - Click "Enable"

### 2. Create API Key

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "API Key"
3. **Important**: Restrict the API key:
   - Click on the key to edit
   - Under "API restrictions", select "Restrict key"
   - Choose "Places API"
   - Under "Application restrictions", add your server IPs

### 3. Set Environment Variable

```bash
# Add to your shell profile (.bashrc, .zshrc, etc.)
export GOOGLE_PLACES_API_KEY="your_api_key_here"

# Or set for current session
export GOOGLE_PLACES_API_KEY="your_api_key_here"
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Test Run (5 restaurants)
```bash
python scripts/enrich_with_google_places.py
```

### Full Enhancement (all 106 restaurants)
```bash
# Edit the script to remove the limit=5 parameter
python scripts/enrich_with_google_places.py
```

### Fix Address Format Issues
```bash
python scripts/fix_address_format.py
```

## Cost Estimation

**Google Places API Pricing:**
- Place Search: $0.032 per request
- Place Details: $0.017 per request  
- Total per restaurant: ~$0.049

**Project Costs:**
- Initial load (106 restaurants): ~$5.20
- Monthly updates: ~$2-3
- **Total monthly cost: <$10**

## Data Enhancement

The API integration adds these fields to each restaurant:

```json
{
  "address": "1453 Larimer St, Denver, CO 80202",
  "contact_info": {
    "primary_phone": "(303) 534-5855",
    "international_phone": "+1 303-534-5855"
  },
  "operating_hours": {
    "monday": {"open": "17:00", "close": "22:00"},
    "tuesday": {"open": "17:00", "close": "22:00"}
  },
  "google_places": {
    "place_id": "ChIJ...",
    "rating": 4.5,
    "user_ratings_total": 1247,
    "price_level": 3,
    "business_status": "OPERATIONAL",
    "last_updated": "2025-08-19T..."
  },
  "coordinates": {
    "latitude": 39.7496,
    "longitude": -104.9978
  }
}
```

## Benefits for Value-Driven Culinary Adventurers

1. **Accurate operating hours** - No more arriving at closed restaurants
2. **Real business status** - Know if temporarily closed/permanently closed  
3. **Reliable contact info** - Call ahead for reservations
4. **Coordinates** - Perfect for mapping and "restaurants near me"
5. **Price levels** - Helps users find appropriate value tier
6. **Ratings** - Social proof for restaurant discovery

## Hybrid Architecture

We maintain our competitive advantage by combining:
- **Google Places API**: Reliable business metadata
- **Web Scraping**: Unique happy hour deals and specials

This gives us the best data quality while preserving our unique value proposition for spontaneous foodies seeking smart luxury experiences!