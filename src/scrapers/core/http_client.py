#!/usr/bin/env python3
"""
HTTP client with circuit breaker, robots.txt compliance, and retry logic
Extracted from BaseScraper for separation of concerns
"""

import requests
import time
import logging
import random
from datetime import datetime
from typing import Optional, Dict, Any
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse

from ..exceptions import TemporaryScrapingError, PermanentScrapingError

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker to avoid hammering failed endpoints"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if we can execute a request"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time and \
               (datetime.now() - self.last_failure_time).seconds > self.timeout:
                self.state = "half-open"
                return True
            return False
        
        # half-open state
        return True
    
    def on_success(self):
        """Called when request succeeds"""
        self.failure_count = 0
        self.state = "closed"
    
    def on_failure(self):
        """Called when request fails"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class HttpClient:
    """HTTP client with robust error handling, retry logic, and bot detection avoidance"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.circuit_breaker = CircuitBreaker()
        self.session = self._create_session()
        self.robots_cache = {}
        
        # Adaptive delays
        self.base_delay = self.config.get('base_delay', 2.0)
        self.max_delay = self.config.get('max_delay', 60.0)
        self.current_delay = self.base_delay
        self.failed_attempts = 0
    
    def _create_session(self) -> requests.Session:
        """Create a robust requests session with retries and timeouts"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set polite headers
        headers = {
            'User-Agent': 'SipsAndStealsBot/1.0 (+https://github.com/sips-and-steals/scraper) - Denver Happy Hour Aggregator',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=300',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Add custom headers from config
        custom_headers = self.config.get('custom_headers', {})
        headers.update(custom_headers)
        session.headers.update(headers)
        
        return session
    
    def fetch_url(self, url: str, timeout: Optional[int] = None) -> requests.Response:
        """Fetch a URL with comprehensive error handling"""
        timeout = timeout or self.config.get('timeout_seconds', 30)
        
        if not self.circuit_breaker.can_execute():
            raise TemporaryScrapingError("Circuit breaker is open, skipping request")
        
        # Check robots.txt compliance
        if not self._can_fetch_url(url):
            raise PermanentScrapingError(f"Robots.txt disallows fetching {url}")
        
        # Add progressive delay on failures
        if self.failed_attempts > 0:
            delay = min(self.base_delay * (2 ** self.failed_attempts), self.max_delay)
            logger.info(f"Adding {delay}s delay before fetching {url} (attempt after {self.failed_attempts} failures)")
            time.sleep(delay)
        
        logger.info(f"Fetching {url}")
        
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Check for bot detection patterns
            self._check_bot_detection(response)
            
            self.circuit_breaker.on_success()
            self.failed_attempts = 0
            
            return response
            
        except Exception as e:
            self.circuit_breaker.on_failure()
            self.failed_attempts += 1
            raise
    
    def _can_fetch_url(self, url: str) -> bool:
        """Check if robots.txt allows fetching this URL"""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if base_url not in self.robots_cache:
                robots_url = urljoin(base_url, '/robots.txt')
                
                try:
                    rp = RobotFileParser()
                    rp.set_url(robots_url)
                    
                    robots_response = self.session.get(robots_url, timeout=5)
                    if robots_response.status_code == 200:
                        rp.read()
                        self.robots_cache[base_url] = rp
                    else:
                        # If no robots.txt, assume we can fetch
                        self.robots_cache[base_url] = None
                        
                except Exception:
                    # If we can't fetch robots.txt, assume we can proceed
                    self.robots_cache[base_url] = None
            
            rp = self.robots_cache[base_url]
            if rp is None:
                return True
                
            # Check if our user agent can fetch this URL
            user_agent = self.session.headers.get('User-Agent', '*')
            return rp.can_fetch(user_agent, url)
            
        except Exception:
            # If there's any error with robots.txt checking, allow the fetch
            return True
    
    def _check_bot_detection(self, response: requests.Response):
        """Check if the response indicates bot detection"""
        content = response.text.lower()
        
        # Check response headers first
        if response.status_code == 429:
            raise TemporaryScrapingError("Rate limited by server")
        
        # Bot detection patterns
        bot_indicators = [
            'access denied', 'blocked', 'captcha', 'cloudflare security',
            'security check', 'bot detection', 'please enable javascript',
            'automated requests', 'suspicious activity', 'verify you are human'
        ]
        
        # Check for very short responses (often a sign of blocking)
        if len(content) < 500 and any(indicator in content for indicator in bot_indicators):
            raise PermanentScrapingError("Bot detection triggered")
            
        # Check for JavaScript-heavy pages that might be trying to detect bots
        if 'javascript' in content and len(content) < 1000:
            logger.warning(f"Possible JavaScript-heavy page detected")
    
    def adaptive_delay(self):
        """Implement adaptive delays based on website response"""
        delay = self.current_delay + random.uniform(0, 0.5)  # Add jitter
        time.sleep(delay)
        
        # Adjust delay based on success/failure patterns
        if self.circuit_breaker.failure_count == 0:
            self.current_delay = max(self.base_delay, self.current_delay * 0.9)
        else:
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)