"""
Scrapy Middlewares for Sips and Steals

Custom middleware for enhanced crawling behavior.
Most functionality is handled by Scrapy's built-in middlewares.
"""

import logging
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message


class RestaurantCrawlMiddleware:
    """
    Custom middleware for restaurant-specific crawling behavior.
    
    Handles special cases and logging for restaurant websites.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_request(self, request, spider):
        """Process requests before they're sent"""
        # Add restaurant context to request headers for logging
        restaurant_slug = request.meta.get('restaurant_slug')
        if restaurant_slug:
            request.headers['X-Restaurant-Slug'] = restaurant_slug
        
        return None
    
    def process_response(self, request, response, spider):
        """Process successful responses"""
        restaurant_slug = request.meta.get('restaurant_slug')
        
        # Log successful crawls
        if restaurant_slug and response.status == 200:
            self.logger.debug(f"Successfully crawled {response.url} for {restaurant_slug}")
        
        return response
    
    def process_exception(self, request, exception, spider):
        """Process request exceptions"""
        restaurant_slug = request.meta.get('restaurant_slug', 'unknown')
        self.logger.warning(f"Exception crawling {request.url} for {restaurant_slug}: {exception}")
        
        return None


class EnhancedRetryMiddleware(RetryMiddleware):
    """
    Enhanced retry middleware with restaurant-aware logging.
    
    Extends Scrapy's built-in retry middleware with better logging
    for restaurant-specific failures.
    """
    
    def retry(self, request, reason, spider):
        """Enhanced retry with restaurant context"""
        restaurant_slug = request.meta.get('restaurant_slug', 'unknown')
        restaurant_name = request.meta.get('restaurant_name', 'unknown')
        
        retries = request.meta.get('retry_times', 0) + 1
        retry_times = self.max_retry_times
        
        if retries <= retry_times:
            spider.logger.info(f"Retrying {request.url} for {restaurant_name} "
                             f"(retry {retries}/{retry_times}): {reason}")
            
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retries
            retryreq.dont_filter = True
            retryreq.priority = request.priority + self.priority_adjust
            
            return retryreq
        else:
            spider.logger.warning(f"Gave up retrying {request.url} for {restaurant_name} "
                                f"after {retry_times} attempts: {reason}")
            
        return None