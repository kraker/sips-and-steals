#!/usr/bin/env python3
"""
Sips and Steals Scrapy CLI

Simple command-line interface for the new Scrapy-based architecture.
Focuses on essential discovery and extraction workflows.
"""

import argparse
import subprocess
import sys
import json
import logging
from pathlib import Path
from datetime import datetime


class ScrapyCLI:
    """Simple CLI for Scrapy-based scraping system"""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent.parent  # Go up from scripts/ to root
        self.data_dir = self.project_dir / 'data'
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def run_discovery(self, args):
        """Run discovery spider to find happy hour pages"""
        print("🔍 Starting Restaurant Discovery...")
        print("Finding happy hour pages across restaurant websites")
        
        cmd = [
            'scrapy', 'crawl', 'discovery',
            '-s', f'RESTAURANT_DATA_FILE={self.data_dir}/restaurants.json',
            '-s', f'DISCOVERY_OUTPUT_FILE={self.data_dir}/discovered_urls.json',
            '-L', 'INFO'
        ]
        
        if args.restaurant:
            # TODO: Add restaurant filtering
            print(f"Filtering to restaurant: {args.restaurant}")
        
        try:
            result = subprocess.run(cmd, cwd=self.project_dir, check=True)
            print("✅ Discovery completed successfully!")
            self._show_discovery_stats()
        except subprocess.CalledProcessError as e:
            print(f"❌ Discovery failed: {e}")
            return 1
        
        return 0
    
    def run_extraction(self, args):
        """Run extraction spider to extract deals from discovered pages"""
        print("🍽️  Starting Deal Extraction...")
        print("Extracting happy hour deals with data-hungry approach")
        
        # Check if discovery has been run
        discovered_file = self.data_dir / 'discovered_urls.json'
        if not discovered_file.exists():
            print("❌ No discovered pages found. Run discovery first:")
            print("    python cli.py discover")
            return 1
        
        cmd = [
            'scrapy', 'crawl', 'extractor',
            '-s', f'INPUT_FILE={discovered_file}',
            '-s', f'DEALS_OUTPUT_FILE={self.data_dir}/deals.json',
            '-L', 'INFO'
        ]
        
        if args.restaurant:
            # TODO: Add restaurant filtering
            print(f"Filtering to restaurant: {args.restaurant}")
        
        try:
            result = subprocess.run(cmd, cwd=self.project_dir, check=True)
            print("✅ Extraction completed successfully!")
            self._show_extraction_stats()
        except subprocess.CalledProcessError as e:
            print(f"❌ Extraction failed: {e}")
            return 1
        
        return 0
    
    def run_profile_extraction(self, args):
        """Run restaurant profile extraction spider"""
        print("🏢 Starting Restaurant Profile Extraction...")
        print("Extracting comprehensive restaurant data from main pages")
        
        cmd = [
            'scrapy', 'crawl', 'restaurant_profiler',
            '-s', f'INPUT_FILE={self.data_dir}/restaurants.json',
            '-s', f'PROFILES_OUTPUT_FILE={self.data_dir}/restaurant_profiles.json',
            '-L', 'INFO'
        ]
        
        if args.restaurant:
            # TODO: Add restaurant filtering
            print(f"Filtering to restaurant: {args.restaurant}")
        
        try:
            result = subprocess.run(cmd, cwd=self.project_dir, check=True)
            print("✅ Profile extraction completed successfully!")
            self._show_profile_stats()
        except subprocess.CalledProcessError as e:
            print(f"❌ Profile extraction failed: {e}")
            return 1
        
        return 0
    
    def run_comprehensive_pipeline(self, args):
        """Run complete discovery + extraction + profiling pipeline"""
        print("🚀 Starting Comprehensive Pipeline...")
        print("Running discovery, deal extraction, and profile extraction")
        
        # Run discovery
        discovery_result = self.run_discovery(args)
        if discovery_result != 0:
            return discovery_result
        
        print("\n" + "="*50)
        
        # Run deal extraction
        extraction_result = self.run_extraction(args)
        if extraction_result != 0:
            return extraction_result
        
        print("\n" + "="*50)
        
        # Run profile extraction
        profile_result = self.run_profile_extraction(args)
        if profile_result != 0:
            return profile_result
        
        print("\n🎉 Comprehensive pipeline completed successfully!")
        self._show_comprehensive_summary()
        
        return 0
    
    def run_full_pipeline(self, args):
        """Run complete discovery + extraction pipeline"""
        print("🚀 Starting Full Pipeline...")
        print("Running discovery followed by extraction")
        
        # Run discovery
        discovery_result = self.run_discovery(args)
        if discovery_result != 0:
            return discovery_result
        
        print("\n" + "="*50)
        
        # Run extraction
        extraction_result = self.run_extraction(args)
        if extraction_result != 0:
            return extraction_result
        
        print("\n🎉 Full pipeline completed successfully!")
        self._show_pipeline_summary()
        
        return 0
    
    def show_status(self, args):
        """Show current system status and statistics"""
        print("📊 Sips and Steals Scrapy Status")
        print("=" * 40)
        
        # Check for restaurant data
        restaurant_file = self.data_dir / 'restaurants.json'
        if restaurant_file.exists():
            with open(restaurant_file, 'r') as f:
                restaurant_data = json.load(f)
            
            if 'restaurants' in restaurant_data:
                restaurant_count = len(restaurant_data['restaurants'])
            else:
                restaurant_count = len(restaurant_data.get('areas', {}))
            
            print(f"🍽️  Restaurants loaded: {restaurant_count}")
        else:
            print("❌ No restaurant data found")
            return 1
        
        # Check for discovered pages
        discovered_file = self.data_dir / 'discovered_urls.json'
        if discovered_file.exists():
            with open(discovered_file, 'r') as f:
                discovered_data = json.load(f)
            
            page_count = len(discovered_data.get('pages', []))
            print(f"🔍 Pages discovered: {page_count}")
            
            # Show discovery timestamp
            exported_at = discovered_data.get('exported_at', 'Unknown')
            print(f"📅 Last discovery: {exported_at}")
        else:
            print("⚠️  No discovered pages (run discovery first)")
        
        # Check for extracted deals
        deals_file = self.data_dir / 'deals.json'
        if deals_file.exists():
            with open(deals_file, 'r') as f:
                deals_data = json.load(f)
            
            deal_count = len(deals_data.get('deals', []))
            print(f"🎯 Deals extracted: {deal_count}")
            
            # Show extraction timestamp
            exported_at = deals_data.get('exported_at', 'Unknown')
            print(f"📅 Last extraction: {exported_at}")
            
            # Show restaurant coverage
            restaurants_with_deals = set()
            for deal in deals_data.get('deals', []):
                if deal.get('restaurant_slug'):
                    restaurants_with_deals.add(deal['restaurant_slug'])
            
            coverage = len(restaurants_with_deals) / restaurant_count * 100
            print(f"📈 Coverage: {len(restaurants_with_deals)}/{restaurant_count} restaurants ({coverage:.1f}%)")
        else:
            print("⚠️  No extracted deals (run extraction first)")
        
        # Check for restaurant profiles
        profiles_file = self.data_dir / 'restaurant_profiles.json'
        if profiles_file.exists():
            with open(profiles_file, 'r') as f:
                profiles_data = json.load(f)
            
            profile_count = len(profiles_data.get('profiles', []))
            print(f"🏢 Restaurant profiles: {profile_count}")
            
            # Show profile timestamp
            exported_at = profiles_data.get('exported_at', 'Unknown')
            print(f"📅 Last profiling: {exported_at}")
            
            # Show average completeness
            profiles = profiles_data.get('profiles', [])
            if profiles:
                avg_completeness = sum(p.get('completeness_score', 0) for p in profiles) / len(profiles)
                print(f"📊 Avg profile completeness: {avg_completeness:.2f}")
        else:
            print("⚠️  No restaurant profiles (run profile extraction)")
        
        return 0
    
    def analyze_results(self, args):
        """Analyze extraction results and show insights"""
        print("🧠 Analyzing Extraction Results...")
        
        deals_file = self.data_dir / 'deals.json'
        if not deals_file.exists():
            print("❌ No deals found. Run extraction first.")
            return 1
        
        with open(deals_file, 'r') as f:
            deals_data = json.load(f)
        
        deals = deals_data.get('deals', [])
        if not deals:
            print("❌ No deals in file.")
            return 1
        
        print(f"📊 Analyzing {len(deals)} deals...")
        
        # Restaurant analysis
        restaurant_deals = {}
        for deal in deals:
            slug = deal.get('restaurant_slug', 'unknown')
            if slug not in restaurant_deals:
                restaurant_deals[slug] = []
            restaurant_deals[slug].append(deal)
        
        print(f"\n🏆 Top Restaurants by Deal Count:")
        sorted_restaurants = sorted(restaurant_deals.items(), key=lambda x: len(x[1]), reverse=True)
        for i, (slug, restaurant_deals_list) in enumerate(sorted_restaurants[:10], 1):
            avg_confidence = sum(d.get('confidence_score', 0) for d in restaurant_deals_list) / len(restaurant_deals_list)
            print(f"   {i}. {slug}: {len(restaurant_deals_list)} deals (avg confidence: {avg_confidence:.2f})")
        
        # Confidence analysis
        confidences = [d.get('confidence_score', 0) for d in deals]
        avg_confidence = sum(confidences) / len(confidences)
        high_confidence = len([c for c in confidences if c >= 0.8])
        
        print(f"\n🎯 Confidence Analysis:")
        print(f"   Average confidence: {avg_confidence:.2f}")
        print(f"   High confidence deals (≥0.8): {high_confidence}/{len(deals)} ({high_confidence/len(deals)*100:.1f}%)")
        
        # Extraction method analysis
        methods = {}
        for deal in deals:
            method = deal.get('extraction_method', 'unknown')
            methods[method] = methods.get(method, 0) + 1
        
        print(f"\n🛠️  Extraction Methods:")
        for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
            print(f"   {method}: {count} deals")
        
        return 0
    
    def run_pricing_extraction(self, args):
        """Run menu pricing extraction on discovered pages"""
        print("💰 Starting Menu Pricing Extraction...")
        print("Extracting pricing data from restaurant menus and PDFs")
        
        # Check if discovered pages exist
        discovered_file = self.data_dir / 'discovered_urls.json'
        if not discovered_file.exists():
            print("❌ No discovered pages found. Run discovery first:")
            print("   python cli.py discover")
            return 1
        
        cmd = [
            'scrapy', 'crawl', 'menu_pricing',
            '-L', 'INFO'
        ]
        
        if args.restaurant:
            # TODO: Add restaurant filtering capability
            print(f"Filtering to restaurant: {args.restaurant}")
        
        try:
            import os
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.project_dir)
            result = subprocess.run(cmd, cwd=self.project_dir, check=True, env=env)
            print("✅ Menu pricing extraction completed successfully!")
            
            # Show pricing summary
            self._show_pricing_summary()
            
            return 0
        except subprocess.CalledProcessError as e:
            print(f"❌ Menu pricing extraction failed: {e}")
            return 1
    
    def _show_pricing_summary(self):
        """Show summary of pricing extraction results"""
        pricing_file = self.data_dir / 'menu_pricing.json'
        summary_file = self.data_dir / 'pricing_summary.json'
        
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                data = json.load(f)
            
            total_restaurants = data.get('total_restaurants_with_pricing', 0)
            pricing_summary = data.get('pricing_summary', {})
            
            print(f"\n📊 Pricing Extraction Summary:")
            print(f"   Restaurants with pricing data: {total_restaurants}")
            
            # Show price range distribution
            range_counts = {}
            total_items = 0
            
            for restaurant_slug, summary in pricing_summary.items():
                price_range = summary.get('overall_price_range', '$')
                range_counts[price_range] = range_counts.get(price_range, 0) + 1
                total_items += summary.get('total_price_items', 0)
            
            print(f"   Total menu items extracted: {total_items}")
            print("\n   Price Range Distribution:")
            for price_range in ['$', '$$', '$$$', '$$$$']:
                count = range_counts.get(price_range, 0)
                if count > 0:
                    percentage = count / total_restaurants * 100
                    print(f"     {price_range}: {count} restaurants ({percentage:.1f}%)")
            
            # Show top restaurants by price item count
            if pricing_summary:
                top_restaurants = sorted(
                    pricing_summary.items(),
                    key=lambda x: x[1].get('total_price_items', 0),
                    reverse=True
                )[:3]
                
                print("\n🏆 Top Restaurants by Menu Items Extracted:")
                for slug, summary in top_restaurants:
                    name = summary.get('restaurant_name', slug)
                    items = summary.get('total_price_items', 0)
                    price_range = summary.get('overall_price_range', '$')
                    avg_price = summary.get('overall_average_price', 0)
                    print(f"     {name}: {items} items ({price_range}, avg: ${avg_price})")
        else:
            print("\n⚠️  No pricing summary found")
    
    def _show_discovery_stats(self):
        """Show discovery statistics"""
        discovered_file = self.data_dir / 'discovered_urls.json'
        if discovered_file.exists():
            with open(discovered_file, 'r') as f:
                data = json.load(f)
            
            page_count = len(data.get('pages', []))
            print(f"📊 Discovered {page_count} potentially relevant pages")
            
            # Show top restaurants by pages discovered
            restaurant_pages = {}
            for page in data.get('pages', []):
                slug = page.get('restaurant_slug', 'unknown')
                restaurant_pages[slug] = restaurant_pages.get(slug, 0) + 1
            
            if restaurant_pages:
                top_restaurants = sorted(restaurant_pages.items(), key=lambda x: x[1], reverse=True)[:5]
                print("🏆 Top discoveries:")
                for slug, count in top_restaurants:
                    print(f"   {slug}: {count} pages")
    
    def _show_extraction_stats(self):
        """Show extraction statistics"""
        deals_file = self.data_dir / 'deals.json'
        if deals_file.exists():
            with open(deals_file, 'r') as f:
                data = json.load(f)
            
            deal_count = len(data.get('deals', []))
            print(f"📊 Extracted {deal_count} deals")
            
            # Show restaurants with deals
            restaurants_with_deals = set()
            for deal in data.get('deals', []):
                if deal.get('restaurant_slug'):
                    restaurants_with_deals.add(deal['restaurant_slug'])
            
            print(f"🍽️  Found deals for {len(restaurants_with_deals)} restaurants")
    
    def _show_profile_stats(self):
        """Show profile extraction statistics"""
        profiles_file = self.data_dir / 'restaurant_profiles.json'
        if profiles_file.exists():
            with open(profiles_file, 'r') as f:
                data = json.load(f)
            
            profile_count = len(data.get('profiles', []))
            print(f"📊 Extracted {profile_count} restaurant profiles")
            
            # Show completeness statistics
            profiles = data.get('profiles', [])
            if profiles:
                completeness_scores = [p.get('completeness_score', 0) for p in profiles]
                avg_completeness = sum(completeness_scores) / len(completeness_scores)
                high_completeness = len([s for s in completeness_scores if s >= 0.5])
                
                print(f"📈 Avg completeness: {avg_completeness:.2f}")
                print(f"🎯 High completeness profiles (≥0.5): {high_completeness}/{profile_count}")
                
                # Show top complete profiles
                profiles_by_completeness = sorted(profiles, 
                                                key=lambda x: x.get('completeness_score', 0), 
                                                reverse=True)[:5]
                print("🏆 Most complete profiles:")
                for profile in profiles_by_completeness:
                    name = profile.get('restaurant_name', 'Unknown')
                    score = profile.get('completeness_score', 0)
                    print(f"   {name}: {score:.2f}")
    
    def _show_comprehensive_summary(self):
        """Show comprehensive pipeline summary"""
        print("\n📈 Comprehensive Pipeline Summary:")
        
        # Load all data files
        discovered_file = self.data_dir / 'discovered_urls.json'
        deals_file = self.data_dir / 'deals.json'
        profiles_file = self.data_dir / 'restaurant_profiles.json'
        
        stats = {}
        
        if discovered_file.exists():
            with open(discovered_file, 'r') as f:
                discovered_data = json.load(f)
            stats['pages'] = len(discovered_data.get('pages', []))
        
        if deals_file.exists():
            with open(deals_file, 'r') as f:
                deals_data = json.load(f)
            stats['deals'] = len(deals_data.get('deals', []))
            
            # Count restaurants with deals
            restaurants_with_deals = set()
            for deal in deals_data.get('deals', []):
                if deal.get('restaurant_slug'):
                    restaurants_with_deals.add(deal['restaurant_slug'])
            stats['restaurants_with_deals'] = len(restaurants_with_deals)
        
        if profiles_file.exists():
            with open(profiles_file, 'r') as f:
                profiles_data = json.load(f)
            stats['profiles'] = len(profiles_data.get('profiles', []))
            
            # Calculate average completeness
            profiles = profiles_data.get('profiles', [])
            if profiles:
                avg_completeness = sum(p.get('completeness_score', 0) for p in profiles) / len(profiles)
                stats['avg_completeness'] = avg_completeness
        
        # Display comprehensive stats
        if 'pages' in stats and 'deals' in stats:
            print(f"   Discovery → Deals: {stats['pages']} pages → {stats['deals']} deals")
        
        if 'profiles' in stats:
            print(f"   Restaurant Profiling: {stats['profiles']} comprehensive profiles")
            if 'avg_completeness' in stats:
                print(f"   Average Profile Completeness: {stats['avg_completeness']:.2f}")
        
        if 'restaurants_with_deals' in stats and 'profiles' in stats:
            print(f"   Total Restaurant Coverage: {max(stats['restaurants_with_deals'], stats['profiles'])} restaurants")
    
    def _show_pipeline_summary(self):
        """Show complete pipeline summary"""
        print("\n📈 Pipeline Summary:")
        
        # Load all data files
        discovered_file = self.data_dir / 'discovered_urls.json'
        deals_file = self.data_dir / 'deals.json'
        
        if discovered_file.exists() and deals_file.exists():
            with open(discovered_file, 'r') as f:
                discovered_data = json.load(f)
            with open(deals_file, 'r') as f:
                deals_data = json.load(f)
            
            page_count = len(discovered_data.get('pages', []))
            deal_count = len(deals_data.get('deals', []))
            
            if page_count > 0:
                extraction_rate = deal_count / page_count * 100
                print(f"   Discovery → Extraction: {page_count} pages → {deal_count} deals ({extraction_rate:.1f}% success rate)")
            
            # Show top performing restaurants
            restaurant_deals = {}
            for deal in deals_data.get('deals', []):
                slug = deal.get('restaurant_slug', 'unknown')
                restaurant_deals[slug] = restaurant_deals.get(slug, 0) + 1
            
            if restaurant_deals:
                top_performers = sorted(restaurant_deals.items(), key=lambda x: x[1], reverse=True)[:3]
                print("\n🏆 Top Performers:")
                for slug, count in top_performers:
                    print(f"   {slug}: {count} deals")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Sips and Steals Scrapy CLI - Minimal Viable Architecture',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py discover                    # Discover happy hour pages
  python cli.py extract                     # Extract deals from discovered pages
  python cli.py profile                     # Extract restaurant profiles
  python cli.py pipeline                    # Run discovery + extraction (deals only)
  python cli.py comprehensive               # Run full discovery + extraction + profiling
  python cli.py status                      # Show system status
  python cli.py analyze                     # Analyze extraction results
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Discovery command
    discover_parser = subparsers.add_parser('discover', help='Discover happy hour pages')
    discover_parser.add_argument('--restaurant', help='Filter to specific restaurant slug')
    
    # Extraction command
    extract_parser = subparsers.add_parser('extract', help='Extract deals from discovered pages')
    extract_parser.add_argument('--restaurant', help='Filter to specific restaurant slug')
    
    # Profile extraction command
    profile_parser = subparsers.add_parser('profile', help='Extract comprehensive restaurant profiles')
    profile_parser.add_argument('--restaurant', help='Filter to specific restaurant slug')
    
    # Pipeline command (deals only)
    pipeline_parser = subparsers.add_parser('pipeline', help='Run discovery + extraction pipeline (deals only)')
    pipeline_parser.add_argument('--restaurant', help='Filter to specific restaurant slug')
    
    # Comprehensive pipeline command (deals + profiles)
    comprehensive_parser = subparsers.add_parser('comprehensive', help='Run full discovery + extraction + profiling pipeline')
    comprehensive_parser.add_argument('--restaurant', help='Filter to specific restaurant slug')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    # Analysis command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze extraction results')
    
    # Pricing command  
    pricing_parser = subparsers.add_parser('pricing', help='Run menu pricing extraction on discovered pages')
    pricing_parser.add_argument('--restaurant', help='Filter to specific restaurant slug')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = ScrapyCLI()
    
    # Route to appropriate method
    if args.command == 'discover':
        return cli.run_discovery(args)
    elif args.command == 'extract':
        return cli.run_extraction(args)
    elif args.command == 'profile':
        return cli.run_profile_extraction(args)
    elif args.command == 'pipeline':
        return cli.run_full_pipeline(args)
    elif args.command == 'comprehensive':
        return cli.run_comprehensive_pipeline(args)
    elif args.command == 'status':
        return cli.show_status(args)
    elif args.command == 'analyze':
        return cli.analyze_results(args)
    elif args.command == 'pricing':
        return cli.run_pricing_extraction(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())