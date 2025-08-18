"""
Scrapy Pipelines for Sips and Steals

Processes extracted deals through validation, semantic analysis, and export.
Implements our proven data-hungry approach with intelligent deduplication.
"""

import json
import re
from typing import Dict, List, Any, Set, Tuple, Optional
from datetime import datetime
from collections import defaultdict, Counter
from pathlib import Path

from .items import DealItem, RestaurantPageItem, DiscoveredLinkItem, RestaurantProfileItem, MenuPricingItem, HappyHourDealsItem


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


class RestaurantProfilePipeline:
    """
    Processes and validates restaurant profiles extracted from websites.
    
    Handles contact info validation, address enhancement, and data quality scoring.
    """
    
    def __init__(self):
        self.profiles = []
        self.stats = {
            'profiles_processed': 0,
            'profiles_enhanced': 0,
            'validation_issues': defaultdict(int)
        }
    
    def process_item(self, item, spider):
        # Only process RestaurantProfileItems
        if not isinstance(item, RestaurantProfileItem):
            return item
        
        self.stats['profiles_processed'] += 1
        
        # Validate and enhance the profile
        enhanced_item = self._enhance_profile(item, spider)
        
        # Store for final export
        self.profiles.append(dict(enhanced_item))
        
        return enhanced_item
    
    def _enhance_profile(self, item, spider) -> RestaurantProfileItem:
        """Enhance and validate profile data"""
        enhanced_count = 0
        
        # Validate and clean phone numbers
        if item.get('primary_phone'):
            cleaned_phone = self._validate_phone(item['primary_phone'])
            if cleaned_phone:
                item['primary_phone'] = cleaned_phone
                enhanced_count += 1
            else:
                self.stats['validation_issues']['invalid_phone'] += 1
                item['primary_phone'] = None
        
        if item.get('reservation_phone'):
            cleaned_phone = self._validate_phone(item['reservation_phone'])
            if cleaned_phone:
                item['reservation_phone'] = cleaned_phone
                enhanced_count += 1
            else:
                item['reservation_phone'] = None
        
        # Validate and clean email addresses
        email_fields = ['general_email', 'reservations_email', 'events_email']
        for field in email_fields:
            if item.get(field):
                if self._validate_email(item[field]):
                    enhanced_count += 1
                else:
                    self.stats['validation_issues']['invalid_email'] += 1
                    item[field] = None
        
        # Enhance social media handles
        social_fields = ['instagram', 'facebook', 'twitter', 'tiktok']
        for field in social_fields:
            if item.get(field):
                cleaned_handle = self._clean_social_handle(item[field])
                if cleaned_handle:
                    item[field] = cleaned_handle
                    enhanced_count += 1
        
        # Validate operating hours format
        if item.get('operating_hours'):
            validated_hours = self._validate_operating_hours(item['operating_hours'])
            if validated_hours:
                item['operating_hours'] = validated_hours
                enhanced_count += 1
            else:
                self.stats['validation_issues']['invalid_hours'] += 1
        
        # Enhance address data (if we found any)
        if any(item.get(field) for field in ['street_address', 'city', 'state', 'zip_code']):
            enhanced_address = self._enhance_address_data(item)
            if enhanced_address:
                # Update item with enhanced address fields
                for field, value in enhanced_address.items():
                    item[field] = value
                enhanced_count += 1
        
        # Update quality scores based on enhancements
        if enhanced_count > 0:
            self.stats['profiles_enhanced'] += 1
            current_confidence = item.get('confidence_score', 0.7)
            enhancement_boost = min(0.2, enhanced_count * 0.05)
            item['confidence_score'] = min(0.95, current_confidence + enhancement_boost)
        
        # Calculate final completeness score
        item['completeness_score'] = self._calculate_completeness_score(item)
        
        return item
    
    def _validate_phone(self, phone: str) -> Optional[str]:
        """Validate and format phone number"""
        if not phone:
            return None
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Validate US phone numbers (10 digits, or 11 with leading 1)
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            digits = digits[1:]  # Remove leading 1
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        
        return None  # Invalid format
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email.strip().lower()) is not None
    
    def _clean_social_handle(self, handle: str) -> Optional[str]:
        """Clean and normalize social media handle"""
        if not handle:
            return None
        
        # Remove @ symbol, trailing slashes, and URL parameters
        cleaned = handle.strip('@/').split('?')[0].split('#')[0]
        
        # Remove domain if it's a full URL
        if '/' in cleaned:
            cleaned = cleaned.split('/')[-1]
        
        # Validate handle format (basic alphanumeric + underscore/dot)
        if re.match(r'^[a-zA-Z0-9_.]+$', cleaned) and len(cleaned) > 0:
            return cleaned
        
        return None
    
    def _validate_operating_hours(self, hours: Dict) -> Optional[Dict]:
        """Validate operating hours format"""
        if not isinstance(hours, dict):
            return None
        
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        time_pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'  # HH:MM format
        
        validated_hours = {}
        
        for day, day_hours in hours.items():
            if day.lower() not in valid_days:
                continue
            
            if not isinstance(day_hours, dict):
                continue
            
            # Check for 'closed' status
            if day_hours.get('closed'):
                validated_hours[day.lower()] = {'closed': True}
                continue
            
            # Validate open/close times
            open_time = day_hours.get('open')
            close_time = day_hours.get('close')
            
            if (open_time and close_time and 
                re.match(time_pattern, open_time) and 
                re.match(time_pattern, close_time)):
                validated_hours[day.lower()] = {
                    'open': open_time,
                    'close': close_time
                }
        
        return validated_hours if validated_hours else None
    
    def _enhance_address_data(self, item) -> Optional[Dict]:
        """Enhance address data with validation"""
        address_data = {}
        
        # Collect address components
        street = item.get('street_address')
        city = item.get('city')
        state = item.get('state')
        zip_code = item.get('zip_code')
        
        # Validate and clean components
        if street:
            # Basic street address validation
            if re.search(r'\d+\s+[A-Za-z\s]+', street):
                address_data['street_address'] = street.strip()
        
        if city:
            address_data['city'] = city.strip().title()
        
        if state:
            # Normalize state to CO format
            state_cleaned = state.strip().upper()
            if state_cleaned in ['CO', 'COLORADO']:
                address_data['state'] = 'CO'
        
        if zip_code:
            # Validate Colorado zip code format
            zip_match = re.match(r'^(80\d{3})(?:-\d{4})?$', zip_code.strip())
            if zip_match:
                address_data['zip_code'] = zip_match.group(1)  # Use 5-digit format
        
        return address_data if address_data else None
    
    def _calculate_completeness_score(self, item) -> float:
        """Calculate how complete the profile is"""
        # Define important fields and their weights
        field_weights = {
            # Contact info (30%)
            'primary_phone': 0.15,
            'general_email': 0.15,
            
            # Business info (25%)
            'operating_hours': 0.15,
            'business_status': 0.05,
            'price_range': 0.05,
            
            # Service info (20%)
            'accepts_reservations': 0.05,
            'offers_delivery': 0.05,
            'offers_takeout': 0.05,
            'opentable_url': 0.05,
            
            # Social media (15%)
            'instagram': 0.05,
            'facebook': 0.05,
            'twitter': 0.05,
            
            # Address (10%)
            'street_address': 0.05,
            'zip_code': 0.05,
        }
        
        total_score = 0.0
        for field, weight in field_weights.items():
            if item.get(field):
                total_score += weight
        
        return min(1.0, total_score)
    
    def close_spider(self, spider):
        """Export restaurant profiles and log statistics"""
        spider.logger.info(f"Restaurant profile pipeline stats: {dict(self.stats)}")
        
        # Export profiles to JSON
        if self.profiles:
            output_dir = Path('data')
            output_dir.mkdir(exist_ok=True)
            
            profiles_file = output_dir / 'restaurant_profiles.json'
            with open(profiles_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'exported_at': datetime.now().isoformat(),
                    'total_profiles': len(self.profiles),
                    'profiles': self.profiles,
                    'pipeline_stats': dict(self.stats)
                }, f, indent=2, ensure_ascii=False)
            
            spider.logger.info(f"Exported {len(self.profiles)} restaurant profiles to {profiles_file}")
        
        # Log summary statistics
        if self.stats['profiles_processed'] > 0:
            enhancement_rate = (self.stats['profiles_enhanced'] / self.stats['profiles_processed']) * 100
            avg_completeness = sum(p.get('completeness_score', 0) for p in self.profiles) / len(self.profiles)
            
            spider.logger.info(f"Profile enhancement rate: {enhancement_rate:.1f}%")
            spider.logger.info(f"Average profile completeness: {avg_completeness:.2f}")


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
        self.restaurant_profiles = []
    
    def process_item(self, item, spider):
        # Collect items by type
        if isinstance(item, DealItem):
            self.deals.append(dict(item))
        elif isinstance(item, RestaurantPageItem):
            self.discovered_pages.append(dict(item))
        elif isinstance(item, DiscoveredLinkItem):
            self.discovered_links.append(dict(item))
        elif isinstance(item, RestaurantProfileItem):
            self.restaurant_profiles.append(dict(item))
        
        return item
    
    def close_spider(self, spider):
        """Export collected data to JSON files"""
        # Export deals
        if self.deals:
            deals_file = self.output_dir / 'deals.json'
            with open(deals_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'exported_at': datetime.now().isoformat(),
                    'total_deals': len(self.deals),
                    'deals': self.deals
                }, f, indent=2, ensure_ascii=False)
            
            spider.logger.info(f"Exported {len(self.deals)} deals to {deals_file}")
        
        # Export discovered pages  
        if self.discovered_pages:
            pages_file = self.output_dir / 'discovered_urls.json'
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
        
        # Export restaurant profiles
        if self.restaurant_profiles:
            profiles_file = self.output_dir / 'restaurant_profiles_export.json'
            with open(profiles_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'exported_at': datetime.now().isoformat(),
                    'total_profiles': len(self.restaurant_profiles),
                    'profiles': self.restaurant_profiles
                }, f, indent=2, ensure_ascii=False)
            
            spider.logger.info(f"Exported {len(self.restaurant_profiles)} restaurant profiles to {profiles_file}")


class MenuPricingPipeline:
    """
    Pipeline for processing menu pricing data.
    
    Validates pricing data, normalizes price formats, and exports
    comprehensive pricing intelligence for restaurants.
    """
    
    def __init__(self):
        self.pricing_data = []
        self.stats = {
            'items_processed': 0,
            'price_items_extracted': 0,
            'restaurants_covered': set(),
            'menu_types_found': defaultdict(int),
        }
    
    def process_item(self, item, spider):
        # Only process MenuPricingItems
        if not isinstance(item, MenuPricingItem):
            return item
        
        self.stats['items_processed'] += 1
        self.stats['restaurants_covered'].add(item.get('restaurant_slug', 'unknown'))
        self.stats['menu_types_found'][item.get('menu_type', 'unknown')] += 1
        
        # Count extracted price items
        price_items = item.get('price_items', [])
        self.stats['price_items_extracted'] += len(price_items)
        
        # Validate and normalize pricing data
        item = self._normalize_pricing_data(item)
        
        # Store for export
        self.pricing_data.append(dict(item))
        
        spider.logger.debug(f"Processed pricing data for {item.get('restaurant_name')} "
                          f"({item.get('menu_type')}) - {len(price_items)} items")
        
        return item
    
    def _normalize_pricing_data(self, item):
        """Normalize and validate pricing data with enhanced price classification"""
        # Ensure price items is a list of dictionaries
        price_items = item.get('price_items', [])
        if price_items and isinstance(price_items[0], dict):
            # Already normalized
            pass
        
        # Ensure numeric price fields
        for field in ['average_price', 'min_price', 'max_price']:
            value = item.get(field, 0)
            if isinstance(value, str):
                try:
                    item[field] = float(value.replace('$', '').replace(',', ''))
                except ValueError:
                    item[field] = 0.0
        
        # Enhanced price range classification
        item['price_range_detected'] = self._classify_price_range(
            item.get('average_price', 0),
            item.get('min_price', 0),
            item.get('max_price', 0),
            item.get('menu_type', 'dinner'),
            len(price_items)
        )
        
        return item
    
    def _classify_price_range(self, avg_price: float, min_price: float, max_price: float, 
                            menu_type: str, item_count: int) -> str:
        """
        Enhanced price range classification using multiple factors.
        
        Considers menu type, price distribution, and Denver market standards.
        """
        if avg_price == 0 or item_count == 0:
            return '$'  # Default for no pricing data
        
        # Adjust thresholds based on menu type
        if menu_type == 'happy_hour':
            # Happy hour prices are typically 20-40% lower
            thresholds = {'$': 12, '$$': 18, '$$$': 28}
        elif menu_type == 'brunch':
            # Brunch typically falls between lunch and dinner
            thresholds = {'$': 16, '$$': 24, '$$$': 35}
        elif menu_type == 'lunch':
            # Lunch prices are generally lower
            thresholds = {'$': 14, '$$': 22, '$$$': 32}
        elif menu_type == 'wine':
            # Wine pricing has different scale (per glass)
            thresholds = {'$': 10, '$$': 15, '$$$': 25}
        else:  # dinner and general
            # Standard dinner pricing thresholds for Denver market
            thresholds = {'$': 18, '$$': 28, '$$$': 40}
        
        # Consider price distribution - high max price can bump up category
        price_spread = max_price - min_price if max_price > min_price else 0
        
        # Base classification on average price
        if avg_price <= thresholds['$']:
            base_category = '$'
        elif avg_price <= thresholds['$$']:
            base_category = '$$'
        elif avg_price <= thresholds['$$$']:
            base_category = '$$$'
        else:
            base_category = '$$$$'
        
        # Adjust based on max price and spread
        if base_category in ['$', '$$'] and max_price > thresholds['$$$']:
            # High-end items present, bump up one category
            if base_category == '$':
                return '$$'
            elif base_category == '$$':
                return '$$$'
        
        # Special case for very high-end restaurants
        if max_price > 60 and avg_price > 35:
            return '$$$$'
        
        return base_category
    
    def close_spider(self, spider):
        """Export pricing data when spider closes"""
        if not self.pricing_data:
            spider.logger.info("No pricing data to export")
            return
        
        # Create output directory
        output_dir = Path('data')
        output_dir.mkdir(exist_ok=True)
        
        # Export pricing data
        pricing_file = output_dir / 'cache/menu_pricing_debug.json'
        with open(pricing_file, 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'total_menus': len(self.pricing_data),
                'total_price_items': self.stats['price_items_extracted'],
                'restaurants_covered': len(self.stats['restaurants_covered']),
                'menu_types': dict(self.stats['menu_types_found']),
                'pricing_data': self.pricing_data
            }, f, indent=2, ensure_ascii=False)
        
        spider.logger.info(f"Exported {len(self.pricing_data)} menu pricing records to {pricing_file}")
        spider.logger.info(f"Menu pricing pipeline stats: {dict(self.stats)}")
        
        # Create pricing summary for integration with restaurant profiles
        self._create_pricing_summary(output_dir)
    
    def _create_pricing_summary(self, output_dir):
        """Create a summary of pricing data for restaurant profile integration"""
        pricing_summary = {}
        
        for pricing_item in self.pricing_data:
            restaurant_slug = pricing_item.get('restaurant_slug')
            if not restaurant_slug:
                continue
            
            if restaurant_slug not in pricing_summary:
                pricing_summary[restaurant_slug] = {
                    'restaurant_slug': restaurant_slug,
                    'restaurant_name': pricing_item.get('restaurant_name'),
                    'pricing_data_available': True,
                    'price_ranges_by_menu': {},
                    'overall_price_range': None,
                    'average_prices': [],
                    'menu_types_found': [],
                    'total_price_items': 0,
                    'confidence_scores': []
                }
            
            summary = pricing_summary[restaurant_slug]
            menu_type = pricing_item.get('menu_type', 'unknown')
            
            # Aggregate menu-specific data
            summary['menu_types_found'].append(menu_type)
            summary['price_ranges_by_menu'][menu_type] = pricing_item.get('price_range_detected', '$')
            summary['total_price_items'] += len(pricing_item.get('price_items', []))
            summary['confidence_scores'].append(pricing_item.get('confidence_score', 0.0))
            
            # Collect average prices for overall calculation
            avg_price = pricing_item.get('average_price', 0)
            if avg_price > 0:
                summary['average_prices'].append(avg_price)
        
        # Calculate overall metrics for each restaurant
        for restaurant_slug, summary in pricing_summary.items():
            # Determine overall price range (prioritize dinner, then highest range)
            if 'dinner' in summary['price_ranges_by_menu']:
                summary['overall_price_range'] = summary['price_ranges_by_menu']['dinner']
            elif summary['price_ranges_by_menu']:
                # Use the highest price range found
                ranges = list(summary['price_ranges_by_menu'].values())
                range_order = {'$': 1, '$$': 2, '$$$': 3, '$$$$': 4}
                highest_range = max(ranges, key=lambda x: range_order.get(x, 1))
                summary['overall_price_range'] = highest_range
            else:
                summary['overall_price_range'] = '$'
            
            # Calculate overall average price
            if summary['average_prices']:
                summary['overall_average_price'] = round(
                    sum(summary['average_prices']) / len(summary['average_prices']), 2
                )
                summary['price_range_min'] = round(min(summary['average_prices']), 2)
                summary['price_range_max'] = round(max(summary['average_prices']), 2)
            else:
                summary['overall_average_price'] = 0
                summary['price_range_min'] = 0
                summary['price_range_max'] = 0
            
            # Calculate overall confidence
            if summary['confidence_scores']:
                summary['overall_confidence'] = round(
                    sum(summary['confidence_scores']) / len(summary['confidence_scores']), 2
                )
            else:
                summary['overall_confidence'] = 0.0
            
            # Clean up temporary lists
            summary['menu_types_found'] = list(set(summary['menu_types_found']))
            del summary['average_prices']
            del summary['confidence_scores']
        
        # Export pricing summary
        summary_file = output_dir / 'pricing_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'total_restaurants_with_pricing': len(pricing_summary),
                'pricing_summary': pricing_summary
            }, f, indent=2, ensure_ascii=False)
        
        return pricing_summary


class HappyHourDealsPipeline:
    """
    Pipeline for processing happy hour deals data.
    
    Validates deals, normalizes time formats, and exports
    structured happy hour deals for restaurants.
    """
    
    def __init__(self):
        self.deals_data = []
        self.stats = {
            'items_processed': 0,
            'deals_extracted': 0,
            'restaurants_covered': set(),
            'timeframes_found': set(),
            'days_found': set(),
        }
    
    def process_item(self, item, spider):
        # Only process HappyHourDealsItems
        if not isinstance(item, HappyHourDealsItem):
            return item
        
        self.stats['items_processed'] += 1
        self.stats['restaurants_covered'].add(item.get('restaurant_slug', 'unknown'))
        
        # Count extracted deals
        deals = item.get('happy_hour_deals', [])
        self.stats['deals_extracted'] += len(deals)
        
        # Collect timeframes and days
        timeframes = item.get('timeframes_found', [])
        days = item.get('days_found', [])
        self.stats['timeframes_found'].update(timeframes)
        self.stats['days_found'].update(days)
        
        # Validate and normalize deals data
        item = self._normalize_deals_data(item)
        
        # Store for export
        self.deals_data.append(dict(item))
        
        spider.logger.debug(f"Processed happy hour deals for {item.get('restaurant_name')} "
                          f"- {len(deals)} deals")
        
        return item
    
    def _normalize_deals_data(self, item):
        """Normalize and validate happy hour deals data"""
        deals = item.get('happy_hour_deals', [])
        normalized_deals = []
        
        for deal in deals:
            # Ensure deal is a dictionary
            if isinstance(deal, dict):
                # Normalize price format
                price = deal.get('price', '')
                if price and not price.startswith('$'):
                    deal['price'] = f"${price}"
                
                # Validate price range (reasonable happy hour pricing)
                if price:
                    try:
                        price_num = float(price.replace('$', ''))
                        if 3 <= price_num <= 50:  # Reasonable happy hour range
                            normalized_deals.append(deal)
                    except ValueError:
                        # Keep deals without valid prices for context
                        normalized_deals.append(deal)
                else:
                    normalized_deals.append(deal)
        
        item['happy_hour_deals'] = normalized_deals
        return item
    
    def close_spider(self, spider):
        """Export happy hour deals data when spider closes"""
        if not self.deals_data:
            spider.logger.info("No happy hour deals data to export")
            return
        
        # Create output directory
        output_dir = Path('data')
        output_dir.mkdir(exist_ok=True)
        
        # Export deals data
        deals_file = output_dir / 'cache/happy_hour_deals_debug.json'
        with open(deals_file, 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'total_pages_processed': len(self.deals_data),
                'total_deals_extracted': self.stats['deals_extracted'],
                'restaurants_covered': len(self.stats['restaurants_covered']),
                'timeframes_found': list(self.stats['timeframes_found']),
                'days_found': list(self.stats['days_found']),
                'deals_data': self.deals_data
            }, f, indent=2, ensure_ascii=False)
        
        spider.logger.info(f"Exported {len(self.deals_data)} happy hour deals records to {deals_file}")
        
        # Create summary for integration
        self._create_deals_summary(output_dir)
        
        spider.logger.info(f"Happy hour deals pipeline stats: {dict(self.stats)}")
    
    def _create_deals_summary(self, output_dir):
        """Create a summary of happy hour deals for restaurant integration"""
        deals_summary = {}
        
        for deals_item in self.deals_data:
            restaurant_slug = deals_item.get('restaurant_slug')
            if not restaurant_slug:
                continue
            
            if restaurant_slug not in deals_summary:
                deals_summary[restaurant_slug] = {
                    'restaurant_slug': restaurant_slug,
                    'restaurant_name': deals_item.get('restaurant_name'),
                    'happy_hour_data_available': True,
                    'total_deals': 0,
                    'food_deals': 0,
                    'drink_deals': 0,
                    'timeframes': [],
                    'days': [],
                    'location_restrictions': [],
                    'average_food_price': 0,
                    'average_drink_price': 0,
                    'confidence_score': 0
                }
            
            summary = deals_summary[restaurant_slug]
            deals = deals_item.get('happy_hour_deals', [])
            
            # Aggregate deal data
            food_prices = []
            drink_prices = []
            
            for deal in deals:
                summary['total_deals'] += 1
                
                deal_type = deal.get('deal_type', 'unknown')
                if deal_type == 'food':
                    summary['food_deals'] += 1
                elif deal_type == 'drink':
                    summary['drink_deals'] += 1
                
                # Collect prices for averaging
                price = deal.get('price', '')
                if price and price.startswith('$'):
                    try:
                        price_num = float(price.replace('$', ''))
                        if deal_type == 'food':
                            food_prices.append(price_num)
                        elif deal_type == 'drink':
                            drink_prices.append(price_num)
                    except ValueError:
                        pass
            
            # Update timeframes and days
            summary['timeframes'].extend(deals_item.get('timeframes_found', []))
            summary['days'].extend(deals_item.get('days_found', []))
            summary['location_restrictions'].extend(deals_item.get('location_restrictions', []))
            
            # Calculate averages
            if food_prices:
                summary['average_food_price'] = round(sum(food_prices) / len(food_prices), 2)
            if drink_prices:
                summary['average_drink_price'] = round(sum(drink_prices) / len(drink_prices), 2)
            
            # Set confidence score
            summary['confidence_score'] = deals_item.get('confidence_score', 0.0)
        
        # Clean up duplicates in lists
        for restaurant_slug, summary in deals_summary.items():
            summary['timeframes'] = list(set(summary['timeframes']))
            summary['days'] = list(set(summary['days']))
            summary['location_restrictions'] = list(set(summary['location_restrictions']))
        
        # Export deals summary
        summary_file = output_dir / 'happy_hour_deals_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'total_restaurants_with_deals': len(deals_summary),
                'deals_summary': deals_summary
            }, f, indent=2, ensure_ascii=False)
        
        return deals_summary


# Exception for dropping items
class DropItem(Exception):
    pass