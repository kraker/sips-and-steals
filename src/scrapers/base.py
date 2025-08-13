import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import time
import logging
from src.csv_manager import CSVManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all restaurant scrapers"""
    
    def __init__(self, restaurant_name: str, website_url: str):
        self.restaurant_name = restaurant_name
        self.website_url = website_url
        self.csv_manager = CSVManager()
        self.session = requests.Session()
        # Be polite - add headers to look like a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
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
            # Scrape new deals
            deals = self.scrape_deals()
            
            # Save deals to CSV (this automatically clears old deals for this restaurant)
            self.csv_manager.add_deals(
                restaurant_name=self.restaurant_name,
                website_url=self.website_url,
                deals=deals
            )
            
            logger.info(f"Successfully scraped {len(deals)} deals for {self.restaurant_name}")
            
        except Exception as e:
            logger.error(f"Error scraping {self.restaurant_name}: {e}")
            raise
        
        finally:
            # Be polite - add a small delay
            time.sleep(1)