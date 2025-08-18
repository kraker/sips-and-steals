#!/usr/bin/env python3
"""
LoDo Individual Restaurant Profile Generator

Creates detailed individual profiles for each LoDo restaurant
with comprehensive deal analysis and strategic dining insights.
"""

import json
from typing import Dict, List, Any
from datetime import datetime


class RestaurantProfileGenerator:
    """Generate detailed individual restaurant profiles"""
    
    def __init__(self, summary_file: str, restaurant_data_file: str):
        self.summary_file = summary_file
        self.restaurant_data_file = restaurant_data_file
        self.summary_data = self._load_summary_data()
        self.restaurant_metadata = self._load_restaurant_metadata()
        
    def _load_summary_data(self) -> Dict:
        """Load happy hour deals summary"""
        with open(self.summary_file, 'r') as f:
            return json.load(f)
    
    def _load_restaurant_metadata(self) -> Dict:
        """Load restaurant metadata"""
        with open(self.restaurant_data_file, 'r') as f:
            data = json.load(f)
            return data.get('restaurants', {})
    
    def generate_all_profiles(self):
        """Generate profiles for all LoDo restaurants"""
        profiles_data = {
            'generated_at': datetime.now().isoformat(),
            'district': 'LoDo (Lower Downtown)',
            'total_restaurants': len(self.summary_data['deals_summary']),
            'profiles': {}
        }
        
        print("🏪 **LoDo Individual Restaurant Profiles**")
        print("=" * 50)
        
        # Sort restaurants by deal count for ranking
        sorted_restaurants = sorted(
            self.summary_data['deals_summary'].items(),
            key=lambda x: x[1].get('total_deals', 0),
            reverse=True
        )
        
        for rank, (slug, deal_data) in enumerate(sorted_restaurants, 1):
            profile = self._generate_single_profile(slug, deal_data, rank)
            profiles_data['profiles'][slug] = profile
            self._print_profile(profile)
        
        # Export profiles data
        with open('data/lodo_restaurant_profiles.json', 'w') as f:
            json.dump(profiles_data, f, indent=2, default=str)
        
        print(f"\n💾 Individual profiles exported to: data/lodo_restaurant_profiles.json")
        
    def _generate_single_profile(self, slug: str, deal_data: Dict, rank: int) -> Dict:
        """Generate comprehensive profile for a single restaurant"""
        metadata = self.restaurant_metadata.get(slug, {})
        
        # Basic info
        name = deal_data.get('restaurant_name', slug.replace('-', ' ')).title()
        cuisine = metadata.get('cuisine', 'Unknown')
        website = metadata.get('website', '')
        expected_deals = metadata.get('expected_deals', '')
        
        # Deal analysis
        total_deals = deal_data.get('total_deals', 0)
        food_deals = deal_data.get('food_deals', 0)
        drink_deals = deal_data.get('drink_deals', 0)
        avg_food_price = deal_data.get('average_food_price', 0)
        avg_drink_price = deal_data.get('average_drink_price', 0)
        confidence = deal_data.get('confidence_score', 0)
        
        # Clean timeframes and days
        timeframes = self._clean_timeframes(deal_data.get('timeframes', []))
        days = self._clean_days(deal_data.get('days', []))
        
        # Generate insights
        insights = self._generate_restaurant_insights(
            name, cuisine, total_deals, food_deals, drink_deals,
            avg_food_price, avg_drink_price, timeframes, days
        )
        
        # Value assessment
        value_assessment = self._assess_value(avg_food_price, avg_drink_price, cuisine)
        
        return {
            'rank': rank,
            'name': name,
            'slug': slug,
            'cuisine': cuisine,
            'website': website,
            'expected_deals': expected_deals,
            'deal_metrics': {
                'total_deals': total_deals,
                'food_deals': food_deals,
                'drink_deals': drink_deals,
                'avg_food_price': avg_food_price,
                'avg_drink_price': avg_drink_price,
                'confidence_score': confidence
            },
            'schedule': {
                'timeframes': timeframes[:5],  # Top 5
                'days': days
            },
            'value_assessment': value_assessment,
            'strategic_insights': insights,
            'data_quality': self._assess_data_quality(total_deals, confidence)
        }
    
    def _clean_timeframes(self, timeframes: List[str]) -> List[str]:
        """Clean and filter valid timeframes"""
        valid_timeframes = []
        for tf in timeframes:
            # Skip invalid times
            if any(invalid in tf for invalid in ['30:', '40:', '50:', '60:', '70:', '80:', '90:']):
                continue
            if 'AM - PM' in tf or 'PM - AM' in tf:
                continue
            if len(tf) > 25:  # Too long
                continue
            
            # Keep valid ones
            if tf.lower() == 'all day':
                valid_timeframes.append('All Day')
            elif any(valid in tf.lower() for valid in ['pm', 'am', ':']):
                valid_timeframes.append(tf)
        
        return list(set(valid_timeframes))  # Remove duplicates
    
    def _clean_days(self, days: List[str]) -> List[str]:
        """Clean and normalize days"""
        day_mapping = {
            'mon': 'Monday', 'tue': 'Tuesday', 'wed': 'Wednesday', 'thu': 'Thursday',
            'fri': 'Friday', 'sat': 'Saturday', 'sun': 'Sunday',
            'weekday': 'Weekdays', 'weekend': 'Weekends', 'daily': 'Daily'
        }
        
        clean_days = []
        for day in days:
            normalized = day_mapping.get(day.lower(), day.title())
            if normalized not in clean_days:
                clean_days.append(normalized)
        
        return clean_days
    
    def _generate_restaurant_insights(self, name: str, cuisine: str, total_deals: int,
                                    food_deals: int, drink_deals: int, avg_food: float,
                                    avg_drink: float, timeframes: List[str], days: List[str]) -> List[str]:
        """Generate strategic insights for restaurant"""
        insights = []
        
        # Deal volume insights
        if total_deals > 100:
            insights.append(f"🎯 **Deal Leader**: {total_deals} deals - extensive happy hour program")
        elif total_deals > 50:
            insights.append(f"📊 **Strong Offering**: {total_deals} deals - solid happy hour selection")
        elif total_deals < 10:
            insights.append(f"📈 **Limited Data**: {total_deals} deals - potential for enhanced extraction")
        
        # Pricing insights
        if avg_drink > 0:
            if avg_drink < 10:
                insights.append(f"💰 **Excellent Value**: ${avg_drink:.2f} avg drinks - budget-friendly")
            elif avg_drink > 15:
                insights.append(f"🥂 **Premium Experience**: ${avg_drink:.2f} avg drinks - craft focus")
            else:
                insights.append(f"⚖️ **Balanced Pricing**: ${avg_drink:.2f} avg drinks - good value")
        
        if avg_food > 0:
            if avg_food < 12:
                insights.append(f"🍽️ **Food Value**: ${avg_food:.2f} avg food - affordable bites")
            elif avg_food > 18:
                insights.append(f"🍴 **Elevated Dining**: ${avg_food:.2f} avg food - quality focus")
        
        # Schedule insights
        if 'All Day' in timeframes:
            insights.append("⏰ **All-Day Specials**: Flexible timing for any schedule")
        
        weekday_count = sum(1 for day in days if day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
        if weekday_count >= 4:
            insights.append("📅 **Weekday Strength**: Strong after-work offerings")
        
        # Cuisine-specific insights
        if cuisine == 'Italian':
            insights.append("🍷 **Italian Excellence**: Expect quality wine and aperitivo culture")
        elif cuisine == 'Steakhouse':
            insights.append("🥩 **Premium Dining**: Upscale happy hour in steakhouse setting")
        elif cuisine == 'Mediterranean':
            insights.append("🫒 **Mediterranean Flair**: Wine-focused with regional specialties")
        elif cuisine == 'American':
            insights.append("🇺🇸 **Classic American**: Broad appeal with familiar favorites")
        
        # Deal focus insights
        if drink_deals > food_deals * 2:
            insights.append("🍹 **Drink-Focused**: Strong beverage program and cocktail culture")
        elif food_deals > drink_deals:
            insights.append("🍽️ **Food-Forward**: Substantial happy hour dining options")
        
        return insights
    
    def _assess_value(self, avg_food: float, avg_drink: float, cuisine: str) -> Dict[str, Any]:
        """Assess value proposition"""
        assessment = {
            'overall_rating': 'Good',
            'price_category': 'Mid-Range',
            'best_for': [],
            'value_score': 7.0  # Out of 10
        }
        
        # Price category
        drink_avg = avg_drink if avg_drink > 0 else 12  # Default estimate
        if drink_avg < 10:
            assessment['price_category'] = 'Budget-Friendly'
            assessment['value_score'] += 1
        elif drink_avg > 15:
            assessment['price_category'] = 'Premium'
            assessment['value_score'] -= 0.5
        
        # Best for recommendations
        if cuisine == 'Steakhouse':
            assessment['best_for'].extend(['Business Dining', 'Special Occasions', 'Premium Cocktails'])
        elif cuisine == 'Italian':
            assessment['best_for'].extend(['Wine Lovers', 'Date Nights', 'Authentic Cuisine'])
        elif cuisine == 'Mediterranean':
            assessment['best_for'].extend(['Wine Enthusiasts', 'Healthy Options', 'Cultural Experience'])
        elif cuisine == 'American':
            assessment['best_for'].extend(['Casual Dining', 'Groups', 'Familiar Menu'])
        
        # Location benefits
        assessment['best_for'].append('LoDo Exploration')
        
        # Overall rating
        if assessment['value_score'] >= 8.5:
            assessment['overall_rating'] = 'Excellent'
        elif assessment['value_score'] >= 7.5:
            assessment['overall_rating'] = 'Very Good'
        elif assessment['value_score'] < 6:
            assessment['overall_rating'] = 'Fair'
        
        return assessment
    
    def _assess_data_quality(self, total_deals: int, confidence: float) -> Dict[str, Any]:
        """Assess data extraction quality"""
        quality = {
            'rating': 'Good',
            'reliability': 'High',
            'completeness': 'Partial',
            'recommendations': []
        }
        
        if confidence >= 0.9 and total_deals > 20:
            quality['rating'] = 'Excellent'
            quality['completeness'] = 'Comprehensive'
        elif confidence >= 0.7 and total_deals > 10:
            quality['rating'] = 'Good'
            quality['completeness'] = 'Good'
        elif total_deals < 5:
            quality['rating'] = 'Limited'
            quality['reliability'] = 'Medium'
            quality['recommendations'].append("Enhanced extraction needed")
        
        if confidence < 0.6:
            quality['reliability'] = 'Medium'
            quality['recommendations'].append("Data validation required")
        
        return quality
    
    def _print_profile(self, profile: Dict):
        """Print formatted restaurant profile"""
        print(f"\n#{profile['rank']}. **{profile['name']}** ({profile['cuisine']})")
        print(f"    Website: {profile['website']}")
        print(f"    Expected Deals: {profile['expected_deals']}")
        
        metrics = profile['deal_metrics']
        print(f"    📊 Deal Metrics: {metrics['total_deals']} total ({metrics['food_deals']} food, {metrics['drink_deals']} drinks)")
        
        if metrics['avg_food_price'] > 0:
            print(f"    💰 Food: ${metrics['avg_food_price']:.2f} avg")
        if metrics['avg_drink_price'] > 0:
            print(f"    🍹 Drinks: ${metrics['avg_drink_price']:.2f} avg")
        
        schedule = profile['schedule']
        if schedule['timeframes']:
            print(f"    🕒 Times: {', '.join(schedule['timeframes'][:3])}")
        if schedule['days']:
            print(f"    📅 Days: {', '.join(schedule['days'][:5])}")
        
        value = profile['value_assessment']
        print(f"    ⭐ Value: {value['overall_rating']} ({value['price_category']})")
        print(f"    🎯 Best For: {', '.join(value['best_for'][:3])}")
        
        print(f"    🔍 Data Quality: {profile['data_quality']['rating']} ({metrics['confidence_score']:.1f} confidence)")
        
        print(f"    💡 Key Insights:")
        for insight in profile['strategic_insights'][:3]:
            print(f"       • {insight}")


def main():
    """Generate all LoDo restaurant profiles"""
    generator = RestaurantProfileGenerator(
        summary_file='data/happy_hour_deals_summary.json',
        restaurant_data_file='data/lodo_restaurants.json'
    )
    
    generator.generate_all_profiles()


if __name__ == '__main__':
    main()