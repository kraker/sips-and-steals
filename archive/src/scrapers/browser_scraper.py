#!/usr/bin/env python3
"""
Browser-Based Scraper with JavaScript Support

Uses Playwright to handle websites with dynamic content loading, JavaScript
interactions, and modern web application patterns.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup

from models import Restaurant, Deal
from .core.base import BaseScraper
from .universal_extractor import UniversalHappyHourExtractor

logger = logging.getLogger(__name__)


class BrowserScraper(BaseScraper):
    """
    Browser-based scraper using Playwright for JavaScript-enabled websites.
    
    Handles modern web applications with dynamic content loading, AJAX calls,
    and JavaScript-based navigation.
    """
    
    def __init__(self, restaurant: Restaurant, headless: bool = True, timeout: int = 30000):
        super().__init__(restaurant)
        self.extractor = UniversalHappyHourExtractor()
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        logger.info(f"Initialized browser scraper for {restaurant.name}")
    
    def scrape_deals(self) -> List[Deal]:
        """
        Scrape deals using browser automation with JavaScript support.
        
        Returns:
            List of Deal objects found using browser-based extraction
        """
        website = self.restaurant.website
        if not website:
            logger.warning(f"No website available for {self.restaurant.name}")
            return []
        
        try:
            # Run async scraping in sync context
            return asyncio.run(self._scrape_deals_async(website))
        except Exception as e:
            logger.error(f"Error in browser scraping for {self.restaurant.name}: {e}")
            return []
    
    async def _scrape_deals_async(self, website: str) -> List[Deal]:
        """Async implementation of deal scraping"""
        async with async_playwright() as playwright:
            # Launch browser
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            )
            
            try:
                # Create context with optimizations
                self.context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (compatible; SipsAndSteals/1.0; +https://sips-and-steals.com)',
                    java_script_enabled=True,
                    # Block unnecessary resources for speed
                    bypass_csp=True
                )
                
                # Block images, fonts, and other non-essential resources
                await self.context.route('**/*', self._route_handler)
                
                page = await self.context.new_page()
                
                # Set page timeout
                page.set_default_timeout(self.timeout)
                
                # Navigate to the website
                logger.info(f"Navigating to {website} with browser automation")
                await page.goto(website, wait_until='domcontentloaded')
                
                # Handle potential JavaScript-based navigation or content loading
                deals = await self._extract_deals_from_page(page, website)
                
                return deals
                
            finally:
                if self.context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()
    
    async def _route_handler(self, route):
        """Route handler to block unnecessary resources for performance"""
        request = route.request
        resource_type = request.resource_type
        
        # Block images, fonts, stylesheets for faster loading
        if resource_type in ['image', 'font', 'stylesheet', 'media']:
            await route.abort()
        else:
            await route.continue_()
    
    async def _extract_deals_from_page(self, page: Page, url: str) -> List[Deal]:
        """
        Extract deals from a JavaScript-rendered page.
        
        Args:
            page: Playwright page object
            url: Source URL
            
        Returns:
            List of extracted deals
        """
        deals = []
        
        try:
            # Wait for potential dynamic content to load
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Check for specific JavaScript interactions (like STK's dropdown)
            await self._handle_special_interactions(page)
            
            # Get the fully rendered HTML
            html_content = await page.content()
            
            # Use BeautifulSoup and our universal extractor
            soup = BeautifulSoup(html_content, 'html.parser')
            result = self.extractor.extract_from_soup(soup, url)
            
            logger.info(f"Browser extraction found {len(result.deals)} deals for {self.restaurant.name} "
                       f"(confidence: {result.confidence_score:.2f})")
            
            return result.deals
            
        except Exception as e:
            logger.warning(f"Error extracting deals from page {url}: {e}")
            return []
    
    async def _handle_special_interactions(self, page: Page):
        """
        Handle special JavaScript interactions for specific restaurant types.
        
        Args:
            page: Playwright page object
        """
        try:
            # STK-specific: Handle location dropdown
            if 'stksteakhouse.com' in page.url:
                await self._handle_stk_location_dropdown(page)
            
            # Add other restaurant-specific interactions here
            # elif 'other-restaurant.com' in page.url:
            #     await self._handle_other_restaurant_interactions(page)
            
        except Exception as e:
            logger.warning(f"Error handling special interactions: {e}")
    
    async def _handle_stk_location_dropdown(self, page: Page):
        """Handle STK's location dropdown interaction"""
        try:
            logger.info("Handling STK location dropdown")
            
            # Wait for the location dropdown to be available
            location_selector = 'select[name="location"]'
            await page.wait_for_selector(location_selector, timeout=5000)
            
            # Select Denver location (value might be different, need to check)
            # This value was mentioned in our roadmap research
            await page.select_option(location_selector, value='699')  # Denver location ID
            
            # Wait for content to update after selection
            await page.wait_for_timeout(2000)
            
            logger.info("Successfully selected Denver location for STK")
            
        except Exception as e:
            logger.warning(f"Could not handle STK location dropdown: {e}")
    
    def get_scraper_info(self) -> dict:
        """Get information about this scraper"""
        return {
            'type': 'browser',
            'description': 'JavaScript-enabled browser scraper using Playwright',
            'requires_config': False,
            'supports_js': True,
            'supports_pdf': False,
            'extraction_methods': [
                'javascript_execution',
                'dynamic_content_loading',
                'ajax_request_handling',
                'browser_automation',
                'happy_hour_keywords',
                'context_aware_time_extraction'
            ],
            'browser_engine': 'chromium',
            'headless_mode': self.headless
        }


class BrowserScraperPool:
    """
    Browser instance pool for performance optimization.
    
    Reuses browser instances across multiple scraping operations
    to reduce startup overhead.
    """
    
    def __init__(self, max_instances: int = 3):
        self.max_instances = max_instances
        self.active_browsers: List[Browser] = []
        self.available_browsers: List[Browser] = []
        
    async def get_browser(self) -> Browser:
        """Get an available browser instance"""
        if self.available_browsers:
            return self.available_browsers.pop()
        
        if len(self.active_browsers) < self.max_instances:
            # Create new browser instance
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.active_browsers.append(browser)
            return browser
        
        # Wait for an available browser (simple approach)
        await asyncio.sleep(1)
        return await self.get_browser()
    
    async def return_browser(self, browser: Browser):
        """Return a browser instance to the pool"""
        if browser in self.active_browsers and len(self.available_browsers) < self.max_instances:
            self.available_browsers.append(browser)
    
    async def close_all(self):
        """Close all browser instances"""
        for browser in self.active_browsers + self.available_browsers:
            try:
                await browser.close()
            except:
                pass
        self.active_browsers.clear()
        self.available_browsers.clear()


# Test function for development
if __name__ == "__main__":
    from models import Restaurant
    
    # Test with STK (known JavaScript site)
    restaurant = Restaurant(
        name='STK',
        slug='stk',
        district='Central',
        cuisine='Steakhouse',
        website='https://stksteakhouse.com/happenings/happy-hour/'
    )
    
    scraper = BrowserScraper(restaurant, headless=False)  # Visible for debugging
    deals = scraper.scrape_deals()
    
    print(f"Found {len(deals)} deals:")
    for deal in deals:
        print(f"- {deal.title}: {deal.description}")