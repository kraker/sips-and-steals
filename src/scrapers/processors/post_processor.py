#!/usr/bin/env python3
"""
Post-processing engine for enhancing scraped deals based on YAML config rules
This implements the hybrid approach requested for Fogo de Chão and other restaurants
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import models (adjust path as needed)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from models import Deal, DealType, DayOfWeek

logger = logging.getLogger(__name__)


class PostProcessor:
    """Process and enhance deals based on configuration rules"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.post_processing_config = config.get('post_processing', {})
    
    def enhance_deals(self, deals: List[Deal]) -> List[Deal]:
        """Apply post-processing enhancements to deals"""
        if not self.post_processing_config:
            return deals
        
        enhanced_deals = deals.copy()
        
        # Apply deal transformations
        if 'deal_transformations' in self.post_processing_config:
            enhanced_deals = self._apply_transformations(enhanced_deals)
        
        # Apply merge rules
        if 'merge_rules' in self.post_processing_config:
            enhanced_deals = self._apply_merge_rules(enhanced_deals)
        
        # Apply fallback deals if no good deals were found (based on confidence and content quality)
        good_deals = [deal for deal in enhanced_deals if deal.confidence_score >= 0.6 and (deal.prices or deal.start_time)]
        if not good_deals and 'fallback_deals' in self.post_processing_config:
            logger.info(f"No quality deals found, using fallback deals")
            enhanced_deals = self._create_fallback_deals()
        
        return enhanced_deals
    
    def _apply_transformations(self, deals: List[Deal]) -> List[Deal]:
        """Apply deal transformation rules"""
        transformations = self.post_processing_config.get('deal_transformations', [])
        enhanced_deals = []
        
        for deal in deals:
            # Check if this deal matches any transformation pattern
            transformed = False
            
            for transformation in transformations:
                match_pattern = transformation.get('match_pattern')
                if not match_pattern:
                    continue
                
                # Check if deal description matches the pattern
                deal_text = f"{deal.title} {deal.description or ''}"
                if re.search(match_pattern, deal_text, re.IGNORECASE):
                    logger.info(f"Applying transformation to deal: {deal.title}")
                    
                    # Create enhanced deal
                    enhanced_deal = self._transform_deal(deal, transformation)
                    enhanced_deals.append(enhanced_deal)
                    transformed = True
                    break
            
            # If no transformation applied, keep original deal
            if not transformed:
                enhanced_deals.append(deal)
        
        return enhanced_deals
    
    def _transform_deal(self, original_deal: Deal, transformation: Dict[str, Any]) -> Deal:
        """Transform a deal based on transformation rules"""
        # Start with original deal attributes
        new_deal = Deal(
            title=transformation.get('new_title', original_deal.title),
            description=original_deal.description,
            deal_type=original_deal.deal_type,
            days_of_week=original_deal.days_of_week,
            start_time=original_deal.start_time,
            end_time=original_deal.end_time,
            prices=original_deal.prices.copy() if hasattr(original_deal, 'prices') else [],
            is_all_day=original_deal.is_all_day,
            special_notes=original_deal.special_notes.copy(),
            scraped_at=original_deal.scraped_at,
            source_url=original_deal.source_url,
            confidence_score=original_deal.confidence_score
        )
        
        # Apply specific transformations
        if 'days_of_week' in transformation:
            day_strings = transformation['days_of_week']
            new_deal.days_of_week = [self._string_to_day_of_week(day) for day in day_strings]
            new_deal.days_of_week = [day for day in new_deal.days_of_week if day]  # Filter None values
        
        if 'start_time' in transformation:
            new_deal.start_time = transformation['start_time']
        
        if 'end_time' in transformation:
            new_deal.end_time = transformation['end_time']
        
        if 'confidence_boost' in transformation:
            new_deal.confidence_score = min(1.0, new_deal.confidence_score + transformation['confidence_boost'])
        
        if 'append_to_description' in transformation:
            if new_deal.description:
                new_deal.description += transformation['append_to_description']
            else:
                new_deal.description = transformation['append_to_description'].strip(' -')
        
        # Apply promotional content if configured
        promotional_content = self.post_processing_config.get('promotional_content', {})
        if promotional_content:
            if promotional_content.get('description'):
                if new_deal.description:
                    new_deal.description = f"{promotional_content['description']} ({new_deal.description})"
                else:
                    new_deal.description = promotional_content['description']
            
            if promotional_content.get('price') and not new_deal.prices:
                new_deal.set_price_from_string(promotional_content['price'])
            
            # Clean up redundant pricing in description when structured prices exist
            if new_deal.prices and new_deal.description:
                price_string = ", ".join(new_deal.prices)
                new_deal.description = self._remove_pricing_from_description(new_deal.description, price_string)
        
        return new_deal
    
    def _apply_merge_rules(self, deals: List[Deal]) -> List[Deal]:
        """Apply merge rules to deals"""
        merge_rules = self.post_processing_config.get('merge_rules', [])
        enhanced_deals = deals.copy()
        
        for rule in merge_rules:
            apply_to = rule.get('apply_to', '')
            
            if apply_to == 'all':
                # Apply to all deals
                enhanced_deals = [self._apply_merge_rule_to_deal(deal, rule) for deal in enhanced_deals]
            
            elif apply_to.startswith('title:'):
                # Apply to deals with specific title
                target_title = apply_to[6:]  # Remove 'title:' prefix
                enhanced_deals = [
                    self._apply_merge_rule_to_deal(deal, rule) if target_title.lower() in deal.title.lower() else deal
                    for deal in enhanced_deals
                ]
        
        return enhanced_deals
    
    def _apply_merge_rule_to_deal(self, deal: Deal, rule: Dict[str, Any]) -> Deal:
        """Apply a merge rule to a specific deal"""
        # Create copy of deal
        enhanced_deal = Deal(
            title=deal.title,
            description=deal.description,
            deal_type=deal.deal_type,
            days_of_week=deal.days_of_week.copy(),
            start_time=deal.start_time,
            end_time=deal.end_time,
            prices=deal.prices.copy() if hasattr(deal, 'prices') else [],
            is_all_day=deal.is_all_day,
            special_notes=deal.special_notes.copy(),
            scraped_at=deal.scraped_at,
            source_url=deal.source_url,
            confidence_score=deal.confidence_score
        )
        
        # Apply promotional content if merge rule specifies it
        promotional_content = self.post_processing_config.get('promotional_content', {})
        
        if rule.get('merge_description') and promotional_content.get('description'):
            if enhanced_deal.description:
                enhanced_deal.description = f"{promotional_content['description']} - {enhanced_deal.description}"
            else:
                enhanced_deal.description = promotional_content['description']
        
        if rule.get('merge_price') and promotional_content.get('price'):
            if not enhanced_deal.prices:
                enhanced_deal.set_price_from_string(promotional_content['price'])
        
        # Clean up redundant pricing in description when structured prices exist
        if enhanced_deal.prices and enhanced_deal.description:
            price_string = ", ".join(enhanced_deal.prices)
            enhanced_deal.description = self._remove_pricing_from_description(enhanced_deal.description, price_string)
        
        return enhanced_deal
    
    def _create_fallback_deals(self) -> List[Deal]:
        """Create fallback deals when no deals are found"""
        fallback_deals_config = self.post_processing_config.get('fallback_deals', [])
        fallback_deals = []
        
        for deal_config in fallback_deals_config:
            # Convert day strings to DayOfWeek enums
            days_of_week = []
            if 'days_of_week' in deal_config:
                days_of_week = [self._string_to_day_of_week(day) for day in deal_config['days_of_week']]
                days_of_week = [day for day in days_of_week if day]  # Filter None values
            
            deal = Deal(
                title=deal_config.get('title', 'Happy Hour'),
                description=deal_config.get('description', ''),
                deal_type=DealType.HAPPY_HOUR,
                days_of_week=days_of_week,
                start_time=deal_config.get('start_time'),
                end_time=deal_config.get('end_time'),
                is_all_day=deal_config.get('is_all_day', False),
                confidence_score=deal_config.get('confidence_score', 0.8),
                scraped_at=datetime.now(),
                source_url=None
            )
            
            # Set pricing using the new structured approach
            price_string = deal_config.get('price')
            if price_string:
                deal.set_price_from_string(price_string)
            
            fallback_deals.append(deal)
        
        # Apply description cleaning to fallback deals if they have pricing
        for deal in fallback_deals:
            if deal.prices and deal.description:
                price_string = ", ".join(deal.prices)
                deal.description = self._remove_pricing_from_description(deal.description, price_string)
        
        logger.info(f"Created {len(fallback_deals)} fallback deals")
        return fallback_deals
    
    def _string_to_day_of_week(self, day_string: str) -> Optional[DayOfWeek]:
        """Convert string to DayOfWeek enum"""
        day_mapping = {
            'monday': DayOfWeek.MONDAY,
            'tuesday': DayOfWeek.TUESDAY,
            'wednesday': DayOfWeek.WEDNESDAY,
            'thursday': DayOfWeek.THURSDAY,
            'friday': DayOfWeek.FRIDAY,
            'saturday': DayOfWeek.SATURDAY,
            'sunday': DayOfWeek.SUNDAY
        }
        return day_mapping.get(day_string.lower())
    
    def _remove_pricing_from_description(self, description: str, price: str) -> str:
        """Remove redundant pricing information and title repetition from description"""
        if not description:
            return description
        
        cleaned_description = description
        
        # Remove redundant "All Day Happy Hour" from description since it's likely the title
        cleaned_description = re.sub(r'^All Day Happy Hour\s*', '', cleaned_description, flags=re.IGNORECASE)
        cleaned_description = re.sub(r'\s*All Day Happy Hour\s*', ' ', cleaned_description, flags=re.IGNORECASE)
        
        # Extract key pricing elements from the price field to identify in description if price exists
        if price:
            price_elements = re.findall(r'\$\d+(?:\.\d{2})?\s*[A-Za-z\s,&-]+', price)
        else:
            price_elements = []
        
        # Remove price patterns that match elements in the price field
        for price_element in price_elements:
            # Create flexible pattern to match pricing in description
            # e.g., "$5 Beers" should match "$5 Beers", "$5 Beer", etc.
            base_amount = re.search(r'\$\d+(?:\.\d{2})?', price_element)
            if base_amount:
                amount = base_amount.group()
                # Create pattern that matches the amount with various drink/food terms
                price_pattern = rf'{re.escape(amount)}\s*[A-Za-z\s,&-]*'
                cleaned_description = re.sub(price_pattern, '', cleaned_description, flags=re.IGNORECASE)
        
        # Clean up extra whitespace, commas, and formatting artifacts
        cleaned_description = re.sub(r'\s*,\s*,\s*', ', ', cleaned_description)  # Multiple commas
        cleaned_description = re.sub(r'\s*,\s*and\s*,\s*', ' and ', cleaned_description)  # "and" with extra commas
        cleaned_description = re.sub(r'\s+', ' ', cleaned_description)  # Multiple spaces
        cleaned_description = re.sub(r'\s*-\s*$', '', cleaned_description)  # Trailing dash
        cleaned_description = re.sub(r'^\s*-\s*', '', cleaned_description)  # Leading dash
        cleaned_description = cleaned_description.strip(' ,-')
        
        # Additional cleanup for common patterns
        cleaned_description = re.sub(r'^at\s+', '', cleaned_description, flags=re.IGNORECASE)  # Remove leading "at"
        cleaned_description = cleaned_description.strip(' ,-')
        
        # If we've removed too much and left something very short or generic, provide a better description
        if len(cleaned_description) < 5 or cleaned_description.lower() in ['at bar fogo', 'bar fogo', '']:
            # Return a clean, informative description
            return "Happy hour at Bar Fogo"
        
        return cleaned_description


# Test the post-processor with Fogo de Chão style config
if __name__ == "__main__":
    # Example config similar to our Fogo de Chão YAML
    test_config = {
        'post_processing': {
            'promotional_content': {
                'description': "All Day Happy Hour at Bar Fogo featuring $5 Beers, $8 South American Wines and $10 Brazilian-Inspired Cocktails",
                'price': "$5 Beers, $8 Wines, $10 Cocktails"
            },
            'deal_transformations': [
                {
                    'match_pattern': r"Mon\s*-\s*Thu.*3:00\s*PM.*9:30\s*PM",
                    'new_title': "Monday-Thursday Happy Hour",
                    'days_of_week': ["monday", "tuesday", "wednesday", "thursday"],
                    'start_time': "3:00 PM",
                    'end_time': "9:30 PM",
                    'confidence_boost': 0.4
                }
            ],
            'merge_rules': [
                {
                    'apply_to': "all",
                    'merge_description': True,
                    'merge_price': True
                }
            ]
        }
    }
    
    # Test deal
    test_deal = Deal(
        title="Time-based Special",
        description="Mon - Thu 3:00 PM - 9:30PM",
        deal_type=DealType.HAPPY_HOUR,
        confidence_score=0.6
    )
    
    processor = PostProcessor(test_config)
    enhanced_deals = processor.enhance_deals([test_deal])
    
    print("Original deal:", test_deal.title, "-", test_deal.description)
    print("Enhanced deal:", enhanced_deals[0].title, "-", enhanced_deals[0].description)
    print("Days:", enhanced_deals[0].days_of_week)
    print("Time:", enhanced_deals[0].start_time, "-", enhanced_deals[0].end_time)
    print("Price:", enhanced_deals[0].prices)