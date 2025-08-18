#!/usr/bin/env python3
"""
Proof of Concept: Semantic Analysis of Happy Hour Deals

Data-hungry approach that collects all extraction data with rich context,
then applies intelligent semantic analysis for deduplication and ranking.
"""

import json
import re
from typing import List, Dict, Any, Set, Tuple
from datetime import datetime
from dataclasses import asdict
from collections import defaultdict, Counter
import logging

from src.models import Deal, DealType
from src.data_manager import DataManager

logger = logging.getLogger(__name__)

class SemanticDealAnalyzer:
    """
    Intelligent semantic analysis for deal deduplication and ranking.
    
    Uses extraction context, pattern analysis, and semantic similarity
    to consolidate multiple deal extractions into clean, distinct deals.
    """
    
    def __init__(self):
        self.time_patterns = [
            r'(\d{1,2})\s*(?::\d{2})?\s*(am|pm|AM|PM)\s*[–\-~]\s*(\d{1,2})\s*(?::\d{2})?\s*(am|pm|AM|PM)',  # "3 PM - 6 PM"
            r'(\d{1,2})\s*(?::\d{2})?\s*(pm|am|PM|AM)\s*[–\-~]\s*(close|Close|CLOSE)',  # "9 PM - Close"
            r'all\s+day',  # "All Day"
            r'daily',  # "Daily"
        ]
        
        self.day_patterns = [
            r'monday\s*[–\-~]\s*friday',  # "Monday - Friday"
            r'mon\s*[–\-~]\s*fri',  # "Mon - Fri" 
            r'weekdays?',  # "Weekday", "Weekdays"
            r'every\s+day',  # "Every day"
            r'daily',  # "Daily"
            r'thurs?\s*[–\-~]\s*sat',  # "Thurs - Sat", "Thu - Sat"
        ]
    
    def analyze_restaurant_deals(self, restaurant_slug: str, deals: List[Deal]) -> Dict[str, Any]:
        """
        Perform comprehensive semantic analysis on all deals for a restaurant.
        
        Args:
            restaurant_slug: Restaurant identifier
            deals: List of all extracted deals (including duplicates)
            
        Returns:
            Analysis results with consolidation recommendations
        """
        logger.info(f"Analyzing {len(deals)} deals for {restaurant_slug}")
        
        analysis = {
            'restaurant_slug': restaurant_slug,
            'total_deals': len(deals),
            'analyzed_at': datetime.now().isoformat(),
            'time_clusters': self._cluster_by_time_patterns(deals),
            'day_clusters': self._cluster_by_day_patterns(deals),
            'semantic_groups': self._group_by_semantic_similarity(deals),
            'confidence_distribution': self._analyze_confidence_scores(deals),
            'extraction_methods': self._analyze_extraction_methods(deals),
            'recommended_consolidation': None,  # Will be populated
            'quality_score': 0.0  # Will be calculated
        }
        
        # Generate consolidation recommendations
        analysis['recommended_consolidation'] = self._generate_consolidation_plan(deals, analysis)
        
        # Calculate overall quality score
        analysis['quality_score'] = self._calculate_quality_score(analysis)
        
        return analysis
    
    def _cluster_by_time_patterns(self, deals: List[Deal]) -> Dict[str, List[Dict]]:
        """Group deals by similar time patterns"""
        clusters = defaultdict(list)
        
        for deal in deals:
            time_signature = self._extract_time_signature(deal)
            clusters[time_signature].append({
                'deal_index': deals.index(deal),
                'start_time': deal.start_time,
                'end_time': deal.end_time,
                'raw_time_matches': deal.raw_time_matches,
                'confidence_score': deal.confidence_score,
                'source_text_snippet': deal.source_text[:100] if deal.source_text else None
            })
        
        return dict(clusters)
    
    def _cluster_by_day_patterns(self, deals: List[Deal]) -> Dict[str, List[Dict]]:
        """Group deals by similar day patterns"""
        clusters = defaultdict(list)
        
        for deal in deals:
            day_signature = self._extract_day_signature(deal)
            clusters[day_signature].append({
                'deal_index': deals.index(deal),
                'days_of_week': [day.value for day in deal.days_of_week],
                'raw_day_matches': deal.raw_day_matches,
                'confidence_score': deal.confidence_score,
                'source_text_snippet': deal.source_text[:100] if deal.source_text else None
            })
        
        return dict(clusters)
    
    def _group_by_semantic_similarity(self, deals: List[Deal]) -> List[Dict]:
        """Group deals by semantic content similarity"""
        groups = []
        
        # Simple similarity based on description content
        description_groups = defaultdict(list)
        for i, deal in enumerate(deals):
            # Extract key content words from description
            if deal.description:
                content_key = self._extract_content_key(deal.description)
                description_groups[content_key].append(i)
        
        for content_key, deal_indices in description_groups.items():
            if len(deal_indices) > 1:  # Only groups with multiple deals
                groups.append({
                    'content_key': content_key,
                    'deal_indices': deal_indices,
                    'similarity_score': self._calculate_group_similarity(
                        [deals[i] for i in deal_indices]
                    )
                })
        
        return groups
    
    def _extract_time_signature(self, deal: Deal) -> str:
        """Extract a normalized time signature for clustering"""
        if deal.is_all_day:
            return "all_day"
        
        if not deal.start_time or not deal.end_time:
            return "no_time"
        
        # Normalize time format
        start = self._normalize_time(deal.start_time)
        end = self._normalize_time(deal.end_time)
        
        return f"{start}_{end}"
    
    def _extract_day_signature(self, deal: Deal) -> str:
        """Extract a normalized day signature for clustering"""
        if not deal.days_of_week:
            return "no_days"
        
        days = sorted([day.value for day in deal.days_of_week])
        
        # Detect common patterns
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        weekend = ['saturday', 'sunday']
        all_days = weekdays + weekend
        
        if set(days) == set(weekdays):
            return "weekdays"
        elif set(days) == set(weekend):
            return "weekend"
        elif set(days) == set(all_days):
            return "daily"
        elif len(days) == 1:
            return f"single_{days[0]}"
        else:
            return "_".join(days)
    
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
    
    def _calculate_group_similarity(self, deals: List[Deal]) -> float:
        """Calculate similarity score for a group of deals"""
        if len(deals) < 2:
            return 1.0
        
        # Compare time patterns
        time_signatures = [self._extract_time_signature(deal) for deal in deals]
        time_similarity = len(set(time_signatures)) / len(time_signatures)
        
        # Compare day patterns  
        day_signatures = [self._extract_day_signature(deal) for deal in deals]
        day_similarity = len(set(day_signatures)) / len(day_signatures)
        
        # Compare confidence scores
        confidences = [deal.confidence_score for deal in deals]
        confidence_variance = 1.0 - (max(confidences) - min(confidences))
        
        # Weighted similarity score
        return (time_similarity * 0.4 + day_similarity * 0.4 + confidence_variance * 0.2)
    
    def _analyze_confidence_scores(self, deals: List[Deal]) -> Dict[str, Any]:
        """Analyze distribution of confidence scores"""
        scores = [deal.confidence_score for deal in deals]
        
        return {
            'mean': sum(scores) / len(scores) if scores else 0,
            'min': min(scores) if scores else 0,
            'max': max(scores) if scores else 0,
            'high_confidence_count': len([s for s in scores if s >= 0.8]),
            'low_confidence_count': len([s for s in scores if s < 0.6]),
            'distribution': Counter([round(s, 1) for s in scores])
        }
    
    def _analyze_extraction_methods(self, deals: List[Deal]) -> Dict[str, int]:
        """Analyze which extraction methods were used"""
        methods = [deal.extraction_method for deal in deals if deal.extraction_method]
        return Counter(methods)
    
    def _generate_consolidation_plan(self, deals: List[Deal], analysis: Dict[str, Any]) -> List[Dict]:
        """Generate recommendations for consolidating duplicate deals"""
        consolidation_plan = []
        
        # Group deals by time clusters
        for time_sig, time_cluster in analysis['time_clusters'].items():
            if len(time_cluster) > 1:
                # Multiple deals with same time pattern
                indices = [item['deal_index'] for item in time_cluster]
                cluster_deals = [deals[i] for i in indices]
                
                # Find the best representative deal
                best_deal_idx = self._select_best_deal(cluster_deals, indices)
                
                consolidation_plan.append({
                    'action': 'merge_time_duplicates',
                    'time_signature': time_sig,
                    'source_indices': indices,
                    'recommended_representative': best_deal_idx,
                    'confidence': max([deals[i].confidence_score for i in indices]),
                    'reasoning': f"Multiple deals with identical time pattern: {time_sig}"
                })
        
        # Look for semantic duplicates across different extraction methods
        for group in analysis['semantic_groups']:
            if group['similarity_score'] > 0.7 and len(group['deal_indices']) > 1:
                indices = group['deal_indices']
                cluster_deals = [deals[i] for i in indices]
                
                best_deal_idx = self._select_best_deal(cluster_deals, indices)
                
                consolidation_plan.append({
                    'action': 'merge_semantic_duplicates',
                    'content_key': group['content_key'],
                    'source_indices': indices,
                    'recommended_representative': best_deal_idx,
                    'similarity_score': group['similarity_score'],
                    'reasoning': f"Semantically similar deals with content: {group['content_key']}"
                })
        
        return consolidation_plan
    
    def _select_best_deal(self, deals: List[Deal], indices: List[int]) -> int:
        """Select the best representative deal from a cluster"""
        # Score deals based on multiple factors
        scores = []
        
        for i, deal in enumerate(deals):
            score = 0.0
            
            # Confidence score (40% weight)
            score += deal.confidence_score * 0.4
            
            # Completeness (30% weight) - has both time and days
            completeness = 0.0
            if deal.start_time and deal.end_time:
                completeness += 0.5
            if deal.days_of_week:
                completeness += 0.5
            score += completeness * 0.3
            
            # Source text quality (20% weight)
            text_quality = 0.0
            if deal.source_text:
                text_length = len(deal.source_text)
                text_quality = min(text_length / 200, 1.0)  # Normalize to 200 chars
            score += text_quality * 0.2
            
            # Extraction method preference (10% weight)
            method_score = 0.0
            if deal.extraction_method == 'universal_html_section':
                method_score = 1.0
            elif deal.extraction_method == 'structured_data':
                method_score = 0.8
            score += method_score * 0.1
            
            scores.append(score)
        
        # Return index of best deal
        best_local_idx = scores.index(max(scores))
        return indices[best_local_idx]
    
    def _calculate_quality_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall quality score for the analysis"""
        # Base on confidence distribution
        conf_dist = analysis['confidence_distribution']
        avg_confidence = conf_dist['mean']
        
        # Penalize for too many duplicates
        total_deals = analysis['total_deals']
        unique_time_clusters = len(analysis['time_clusters'])
        duplication_penalty = max(0, (total_deals - unique_time_clusters * 2) / total_deals)
        
        # Reward for high confidence deals
        high_conf_ratio = conf_dist['high_confidence_count'] / total_deals
        
        quality_score = avg_confidence * 0.5 + high_conf_ratio * 0.3 - duplication_penalty * 0.2
        
        return max(0.0, min(1.0, quality_score))


class PoCDatabase:
    """
    Proof of Concept database for semantic analysis experiments.
    
    Stores deals with rich extraction context for analysis and deduplication testing.
    """
    
    def __init__(self, database_path: str = "data/poc_deals.json"):
        self.database_path = database_path
        self.analyzer = SemanticDealAnalyzer()
        
    def populate_from_archive(self, restaurant_slugs: List[str]):
        """Populate PoC database from existing deal archives"""
        poc_data = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'purpose': 'semantic_analysis_poc',
                'target_restaurants': restaurant_slugs,
                'source': 'deals_archive'
            },
            'restaurants': {}
        }
        
        for slug in restaurant_slugs:
            logger.info(f"Loading deals for {slug}")
            
            # Load deals from archive directly
            deals = self._load_archived_deals(slug)
            
            if deals:
                # Convert to dictionaries with full context
                deal_dicts = []
                for deal in deals:
                    deal_dict = asdict(deal)
                    # Ensure datetime is serializable
                    if isinstance(deal_dict['scraped_at'], datetime):
                        deal_dict['scraped_at'] = deal_dict['scraped_at'].isoformat()
                    
                    # Convert enums to strings for JSON serialization
                    if 'deal_type' in deal_dict and hasattr(deal_dict['deal_type'], 'value'):
                        deal_dict['deal_type'] = deal_dict['deal_type'].value
                    
                    if 'days_of_week' in deal_dict:
                        deal_dict['days_of_week'] = [
                            day.value if hasattr(day, 'value') else day 
                            for day in deal_dict['days_of_week']
                        ]
                    
                    deal_dicts.append(deal_dict)
                
                # Perform semantic analysis
                analysis = self.analyzer.analyze_restaurant_deals(slug, deals)
                
                poc_data['restaurants'][slug] = {
                    'raw_deals': deal_dicts,
                    'semantic_analysis': analysis,
                    'deal_count': len(deals)
                }
                
                logger.info(f"Added {len(deals)} deals for {slug} with quality score {analysis['quality_score']:.2f}")
            else:
                logger.warning(f"No deals found for {slug}")
        
        # Save PoC database
        with open(self.database_path, 'w', encoding='utf-8') as f:
            json.dump(poc_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"PoC database saved to {self.database_path}")
        return poc_data
    
    def _load_archived_deals(self, restaurant_slug: str) -> List[Deal]:
        """Load deals from the most recent archive file for a restaurant"""
        import glob
        import os
        from src.models import Deal, DealType
        
        # Find the most recent archive file for this restaurant
        archive_pattern = f"data/deals_archive/{restaurant_slug}_*.json"
        archive_files = glob.glob(archive_pattern)
        
        if not archive_files:
            logger.warning(f"No archive files found for {restaurant_slug}")
            return []
        
        # Get the most recent file
        most_recent_file = max(archive_files, key=os.path.getctime)
        logger.info(f"Loading deals from {most_recent_file}")
        
        try:
            with open(most_recent_file, 'r', encoding='utf-8') as f:
                archive_data = json.load(f)
            
            deals = []
            for deal_dict in archive_data.get('deals', []):
                # Convert deal_type string to enum
                deal_type_str = deal_dict.get('deal_type', 'happy_hour')
                deal_dict['deal_type'] = DealType(deal_type_str)
                
                # Convert days_of_week strings to enums if present
                if 'days_of_week' in deal_dict:
                    from src.models import DayOfWeek
                    deal_dict['days_of_week'] = [DayOfWeek(day) for day in deal_dict['days_of_week']]
                
                # Convert scraped_at string back to datetime
                if 'scraped_at' in deal_dict and isinstance(deal_dict['scraped_at'], str):
                    deal_dict['scraped_at'] = datetime.fromisoformat(deal_dict['scraped_at'])
                
                # Handle missing fields with defaults
                deal_dict.setdefault('extraction_method', None)
                deal_dict.setdefault('source_text', None)
                deal_dict.setdefault('html_context', None)
                deal_dict.setdefault('extraction_patterns', [])
                deal_dict.setdefault('raw_time_matches', [])
                deal_dict.setdefault('raw_day_matches', [])
                
                # Create Deal object
                deal = Deal(**deal_dict)
                deals.append(deal)
            
            logger.info(f"Loaded {len(deals)} deals for {restaurant_slug}")
            return deals
            
        except Exception as e:
            logger.error(f"Error loading archived deals for {restaurant_slug}: {e}")
            return []
    
    def load_poc_data(self) -> Dict[str, Any]:
        """Load PoC database"""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"PoC database not found at {self.database_path}")
            return {}
    
    def generate_consolidation_report(self, restaurant_slug: str) -> Dict[str, Any]:
        """Generate detailed consolidation report for a restaurant"""
        poc_data = self.load_poc_data()
        
        if restaurant_slug not in poc_data.get('restaurants', {}):
            logger.error(f"Restaurant {restaurant_slug} not found in PoC database")
            return {}
        
        restaurant_data = poc_data['restaurants'][restaurant_slug]
        analysis = restaurant_data['semantic_analysis']
        
        report = {
            'restaurant_slug': restaurant_slug,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_deals': analysis['total_deals'],
                'quality_score': analysis['quality_score'],
                'recommended_final_deals': len(set([
                    plan['recommended_representative'] 
                    for plan in analysis['recommended_consolidation']
                ])) if analysis['recommended_consolidation'] else analysis['total_deals']
            },
            'consolidation_plan': analysis['recommended_consolidation'],
            'cluster_analysis': {
                'time_clusters': analysis['time_clusters'],
                'day_clusters': analysis['day_clusters']
            },
            'quality_metrics': {
                'confidence_distribution': analysis['confidence_distribution'],
                'extraction_methods': analysis['extraction_methods']
            }
        }
        
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize PoC database with our target restaurants
    poc_db = PoCDatabase()
    
    target_restaurants = [
        'thirsty-lion',
        'jax-fish-house', 
        'tamayo',
        'city-o-city',
        'ajax-downtown'
    ]
    
    # Populate database
    print("🔬 Creating Semantic Analysis PoC Database...")
    poc_data = poc_db.populate_from_archive(target_restaurants)
    
    # Generate reports for each restaurant
    print("\n📊 Generating Consolidation Reports...")
    for slug in target_restaurants:
        if slug in poc_data['restaurants']:
            report = poc_db.generate_consolidation_report(slug)
            print(f"\n🍽️  {slug.upper()}:")
            print(f"   Total Deals: {report['summary']['total_deals']}")
            print(f"   Quality Score: {report['summary']['quality_score']:.2f}")
            print(f"   Recommended Final: {report['summary']['recommended_final_deals']}")
            
            if report['consolidation_plan']:
                print(f"   Consolidation Actions:")
                for plan in report['consolidation_plan']:
                    print(f"     - {plan['action']}: {plan['reasoning']}")