from .base import BaseScraper
from typing import List, Dict, Any
import logging
import json
import re

logger = logging.getLogger(__name__)

class JaxFishHouseScraper(BaseScraper):
    """Scraper for Jax Fish House Union Station location"""
    
    def __init__(self):
        super().__init__(
            restaurant_name="Jax Fish House",
            website_url="https://www.jaxfishhouse.com/lodo-menu/"
        )
    
    def scrape_deals(self) -> List[Dict[str, Any]]:
        """Scrape happy hour deals from Jax Fish House"""
        deals = []
        
        try:
            soup = self.fetch_page()
            
            # Look for JSON-LD structured data
            scripts = soup.find_all('script', type='application/ld+json')
            
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Look for Menu data with Happy Hour or Weekly Specials
                    if data.get('@type') == 'Menu':
                        menu_name = data.get('name', '')
                        
                        if menu_name == 'Happy Hour':
                            logger.info("Found Happy Hour menu data!")
                            self._parse_happy_hour_menu(data, deals)
                            
                        elif menu_name == 'Dinner':
                            logger.info("Found Dinner menu data - checking for weekly specials!")
                            self._parse_weekly_specials(data, deals)
                        
                except json.JSONDecodeError:
                    continue
            
            if not deals:
                # Fallback to basic info from Giovanni's data if structured data parsing fails
                deals = [{
                    'title': 'Happy Hour (fallback)',
                    'description': 'Check website for current deals',
                    'day_of_week': 'Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday',
                    'start_time': '3:30 PM',
                    'end_time': '5:00 PM',
                    'deal_type': 'happy_hour',
                    'price': None
                }]
            
            logger.info(f"Found {len(deals)} deals for Jax Fish House")
            
        except Exception as e:
            logger.error(f"Error scraping Jax Fish House: {e}")
            # Return basic info from Giovanni's data as fallback
            deals = [{
                'title': 'Happy Hour (error fallback)',
                'description': 'Check website for current deals',
                'day_of_week': 'Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday',
                'start_time': '3:30 PM',
                'end_time': '5:00 PM',
                'deal_type': 'happy_hour',
                'price': None
            }]
        
        return deals
    
    def _parse_happy_hour_menu(self, data: dict, deals: list):
        """Parse happy hour menu data"""
        # Extract happy hour times from description
        description = data.get('description', '')
        # "All Night MondayTuesday - Saturday 3pm-6pmSunday 2pm-6pm"
        
        # Parse the time information
        if 'All Night Monday' in description:
            deals.append({
                'title': 'Monday All Night Happy Hour',
                'description': 'All day happy hour specials',
                'day_of_week': 'Monday',
                'start_time': 'All Day',
                'end_time': 'All Day',
                'deal_type': 'happy_hour',
                'price': None
            })
        
        # Tuesday-Saturday 3pm-6pm
        if '3pm-6pm' in description:
            deals.append({
                'title': 'Weekday Happy Hour',
                'description': 'Happy hour specials Tuesday through Saturday',
                'day_of_week': 'Tuesday,Wednesday,Thursday,Friday,Saturday',
                'start_time': '3:00 PM',
                'end_time': '6:00 PM',
                'deal_type': 'happy_hour',
                'price': None
            })
        
        # Sunday 2pm-6pm
        if 'Sunday 2pm-6pm' in description:
            deals.append({
                'title': 'Sunday Happy Hour',
                'description': 'Sunday happy hour specials',
                'day_of_week': 'Sunday',
                'start_time': '2:00 PM',
                'end_time': '6:00 PM',
                'deal_type': 'happy_hour',
                'price': None
            })
        
        # Extract specific happy hour menu items
        menu_sections = data.get('hasMenuSection', [])
        if isinstance(menu_sections, list):
            for section in menu_sections:
                if isinstance(section, dict):
                    menu_items = section.get('hasMenuItem', [])
                    if isinstance(menu_items, list):
                        for item in menu_items[:8]:  # First 8 items to avoid too much data
                            if isinstance(item, dict):
                                name = item.get('name', '')
                                description = item.get('description', '')
                                offers = item.get('offers', {})
                                
                                price = None
                                if isinstance(offers, dict) and 'price' in offers:
                                    price = f"${offers['price']}"
                                
                                deals.append({
                                    'title': name,
                                    'description': description,
                                    'day_of_week': 'Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday',
                                    'start_time': 'Happy Hour',
                                    'end_time': 'Happy Hour',
                                    'deal_type': 'food',
                                    'price': price
                                })
    
    def _parse_weekly_specials(self, data: dict, deals: list):
        """Parse weekly specials from dinner menu data"""
        menu_sections = data.get('hasMenuSection', [])
        if isinstance(menu_sections, list):
            for section in menu_sections:
                if isinstance(section, dict):
                    section_name = section.get('name', '')
                    
                    # Look for Weekly Specials section
                    if 'weekly' in section_name.lower() or 'special' in section_name.lower():
                        logger.info(f"Found weekly specials section: {section_name}")
                        
                        menu_items = section.get('hasMenuItem', [])
                        if isinstance(menu_items, list):
                            for item in menu_items:
                                if isinstance(item, dict):
                                    name = item.get('name', '')
                                    description = item.get('description', '')
                                    offers = item.get('offers', {})
                                    
                                    price = None
                                    if isinstance(offers, dict) and 'price' in offers:
                                        price = f"${offers['price']}"
                                    
                                    # Extract day from name (like "Monday<br />All Night Happy Hour")
                                    day = self._extract_day_from_name(name)
                                    
                                    deals.append({
                                        'title': name.replace('<br />', ' - ').replace('\n', ' '),
                                        'description': description,
                                        'day_of_week': day,
                                        'start_time': self._extract_time_from_description(description),
                                        'end_time': self._extract_end_time_from_description(description),
                                        'deal_type': 'weekly_special',
                                        'price': price
                                    })
    
    def _extract_day_from_name(self, name: str) -> str:
        """Extract day of week from item name"""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days:
            if day.lower() in name.lower():
                return day
        return None
    
    def _extract_time_from_description(self, description: str) -> str:
        """Extract start time from description"""
        if '2-9pm' in description.lower():
            return '2:00 PM'
        return None
    
    def _extract_end_time_from_description(self, description: str) -> str:
        """Extract end time from description"""
        if '2-9pm' in description.lower():
            return '9:00 PM'
        return None

if __name__ == "__main__":
    # Test the scraper
    scraper = JaxFishHouseScraper()
    scraper.run()