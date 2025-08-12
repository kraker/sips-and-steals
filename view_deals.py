#!/usr/bin/env python3
"""
Pretty print the latest CSV data for easy viewing
"""

import csv
import os
from datetime import datetime

def find_latest_csv():
    """Find the most recent CSV file"""
    data_dir = "data"
    csv_files = [f for f in os.listdir(data_dir) if f.startswith("happy_hour_deals_") and f.endswith(".csv")]
    
    if not csv_files:
        return None
    
    # Sort by filename (which includes timestamp)
    csv_files.sort(reverse=True)
    return os.path.join(data_dir, csv_files[0])

def pretty_print_deals():
    """Pretty print the deals data"""
    csv_file = find_latest_csv()
    
    if not csv_file:
        print("❌ No CSV files found in data directory")
        return
    
    print(f"📊 Reading deals from: {os.path.basename(csv_file)}")
    print("=" * 80)
    
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        current_restaurant = None
        deal_count = 0
        
        for row in reader:
            restaurant = row['Restaurant Name']
            
            # Print restaurant header when it changes
            if restaurant != current_restaurant:
                if current_restaurant is not None:
                    print()  # Extra space between restaurants
                
                print(f"\n🍽️  {restaurant.upper()}")
                print("-" * 60)
                current_restaurant = restaurant
            
            deal_count += 1
            
            # Format the deal info
            title = row['Title']
            description = row['Description']
            days = row['Day Of Week']
            start_time = row['Start Time']
            end_time = row['End Time']
            price = row['Price']
            deal_type = row['Deal Type']
            
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
    print(f"📅 Last scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    pretty_print_deals()