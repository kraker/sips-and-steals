import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import time
import logging
from src.database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all restaurant scrapers"""
    
    def __init__(self, restaurant_name: str, website_url: str):
        self.restaurant_name = restaurant_name
        self.website_url = website_url
        self.db = Database()
        self.session = requests.Session()
        # Be polite - add headers to look like a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_or_create_restaurant(self) -> int:
        """Get restaurant ID or create new restaurant record"""
        restaurant = self.db.get_restaurant_by_name(self.restaurant_name)
        if restaurant:
            return restaurant['id']
        else:
            return self.db.add_restaurant(
                name=self.restaurant_name,
                website_url=self.website_url
            )
    
    def fetch_page(self, url: str = None) -> BeautifulSoup:
        """Fetch and parse a webpage"""
        url = url or self.website_url
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            raise
    
    @abstractmethod
    def scrape_deals(self) -> List[Dict[str, Any]]:
        """
        Scrape deals from the restaurant website.
        Should return a list of dictionaries with keys:
        - title: str
        - description: str (optional)
        - day_of_week: str (optional)
        - start_time: str (optional)
        - end_time: str (optional)
        - deal_type: str ('happy_hour', 'daily_special', 'food', 'drink')
        - price: str (optional)
        """
        pass
    
    def run(self):
        """Main method to run the scraper"""
        logger.info(f"Starting scrape for {self.restaurant_name}")
        
        try:
            # Get or create restaurant record
            restaurant_id = self.get_or_create_restaurant()
            
            # Clear old deals for fresh data
            self.db.clear_restaurant_deals(restaurant_id)
            
            # Scrape new deals
            deals = self.scrape_deals()
            
            # Save deals to database
            for deal in deals:
                self.db.add_deal(
                    restaurant_id=restaurant_id,
                    title=deal.get('title', ''),
                    description=deal.get('description'),
                    day_of_week=deal.get('day_of_week'),
                    start_time=deal.get('start_time'),
                    end_time=deal.get('end_time'),
                    deal_type=deal.get('deal_type', 'happy_hour'),
                    price=deal.get('price')
                )
            
            logger.info(f"Successfully scraped {len(deals)} deals for {self.restaurant_name}")
            
        except Exception as e:
            logger.error(f"Error scraping {self.restaurant_name}: {e}")
            raise
        
        finally:
            # Be polite - add a small delay
            time.sleep(1)