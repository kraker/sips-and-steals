#!/usr/bin/env python3
"""
Simple runner script for Sips and Steals happy hour scraper
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.scrapers.jax_fish_house import JaxFishHouseScraper
from src.scrapers.hapa_sushi import HapaSushiScraper
from src.scrapers.tamayo import TamayoScraper
from src.csv_manager import CSVManager

def main():
    print("🍻 Sips and Steals - Happy Hour Scraper (Proof of Concept)")
    print("=" * 60)
    print("Scraping Denver Union Station area restaurants...")
    
    # Initialize CSV manager
    csv_manager = CSVManager()
    print("✅ CSV storage initialized")
    
    # List of scrapers to run
    scrapers = [
        ("🐟", "Jax Fish House", JaxFishHouseScraper),
        ("🍣", "Hapa Sushi", HapaSushiScraper),
        ("🌮", "Tamayo", TamayoScraper)
    ]
    
    # Run all scrapers
    for emoji, name, scraper_class in scrapers:
        print(f"\n{emoji} Scraping {name}...")
        scraper = scraper_class()
        try:
            scraper.run()
            print(f"✅ {name} scraping completed")
        except Exception as e:
            print(f"❌ Error scraping {name}: {e}")
    
    # Show what we got
    deals = csv_manager.get_all_deals()
    print(f"\n📊 Found {len(deals)} total deals")
    
    # Group deals by restaurant for better display
    restaurants = {}
    for deal in deals:
        restaurant = deal['restaurant_name']
        if restaurant not in restaurants:
            restaurants[restaurant] = []
        restaurants[restaurant].append(deal)
    
    for restaurant, restaurant_deals in restaurants.items():
        print(f"\n  📍 {restaurant} ({len(restaurant_deals)} deals)")
        for deal in restaurant_deals[:3]:  # Show first 3 deals
            print(f"    • {deal['title']} ({deal['day_of_week']})")
        if len(restaurant_deals) > 3:
            print(f"    ... and {len(restaurant_deals) - 3} more")
    
    print(f"\n📁 Data saved to: {csv_manager.csv_path}")
    print("🎉 Ready to share with Giovanni - he can open the CSV directly in Excel!")

if __name__ == "__main__":
    main()