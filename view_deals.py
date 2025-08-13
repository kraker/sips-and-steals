#!/usr/bin/env python3
"""
Pretty print the CSV data for easy viewing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.csv_manager import CSVManager
from datetime import datetime

def pretty_print_deals():
    """Pretty print the deals data"""
    csv_manager = CSVManager()
    
    if not os.path.exists(csv_manager.csv_path):
        print("❌ No CSV file found. Run the scraper first!")
        return
    
    print(f"📊 Reading deals from: {csv_manager.csv_path}")
    print("=" * 80)
    
    deals = csv_manager.get_all_deals()
    
    if not deals:
        print("❌ No deals found in CSV")
        return
    
    current_restaurant = None
    deal_count = 0
    
    for deal in deals:
        restaurant = deal['restaurant_name']
        
        # Print restaurant header when it changes
        if restaurant != current_restaurant:
            if current_restaurant is not None:
                print()  # Extra space between restaurants
            
            print(f"\n🍽️  {restaurant.upper()}")
            print("-" * 60)
            current_restaurant = restaurant
        
        deal_count += 1
        
        # Format the deal info
        title = deal['title']
        description = deal['description']
        days = deal['day_of_week']
        start_time = deal['start_time']
        end_time = deal['end_time']
        price = deal['price']
        deal_type = deal['deal_type']
        
        print(f"\n   {title}")
        
        if description:
            # Truncate long descriptions
            desc = description[:80] + "..." if len(description) > 80 else description
            print(f"   📝 {desc}")
        
        # Time info
        if start_time and end_time:
            if start_time == end_time:
                time_info = start_time
            else:
                time_info = f"{start_time} - {end_time}"
            print(f"   ⏰ {time_info}")
        
        # Days info
        if days:
            # Clean up the days display
            if "," in days:
                day_list = days.split(",")
                if len(day_list) > 3:
                    days_display = f"{day_list[0]}, {day_list[1]}...+{len(day_list)-2} more"
                else:
                    days_display = ", ".join(day_list)
            else:
                days_display = days
            print(f"   📅 {days_display}")
        
        # Price info
        if price:
            print(f"   💰 {price}")
        
        # Deal type
        if deal_type:
            emoji = "🍺" if deal_type == "happy_hour" else "🍽️"
            print(f"   {emoji} {deal_type.replace('_', ' ').title()}")
    
    print(f"\n" + "=" * 80)
    print(f"📈 Total deals found: {deal_count}")
    print(f"📅 Data file: {csv_manager.csv_path}")

if __name__ == "__main__":
    pretty_print_deals()