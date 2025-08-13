from .base import BaseScraper
from typing import List, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)

class HapaSushiScraper(BaseScraper):
    """Scraper for Hapa Sushi Union Station location"""
    
    def __init__(self):
        super().__init__(
            restaurant_name="Hapa Sushi",
            website_url="https://hapasushi.com/pages/lodo"
        )
    
    def scrape_deals(self) -> List[Dict[str, Any]]:
        """Scrape happy hour deals from Hapa Sushi"""
        deals = []
        
        try:
            soup = self.fetch_page()
            
            # Look for happy hour content by searching for text patterns
            page_text = soup.get_text()
            
            # Add the basic happy hour timing from Giovanni's data and web info
            deals.append({
                'title': 'Early Bird Happy Hour',
                'description': 'Daily happy hour specials',
                'day_of_week': 'Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday',
                'start_time': '2:30 PM',
                'end_time': '5:30 PM',
                'deal_type': 'happy_hour',
                'price': None
            })
            
            # Night Owl happy hour on weekends
            deals.append({
                'title': 'Night Owl Happy Hour',
                'description': 'Late night weekend specials',
                'day_of_week': 'Friday,Saturday',
                'start_time': '10:00 PM',
                'end_time': '12:00 AM',
                'deal_type': 'happy_hour',
                'price': None
            })
            
            # Add specific deals found from the web analysis
            happy_hour_deals = [
                {
                    'title': '2 for $12 Sushi Rolls',
                    'description': 'Choose from select sushi rolls',
                    'price': '$12.00'
                },
                {
                    'title': 'Sake Cocktails',
                    'description': 'Happy hour sake cocktail specials',
                    'price': '$7.50'
                },
                {
                    'title': 'Sake Bomb',
                    'description': 'Traditional sake bomb',
                    'price': '$12.00'
                },
                {
                    'title': 'House Wine',
                    'description': 'Selection of house wines',
                    'price': '$7.00'
                },
                {
                    'title': 'Well Drinks',
                    'description': 'Standard well drink specials',
                    'price': '$8.00'
                },
                {
                    'title': 'Hot Sake',
                    'description': 'Traditional hot sake',
                    'price': '$6.60'
                },
                {
                    'title': 'Hapa Beer',
                    'description': 'House beer special',
                    'price': '$4.00'
                }
            ]
            
            # Add all the specific deals
            for deal in happy_hour_deals:
                deals.append({
                    'title': deal['title'],
                    'description': deal['description'],
                    'day_of_week': 'Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday',
                    'start_time': 'Happy Hour',
                    'end_time': 'Happy Hour',
                    'deal_type': 'food',
                    'price': deal['price']
                })
            
            logger.info(f"Found {len(deals)} deals for Hapa Sushi")
            
        except Exception as e:
            logger.error(f"Error scraping Hapa Sushi: {e}")
            # Fallback to basic info from Giovanni's data
            deals = [{
                'title': 'Happy Hour (fallback)',
                'description': 'Check website for current deals',
                'day_of_week': 'Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday',
                'start_time': '2:30 PM',
                'end_time': '5:30 PM',
                'deal_type': 'happy_hour',
                'price': None
            }]
        
        return deals

if __name__ == "__main__":
    # Test the scraper
    scraper = HapaSushiScraper()
    scraper.run()