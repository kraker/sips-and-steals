import pandas as pd
from datetime import datetime
from src.database import Database
import os

def export_deals_to_csv(output_path: str = None) -> str:
    """Export all deals to CSV file"""
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/happy_hour_deals_{timestamp}.csv"
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Get data from database
    db = Database()
    deals = db.get_all_deals()
    
    if not deals:
        print("No deals found in database")
        return output_path
    
    # Convert to DataFrame
    df = pd.DataFrame(deals)
    
    # Clean up column names for Excel compatibility
    df.columns = [col.replace('_', ' ').title() for col in df.columns]
    
    # Reorder columns for better readability
    column_order = [
        'Restaurant Name', 'Title', 'Description', 'Day Of Week', 
        'Start Time', 'End Time', 'Deal Type', 'Price', 'Address', 
        'Website Url', 'Scraped At'
    ]
    
    # Only include columns that exist
    available_columns = [col for col in column_order if col in df.columns]
    df = df[available_columns]
    
    # Export to CSV
    df.to_csv(output_path, index=False)
    
    print(f"Exported {len(deals)} deals to {output_path}")
    return output_path

if __name__ == "__main__":
    export_deals_to_csv()