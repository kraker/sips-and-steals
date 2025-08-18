#!/usr/bin/env python3
"""
Data Schema Summary
Demonstrates the new consolidated data architecture (Schema v2.0)
"""

import json
from pathlib import Path
from datetime import datetime


def summarize_data_schema():
    """Generate summary of the new data schema"""
    
    data_dir = Path('data')
    
    print("🏗️ Data Schema v2.0 Summary")
    print("="*50)
    
    # Core data files
    print("\n📊 Core Data Files:")
    
    # restaurants.json
    restaurants_file = data_dir / 'restaurants.json'
    if restaurants_file.exists():
        with open(restaurants_file) as f:
            restaurant_data = json.load(f)
        total_restaurants = len(restaurant_data.get('restaurants', {}))
        districts = len(restaurant_data.get('metadata', {}).get('districts', []))
        print(f"  • restaurants.json: {total_restaurants} restaurants across {districts} districts")
    
    # deals.json (consolidated)
    deals_file = data_dir / 'deals.json'
    if deals_file.exists():
        with open(deals_file) as f:
            deals_data = json.load(f)
        total_deals = deals_data.get('total_deals', 0)
        high_quality = deals_data.get('data_quality_levels', {}).get('high', 0)
        print(f"  • deals.json: {total_deals} deals ({high_quality} high quality)")
    
    # discovered_urls.json
    urls_file = data_dir / 'discovered_urls.json'
    if urls_file.exists():
        with open(urls_file) as f:
            urls_data = json.load(f)
        total_pages = urls_data.get('total_pages', 0)
        print(f"  • discovered_urls.json: {total_pages} discovered happy hour pages")
    
    # discovered_links.json
    links_file = data_dir / 'discovered_links.json'
    if links_file.exists():
        with open(links_file) as f:
            links_data = json.load(f)
        total_links = links_data.get('total_links', 0)
        print(f"  • discovered_links.json: {total_links} total discovered links")
    
    # Directory structure
    print("\n📁 Directory Structure:")
    
    cache_dir = data_dir / 'cache'
    archives_dir = data_dir / 'archives'
    testing_dir = data_dir / 'archive' / 'testing'
    
    if cache_dir.exists():
        cache_files = list(cache_dir.glob('*.json'))
        print(f"  • data/cache/: {len(cache_files)} operational status files")
    
    if archives_dir.exists():
        archive_files = list(archives_dir.glob('*.json'))
        print(f"  • data/archives/: {len(archive_files)} historical snapshots")
    
    if testing_dir.exists():
        test_files = list(testing_dir.glob('*.json'))
        print(f"  • data/archive/testing/: {len(test_files)} archived test files")
    
    print("\n✅ Schema Migration Summary:")
    print("  • Consolidated deals from multiple sources → deals.json")
    print("  • Renamed discovered_pages.json → discovered_urls.json")
    print("  • Moved test/lodo files → archive/testing/")
    print("  • Removed redundant files (menu_pricing, scrapy_deals, etc.)")
    print("  • Created cache/ for operational files")
    print("  • Created archives/ for historical data")
    
    # File size summary
    print(f"\n💾 Data Volume:")
    total_size = 0
    for json_file in data_dir.glob('*.json'):
        size = json_file.stat().st_size
        total_size += size
        size_mb = size / (1024 * 1024)
        print(f"  • {json_file.name}: {size_mb:.1f} MB")
    
    print(f"  • Total core data: {total_size / (1024 * 1024):.1f} MB")
    
    print(f"\n📅 Schema updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    summarize_data_schema()