#!/usr/bin/env python3
"""
LoDo District Happy Hour Analysis & Dashboard Generator

Analyzes aggregated happy hour data from Lower Downtown Denver restaurants
and generates a comprehensive district overview for proof of concept.
"""

import json
from typing import Dict, List, Any
from datetime import datetime
from collections import defaultdict, Counter
from dataclasses import dataclass, field


@dataclass
class LoDoDeal:
    """Structured deal data for analysis"""
    restaurant: str
    title: str
    price: str
    deal_type: str
    category: str
    timeframes: List[str] = field(default_factory=list)
    days: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class RestaurantProfile:
    """Individual restaurant profile"""
    name: str
    slug: str
    cuisine: str
    total_deals: int
    food_deals: int
    drink_deals: int
    avg_food_price: float
    avg_drink_price: float
    timeframes: List[str]
    days: List[str]
    confidence: float
    
    
@dataclass
class DistrictInsights:
    """LoDo district-level insights"""
    total_restaurants: int
    total_deals: int
    coverage_rate: float
    price_ranges: Dict[str, Dict[str, float]]
    popular_timeframes: List[tuple]
    popular_days: List[tuple]
    cuisine_distribution: Dict[str, int]
    deal_type_distribution: Dict[str, int]
    recommendations: List[str]


class LoDoDistrictAnalysis:
    """Comprehensive analysis of LoDo happy hour landscape"""
    
    def __init__(self, summary_file: str, restaurant_data_file: str):
        self.summary_file = summary_file
        self.restaurant_data_file = restaurant_data_file
        self.summary_data = self._load_summary_data()
        self.restaurant_metadata = self._load_restaurant_metadata()
        self.deals = []
        self.profiles = {}
        self.insights = None
        
    def _load_summary_data(self) -> Dict:
        """Load happy hour deals summary"""
        with open(self.summary_file, 'r') as f:
            return json.load(f)
    
    def _load_restaurant_metadata(self) -> Dict:
        """Load restaurant metadata for enhanced profiles"""
        with open(self.restaurant_data_file, 'r') as f:
            data = json.load(f)
            return data.get('restaurants', {})
    
    def _clean_timeframe(self, timeframe: str) -> str:
        """Clean and normalize timeframe data"""
        # Fix common parsing errors
        timeframe = timeframe.strip()
        
        # Skip clearly invalid times
        if any(invalid in timeframe for invalid in ['30:', '40:', '50:', '60:', '70:', '80:', '90:']):
            return None
        if 'AM - PM' in timeframe or 'PM - AM' in timeframe:
            return None
        if len(timeframe) > 20:  # Suspiciously long timeframes
            return None
            
        # Normalize common patterns
        if timeframe.lower() == 'all day':
            return 'All Day'
        
        # Return valid-looking timeframes as-is for now
        if any(valid in timeframe for valid in ['PM', 'AM', ':']):
            return timeframe
            
        return None
    
    def _clean_day(self, day: str) -> str:
        """Clean and normalize day data"""
        day_mapping = {
            'mon': 'Monday', 'tue': 'Tuesday', 'wed': 'Wednesday', 'thu': 'Thursday',
            'fri': 'Friday', 'sat': 'Saturday', 'sun': 'Sunday',
            'weekday': 'Weekdays', 'weekend': 'Weekends', 'daily': 'Daily'
        }
        return day_mapping.get(day.lower(), day.title())
    
    def analyze_district(self):
        """Perform comprehensive district analysis"""
        print("🏙️  **LoDo Happy Hour District Analysis**")
        print("=" * 50)
        
        # Process individual restaurants
        for slug, data in self.summary_data['deals_summary'].items():
            self._process_restaurant(slug, data)
        
        # Generate district-level insights
        self._generate_insights()
        
        # Output analysis
        self._print_analysis()
        
    def _process_restaurant(self, slug: str, data: Dict):
        """Process individual restaurant data"""
        metadata = self.restaurant_metadata.get(slug, {})
        
        # Clean timeframes and days
        clean_timeframes = [self._clean_timeframe(tf) for tf in data.get('timeframes', [])]
        clean_timeframes = [tf for tf in clean_timeframes if tf]
        
        clean_days = [self._clean_day(day) for day in data.get('days', [])]
        clean_days = list(set(clean_days))  # Remove duplicates
        
        # Create restaurant profile
        profile = RestaurantProfile(
            name=data.get('restaurant_name', slug).replace('-', ' ').title(),
            slug=slug,
            cuisine=metadata.get('cuisine', 'Unknown'),
            total_deals=data.get('total_deals', 0),
            food_deals=data.get('food_deals', 0),
            drink_deals=data.get('drink_deals', 0),
            avg_food_price=data.get('average_food_price', 0),
            avg_drink_price=data.get('average_drink_price', 0),
            timeframes=clean_timeframes[:5],  # Top 5 timeframes
            days=clean_days,
            confidence=data.get('confidence_score', 0)
        )
        
        self.profiles[slug] = profile
    
    def _generate_insights(self):
        """Generate district-level insights"""
        total_restaurants = len(self.profiles)
        total_deals = sum(p.total_deals for p in self.profiles.values())
        successful_restaurants = sum(1 for p in self.profiles.values() if p.total_deals > 0)
        coverage_rate = (successful_restaurants / total_restaurants) * 100 if total_restaurants > 0 else 0
        
        # Price analysis
        food_prices = [p.avg_food_price for p in self.profiles.values() if p.avg_food_price > 0]
        drink_prices = [p.avg_drink_price for p in self.profiles.values() if p.avg_drink_price > 0]
        
        price_ranges = {
            'food': {
                'min': min(food_prices) if food_prices else 0,
                'max': max(food_prices) if food_prices else 0,
                'avg': sum(food_prices) / len(food_prices) if food_prices else 0
            },
            'drinks': {
                'min': min(drink_prices) if drink_prices else 0,
                'max': max(drink_prices) if drink_prices else 0,
                'avg': sum(drink_prices) / len(drink_prices) if drink_prices else 0
            }
        }
        
        # Timeframe and day analysis
        all_timeframes = []
        all_days = []
        cuisines = []
        
        for profile in self.profiles.values():
            all_timeframes.extend(profile.timeframes)
            all_days.extend(profile.days)
            cuisines.append(profile.cuisine)
        
        popular_timeframes = Counter(all_timeframes).most_common(5)
        popular_days = Counter(all_days).most_common(7)
        cuisine_distribution = Counter(cuisines)
        
        # Deal type analysis
        deal_types = {
            'food_focused': sum(1 for p in self.profiles.values() if p.food_deals > p.drink_deals),
            'drink_focused': sum(1 for p in self.profiles.values() if p.drink_deals > p.food_deals),
            'balanced': sum(1 for p in self.profiles.values() if p.food_deals == p.drink_deals and p.food_deals > 0)
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(price_ranges, popular_timeframes, popular_days)
        
        self.insights = DistrictInsights(
            total_restaurants=total_restaurants,
            total_deals=total_deals,
            coverage_rate=coverage_rate,
            price_ranges=price_ranges,
            popular_timeframes=popular_timeframes,
            popular_days=popular_days,
            cuisine_distribution=dict(cuisine_distribution),
            deal_type_distribution=deal_types,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self, price_ranges: Dict, timeframes: List[tuple], days: List[tuple]) -> List[str]:
        """Generate strategic dining recommendations"""
        recommendations = []
        
        # Price-based recommendations
        if price_ranges['drinks']['avg'] > 0:
            avg_drink = price_ranges['drinks']['avg']
            if avg_drink < 12:
                recommendations.append(f"💰 **Excellent Value**: Average drink prices ${avg_drink:.2f} - exceptional value for premium LoDo location")
            elif avg_drink > 15:
                recommendations.append(f"🥂 **Premium Experience**: Average drink prices ${avg_drink:.2f} - craft cocktails and elevated experiences")
        
        # Timeframe recommendations
        if timeframes:
            top_time = timeframes[0][0]
            if 'All Day' in top_time:
                recommendations.append("⏰ **Flexible Timing**: Many restaurants offer all-day specials - perfect for any schedule")
            elif '3:00 PM' in top_time or '4:00 PM' in top_time:
                recommendations.append("🕒 **Classic Happy Hour**: Peak deals 3-6 PM - traditional after-work timing")
        
        # Day recommendations
        if days:
            weekday_days = [day for day, count in days if day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']]
            if len(weekday_days) >= 3:
                recommendations.append("📅 **Weekday Advantage**: Strong weekday offerings - perfect for after-work dining")
        
        # Coverage recommendations
        if self.insights and self.insights.coverage_rate > 75:
            recommendations.append("🎯 **District Strength**: High coverage rate - LoDo is a happy hour destination")
        
        return recommendations
    
    def _print_analysis(self):
        """Print comprehensive analysis results"""
        if not self.insights:
            return
        
        print(f"\n📊 **District Overview**")
        print(f"   • {self.insights.total_restaurants} restaurants analyzed")
        print(f"   • {self.insights.total_deals} total deals extracted")
        print(f"   • {self.insights.coverage_rate:.1f}% successful data extraction")
        
        print(f"\n💵 **Price Analysis**")
        food = self.insights.price_ranges['food']
        drinks = self.insights.price_ranges['drinks']
        if food['avg'] > 0:
            print(f"   • Food: ${food['min']:.2f} - ${food['max']:.2f} (avg: ${food['avg']:.2f})")
        if drinks['avg'] > 0:
            print(f"   • Drinks: ${drinks['min']:.2f} - ${drinks['max']:.2f} (avg: ${drinks['avg']:.2f})")
        
        print(f"\n🕒 **Popular Timeframes**")
        for timeframe, count in self.insights.popular_timeframes:
            print(f"   • {timeframe} ({count} mentions)")
        
        print(f"\n📅 **Popular Days**")
        for day, count in self.insights.popular_days:
            print(f"   • {day} ({count} mentions)")
        
        print(f"\n🍽️ **Cuisine Distribution**")
        for cuisine, count in self.insights.cuisine_distribution.items():
            print(f"   • {cuisine}: {count} restaurants")
        
        print(f"\n🎯 **Strategic Recommendations**")
        for rec in self.insights.recommendations:
            print(f"   {rec}")
        
        print(f"\n🏪 **Individual Restaurant Profiles**")
        print("=" * 50)
        
        # Sort by total deals for ranking
        sorted_profiles = sorted(self.profiles.values(), key=lambda p: p.total_deals, reverse=True)
        
        for i, profile in enumerate(sorted_profiles, 1):
            print(f"\n#{i}. **{profile.name}** ({profile.cuisine})")
            print(f"    • {profile.total_deals} total deals ({profile.food_deals} food, {profile.drink_deals} drinks)")
            if profile.avg_food_price > 0:
                print(f"    • Avg food price: ${profile.avg_food_price:.2f}")
            if profile.avg_drink_price > 0:
                print(f"    • Avg drink price: ${profile.avg_drink_price:.2f}")
            if profile.timeframes:
                print(f"    • Key times: {', '.join(profile.timeframes[:3])}")
            if profile.days:
                print(f"    • Available: {', '.join(profile.days[:5])}")
            print(f"    • Data confidence: {profile.confidence:.1f}")
    
    def export_dashboard_data(self, output_file: str):
        """Export data for dashboard generation"""
        dashboard_data = {
            'exported_at': datetime.now().isoformat(),
            'district': 'LoDo (Lower Downtown)',
            'summary': {
                'total_restaurants': self.insights.total_restaurants,
                'total_deals': self.insights.total_deals,
                'coverage_rate': self.insights.coverage_rate,
                'price_ranges': self.insights.price_ranges,
                'popular_timeframes': self.insights.popular_timeframes,
                'popular_days': self.insights.popular_days,
                'cuisine_distribution': self.insights.cuisine_distribution,
                'recommendations': self.insights.recommendations
            },
            'restaurant_profiles': {
                slug: {
                    'name': profile.name,
                    'cuisine': profile.cuisine,
                    'total_deals': profile.total_deals,
                    'food_deals': profile.food_deals,
                    'drink_deals': profile.drink_deals,
                    'avg_food_price': profile.avg_food_price,
                    'avg_drink_price': profile.avg_drink_price,
                    'timeframes': profile.timeframes,
                    'days': profile.days,
                    'confidence': profile.confidence
                }
                for slug, profile in self.profiles.items()
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        
        print(f"\n💾 Dashboard data exported to: {output_file}")


def main():
    """Run LoDo district analysis"""
    print("🏙️ **LoDo Happy Hour District Analysis & Proof of Concept**")
    print("=" * 60)
    print("Analyzing aggregated restaurant and deals data for proof of concept")
    print("demonstration of our new architecture and data-mining strategy.\n")
    
    analyzer = LoDoDistrictAnalysis(
        summary_file='data/happy_hour_deals_summary.json',
        restaurant_data_file='data/lodo_restaurants.json'
    )
    
    analyzer.analyze_district()
    analyzer.export_dashboard_data('data/lodo_district_dashboard.json')
    
    print(f"\n✅ **Proof of Concept Complete**")
    print("The LoDo district analysis demonstrates our refined scraping system's")
    print("capability to discover, extract, and aggregate high-quality happy hour")
    print("deals data at scale across premium restaurant establishments.")


if __name__ == '__main__':
    main()