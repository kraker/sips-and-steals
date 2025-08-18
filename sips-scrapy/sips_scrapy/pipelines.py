"""
Scrapy Pipelines for Sips and Steals

Processes extracted deals through validation, semantic analysis, and export.
Implements our proven data-hungry approach with intelligent deduplication.
"""

import json
import re
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime
from collections import defaultdict, Counter
from pathlib import Path

from .items import DealItem, RestaurantPageItem, DiscoveredLinkItem


class DealValidationPipeline:
    """
    Validates and cleans deal items before further processing.
    
    Ensures basic data quality while preserving our data-hungry approach.
    """
    
    def __init__(self):
        self.stats = {
            'items_processed': 0,
            'items_dropped': 0,
            'validation_errors': defaultdict(int)
        }
    
    def process_item(self, item, spider):
        self.stats['items_processed'] += 1
        
        # Only validate DealItems
        if not isinstance(item, DealItem):
            return item
        
        # Basic required fields
        if not item.get('title'):
            self._drop_item("Missing title", item)
        
        if not item.get('restaurant_slug'):
            self._drop_item("Missing restaurant_slug", item)
        
        # Clean and normalize data
        item = self._clean_item(item)
        
        return item
    
    def _clean_item(self, item):
        """Clean and normalize item data"""
        # Clean title and description
        if item.get('title'):
            item['title'] = item['title'].strip()
        
        if item.get('description'):
            item['description'] = item['description'].strip()
            # Remove extra whitespace
            item['description'] = re.sub(r'\s+', ' ', item['description'])
        
        # Ensure confidence score is in valid range
        confidence = item.get('confidence_score', 1.0)
        item['confidence_score'] = max(0.0, min(1.0, float(confidence)))
        
        # Ensure scraped_at is properly formatted
        if not item.get('scraped_at'):
            item['scraped_at'] = datetime.now().isoformat()
        
        # Clean day lists
        if item.get('days_of_week') and isinstance(item['days_of_week'], list):
            # Remove duplicates and normalize
            days = []
            for day in item['days_of_week']:
                if isinstance(day, str) and day.lower() not in days:
                    days.append(day.lower())
            item['days_of_week'] = days
        
        return item
    
    def _drop_item(self, reason, item):
        """Drop item with logging"""
        self.stats['items_dropped'] += 1
        self.stats['validation_errors'][reason] += 1
        raise DropItem(f"Validation failed: {reason}")
    
    def close_spider(self, spider):
        """Log validation statistics"""
        spider.logger.info(f"Validation stats: {dict(self.stats)}")


class SemanticAnalysisPipeline:
    """
    Applies our proven semantic analysis and deduplication algorithms.
    
    Groups deals by restaurant and applies intelligent consolidation
    based on time patterns, day patterns, and semantic similarity.
    """
    
    def __init__(self):
        self.restaurant_deals = defaultdict(list)
        self.processed_items = []
        
        # Time patterns for clustering (from our PoC)
        self.time_patterns = [
            r'(\d{1,2})\s*(?::\d{2})?\s*(am|pm|AM|PM)\s*[–\-~]\s*(\d{1,2})\s*(?::\d{2})?\s*(am|pm|AM|PM)',
            r'(\d{1,2})\s*[–\-~]\s*(\d{1,2})\s*(pm|am|PM|AM)',
            r'(\d{1,2})\s*(?::\d{2})?\s*(pm|am|PM|AM)\s*[–\-~]\s*(close|Close|CLOSE)',
            r'all\s+day',
            r'daily',
        ]
        
        self.day_patterns = [
            r'monday\s*[–\-~]\s*friday',
            r'mon\s*[–\-~]\s*fri',
            r'weekdays?',
            r'every\s+day',
            r'daily',
            r'thurs?\s*[–\-~]\s*sat',
        ]
    
    def process_item(self, item, spider):
        # Only process DealItems
        if isinstance(item, DealItem):
            restaurant_slug = item['restaurant_slug']
            self.restaurant_deals[restaurant_slug].append(dict(item))
        
        return item
    
    def close_spider(self, spider):
        """Apply semantic analysis when spider closes"""
        spider.logger.info("Starting semantic analysis and deduplication")
        
        total_deals_before = sum(len(deals) for deals in self.restaurant_deals.values())
        total_deals_after = 0
        
        for restaurant_slug, deals in self.restaurant_deals.items():
            if not deals:
                continue
            
            spider.logger.info(f"Analyzing {len(deals)} deals for {restaurant_slug}")
            
            # Apply our proven semantic analysis
            analysis = self._analyze_restaurant_deals(restaurant_slug, deals)
            consolidated_deals = self._apply_consolidation(deals, analysis)
            
            total_deals_after += len(consolidated_deals)
            
            spider.logger.info(f"Consolidated {len(deals)} → {len(consolidated_deals)} deals for {restaurant_slug}")
            
            # Store consolidated deals
            self.restaurant_deals[restaurant_slug] = consolidated_deals
        
        spider.logger.info(f"Semantic analysis complete: {total_deals_before} → {total_deals_after} deals")
    
    def _analyze_restaurant_deals(self, restaurant_slug: str, deals: List[Dict]) -> Dict[str, Any]:
        """Analyze deals for a restaurant using our proven algorithms"""
        analysis = {
            'restaurant_slug': restaurant_slug,
            'total_deals': len(deals),
            'time_clusters': self._cluster_by_time_patterns(deals),
            'day_clusters': self._cluster_by_day_patterns(deals),
            'semantic_groups': self._group_by_semantic_similarity(deals),
            'recommended_consolidation': []
        }
        
        # Generate consolidation recommendations
        analysis['recommended_consolidation'] = self._generate_consolidation_plan(deals, analysis)
        
        return analysis
    
    def _cluster_by_time_patterns(self, deals: List[Dict]) -> Dict[str, List[int]]:
        """Group deals by similar time patterns"""
        clusters = defaultdict(list)
        
        for i, deal in enumerate(deals):
            time_signature = self._extract_time_signature(deal)
            clusters[time_signature].append(i)
        
        return dict(clusters)
    
    def _cluster_by_day_patterns(self, deals: List[Dict]) -> Dict[str, List[int]]:
        """Group deals by similar day patterns"""
        clusters = defaultdict(list)
        
        for i, deal in enumerate(deals):
            day_signature = self._extract_day_signature(deal)
            clusters[day_signature].append(i)
        
        return dict(clusters)
    
    def _group_by_semantic_similarity(self, deals: List[Dict]) -> List[Dict]:
        """Group deals by semantic content similarity"""
        groups = []
        
        # Simple similarity based on description content
        description_groups = defaultdict(list)
        for i, deal in enumerate(deals):
            if deal.get('description'):
                content_key = self._extract_content_key(deal['description'])
                description_groups[content_key].append(i)
        
        for content_key, deal_indices in description_groups.items():
            if len(deal_indices) > 1:
                groups.append({
                    'content_key': content_key,
                    'deal_indices': deal_indices,
                    'similarity_score': 0.8  # Simplified scoring
                })
        
        return groups
    
    def _extract_time_signature(self, deal: Dict) -> str:
        """Extract normalized time signature for clustering"""
        if deal.get('is_all_day'):
            return "all_day"
        
        start_time = deal.get('start_time')
        end_time = deal.get('end_time')
        
        if not start_time or not end_time:
            return "no_time"
        
        # Normalize time format
        start_norm = self._normalize_time(start_time)
        end_norm = self._normalize_time(end_time)
        
        return f"{start_norm}_{end_norm}"
    
    def _extract_day_signature(self, deal: Dict) -> str:
        """Extract normalized day signature for clustering"""
        days = deal.get('days_of_week', [])
        
        if not days:
            return "no_days"
        
        days_sorted = sorted(days)
        
        # Detect common patterns
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        weekend = ['saturday', 'sunday']
        all_days = weekdays + weekend
        
        if set(days_sorted) == set(weekdays):
            return "weekdays"
        elif set(days_sorted) == set(weekend):
            return "weekend"
        elif set(days_sorted) == set(all_days):
            return "daily"
        elif len(days_sorted) == 1:
            return f"single_{days_sorted[0]}"
        else:
            return "_".join(days_sorted)
    
    def _normalize_time(self, time_str: str) -> str:
        """Normalize time string for comparison"""
        if not time_str:
            return "unknown"
        
        time_lower = time_str.lower().strip()
        
        # Handle special cases
        if 'close' in time_lower:
            return "close"
        if 'all' in time_lower and 'day' in time_lower:
            return "all_day"
        
        # Extract hour and period
        match = re.search(r'(\d{1,2})\s*(?::\d{2})?\s*(am|pm)', time_lower)
        if match:
            hour, period = match.groups()
            return f"{hour}{period}"
        
        return time_lower.replace(' ', '_')
    
    def _extract_content_key(self, description: str) -> str:
        """Extract key content words for semantic grouping"""
        if not description:
            return "empty"
        
        # Remove common words and extract key terms
        content = description.lower()
        
        # Remove time and day information for pure content comparison
        content = re.sub(r'\b\d{1,2}\s*(?:am|pm)\b', '', content)
        content = re.sub(r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', '', content)
        content = re.sub(r'\btime:\s*', '', content)
        content = re.sub(r'\bdays:\s*', '', content)
        
        # Extract meaningful words
        words = re.findall(r'\b[a-z]{3,}\b', content)
        key_words = [w for w in words if w not in ['happy', 'hour', 'found', 'pattern']]
        
        return '_'.join(sorted(set(key_words))[:3])  # Top 3 unique words
    
    def _generate_consolidation_plan(self, deals: List[Dict], analysis: Dict[str, Any]) -> List[Dict]:
        """Generate recommendations for consolidating duplicate deals"""
        consolidation_plan = []
        
        # Look for time-based duplicates
        for time_sig, indices in analysis['time_clusters'].items():
            if len(indices) > 1:
                best_idx = self._select_best_deal([deals[i] for i in indices], indices)
                consolidation_plan.append({
                    'action': 'merge_time_duplicates',
                    'source_indices': indices,
                    'recommended_representative': best_idx,
                    'reasoning': f"Multiple deals with identical time pattern: {time_sig}"
                })
        
        # Look for semantic duplicates
        for group in analysis['semantic_groups']:
            if len(group['deal_indices']) > 1:
                indices = group['deal_indices']
                best_idx = self._select_best_deal([deals[i] for i in indices], indices)
                consolidation_plan.append({
                    'action': 'merge_semantic_duplicates',
                    'source_indices': indices,
                    'recommended_representative': best_idx,
                    'reasoning': f"Semantically similar deals"
                })
        
        return consolidation_plan
    
    def _select_best_deal(self, deals: List[Dict], indices: List[int]) -> int:
        """Select best representative deal from a cluster"""
        scores = []
        
        for i, deal in enumerate(deals):
            score = 0.0
            
            # Confidence score (40% weight)
            score += deal.get('confidence_score', 0.5) * 0.4
            
            # Completeness (30% weight)
            completeness = 0.0
            if deal.get('start_time') and deal.get('end_time'):
                completeness += 0.5
            if deal.get('days_of_week'):
                completeness += 0.5
            score += completeness * 0.3
            
            # Source text quality (20% weight)
            text_quality = 0.0
            source_text = deal.get('source_text', '')
            if source_text:
                text_quality = min(len(source_text) / 200, 1.0)
            score += text_quality * 0.2
            
            # Extraction method preference (10% weight)
            method_score = 0.8 if deal.get('extraction_method') == 'universal_html_section' else 0.5
            score += method_score * 0.1
            
            scores.append(score)
        
        # Return index of best deal
        best_local_idx = scores.index(max(scores))
        return indices[best_local_idx]
    
    def _apply_consolidation(self, deals: List[Dict], analysis: Dict[str, Any]) -> List[Dict]:
        """Apply consolidation plan to reduce duplicate deals"""
        if not analysis['recommended_consolidation']:
            return deals  # No consolidation needed
        
        # Track which deals to keep
        deals_to_keep = set(range(len(deals)))
        
        for plan in analysis['recommended_consolidation']:
            source_indices = plan['source_indices']
            best_idx = plan['recommended_representative']
            
            # Remove all source indices except the best one
            for idx in source_indices:
                if idx != best_idx:
                    deals_to_keep.discard(idx)
        
        # Return only the deals we want to keep
        consolidated = [deals[i] for i in sorted(deals_to_keep)]
        return consolidated


class JSONExportPipeline:
    """
    Export processed deals to JSON files for integration with existing system.
    """
    
    def __init__(self, output_dir='data'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.deals = []
        self.discovered_pages = []
        self.discovered_links = []
    
    def process_item(self, item, spider):
        # Collect items by type
        if isinstance(item, DealItem):
            self.deals.append(dict(item))
        elif isinstance(item, RestaurantPageItem):
            self.discovered_pages.append(dict(item))
        elif isinstance(item, DiscoveredLinkItem):
            self.discovered_links.append(dict(item))
        
        return item
    
    def close_spider(self, spider):
        """Export collected data to JSON files"""
        # Export deals
        if self.deals:
            deals_file = self.output_dir / 'scrapy_deals.json'
            with open(deals_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'exported_at': datetime.now().isoformat(),
                    'total_deals': len(self.deals),
                    'deals': self.deals
                }, f, indent=2, ensure_ascii=False)
            
            spider.logger.info(f"Exported {len(self.deals)} deals to {deals_file}")
        
        # Export discovered pages  
        if self.discovered_pages:
            pages_file = self.output_dir / 'discovered_pages.json'
            with open(pages_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'exported_at': datetime.now().isoformat(),
                    'total_pages': len(self.discovered_pages),
                    'pages': self.discovered_pages
                }, f, indent=2, ensure_ascii=False)
            
            spider.logger.info(f"Exported {len(self.discovered_pages)} discovered pages to {pages_file}")
        
        # Export discovered links
        if self.discovered_links:
            links_file = self.output_dir / 'discovered_links.json'
            with open(links_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'exported_at': datetime.now().isoformat(),
                    'total_links': len(self.discovered_links),
                    'links': self.discovered_links
                }, f, indent=2, ensure_ascii=False)
            
            spider.logger.info(f"Exported {len(self.discovered_links)} discovered links to {links_file}")


# Exception for dropping items
class DropItem(Exception):
    pass