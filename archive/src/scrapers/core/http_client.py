#!/usr/bin/env python3
"""
HTTP client with circuit breaker, robots.txt compliance, and retry logic
Extracted from BaseScraper for separation of concerns
"""

import httpx
import time
import logging
import random
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
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
        self.client = self._create_client()
        self.robots_cache = {}
        
        # Adaptive delays
        self.base_delay = self.config.get('base_delay', 2.0)
        self.max_delay = self.config.get('max_delay', 60.0)
        self.current_delay = self.base_delay
        self.failed_attempts = 0
    
    def _create_client(self) -> httpx.Client:
        """Create a robust httpx client with retries and timeouts"""
        
        # Set polite headers
        headers = {
            'User-Agent': 'SipsAndStealsBot/1.0 (+https://github.com/sips-and-steals/scraper) - Denver Happy Hour Aggregator',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'max-age=300',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Add custom headers from config
        custom_headers = self.config.get('custom_headers', {})
        headers.update(custom_headers)
        
        # Create httpx client with connection limits and timeout
        client = httpx.Client(
            headers=headers,
            timeout=self.config.get('timeout_seconds', 30),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5
            ),
            # Built-in retry support and redirect handling
            transport=httpx.HTTPTransport(retries=3),
            follow_redirects=True,  # Automatically follow redirects
            max_redirects=10  # Reasonable limit to prevent infinite loops
        )
        
        return client
    
    def fetch_url(self, url: str, timeout: Optional[int] = None) -> httpx.Response:
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
            response = self.client.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Log and handle redirects
            redirect_info = self._handle_redirects(url, response)
            
            # Check for bot detection patterns
            self._check_bot_detection(response)
            
            self.circuit_breaker.on_success()
            self.failed_attempts = 0
            
            # Add redirect info to response for upstream handling
            if redirect_info:
                response.redirect_info = redirect_info
            
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
                    
                    robots_response = self.client.get(robots_url, timeout=5)
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
            user_agent = self.client.headers.get('User-Agent', '*')
            return rp.can_fetch(user_agent, url)
            
        except Exception:
            # If there's any error with robots.txt checking, allow the fetch
            return True
    
    def _check_bot_detection(self, response: httpx.Response):
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
    
    def _handle_redirects(self, original_url: str, response: httpx.Response) -> Optional[Dict[str, Any]]:
        """Handle redirect tracking and logging"""
        if not response.history:
            return None  # No redirects occurred
        
        redirect_chain = []
        for redirect_response in response.history:
            redirect_chain.append({
                'from_url': redirect_response.url,
                'to_url': redirect_response.headers.get('location'),
                'status_code': redirect_response.status_code,
                'is_permanent': redirect_response.status_code == 301
            })
        
        final_url = str(response.url)
        redirect_info = {
            'original_url': original_url,
            'final_url': final_url,
            'redirect_chain': redirect_chain,
            'redirect_count': len(redirect_chain),
            'has_permanent_redirect': any(r['is_permanent'] for r in redirect_chain)
        }
        
        # Log redirect information
        if redirect_info['has_permanent_redirect']:
            logger.info(f"Permanent redirect detected: {original_url} → {final_url}")
        else:
            logger.info(f"Temporary redirect: {original_url} → {final_url}")
        
        return redirect_info
    
    def adaptive_delay(self):
        """Implement adaptive delays based on website response"""
        delay = self.current_delay + random.uniform(0, 0.5)  # Add jitter
        time.sleep(delay)
        
        # Adjust delay based on success/failure patterns
        if self.circuit_breaker.failure_count == 0:
            self.current_delay = max(self.base_delay, self.current_delay * 0.9)
        else:
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)
    
    def close(self):
        """Close the httpx client and cleanup resources"""
        if hasattr(self, 'client') and self.client:
            self.client.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class AsyncHttpClient:
    """Async HTTP client for concurrent processing with the same error handling and politeness"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.circuit_breaker = CircuitBreaker()
        self.client = None
        self.robots_cache = {}
        
        # Adaptive delays
        self.base_delay = self.config.get('base_delay', 2.0)
        self.max_delay = self.config.get('max_delay', 60.0)
        self.current_delay = self.base_delay
        self.failed_attempts = 0
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._create_async_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _create_async_client(self):
        """Create async httpx client with same configuration as sync client"""
        
        # Set polite headers
        headers = {
            'User-Agent': 'SipsAndStealsBot/1.0 (+https://github.com/sips-and-steals/scraper) - Denver Happy Hour Aggregator',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'max-age=300',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Add custom headers from config
        custom_headers = self.config.get('custom_headers', {})
        headers.update(custom_headers)
        
        # Create async httpx client
        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=self.config.get('timeout_seconds', 30),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5
            ),
            # Built-in retry support and redirect handling
            transport=httpx.AsyncHTTPTransport(retries=3),
            follow_redirects=True,  # Automatically follow redirects
            max_redirects=10  # Reasonable limit to prevent infinite loops
        )
    
    async def fetch_url(self, url: str, timeout: Optional[int] = None) -> httpx.Response:
        """Async fetch with same error handling as sync version"""
        timeout = timeout or self.config.get('timeout_seconds', 30)
        
        if not self.circuit_breaker.can_execute():
            raise TemporaryScrapingError("Circuit breaker is open, skipping request")
        
        # Check robots.txt compliance
        if not await self._can_fetch_url(url):
            raise PermanentScrapingError(f"Robots.txt disallows fetching {url}")
        
        # Add progressive delay on failures
        if self.failed_attempts > 0:
            delay = min(self.base_delay * (2 ** self.failed_attempts), self.max_delay)
            logger.info(f"Adding {delay}s delay before fetching {url} (attempt after {self.failed_attempts} failures)")
            await asyncio.sleep(delay)
        
        logger.info(f"Fetching {url}")
        
        try:
            response = await self.client.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Log and handle redirects
            redirect_info = self._handle_redirects(url, response)
            
            # Check for bot detection patterns
            self._check_bot_detection(response)
            
            self.circuit_breaker.on_success()
            self.failed_attempts = 0
            
            # Add redirect info to response for upstream handling
            if redirect_info:
                response.redirect_info = redirect_info
            
            return response
            
        except Exception as e:
            self.circuit_breaker.on_failure()
            self.failed_attempts += 1
            raise
    
    async def _can_fetch_url(self, url: str) -> bool:
        """Async robots.txt checking"""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if base_url not in self.robots_cache:
                robots_url = urljoin(base_url, '/robots.txt')
                
                try:
                    rp = RobotFileParser()
                    rp.set_url(robots_url)
                    
                    robots_response = await self.client.get(robots_url, timeout=5)
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
            user_agent = self.client.headers.get('User-Agent', '*')
            return rp.can_fetch(user_agent, url)
            
        except Exception:
            # If there's any error with robots.txt checking, allow the fetch
            return True
    
    def _check_bot_detection(self, response: httpx.Response):
        """Check if the response indicates bot detection (same as sync version)"""
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
    
    def _handle_redirects(self, original_url: str, response: httpx.Response) -> Optional[Dict[str, Any]]:
        """Handle redirect tracking and logging (same as sync version)"""
        if not response.history:
            return None  # No redirects occurred
        
        redirect_chain = []
        for redirect_response in response.history:
            redirect_chain.append({
                'from_url': str(redirect_response.url),
                'to_url': redirect_response.headers.get('location'),
                'status_code': redirect_response.status_code,
                'is_permanent': redirect_response.status_code == 301
            })
        
        final_url = str(response.url)
        redirect_info = {
            'original_url': original_url,
            'final_url': final_url,
            'redirect_chain': redirect_chain,
            'redirect_count': len(redirect_chain),
            'has_permanent_redirect': any(r['is_permanent'] for r in redirect_chain)
        }
        
        # Log redirect information
        if redirect_info['has_permanent_redirect']:
            logger.info(f"Permanent redirect detected: {original_url} → {final_url}")
        else:
            logger.info(f"Temporary redirect: {original_url} → {final_url}")
        
        return redirect_info
    
    async def adaptive_delay(self):
        """Async adaptive delays"""
        delay = self.current_delay + random.uniform(0, 0.5)  # Add jitter
        await asyncio.sleep(delay)
        
        # Adjust delay based on success/failure patterns
        if self.circuit_breaker.failure_count == 0:
            self.current_delay = max(self.base_delay, self.current_delay * 0.9)
        else:
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)
    
    async def close(self):
        """Close the async httpx client"""
        if self.client:
            await self.client.aclose()