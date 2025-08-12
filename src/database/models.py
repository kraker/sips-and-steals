import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path: str = "data/sips_and_steals.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS restaurants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    website_url TEXT,
                    address TEXT,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    restaurant_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    day_of_week TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    deal_type TEXT,  -- 'happy_hour', 'daily_special', 'food', 'drink'
                    price TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
                )
            """)
            
            conn.commit()
    
    def add_restaurant(self, name: str, website_url: str = None, 
                      address: str = None, phone: str = None) -> int:
        """Add a new restaurant and return its ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO restaurants (name, website_url, address, phone)
                VALUES (?, ?, ?, ?)
            """, (name, website_url, address, phone))
            return cursor.lastrowid
    
    def add_deal(self, restaurant_id: int, title: str, description: str = None,
                day_of_week: str = None, start_time: str = None, end_time: str = None,
                deal_type: str = "happy_hour", price: str = None) -> int:
        """Add a new deal and return its ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO deals (restaurant_id, title, description, day_of_week, 
                                 start_time, end_time, deal_type, price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (restaurant_id, title, description, day_of_week, 
                  start_time, end_time, deal_type, price))
            return cursor.lastrowid
    
    def get_all_deals(self) -> List[Dict[str, Any]]:
        """Get all active deals with restaurant information"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    r.name as restaurant_name,
                    r.address,
                    r.website_url,
                    d.title,
                    d.description,
                    d.day_of_week,
                    d.start_time,
                    d.end_time,
                    d.deal_type,
                    d.price,
                    d.scraped_at
                FROM deals d
                JOIN restaurants r ON d.restaurant_id = r.id
                WHERE d.is_active = TRUE
                ORDER BY r.name, d.day_of_week, d.start_time
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def clear_restaurant_deals(self, restaurant_id: int):
        """Mark all deals for a restaurant as inactive (for fresh scraping)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE deals SET is_active = FALSE 
                WHERE restaurant_id = ?
            """, (restaurant_id,))
            conn.commit()
    
    def get_restaurant_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get restaurant by name"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM restaurants WHERE name = ?
            """, (name,))
            row = cursor.fetchone()
            return dict(row) if row else None