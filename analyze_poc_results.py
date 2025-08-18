#!/usr/bin/env python3
"""
Analyze and visualize the results of our semantic analysis PoC.

Shows detailed insights into how the data-hungry approach captures extraction context
and enables intelligent deduplication based on semantic similarity.
"""

import json
from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PoCResultsAnalyzer:
    """
    Analyze and visualize semantic analysis PoC results.
    """
    
    def __init__(self, poc_database_path: str = "data/poc_deals.json"):
        self.poc_database_path = poc_database_path
        self.poc_data = self._load_poc_data()
    
    def _load_poc_data(self) -> Dict[str, Any]:
        """Load PoC database"""
        try:
            with open(self.poc_database_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"PoC database not found at {self.poc_database_path}")
            return {}
    
    def show_comprehensive_analysis(self):
        """Display comprehensive analysis of all restaurants in PoC"""
        print("🔬 SEMANTIC ANALYSIS PoC RESULTS")
        print("=" * 60)
        
        metadata = self.poc_data.get('metadata', {})
        print(f"📅 Created: {metadata.get('created_at', 'Unknown')}")
        print(f"🎯 Purpose: {metadata.get('purpose', 'Unknown')}")
        print(f"🍽️  Target Restaurants: {len(metadata.get('target_restaurants', []))}")
        print()
        
        restaurants = self.poc_data.get('restaurants', {})
        
        # Overall statistics
        total_deals = sum(r['deal_count'] for r in restaurants.values())
        avg_quality = sum(r['semantic_analysis']['quality_score'] for r in restaurants.values()) / len(restaurants)
        total_consolidations = sum(
            len(r['semantic_analysis']['recommended_consolidation']) 
            for r in restaurants.values()
        )
        
        print("📊 OVERALL STATISTICS")
        print(f"   Total Raw Deals: {total_deals}")
        print(f"   Average Quality Score: {avg_quality:.2f}")
        print(f"   Total Consolidation Actions: {total_consolidations}")
        print()
        
        # Analyze each restaurant
        for slug, restaurant_data in restaurants.items():
            self._analyze_restaurant(slug, restaurant_data)
            print()
    
    def _analyze_restaurant(self, slug: str, restaurant_data: Dict[str, Any]):
        """Detailed analysis of a single restaurant"""
        print(f"🍽️  {slug.upper().replace('-', ' ')}")
        print("-" * 50)
        
        analysis = restaurant_data['semantic_analysis']
        raw_deals = restaurant_data['raw_deals']
        
        # Basic stats
        print(f"📈 Total Deals: {analysis['total_deals']}")
        print(f"🎯 Quality Score: {analysis['quality_score']:.2f}")
        print(f"⚡ Consolidation Actions: {len(analysis['recommended_consolidation'])}")
        
        # Show confidence distribution
        conf_dist = analysis['confidence_distribution']
        print(f"🔢 Confidence: Avg={conf_dist['mean']:.2f}, Range={conf_dist['min']:.1f}-{conf_dist['max']:.1f}")
        
        # Show extraction methods used
        extraction_methods = analysis['extraction_methods']
        print(f"🛠️  Extraction Methods: {', '.join(extraction_methods.keys())}")
        
        # Time cluster analysis
        time_clusters = analysis['time_clusters']
        print(f"⏰ Time Clusters ({len(time_clusters)}):")
        for time_sig, cluster in time_clusters.items():
            print(f"   • {time_sig}: {len(cluster)} deals")
            if len(cluster) > 1:
                print(f"     → Duplication detected! 🔍")
        
        # Day cluster analysis  
        day_clusters = analysis['day_clusters']
        print(f"📅 Day Clusters ({len(day_clusters)}):")
        for day_sig, cluster in day_clusters.items():
            print(f"   • {day_sig}: {len(cluster)} deals")
        
        # Show consolidation recommendations
        consolidation_plan = analysis['recommended_consolidation']
        if consolidation_plan:
            print(f"🧠 Consolidation Recommendations:")
            for i, plan in enumerate(consolidation_plan, 1):
                action = plan['action']
                reasoning = plan['reasoning']
                best_idx = plan['recommended_representative']
                
                print(f"   {i}. {action}")
                print(f"      Reasoning: {reasoning}")
                print(f"      Best Representative: Deal #{best_idx}")
                
                # Show the recommended deal
                best_deal = raw_deals[best_idx]
                print(f"      → \"{best_deal['description'][:60]}...\"")
        else:
            print("✅ No consolidation needed - deals are already distinct")
    
    def show_thirsty_lion_deep_dive(self):
        """Deep dive into Thirsty Lion's data-hungry success"""
        print("\n🔍 THIRSTY LION DEEP DIVE: Data-Hungry Success Story")
        print("=" * 70)
        
        thirsty_data = self.poc_data['restaurants']['thirsty-lion']
        raw_deals = thirsty_data['raw_deals']
        analysis = thirsty_data['semantic_analysis']
        
        print(f"📊 Successfully captured {len(raw_deals)} deals with rich extraction context")
        print(f"🎯 Quality Score: {analysis['quality_score']:.2f}")
        print()
        
        print("🔬 EXTRACTION CONTEXT ANALYSIS:")
        for i, deal in enumerate(raw_deals):
            print(f"\nDeal #{i}: \"{deal['description'][:50]}...\"")
            print(f"   Confidence: {deal['confidence_score']:.2f}")
            print(f"   Method: {deal['extraction_method']}")
            
            # Show source context
            if deal['source_text']:
                source_snippet = deal['source_text'][:100].replace('\n', ' ')
                print(f"   Source: \"{source_snippet}...\"")
            
            # Show pattern matches
            if deal['raw_time_matches']:
                print(f"   Time Matches: {deal['raw_time_matches']}")
            if deal['raw_day_matches']:
                day_matches = deal['raw_day_matches'][:5]  # Show first 5
                print(f"   Day Matches: {day_matches}{'...' if len(deal['raw_day_matches']) > 5 else ''}")
        
        print("\n🧠 SEMANTIC CLUSTERING RESULTS:")
        
        # Show time clusters
        time_clusters = analysis['time_clusters']
        print(f"⏰ Time-based clustering identified {len(time_clusters)} distinct patterns:")
        for time_sig, cluster in time_clusters.items():
            print(f"   • {time_sig}: {len(cluster)} deals")
        
        # Show consolidation plan
        consolidation_plan = analysis['recommended_consolidation']
        print(f"\n🎯 CONSOLIDATION PLAN ({len(consolidation_plan)} actions):")
        for plan in consolidation_plan:
            source_indices = plan['source_indices']
            best_idx = plan['recommended_representative']
            print(f"   • Merge deals {source_indices} → Keep deal #{best_idx}")
            print(f"     Best deal: \"{raw_deals[best_idx]['description'][:60]}...\"")
        
        expected_final = len(set([plan['recommended_representative'] for plan in consolidation_plan]))
        print(f"\n✨ RESULT: {len(raw_deals)} raw deals → {expected_final} semantically distinct deals")
        print("🎉 Successfully captures both 'Daily 3-6 PM' and 'Thurs-Sat 9PM-Close' deals!")
    
    def show_extraction_method_comparison(self):
        """Compare extraction methods across restaurants"""
        print("\n🛠️  EXTRACTION METHOD ANALYSIS")
        print("=" * 50)
        
        method_stats = {}
        deal_counts = {}
        quality_by_method = {}
        
        for slug, restaurant_data in self.poc_data['restaurants'].items():
            analysis = restaurant_data['semantic_analysis']
            raw_deals = restaurant_data['raw_deals']
            
            # Count extraction methods
            for method, count in analysis['extraction_methods'].items():
                if method not in method_stats:
                    method_stats[method] = 0
                    deal_counts[method] = []
                    quality_by_method[method] = []
                
                method_stats[method] += count
                
                # Find deals using this method
                method_deals = [d for d in raw_deals if d['extraction_method'] == method]
                deal_counts[method].extend(method_deals)
                quality_by_method[method].extend([d['confidence_score'] for d in method_deals])
        
        print("📊 Method Usage:")
        for method, count in sorted(method_stats.items(), key=lambda x: x[1], reverse=True):
            avg_confidence = sum(quality_by_method[method]) / len(quality_by_method[method])
            print(f"   • {method}: {count} deals (avg confidence: {avg_confidence:.2f})")
        
        # Show best performing extraction contexts
        print("\n🏆 Highest Quality Extractions:")
        all_deals = []
        for restaurant_data in self.poc_data['restaurants'].values():
            all_deals.extend(restaurant_data['raw_deals'])
        
        # Sort by confidence score
        top_deals = sorted(all_deals, key=lambda x: x['confidence_score'], reverse=True)[:3]
        
        for i, deal in enumerate(top_deals, 1):
            print(f"   {i}. Confidence: {deal['confidence_score']:.2f}")
            print(f"      Description: \"{deal['description'][:60]}...\"")
            print(f"      Method: {deal['extraction_method']}")
            if deal['source_text']:
                print(f"      Context: \"{deal['source_text'][:80]}...\"")
            print()


if __name__ == "__main__":
    analyzer = PoCResultsAnalyzer()
    
    # Show comprehensive analysis
    analyzer.show_comprehensive_analysis()
    
    # Deep dive into our success story
    analyzer.show_thirsty_lion_deep_dive()
    
    # Compare extraction methods
    analyzer.show_extraction_method_comparison()