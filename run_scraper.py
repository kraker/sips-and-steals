#!/usr/bin/env python3
"""
Simple runner script to test our scrapers and export functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.scrapers.jax_fish_house import JaxFishHouseScraper
from src.exporters.csv_export import export_deals_to_csv
from src.database import Database

def main():
    print("🍻 Sips and Steals - Happy Hour Scraper")
    print("=" * 50)
    
    # Initialize database
    db = Database()
    print("✅ Database initialized")
    
    # Run Jax Fish House scraper
    print("\n🐟 Scraping Jax Fish House...")
    jax_scraper = JaxFishHouseScraper()
    try:
        jax_scraper.run()
        print("✅ Jax Fish House scraping completed")
    except Exception as e:
        print(f"❌ Error scraping Jax Fish House: {e}")
    
    # Show what we got
    deals = db.get_all_deals()
    print(f"\n📊 Found {len(deals)} total deals in database")
    
    for deal in deals:
        print(f"  • {deal['restaurant_name']}: {deal['title']} ({deal['day_of_week']})")
    
    # Export to CSV
    print("\n📁 Exporting to CSV...")
    csv_path = export_deals_to_csv()
    print(f"✅ Exported to: {csv_path}")
    
    print("\n🎉 All done! Check the CSV file for Giovanni.")

if __name__ == "__main__":
    main()