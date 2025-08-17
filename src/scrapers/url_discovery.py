#!/usr/bin/env python3
"""
Automatic Happy Hour URL Discovery Service

Discovers potential happy hour pages by testing common URL patterns
and analyzing content for happy hour indicators.
"""

import logging
from typing import List, Optional, Dict, Set
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class HappyHourUrlDiscovery:
    """
    Service for discovering happy hour URLs automatically.
    
    Tests common URL patterns and analyzes content to find the best
    happy hour pages for each restaurant.
    """
    
    # Common happy hour URL patterns (in priority order)
    HAPPY_HOUR_PATTERNS = [
        '/happy-hour',
        '/happy-hour/',
        '/happyhour',
        '/happyhour/',
        '/specials',
        '/specials/',
        '/deals',
        '/deals/',
        '/promotions',
        '/promotions/',
        '/bar-specials',
        '/drink-specials',
        '/cocktail-hour',
        '/wine-hour',
        '/events',
        '/events/',
        '/menu/happy-hour',
        '/menu/happy-hour/',
        '/menu/specials',
        '/menu/bar',
        '/menus/happy-hour',
        '/menus/specials',
        '/menus/',
        '/food-drink',
        '/food-drink/',
        '/bar',
        '/bar/'
    ]
    
    # Keywords that indicate happy hour content
    HAPPY_HOUR_KEYWORDS = [
        'happy hour', 'happii hour', 'drink specials', 'bar specials',
        'cocktail hour', 'wine hour', 'discounted drinks', 'deals',
        'all day happy', 'daily specials', 'food and drink specials'
    ]
    
    # Patterns that indicate time-based deals
    TIME_PATTERNS = [
        r'\d{1,2}:\d{2}\s*[ap]m',  # "4:00 PM"
        r'\d{1,2}\s*[ap]m',        # "4 PM"
        r'\d{1,2}\s*-\s*\d{1,2}',  # "4-6"
        r'monday|tuesday|wednesday|thursday|friday|saturday|sunday',  # Day names
        r'mon|tue|wed|thu|fri|sat|sun',  # Short day names
        r'daily|everyday|weekday|weekend'  # General time terms
    ]
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; SipsAndSteals/1.0; +https://sips-and-steals.com)'
            }
        )
    
    def discover_urls(self, base_url: str) -> List[Dict[str, any]]:
        """
        Discover potential happy hour URLs for a restaurant.
        
        Returns:
            List of discovered URLs with scores and metadata
        """
        if not base_url:
            return []
        
        logger.info(f"Discovering happy hour URLs for {base_url}")
        
        discovered_urls = []
        
        # Step 1: Test direct URL patterns
        pattern_urls = self._test_url_patterns(base_url)
        discovered_urls.extend(pattern_urls)
        
        # Step 2: Crawl main page for internal links
        try:
            crawled_urls = self._crawl_for_links(base_url)
            discovered_urls.extend(crawled_urls)
        except Exception as e:
            logger.warning(f"Failed to crawl {base_url}: {e}")
        
        # Step 3: Score and rank URLs
        scored_urls = self._score_urls(discovered_urls)
        
        # Step 4: Return top candidates
        return sorted(scored_urls, key=lambda x: x['score'], reverse=True)[:5]
    
    def _test_url_patterns(self, base_url: str) -> List[Dict[str, any]]:
        """Test common happy hour URL patterns"""
        discovered = []
        
        parsed = urlparse(base_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        
        for pattern in self.HAPPY_HOUR_PATTERNS:
            test_url = urljoin(base_domain, pattern)
            
            try:
                response = self.session.head(test_url)
                if response.status_code == 200:
                    # URL exists, test content quality
                    content_score = self._analyze_url_content(test_url)
                    
                    if content_score > 0:
                        discovered.append({
                            'url': test_url,
                            'discovery_method': 'pattern_test',
                            'pattern': pattern,
                            'content_score': content_score,
                            'http_status': response.status_code
                        })
                        logger.debug(f"Found happy hour URL: {test_url} (score: {content_score})")
                
            except Exception as e:
                # URL doesn't exist or is inaccessible
                logger.debug(f"Pattern {pattern} failed for {base_domain}: {e}")
                continue
        
        return discovered
    
    def _crawl_for_links(self, base_url: str) -> List[Dict[str, any]]:
        """Crawl main page for internal links that might contain happy hour content"""
        discovered = []
        
        try:
            response = self.session.get(base_url)
            if response.status_code != 200:
                return discovered
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all internal links
            parsed_base = urlparse(base_url)
            base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    full_url = urljoin(base_domain, href)
                elif href.startswith('http'):
                    parsed_link = urlparse(href)
                    if parsed_link.netloc != parsed_base.netloc:
                        continue  # Skip external links
                    full_url = href
                else:
                    continue  # Skip other types of links
                
                # Check if link text or URL suggests happy hour content
                link_text = link.get_text().lower()
                url_path = urlparse(full_url).path.lower()
                
                happy_hour_indicators = ['happy', 'specials', 'deals', 'bar', 'drink', 'cocktail']
                
                if (any(indicator in link_text for indicator in happy_hour_indicators) or
                    any(indicator in url_path for indicator in happy_hour_indicators)):
                    
                    # Test this URL
                    content_score = self._analyze_url_content(full_url)
                    
                    if content_score > 0:
                        discovered.append({
                            'url': full_url,
                            'discovery_method': 'link_crawl',
                            'link_text': link_text,
                            'content_score': content_score
                        })
        
        except Exception as e:
            logger.warning(f"Failed to crawl {base_url}: {e}")
        
        return discovered
    
    def _analyze_url_content(self, url: str) -> float:
        """
        Analyze URL content to score its happy hour potential.
        
        Returns:
            Float score (0.0 to 1.0) indicating happy hour content quality
        """
        try:
            response = self.session.get(url)
            if response.status_code != 200:
                return 0.0
            
            content = response.text.lower()
            score = 0.0
            
            # Score based on happy hour keywords
            for keyword in self.HAPPY_HOUR_KEYWORDS:
                if keyword in content:
                    score += 0.2
            
            # Score based on time patterns
            for pattern in self.TIME_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    score += min(len(matches) * 0.1, 0.3)  # Cap at 0.3
            
            # Score based on pricing patterns
            price_matches = re.findall(r'\$\d+', content)
            if price_matches:
                score += min(len(price_matches) * 0.05, 0.2)  # Cap at 0.2
            
            # Bonus for specific happy hour sections
            if 'happy hour' in content and any(pattern in content for pattern in ['menu', 'specials', 'deals']):
                score += 0.3
            
            return min(score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.debug(f"Failed to analyze content for {url}: {e}")
            return 0.0
    
    def _score_urls(self, urls: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Score and rank discovered URLs"""
        for url_data in urls:
            base_score = url_data.get('content_score', 0.0)
            
            # Bonus for specific patterns
            pattern = url_data.get('pattern', '')
            if 'happy-hour' in pattern:
                base_score += 0.3
            elif 'specials' in pattern or 'deals' in pattern:
                base_score += 0.2
            elif 'menu' in pattern:
                base_score += 0.1
            
            # Bonus for discovery method
            if url_data.get('discovery_method') == 'pattern_test':
                base_score += 0.1
            
            url_data['score'] = min(base_score, 1.0)
        
        return urls
    
    def get_best_url(self, base_url: str) -> Optional[str]:
        """Get the single best happy hour URL for a restaurant"""
        discovered = self.discover_urls(base_url)
        
        if discovered and discovered[0]['score'] > 0.3:  # Minimum threshold
            return discovered[0]['url']
        
        return None
    
    def __del__(self):
        """Clean up HTTP session"""
        if hasattr(self, 'session'):
            self.session.close()


# Test function
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        discovery = HappyHourUrlDiscovery()
        results = discovery.discover_urls(url)
        
        print(f"Happy hour URL discovery for: {url}")
        print("-" * 50)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['url']} (score: {result['score']:.2f})")
            print(f"   Method: {result['discovery_method']}")
            if 'pattern' in result:
                print(f"   Pattern: {result['pattern']}")
            print()
        
        best = discovery.get_best_url(url)
        if best:
            print(f"Best URL: {best}")
        else:
            print("No suitable happy hour URL found")
    else:
        print("Usage: python url_discovery.py <restaurant_url>")