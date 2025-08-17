#!/usr/bin/env python3
"""
Async contact extractor for batch processing multiple restaurants concurrently
Solves data loss and speed issues from sequential processing
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup

# Import our components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.data_manager import DataManager
from src.models import Restaurant, ContactInfo, ServiceInfo, DiningInfo, BusinessStatus
from src.scrapers.core.http_client import AsyncHttpClient
from src.scrapers.processors.contact_extractor import ContactExtractor
from src.scrapers.processors.text_processor import TextProcessor
from src.scrapers.exceptions import ScrapingError, TemporaryScrapingError, PermanentScrapingError

logger = logging.getLogger(__name__)


class AsyncContactExtractor:
    """Async contact extractor for concurrent processing of multiple restaurants"""
    
    def __init__(self, data_manager: DataManager, config: Dict[str, Any] = None):
        self.data_manager = data_manager
        self.config = config or {}
        
    async def extract_batch(self, restaurant_slugs: List[str], 
                          batch_size: int = 5) -> List[Dict[str, Any]]:
        """Extract contact info for multiple restaurants concurrently"""
        
        async with AsyncHttpClient(self.config) as client:
            # Use semaphore to limit concurrent requests (be polite)
            semaphore = asyncio.Semaphore(batch_size)
            
            async def extract_single(slug: str) -> Dict[str, Any]:
                async with semaphore:
                    try:
                        restaurant = self.data_manager.get_restaurant(slug)
                        if not restaurant:
                            return {
                                'slug': slug,
                                'status': 'error',
                                'error': 'Restaurant not found'
                            }
                        
                        logger.info(f"📞 Processing {restaurant.name}...")
                        
                        # Extract contact info asynchronously
                        contact_info = await self._extract_contact_async(client, restaurant)
                        
                        # Update restaurant object with extracted data
                        updated = self._update_restaurant_data(restaurant, contact_info)
                        
                        if updated:
                            # Save immediately after successful extraction
                            self.data_manager.save_single_restaurant(slug)
                            
                            logger.info(f"  ✅ Updated {restaurant.name}")
                            return {
                                'slug': slug,
                                'status': 'success',
                                'restaurant_name': restaurant.name,
                                'data_extracted': contact_info
                            }
                        else:
                            logger.info(f"  ⚪ No new data for {restaurant.name}")
                            return {
                                'slug': slug,
                                'status': 'no_changes',
                                'restaurant_name': restaurant.name
                            }
                        
                    except PermanentScrapingError as e:
                        error_reason = self._categorize_error(str(e))
                        
                        # Update failure tracking
                        if hasattr(restaurant, 'scraping_config'):
                            restaurant.scraping_config.consecutive_failures += 1
                            restaurant.scraping_config.last_failure_reason = error_reason
                        
                        logger.warning(f"  ❌ Permanent failure for {restaurant.name}: {e}")
                        return {
                            'slug': slug,
                            'status': 'permanent_error',
                            'restaurant_name': restaurant.name,
                            'error': str(e),
                            'error_type': error_reason
                        }
                        
                    except TemporaryScrapingError as e:
                        error_reason = self._categorize_error(str(e))
                        
                        # Update failure tracking
                        if hasattr(restaurant, 'scraping_config'):
                            restaurant.scraping_config.consecutive_failures += 1
                            restaurant.scraping_config.last_failure_reason = error_reason
                        
                        logger.warning(f"  ⚠️  Temporary failure for {restaurant.name}: {e}")
                        return {
                            'slug': slug,
                            'status': 'temporary_error',
                            'restaurant_name': restaurant.name,
                            'error': str(e),
                            'error_type': error_reason
                        }
                        
                    except Exception as e:
                        logger.error(f"  ❌ Unexpected error for {restaurant.name}: {e}")
                        return {
                            'slug': slug,
                            'status': 'error',
                            'restaurant_name': restaurant.name,
                            'error': str(e)
                        }
                    finally:
                        # Polite delay between requests
                        await asyncio.sleep(0.5)
            
            # Process all restaurants concurrently
            logger.info(f"🚀 Processing {len(restaurant_slugs)} restaurants with {batch_size} workers...")
            
            tasks = [extract_single(slug) for slug in restaurant_slugs]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process any exceptions that weren't handled
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    slug = restaurant_slugs[i]
                    restaurant = self.data_manager.get_restaurant(slug)
                    name = restaurant.name if restaurant else slug
                    
                    logger.error(f"Unhandled exception for {name}: {result}")
                    processed_results.append({
                        'slug': slug,
                        'status': 'exception',
                        'restaurant_name': name,
                        'error': str(result)
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
    
    async def _extract_contact_async(self, client: AsyncHttpClient, restaurant: Restaurant) -> Dict[str, Any]:
        """Extract contact information asynchronously"""
        
        # Determine URL to scrape
        if hasattr(restaurant, 'scraping_urls') and restaurant.scraping_urls:
            url = restaurant.scraping_urls[0]  # Use first URL for contact extraction
        else:
            url = restaurant.website
        
        if not url:
            raise PermanentScrapingError("No URL available for scraping")
        
        # Fetch page content
        response = await client.fetch_url(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text()
        
        # Initialize contact extractor
        contact_extractor = ContactExtractor(base_url=url)
        
        extracted_data = {
            'contact_info': {},
            'service_info': {},
            'dining_info': {},
            'operating_hours': {},
            'business_status': 'operational',
            'last_updated': datetime.now().isoformat()
        }
        
        # Extract comprehensive contact information
        contact_info = contact_extractor.extract_contact_info(soup, text_content)
        if contact_info:
            extracted_data['contact_info'] = contact_info.to_dict()
        
        # Extract service information
        service_info = contact_extractor.extract_service_info(soup, text_content)
        if service_info:
            extracted_data['service_info'] = service_info.to_dict()
        
        # Extract dining experience information
        dining_info = contact_extractor.extract_dining_info(soup, text_content)
        if dining_info:
            extracted_data['dining_info'] = dining_info.to_dict()
        
        # Extract operating hours
        operating_hours = contact_extractor.extract_operating_hours(soup, text_content)
        if operating_hours:
            extracted_data['operating_hours'] = operating_hours
        
        return extracted_data
    
    def _update_restaurant_data(self, restaurant: Restaurant, extracted_data: Dict[str, Any]) -> bool:
        """Update restaurant object with extracted data, return True if changes made"""
        updated = False
        
        # Update contact info
        if extracted_data.get('contact_info'):
            contact_info_dict = extracted_data['contact_info']
            
            # Update phone if missing or improve existing
            if contact_info_dict.get('primary_phone') and not restaurant.phone:
                restaurant.phone = contact_info_dict['primary_phone']
                updated = True
            
            # Update contact info object
            if hasattr(restaurant, 'contact_info') and restaurant.contact_info:
                # Update existing contact info
                for key, value in contact_info_dict.items():
                    if value and hasattr(restaurant.contact_info, key):
                        current_value = getattr(restaurant.contact_info, key)
                        if current_value != value:
                            setattr(restaurant.contact_info, key, value)
                            updated = True
            else:
                # Create new contact info object
                restaurant.contact_info = ContactInfo(
                    primary_phone=contact_info_dict.get('primary_phone'),
                    reservation_phone=contact_info_dict.get('reservation_phone'),
                    general_email=contact_info_dict.get('general_email'),
                    reservations_email=contact_info_dict.get('reservations_email'),
                    events_email=contact_info_dict.get('events_email'),
                    instagram=contact_info_dict.get('instagram'),
                    facebook=contact_info_dict.get('facebook'),
                    twitter=contact_info_dict.get('twitter'),
                    tiktok=contact_info_dict.get('tiktok')
                )
                updated = True
        
        # Update operating hours
        if extracted_data.get('operating_hours'):
            restaurant.operating_hours = extracted_data['operating_hours']
            updated = True
        
        # Update service info
        if extracted_data.get('service_info'):
            service_info_dict = extracted_data['service_info']
            restaurant.service_info = ServiceInfo(
                accepts_reservations=service_info_dict.get('accepts_reservations', False),
                offers_delivery=service_info_dict.get('offers_delivery', False),
                offers_takeout=service_info_dict.get('offers_takeout', False),
                offers_curbside=service_info_dict.get('offers_curbside', False),
                opentable_url=service_info_dict.get('opentable_url'),
                resy_url=service_info_dict.get('resy_url'),
                direct_reservation_url=service_info_dict.get('direct_reservation_url'),
                doordash_url=service_info_dict.get('doordash_url'),
                ubereats_url=service_info_dict.get('ubereats_url'),
                grubhub_url=service_info_dict.get('grubhub_url')
            )
            updated = True
        
        # Update dining info
        if extracted_data.get('dining_info'):
            dining_info_dict = extracted_data['dining_info']
            restaurant.dining_info = DiningInfo(
                price_range=dining_info_dict.get('price_range'),
                dress_code=dining_info_dict.get('dress_code'),
                atmosphere=dining_info_dict.get('atmosphere', []),
                dining_style=dining_info_dict.get('dining_style'),
                total_seats=dining_info_dict.get('total_seats'),
                bar_seats=dining_info_dict.get('bar_seats'),
                outdoor_seats=dining_info_dict.get('outdoor_seats')
            )
            updated = True
        
        if updated:
            restaurant.last_updated = datetime.now()
            # Update scraping success tracking
            if hasattr(restaurant, 'scraping_config'):
                restaurant.scraping_config.last_scraped = datetime.now()
                restaurant.scraping_config.last_success = datetime.now()
                restaurant.scraping_config.consecutive_failures = 0
                restaurant.scraping_config.last_failure_reason = None
        
        return updated
    
    def _categorize_error(self, error_str: str) -> str:
        """Categorize error for tracking purposes"""
        error_str_lower = error_str.lower()
        
        if "robots.txt" in error_str_lower:
            return "robots_txt"
        elif "timeout" in error_str_lower:
            return "timeout"
        elif "404" in error_str_lower or "not found" in error_str_lower:
            return "not_found"
        elif "no valid content" in error_str_lower:
            return "no_content"
        elif "connection" in error_str_lower:
            return "connection_error"
        else:
            return "unknown"