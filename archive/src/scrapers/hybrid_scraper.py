#!/usr/bin/env python3
"""
Hybrid Scraper with Intelligent JavaScript Detection

Combines static HTML parsing with browser automation. Tries fast static
parsing first, then falls back to JavaScript-enabled browser scraping
when dynamic content is detected.
"""

import logging
import re
from typing import List, Optional, Set, Dict
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

from models import Restaurant, Deal
from .core.base import BaseScraper
from .universal_scraper import UniversalScraper
from .browser_scraper import BrowserScraper

logger = logging.getLogger(__name__)


class HybridScraper(BaseScraper):
    """
    Intelligent hybrid scraper that automatically chooses between static
    and JavaScript-enabled scraping based on content analysis.
    """
    
    # Indicators that suggest JavaScript is required
    JS_REQUIRED_INDICATORS = [
        # Framework indicators
        'react', 'angular', 'vue.js', 'ember.js', 'backbone.js',
        # Dynamic loading indicators
        'spa-content', 'ajax-content', 'dynamic-content',
        # Common JavaScript patterns
        'document.ready', '$(document)', 'window.onload',
        'fetch(', 'xhr.open', 'xmlhttprequest',
        # Modern framework attributes
        'ng-app', 'ng-controller', 'data-react', 'v-if', 'v-for',
        # Single Page Application indicators
        'router-outlet', 'ui-view', 'data-turbo',
        # Loading states
        'loading-spinner', 'skeleton-loader', 'lazy-load'
    ]
    
    # Domains known to require JavaScript
    JS_REQUIRED_DOMAINS = [
        'stksteakhouse.com',
        'opentable.com',
        'resy.com',
        'squarespace.com',
        'wix.com',
        'weebly.com'
    ]
    
    # Selectors that indicate dynamic content areas
    DYNAMIC_CONTENT_SELECTORS = [
        '[data-react-root]',
        '[ng-app]',
        '[data-vue-app]',
        '.spa-container',
        '.react-component',
        '.angular-component',
        '.vue-component',
        '[data-component]',
        '.js-content',
        '.ajax-content'
    ]
    
    def __init__(self, restaurant: Restaurant):
        super().__init__(restaurant)
        self.static_scraper = UniversalScraper(restaurant)
        self.browser_scraper = BrowserScraper(restaurant)
        self.js_detection_cache: Dict[str, bool] = {}
        logger.info(f"Initialized hybrid scraper for {restaurant.name}")
    
    def scrape_deals(self) -> List[Deal]:
        """
        Scrape deals using hybrid approach: static first, browser fallback.
        
        Returns:
            List of Deal objects found using optimal scraping method
        """
        website = self.restaurant.website
        if not website:
            logger.warning(f"No website available for {self.restaurant.name}")
            return []
        
        try:
            # Step 1: Quick check if this domain is known to require JS
            if self._domain_requires_js(website):
                logger.info(f"Domain {website} known to require JavaScript, using browser scraper")
                return self.browser_scraper.scrape_deals()
            
            # Step 2: Try static scraping first (fast)
            logger.info(f"Attempting static scraping for {self.restaurant.name}")
            static_deals = self.static_scraper.scrape_deals()
            
            # Step 3: Analyze if we need JavaScript based on results and content
            needs_js = self._analyze_js_requirement(website, static_deals)
            
            if not needs_js and static_deals:
                logger.info(f"Static scraping successful for {self.restaurant.name}, found {len(static_deals)} deals")
                return static_deals
            
            # Step 4: Fall back to browser scraping
            logger.info(f"Falling back to browser scraping for {self.restaurant.name}")
            browser_deals = self.browser_scraper.scrape_deals()
            
            # Step 5: Return the better result
            if len(browser_deals) > len(static_deals):
                logger.info(f"Browser scraping found more deals ({len(browser_deals)} vs {len(static_deals)})")
                return browser_deals
            elif static_deals:
                logger.info(f"Static scraping was sufficient ({len(static_deals)} deals)")
                return static_deals
            else:
                return browser_deals
                
        except Exception as e:
            logger.error(f"Error in hybrid scraping for {self.restaurant.name}: {e}")
            # Fallback to static scraper if browser scraping fails
            try:
                return self.static_scraper.scrape_deals()
            except:
                return []
    
    def _domain_requires_js(self, website: str) -> bool:
        """Check if domain is known to require JavaScript"""
        for domain in self.JS_REQUIRED_DOMAINS:
            if domain in website.lower():
                return True
        return False
    
    def _analyze_js_requirement(self, website: str, static_deals: List[Deal]) -> bool:
        """
        Analyze if JavaScript is likely required based on content and results.
        
        Args:
            website: Website URL
            static_deals: Results from static scraping
            
        Returns:
            True if JavaScript is likely required
        """
        # Check cache first
        if website in self.js_detection_cache:
            return self.js_detection_cache[website]
        
        try:
            # Fetch the raw HTML for analysis
            with httpx.Client(timeout=10, follow_redirects=True) as client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; SipsAndSteals/1.0; +https://sips-and-steals.com)'
                }
                response = client.get(website, headers=headers)
                
                if response.status_code != 200:
                    logger.warning(f"Could not fetch {website} for JS analysis")
                    return False
                
                html_content = response.text
                soup = BeautifulSoup(html_content, 'html.parser')
                
                needs_js = self._detect_javascript_requirements(html_content, soup, static_deals)
                
                # Cache the result
                self.js_detection_cache[website] = needs_js
                
                return needs_js
                
        except Exception as e:
            logger.warning(f"Error analyzing JS requirements for {website}: {e}")
            return False
    
    def _detect_javascript_requirements(self, html_content: str, soup: BeautifulSoup, static_deals: List[Deal]) -> bool:
        """
        Detect if JavaScript is required based on content analysis.
        
        Args:
            html_content: Raw HTML content
            soup: BeautifulSoup parsed HTML
            static_deals: Results from static scraping
            
        Returns:
            True if JavaScript is likely required
        """
        confidence_score = 0.0
        
        # 1. Check for JavaScript framework indicators
        html_lower = html_content.lower()
        js_indicators_found = sum(1 for indicator in self.JS_REQUIRED_INDICATORS if indicator in html_lower)
        confidence_score += min(js_indicators_found * 0.15, 0.6)
        
        # 2. Check for dynamic content selectors
        dynamic_selectors_found = 0
        for selector in self.DYNAMIC_CONTENT_SELECTORS:
            try:
                if soup.select(selector):
                    dynamic_selectors_found += 1
            except:
                continue
        confidence_score += min(dynamic_selectors_found * 0.2, 0.4)
        
        # 3. Check for empty content areas that might be populated by JS
        suspicious_empty_areas = 0
        for container in soup.find_all(['div', 'section', 'main'], class_=True):
            classes = ' '.join(container.get('class', []))
            if any(keyword in classes.lower() for keyword in ['content', 'menu', 'deals', 'specials', 'hours']):
                if not container.get_text(strip=True):
                    suspicious_empty_areas += 1
        confidence_score += min(suspicious_empty_areas * 0.1, 0.3)
        
        # 4. Check if static scraping found suspiciously few results
        if len(static_deals) == 0:
            confidence_score += 0.2
        
        # 5. Look for specific patterns that indicate dynamic loading
        dynamic_patterns = [
            r'data-\w+="[^"]*"',  # Data attributes
            r'class="[^"]*loading[^"]*"',  # Loading classes
            r'id="[^"]*app[^"]*"',  # App containers
            r'<script[^>]*src="[^"]*bundle[^"]*"',  # Bundled JavaScript
            r'<script[^>]*>.*react.*</script>',  # React usage
            r'<script[^>]*>.*angular.*</script>',  # Angular usage
        ]
        
        pattern_matches = 0
        for pattern in dynamic_patterns:
            if re.search(pattern, html_content, re.IGNORECASE | re.DOTALL):
                pattern_matches += 1
        confidence_score += min(pattern_matches * 0.05, 0.25)
        
        # 6. Check for AJAX endpoints or API calls in scripts
        if re.search(r'fetch\s*\(\s*["\']/?api/', html_content, re.IGNORECASE):
            confidence_score += 0.15
        
        logger.debug(f"JavaScript requirement confidence: {confidence_score:.2f}")
        
        # Threshold for requiring JavaScript
        return confidence_score > 0.5
    
    def get_scraper_info(self) -> dict:
        """Get information about this scraper"""
        return {
            'type': 'hybrid',
            'description': 'Hybrid scraper with intelligent JS detection',
            'requires_config': False,
            'supports_js': True,
            'supports_pdf': True,  # Via static scraper
            'extraction_methods': [
                'static_html_parsing',
                'javascript_fallback',
                'intelligent_detection',
                'performance_optimization',
                'happy_hour_keywords',
                'dynamic_content_handling'
            ],
            'static_scraper': self.static_scraper.get_scraper_info(),
            'browser_scraper': self.browser_scraper.get_scraper_info()
        }


# Test function for development
if __name__ == "__main__":
    from models import Restaurant
    
    # Test with different types of sites
    test_restaurants = [
        Restaurant(
            name='STK',
            slug='stk', 
            district='Central',
            cuisine='Steakhouse',
            website='https://stksteakhouse.com/happenings/happy-hour/'
        ),
        Restaurant(
            name='Tamayo',
            slug='tamayo',
            district='Central', 
            cuisine='Mexican',
            website='https://tamayodenver.com'
        )
    ]
    
    for restaurant in test_restaurants:
        print(f"\nTesting hybrid scraper with {restaurant.name}...")
        scraper = HybridScraper(restaurant)
        deals = scraper.scrape_deals()
        print(f"Found {len(deals)} deals")
        for deal in deals[:3]:  # Show first 3
            print(f"- {deal.title}: {deal.description}")