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
        self.project_dir = Path(__file__).parent
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
            '-s', f'DISCOVERY_OUTPUT_FILE={self.data_dir}/discovered_pages.json',
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
        discovered_file = self.data_dir / 'discovered_pages.json'
        if not discovered_file.exists():
            print("❌ No discovered pages found. Run discovery first:")
            print("    python cli.py discover")
            return 1
        
        cmd = [
            'scrapy', 'crawl', 'extractor',
            '-s', f'INPUT_FILE={discovered_file}',
            '-s', f'DEALS_OUTPUT_FILE={self.data_dir}/scrapy_deals.json',
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
        discovered_file = self.data_dir / 'discovered_pages.json'
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
        deals_file = self.data_dir / 'scrapy_deals.json'
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
        
        return 0
    
    def analyze_results(self, args):
        """Analyze extraction results and show insights"""
        print("🧠 Analyzing Extraction Results...")
        
        deals_file = self.data_dir / 'scrapy_deals.json'
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
    
    def _show_discovery_stats(self):
        """Show discovery statistics"""
        discovered_file = self.data_dir / 'discovered_pages.json'
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
        deals_file = self.data_dir / 'scrapy_deals.json'
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
    
    def _show_pipeline_summary(self):
        """Show complete pipeline summary"""
        print("\n📈 Pipeline Summary:")
        
        # Load all data files
        discovered_file = self.data_dir / 'discovered_pages.json'
        deals_file = self.data_dir / 'scrapy_deals.json'
        
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
  python cli.py pipeline                    # Run full discovery + extraction
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
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run full discovery + extraction pipeline')
    pipeline_parser.add_argument('--restaurant', help='Filter to specific restaurant slug')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    # Analysis command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze extraction results')
    
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
    elif args.command == 'pipeline':
        return cli.run_full_pipeline(args)
    elif args.command == 'status':
        return cli.show_status(args)
    elif args.command == 'analyze':
        return cli.analyze_results(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())