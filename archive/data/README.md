# Data Directory Structure

This directory contains all restaurant data and system backups for Sips and Steals.

## Core Data Files

- **`restaurants.json`** - Single source of truth containing all restaurant metadata, static deals, and scraping configuration
- **`deals.json`** - Current live scraped deals with timestamps and confidence scores

## Backup Structure

### `backups/migration/`
Critical snapshots taken during major system migrations:
- `restaurants_pre_migration_*.json` - Before converting legacy happy_hour_times to Deal objects
- `restaurants_pre_cleanup_*.json` - Before removing legacy fields

### `backups/archive/`
Recent development backups (3 most recent kept):
- `backup_YYYYMMDD_HHMMSS/` - Automatic backups created during data operations

### `deals_archive/`
Historical deal data organized by restaurant and date:
- `{restaurant-slug}_YYYYMMDD.json` - Daily snapshots of scraped deals for analysis and persistence

## Data Flow

1. **Static Data**: Restaurant metadata and fallback deals stored in `restaurants.json`
2. **Live Scraping**: Fresh deals scraped from websites → `deals.json`
3. **Archival**: Daily deal snapshots → `deals_archive/`
4. **Backups**: Automatic snapshots during operations → `backups/`

## Schema Evolution

- **Legacy**: String-based `happy_hour_times` arrays (archived)
- **Current**: Structured `static_deals` using unified Deal object schema
- **Live**: Same Deal object schema for consistency across all data sources

## Cleanup Policy

- **Migration backups**: Kept permanently for rollback capability
- **Development backups**: Keep 3 most recent, archive older ones
- **Deal archives**: Kept for historical analysis and trend tracking