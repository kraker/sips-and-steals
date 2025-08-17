#!/usr/bin/env python3
"""
Data validation and quality checking system
Ensures scraped data meets quality standards and flags anomalies
"""

import re
import logging
from datetime import datetime, time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

from models import Deal, Restaurant, DealType, DayOfWeek, DealValidator

logger = logging.getLogger(__name__)


class QualityIssueLevel(Enum):
    """Severity levels for quality issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class QualityIssue:
    """Represents a quality issue found in the data"""
    level: QualityIssueLevel
    message: str
    field: Optional[str] = None
    suggested_fix: Optional[str] = None
    confidence: float = 1.0  # 0.0-1.0, confidence this is actually an issue


class QualityChecker:
    """
    Advanced quality checking for restaurant and deal data
    Detects anomalies, validates formats, and suggests improvements
    """
    
    def __init__(self):
        # Common time patterns for validation
        self.time_patterns = {
            'standard': r'^\d{1,2}:\d{2}\s*(AM|PM)$',
            'simple': r'^\d{1,2}\s*(AM|PM)$',
            'all_day': r'^(All Day|Open|Close)$',
            'range': r'^\d{1,2}(?::\d{2})?\s*(AM|PM)\s*-\s*\d{1,2}(?::\d{2})?\s*(AM|PM)$'
        }
        
        # Common price patterns
        self.price_patterns = {
            'dollar': r'^\$\d+(?:\.\d{2})?$',
            'range': r'^\$\d+(?:\.\d{2})?\s*-\s*\$?\d+(?:\.\d{2})?$',
            'percentage': r'^\d+%\s*off$',
            'free': r'^(Free|No charge)$',
            'special': r'^\d+¢$'
        }
        
        # Suspicious patterns that might indicate scraping errors
        self.suspicious_patterns = [
            r'javascript',
            r'function\s*\(',
            r'<[^>]+>',  # HTML tags
            r'Error\s*\d+',
            r'Not\s*Found',
            r'Page\s*Not\s*Found',
            r'Access\s*Denied'
        ]
        
        # Keep statistics for anomaly detection
        self.deal_stats = {
            'typical_title_length': (10, 50),
            'typical_description_length': (20, 200),
            'common_start_times': ['3:00 PM', '4:00 PM', '5:00 PM'],
            'common_end_times': ['6:00 PM', '7:00 PM', '8:00 PM'],
            'typical_price_range': (3, 15)
        }
    
    def check_restaurant_quality(self, restaurant: Restaurant) -> List[QualityIssue]:
        """Check quality of restaurant data"""
        issues = []
        
        # Basic data validation
        if not restaurant.name or len(restaurant.name.strip()) < 2:
            issues.append(QualityIssue(
                level=QualityIssueLevel.ERROR,
                message="Restaurant name is missing or too short",
                field="name"
            ))
        
        if restaurant.website and not self._is_valid_url(restaurant.website):
            issues.append(QualityIssue(
                level=QualityIssueLevel.WARNING,
                message="Website URL appears invalid",
                field="website",
                suggested_fix="Check URL format and accessibility"
            ))
        
        # Address validation
        if restaurant.address and not self._is_reasonable_address(restaurant.address):
            issues.append(QualityIssue(
                level=QualityIssueLevel.WARNING,
                message="Address format seems unusual",
                field="address",
                confidence=0.7
            ))
        
        # Check live deals quality
        if restaurant.live_deals:
            for i, deal in enumerate(restaurant.live_deals):
                deal_issues = self.check_deal_quality(deal)
                for issue in deal_issues:
                    issue.field = f"live_deals[{i}].{issue.field}" if issue.field else f"live_deals[{i}]"
                    issues.append(issue)
        
        # Check for data freshness
        if restaurant.deals_last_updated:
            days_old = (datetime.now() - restaurant.deals_last_updated).days
            if days_old > 7:
                issues.append(QualityIssue(
                    level=QualityIssueLevel.WARNING,
                    message=f"Deal data is {days_old} days old",
                    field="deals_last_updated",
                    suggested_fix="Consider increasing scraping frequency"
                ))
        
        # Check scraping configuration
        if restaurant.scraping_config.consecutive_failures > 3:
            issues.append(QualityIssue(
                level=QualityIssueLevel.ERROR,
                message=f"Scraping has failed {restaurant.scraping_config.consecutive_failures} times consecutively",
                field="scraping_config",
                suggested_fix="Check website accessibility and scraper logic"
            ))
        
        return issues
    
    def check_deal_quality(self, deal: Deal) -> List[QualityIssue]:
        """Check quality of a single deal"""
        issues = []
        
        # Use existing DealValidator for basic validation
        validator_issues = DealValidator.validate_deal(deal)
        for validator_issue in validator_issues:
            issues.append(QualityIssue(
                level=QualityIssueLevel.ERROR,
                message=validator_issue,
                field="validation"
            ))
        
        # Advanced quality checks
        issues.extend(self._check_deal_content_quality(deal))
        issues.extend(self._check_deal_time_logic(deal))
        issues.extend(self._check_deal_anomalies(deal))
        
        return issues
    
    def _check_deal_content_quality(self, deal: Deal) -> List[QualityIssue]:
        """Check content quality of deal text"""
        issues = []
        
        # Check for suspicious content
        for field_name, field_value in [('title', deal.title), ('description', deal.description)]:
            if not field_value:
                continue
                
            for pattern in self.suspicious_patterns:
                if re.search(pattern, field_value, re.IGNORECASE):
                    issues.append(QualityIssue(
                        level=QualityIssueLevel.WARNING,
                        message=f"Suspicious content detected in {field_name}: might be scraping error",
                        field=field_name,
                        confidence=0.8
                    ))
        
        # Check title quality
        if deal.title:
            if len(deal.title) < 5:
                issues.append(QualityIssue(
                    level=QualityIssueLevel.WARNING,
                    message="Deal title is very short",
                    field="title",
                    confidence=0.6
                ))
            elif len(deal.title) > 100:
                issues.append(QualityIssue(
                    level=QualityIssueLevel.WARNING,
                    message="Deal title is unusually long",
                    field="title",
                    suggested_fix="Consider shortening or moving content to description"
                ))
        
        # Check description quality
        if deal.description:
            if len(deal.description) > 500:
                issues.append(QualityIssue(
                    level=QualityIssueLevel.INFO,
                    message="Deal description is very long",
                    field="description",
                    suggested_fix="Consider summarizing for better display"
                ))
        
        return issues
    
    def _check_deal_time_logic(self, deal: Deal) -> List[QualityIssue]:
        """Check logical consistency of deal times"""
        issues = []
        
        if deal.start_time and deal.end_time:
            # Parse times for logical comparison
            start_parsed = self._parse_time(deal.start_time)
            end_parsed = self._parse_time(deal.end_time)
            
            if start_parsed and end_parsed:
                # Check if end time is after start time
                if end_parsed <= start_parsed:
                    # Could be crossing midnight (e.g., 10 PM - 2 AM)
                    if not (start_parsed.hour >= 20 and end_parsed.hour <= 6):
                        issues.append(QualityIssue(
                            level=QualityIssueLevel.WARNING,
                            message="End time appears to be before start time",
                            field="time_range",
                            confidence=0.8
                        ))
                
                # Check for unusually long happy hours
                duration_hours = (end_parsed.hour + (24 if end_parsed < start_parsed else 0)) - start_parsed.hour
                if duration_hours > 8:
                    issues.append(QualityIssue(
                        level=QualityIssueLevel.INFO,
                        message=f"Happy hour duration is unusually long ({duration_hours} hours)",
                        field="time_range",
                        confidence=0.6
                    ))
        
        # Check day consistency
        if deal.days_of_week and deal.is_all_day:
            if len(deal.days_of_week) == 7:
                issues.append(QualityIssue(
                    level=QualityIssueLevel.INFO,
                    message="Deal is marked as all day for all days - might be a permanent feature",
                    field="days_of_week"
                ))
        
        return issues
    
    def _check_deal_anomalies(self, deal: Deal) -> List[QualityIssue]:
        """Check for statistical anomalies in deal data"""
        issues = []
        
        # Check confidence score
        if deal.confidence_score < 0.5:
            issues.append(QualityIssue(
                level=QualityIssueLevel.WARNING,
                message=f"Low confidence score ({deal.confidence_score:.1f}) - data might be uncertain",
                field="confidence_score",
                suggested_fix="Manual review recommended"
            ))
        
        # Check for duplicate-seeming content
        if deal.title and deal.description:
            if deal.title.lower() == deal.description.lower():
                issues.append(QualityIssue(
                    level=QualityIssueLevel.WARNING,
                    message="Title and description are identical",
                    field="content",
                    suggested_fix="Consider using one as title and expanding the other"
                ))
        
        # Check price reasonableness
        if deal.prices:
            for price_item in deal.prices:
                price_value = self._extract_price_value(price_item)
                if price_value:
                    if price_value < 1:
                        issues.append(QualityIssue(
                            level=QualityIssueLevel.WARNING,
                            message="Price seems unusually low",
                            field="prices",
                            confidence=0.7
                        ))
                    elif price_value > 50:
                        issues.append(QualityIssue(
                            level=QualityIssueLevel.WARNING,
                            message="Price seems unusually high for happy hour",
                            field="prices",
                            confidence=0.8
                        ))
        
        return issues
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL format is valid"""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, url, re.IGNORECASE))
    
    def _is_reasonable_address(self, address) -> bool:
        """Check if address format seems reasonable"""
        # Handle both string and Address dataclass
        if hasattr(address, 'formatted_address'):
            address_str = address.formatted_address
        elif hasattr(address, '__str__'):
            address_str = str(address)
        else:
            address_str = address
            
        if not address_str:
            return False
            
        # Should have numbers and street indicators
        has_number = bool(re.search(r'\d+', address_str))
        has_street_indicator = bool(re.search(r'\b(st|street|ave|avenue|blvd|rd|road|drive|way|lane)\b', address_str, re.IGNORECASE))
        return has_number and has_street_indicator
    
    def _parse_time(self, time_str: str) -> Optional[time]:
        """Parse time string to time object"""
        try:
            # Handle various time formats
            time_str = time_str.strip()
            
            # "3:00 PM" format
            if re.match(r'^\d{1,2}:\d{2}\s*(AM|PM)$', time_str, re.IGNORECASE):
                return datetime.strptime(time_str, '%I:%M %p').time()
            
            # "3 PM" format
            if re.match(r'^\d{1,2}\s*(AM|PM)$', time_str, re.IGNORECASE):
                return datetime.strptime(time_str, '%I %p').time()
            
        except ValueError:
            pass
        
        return None
    
    def _extract_price_value(self, price_str: str) -> Optional[float]:
        """Extract numeric value from price string"""
        # Remove currency symbols and extract first number
        numbers = re.findall(r'\d+(?:\.\d{2})?', price_str)
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass
        return None
    
    def generate_quality_report(self, restaurants: List[Restaurant]) -> Dict[str, Any]:
        """Generate comprehensive quality report for restaurants"""
        total_issues = 0
        issues_by_level = {level: 0 for level in QualityIssueLevel}
        issues_by_restaurant = {}
        
        for restaurant in restaurants:
            restaurant_issues = self.check_restaurant_quality(restaurant)
            if restaurant_issues:
                issues_by_restaurant[restaurant.name] = restaurant_issues
                total_issues += len(restaurant_issues)
                
                for issue in restaurant_issues:
                    issues_by_level[issue.level] += 1
        
        # Calculate quality metrics
        restaurants_with_issues = len(issues_by_restaurant)
        quality_score = max(0, 100 - (total_issues / len(restaurants) * 10))
        
        # Top issues
        common_issues = {}
        for issues in issues_by_restaurant.values():
            for issue in issues:
                key = issue.message.split(':')[0]  # Group similar issues
                common_issues[key] = common_issues.get(key, 0) + 1
        
        top_issues = sorted(common_issues.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'summary': {
                'total_restaurants': len(restaurants),
                'restaurants_with_issues': restaurants_with_issues,
                'total_issues': total_issues,
                'quality_score': round(quality_score, 1),
                'generated_at': datetime.now().isoformat()
            },
            'issues_by_level': {level.value: count for level, count in issues_by_level.items()},
            'top_issues': [{'issue': issue, 'count': count} for issue, count in top_issues],
            'restaurants_with_issues': {
                name: [
                    {
                        'level': issue.level.value,
                        'message': issue.message,
                        'field': issue.field,
                        'suggested_fix': issue.suggested_fix,
                        'confidence': issue.confidence
                    }
                    for issue in issues
                ]
                for name, issues in issues_by_restaurant.items()
            }
        }
    
    def get_improvement_suggestions(self, restaurants: List[Restaurant]) -> List[Dict[str, Any]]:
        """Get prioritized improvement suggestions"""
        suggestions = []
        
        # Count restaurants needing scraping
        need_scraping = len([r for r in restaurants if r.needs_scraping()])
        if need_scraping > 0:
            suggestions.append({
                'priority': 'high',
                'category': 'data_freshness',
                'message': f"{need_scraping} restaurants need updated deal data",
                'action': 'Run scheduled scraping'
            })
        
        # Count failed scrapers
        failed_scrapers = len([r for r in restaurants if r.scraping_config.consecutive_failures > 2])
        if failed_scrapers > 0:
            suggestions.append({
                'priority': 'medium',
                'category': 'scraping_reliability',
                'message': f"{failed_scrapers} restaurants have failing scrapers",
                'action': 'Review and fix scraper logic'
            })
        
        # Count restaurants without websites
        no_website = len([r for r in restaurants if not r.website])
        if no_website > 0:
            suggestions.append({
                'priority': 'low',
                'category': 'data_completeness',
                'message': f"{no_website} restaurants missing website URLs",
                'action': 'Research and add missing website information'
            })
        
        return suggestions


if __name__ == "__main__":
    # Test the quality checker
    from data_manager import DataManager
    
    dm = DataManager()
    checker = QualityChecker()
    
    restaurants = list(dm.restaurants.values())[:5]  # Test with first 5
    
    print("Testing quality checker...")
    for restaurant in restaurants:
        issues = checker.check_restaurant_quality(restaurant)
        if issues:
            print(f"\n{restaurant.name}:")
            for issue in issues:
                print(f"  {issue.level.value}: {issue.message}")
    
    # Generate full report
    report = checker.generate_quality_report(restaurants)
    print(f"\nQuality Report:")
    print(f"Quality Score: {report['summary']['quality_score']}")
    print(f"Total Issues: {report['summary']['total_issues']}")
    
    suggestions = checker.get_improvement_suggestions(restaurants)
    print(f"\nSuggestions:")
    for suggestion in suggestions:
        print(f"  {suggestion['priority']}: {suggestion['message']}")