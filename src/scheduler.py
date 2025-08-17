#!/usr/bin/env python3
"""
Basic scheduler foundation for running scrapers
Handles scheduling, queuing, and coordinating scraping tasks
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

from data_manager import DataManager
from models import Restaurant, ScrapingStatus
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


@dataclass
class ScrapingTask:
    """Represents a scraping task"""
    restaurant_slug: str
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = None
    max_retries: int = 3
    retry_count: int = 0
    scheduled_for: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.scheduled_for is None:
            self.scheduled_for = datetime.now()
    
    def __lt__(self, other):
        """For priority queue ordering"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.scheduled_for < other.scheduled_for


class ScrapingScheduler:
    """
    Scheduler for coordinating restaurant scraping tasks
    Handles queuing, rate limiting, and retry logic
    """
    
    def __init__(self, data_manager: DataManager, max_workers: int = 2, rate_limit_delay: float = 5.0):
        self.data_manager = data_manager
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        
        # Task management
        self.task_queue = queue.PriorityQueue()
        self.running_tasks: Dict[str, ScrapingTask] = {}
        self.completed_tasks: List[Dict[str, Any]] = []
        
        # Control flags
        self.is_running = False
        self.stop_requested = False
        
        # Statistics
        self.stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_runtime': 0,
            'last_run': None,
            'average_task_time': 0
        }
        
        # Simplified: use only generic scraper
        logger.info("Using generic scraper for all restaurants")
    
    def schedule_restaurant(self, restaurant_slug: str, priority: TaskPriority = TaskPriority.NORMAL, 
                          delay_minutes: int = 0) -> bool:
        """Schedule a restaurant for scraping"""
        restaurant = self.data_manager.get_restaurant(restaurant_slug)
        if not restaurant:
            logger.error(f"Restaurant {restaurant_slug} not found")
            return False
        
        if not restaurant.website or not restaurant.scraping_config.enabled:
            logger.info(f"Skipping {restaurant.name} - no website or scraping disabled")
            return False
        
        # Check if already queued or running
        if restaurant_slug in self.running_tasks:
            logger.info(f"Restaurant {restaurant.name} already being scraped")
            return False
        
        # Create task
        scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
        task = ScrapingTask(
            restaurant_slug=restaurant_slug,
            priority=priority,
            scheduled_for=scheduled_time
        )
        
        self.task_queue.put(task)
        logger.info(f"Scheduled {restaurant.name} for scraping at {scheduled_time}")
        return True
    
    def schedule_all_needing_update(self) -> int:
        """Schedule all restaurants that need updating"""
        restaurants = self.data_manager.get_restaurants_needing_scraping()
        scheduled_count = 0
        
        for i, restaurant in enumerate(restaurants):
            # Stagger the scheduling to avoid overwhelming servers
            delay_minutes = i * 2  # 2 minute delays between restaurants
            if self.schedule_restaurant(restaurant.slug, TaskPriority.NORMAL, delay_minutes):
                scheduled_count += 1
        
        logger.info(f"Scheduled {scheduled_count} restaurants for scraping")
        return scheduled_count
    
    def schedule_district(self, district: str, priority: TaskPriority = TaskPriority.NORMAL) -> int:
        """Schedule all restaurants in a district"""
        restaurants = self.data_manager.get_restaurants_by_district(district)
        scheduled_count = 0
        
        for i, restaurant in enumerate(restaurants):
            if restaurant.website and restaurant.scraping_config.enabled:
                delay_minutes = i * 0.1  # Stagger scraping with 6-second delays to be polite
                if self.schedule_restaurant(restaurant.slug, priority, delay_minutes):
                    scheduled_count += 1
        
        logger.info(f"Scheduled {scheduled_count} restaurants in {district}")
        return scheduled_count
    
    def schedule_neighborhood(self, neighborhood: str, priority: TaskPriority = TaskPriority.NORMAL) -> int:
        """Schedule all restaurants in a neighborhood"""
        restaurants = self.data_manager.get_restaurants_by_neighborhood(neighborhood)
        scheduled_count = 0
        
        for i, restaurant in enumerate(restaurants):
            if restaurant.website and restaurant.scraping_config.enabled:
                delay_minutes = i * 0.1  # Stagger scraping with 6-second delays to be polite
                if self.schedule_restaurant(restaurant.slug, priority, delay_minutes):
                    scheduled_count += 1
        
        logger.info(f"Scheduled {scheduled_count} restaurants in {neighborhood}")
        return scheduled_count
    
    def run_scheduled_tasks(self) -> Dict[str, Any]:
        """Run all scheduled tasks"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return {'status': 'already_running'}
        
        self.is_running = True
        self.stop_requested = False
        start_time = datetime.now()
        
        logger.info("Starting scheduled scraping tasks")
        
        try:
            # Use ThreadPoolExecutor for concurrent scraping
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}
                
                while not self.stop_requested and not self.task_queue.empty():
                    # Get next task
                    try:
                        task = self.task_queue.get(timeout=1)
                    except queue.Empty:
                        break
                    
                    # Check if scheduled time has arrived
                    if task.scheduled_for > datetime.now():
                        # Put back in queue if not time yet
                        self.task_queue.put(task)
                        time.sleep(1)
                        continue
                    
                    # Submit task to executor
                    future = executor.submit(self._execute_scraping_task, task)
                    futures[future] = task
                    self.running_tasks[task.restaurant_slug] = task
                    
                    # Rate limiting
                    time.sleep(self.rate_limit_delay)
                
                # Wait for all tasks to complete
                for future in as_completed(futures):
                    task = futures[future]
                    try:
                        result = future.result()
                        self._handle_task_completion(task, result)
                    except Exception as e:
                        logger.error(f"Task failed: {e}")
                        self._handle_task_failure(task, str(e))
                    finally:
                        self.running_tasks.pop(task.restaurant_slug, None)
        
        finally:
            self.is_running = False
            end_time = datetime.now()
            runtime = (end_time - start_time).total_seconds()
            
            self.stats['total_runtime'] += runtime
            self.stats['last_run'] = end_time
            
            # Update average task time
            if self.stats['tasks_completed'] > 0:
                self.stats['average_task_time'] = self.stats['total_runtime'] / self.stats['tasks_completed']
        
        # Save updated data
        self.data_manager.save_data()
        
        return {
            'status': 'completed',
            'runtime_seconds': runtime,
            'tasks_completed': len(self.completed_tasks),
            'stats': self.stats
        }
    
    def _execute_scraping_task(self, task: ScrapingTask) -> Dict[str, Any]:
        """Execute a single scraping task"""
        restaurant = self.data_manager.get_restaurant(task.restaurant_slug)
        if not restaurant:
            return {'status': 'error', 'message': 'Restaurant not found'}
        
        logger.info(f"Executing scraping task for {restaurant.name}")
        start_time = datetime.now()
        
        try:
            # Get appropriate scraper
            scraper = self._get_scraper_for_restaurant(restaurant)
            if not scraper:
                return {'status': 'error', 'message': 'No scraper available'}
            
            # Execute scraping
            status, deals, error_message = scraper.run()
            
            # Update restaurant with results
            if status == ScrapingStatus.SUCCESS:
                self.data_manager.update_restaurant_deals(restaurant.slug, deals, "success")
            else:
                self.data_manager.update_restaurant_deals(restaurant.slug, deals, "failure")
            
            end_time = datetime.now()
            runtime = (end_time - start_time).total_seconds()
            
            return {
                'status': status.value,
                'restaurant_name': restaurant.name,
                'deals_count': len(deals),
                'runtime_seconds': runtime,
                'error_message': error_message
            }
        
        except Exception as e:
            logger.error(f"Error executing scraping task for {restaurant.name}: {e}")
            return {
                'status': 'error',
                'restaurant_name': restaurant.name,
                'error_message': str(e),
                'runtime_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    def _get_scraper_for_restaurant(self, restaurant: Restaurant) -> Optional[BaseScraper]:
        """Get generic scraper for restaurant"""
        # Always use generic scraper for scalability
        return GenericScraper(restaurant)
    
    def _handle_task_completion(self, task: ScrapingTask, result: Dict[str, Any]):
        """Handle successful task completion"""
        self.stats['tasks_completed'] += 1
        self.completed_tasks.append({
            'task': task,
            'result': result,
            'completed_at': datetime.now()
        })
        
        restaurant = self.data_manager.get_restaurant(task.restaurant_slug)
        logger.info(f"Completed scraping {restaurant.name}: {result.get('status')} ({result.get('deals_count', 0)} deals)")
    
    def _handle_task_failure(self, task: ScrapingTask, error: str):
        """Handle task failure and retry logic"""
        self.stats['tasks_failed'] += 1
        
        if task.retry_count < task.max_retries:
            # Retry with exponential backoff
            task.retry_count += 1
            delay_minutes = 2 ** task.retry_count  # 2, 4, 8 minutes
            task.scheduled_for = datetime.now() + timedelta(minutes=delay_minutes)
            task.priority = TaskPriority.HIGH  # Higher priority for retries
            
            self.task_queue.put(task)
            logger.warning(f"Retrying task for {task.restaurant_slug} in {delay_minutes} minutes (attempt {task.retry_count})")
        else:
            logger.error(f"Task failed permanently for {task.restaurant_slug}: {error}")
    
    def stop(self):
        """Stop the scheduler gracefully"""
        self.stop_requested = True
        logger.info("Scheduler stop requested")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            'is_running': self.is_running,
            'queue_size': self.task_queue.qsize(),
            'running_tasks': len(self.running_tasks),
            'stats': self.stats,
            'scraper_type': 'generic_only'
        }


class GenericScraper(BaseScraper):
    """Generic scraper using common patterns"""
    
    def scrape_deals(self) -> List:
        """Scrape using common patterns from all available URLs"""
        deals = []
        
        # Use all pages if restaurant has multiple URLs configured
        if hasattr(self.restaurant, 'websites') and len(getattr(self.restaurant, 'websites', [])) > 1:
            logger.info(f"Trying all {len(getattr(self.restaurant, 'websites'))} URLs for {self.restaurant.name}")
            soups = self.fetch_all_pages()
            for soup in soups:
                deals.extend(self.parse_common_patterns(soup))
        else:
            soup = self.fetch_page()
            deals = self.parse_common_patterns(soup)
        
        return deals


# Utility function for one-off scraping
def scrape_restaurant_now(restaurant_slug: str, data_manager: Optional[DataManager] = None) -> Dict[str, Any]:
    """Scrape a single restaurant immediately"""
    if not data_manager:
        data_manager = DataManager()
    
    scheduler = ScrapingScheduler(data_manager, max_workers=1)
    scheduler.schedule_restaurant(restaurant_slug, TaskPriority.URGENT)
    
    return scheduler.run_scheduled_tasks()


if __name__ == "__main__":
    # Test the scheduler
    logging.basicConfig(level=logging.INFO)
    
    dm = DataManager()
    scheduler = ScrapingScheduler(dm, max_workers=2)
    
    print("Scheduler status:", scheduler.get_status())
    
    # Schedule some test restaurants
    scheduled = scheduler.schedule_all_needing_update()
    print(f"Scheduled {scheduled} restaurants")
    
    if scheduled > 0:
        print("Running scheduled tasks...")
        result = scheduler.run_scheduled_tasks()
        print("Results:", result)