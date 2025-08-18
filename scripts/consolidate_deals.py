#!/usr/bin/env python3
"""
Consolidate deals data from multiple sources into a single deals.json file.
This creates a unified data structure for all scraped happy hour deals.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def consolidate_deals():
    """Merge scrapy_deals.json and happy_hour_deals.json into deals.json"""
    
    data_dir = Path('data')
    consolidated_deals = []
    
    # Process scrapy_deals.json (higher quality data)
    scrapy_file = data_dir / 'scrapy_deals.json'
    if scrapy_file.exists():
        with open(scrapy_file, 'r') as f:
            scrapy_data = json.load(f)
            for deal in scrapy_data.get('deals', []):
                # Add source metadata
                deal['source_file'] = 'scrapy_deals'
                deal['data_quality'] = 'high'
                consolidated_deals.append(deal)
        print(f"✅ Added {len(scrapy_data.get('deals', []))} deals from scrapy_deals.json")
    
    # Process happy_hour_deals.json (experimental data)
    hh_file = data_dir / 'happy_hour_deals.json'
    if hh_file.exists():
        with open(hh_file, 'r') as f:
            hh_data = json.load(f)
            # Note: happy_hour_deals.json has different structure - mainly metadata
            # The actual deals would be in a 'deals' array if present
            deals = hh_data.get('deals', [])
            for deal in deals:
                # Add source metadata  
                deal['source_file'] = 'happy_hour_deals'
                deal['data_quality'] = 'experimental'
                consolidated_deals.append(deal)
        print(f"✅ Added {len(deals)} deals from happy_hour_deals.json")
    
    # Create consolidated structure
    output_data = {
        'consolidated_at': datetime.now().isoformat(),
        'total_deals': len(consolidated_deals),
        'sources': ['scrapy_deals.json', 'happy_hour_deals.json'],
        'data_quality_levels': {
            'high': len([d for d in consolidated_deals if d.get('data_quality') == 'high']),
            'experimental': len([d for d in consolidated_deals if d.get('data_quality') == 'experimental'])
        },
        'deals': consolidated_deals
    }
    
    # Write consolidated deals
    output_file = data_dir / 'deals.json'
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print(f"\n💾 Consolidated {len(consolidated_deals)} deals → {output_file}")
    print(f"   High quality: {output_data['data_quality_levels']['high']}")
    print(f"   Experimental: {output_data['data_quality_levels']['experimental']}")
    
    return output_file


if __name__ == '__main__':
    consolidate_deals()