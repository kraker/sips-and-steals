import csv
import os
from datetime import datetime
from typing import List, Dict, Any

class CSVManager:
    """Simple CSV-based data storage for happy hour deals"""
    
    def __init__(self, csv_path: str = "data/happy_hour_deals.csv"):
        self.csv_path = csv_path
        self.ensure_data_dir()
        self.ensure_csv_exists()
    
    def ensure_data_dir(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
    
    def ensure_csv_exists(self):
        """Create CSV with headers if it doesn't exist"""
        if not os.path.exists(self.csv_path):
            headers = [
                'restaurant_name',
                'title', 
                'description',
                'day_of_week',
                'start_time',
                'end_time', 
                'deal_type',
                'price',
                'website_url',
                'scraped_at'
            ]
            
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(headers)
    
    def clear_restaurant_deals(self, restaurant_name: str):
        """Remove all existing deals for a restaurant to avoid duplicates"""
        if not os.path.exists(self.csv_path):
            return
        
        # Read all rows except those for this restaurant
        rows_to_keep = []
        
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            headers = reader.fieldnames
            
            for row in reader:
                if row['restaurant_name'] != restaurant_name:
                    rows_to_keep.append(row)
        
        # Write back the filtered data
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as file:
            if headers:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows_to_keep)
    
    def add_deals(self, restaurant_name: str, website_url: str, deals: List[Dict[str, Any]]):
        """Add new deals for a restaurant"""
        # Clear existing deals for this restaurant first
        self.clear_restaurant_deals(restaurant_name)
        
        # Prepare rows for CSV
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        rows_to_add = []
        for deal in deals:
            row = {
                'restaurant_name': restaurant_name,
                'title': deal.get('title', ''),
                'description': deal.get('description', ''),
                'day_of_week': deal.get('day_of_week', ''),
                'start_time': deal.get('start_time', ''),
                'end_time': deal.get('end_time', ''),
                'deal_type': deal.get('deal_type', ''),
                'price': deal.get('price', ''),
                'website_url': website_url,
                'scraped_at': timestamp
            }
            rows_to_add.append(row)
        
        # Append new deals
        if rows_to_add:
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as file:
                # Get headers from first row
                headers = list(rows_to_add[0].keys())
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writerows(rows_to_add)
    
    def get_all_deals(self) -> List[Dict[str, Any]]:
        """Get all deals from CSV"""
        if not os.path.exists(self.csv_path):
            return []
        
        deals = []
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                deals.append(dict(row))
        
        return deals
    
    def get_deal_count(self) -> int:
        """Get total number of deals"""
        return len(self.get_all_deals())