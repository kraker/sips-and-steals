#!/usr/bin/env python3
"""
Enhanced Sips and Steals CLI - Production scraping system
Command-line interface for the enhanced scraping architecture
"""

import sys
import os
import argparse
import logging
import json
from datetime import datetime
from pathlib import Path

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data_manager import DataManager
from scheduler import ScrapingScheduler, TaskPriority, scrape_restaurant_now
from quality_checker import QualityChecker
from models import ScrapingStatus

# Setup basic logging (detailed setup happens in setup_directories)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_directories():
    """Create necessary directories"""
    dirs = ['logs', 'data/backups', 'data/deals_archive']
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Setup file logging after directories are created
    log_file = Path('logs/scraping.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)


def cmd_status(args):
    """Show system status"""
    dm = DataManager()
    stats = dm.get_scraping_stats()
    
    print("🍻 Sips and Steals - Enhanced Scraping System")
    print("=" * 50)
    print(f"📊 Total Restaurants: {stats['total_restaurants']}")
    print(f"🌐 With Websites: {stats['restaurants_with_websites']}")
    print(f"📈 With Live Deals: {stats['restaurants_with_live_deals']}")
    print(f"🔄 With Fresh Deals: {stats['restaurants_with_fresh_deals']}")
    print(f"✅ Success Rate: {stats['scraping_success_rate']}%")
    print(f"📋 Coverage: {stats['coverage_percentage']}%")
    
    # Show restaurants needing updates
    need_scraping = dm.get_restaurants_needing_scraping()
    if need_scraping:
        print(f"\n⏰ Restaurants needing updates: {len(need_scraping)}")
        for restaurant in need_scraping[:5]:
            print(f"  • {restaurant.name}")
        if len(need_scraping) > 5:
            print(f"  ... and {len(need_scraping) - 5} more")


def cmd_scrape(args):
    """Run scraping tasks"""
    dm = DataManager()
    scheduler = ScrapingScheduler(dm, max_workers=args.workers)
    
    if args.restaurant:
        # Scrape specific restaurant
        print(f"🎯 Scraping {args.restaurant}...")
        scheduled = scheduler.schedule_restaurant(args.restaurant, TaskPriority.URGENT)
        if not scheduled:
            print(f"❌ Could not schedule {args.restaurant}")
            return
    
    elif args.district:
        # Scrape all restaurants in district
        print(f"🏢 Scraping all restaurants in {args.district}...")
        scheduled = scheduler.schedule_district(args.district, TaskPriority.HIGH)
        print(f"📋 Scheduled {scheduled} restaurants")
    
    elif args.all:
        # Scrape all restaurants needing updates
        print("🔄 Scraping all restaurants needing updates...")
        scheduled = scheduler.schedule_all_needing_update()
        print(f"📋 Scheduled {scheduled} restaurants")
    
    else:
        print("❌ Please specify --restaurant, --district, or --all")
        return
    
    # Run the scheduled tasks
    print("🚀 Starting scraping tasks...")
    result = scheduler.run_scheduled_tasks()
    
    print(f"\n✅ Scraping completed!")
    print(f"⏱️  Runtime: {result.get('runtime_seconds', 0):.1f} seconds")
    print(f"✅ Tasks completed: {result.get('tasks_completed', 0)}")
    
    # Show updated stats
    stats = dm.get_scraping_stats()
    print(f"📈 Updated coverage: {stats['coverage_percentage']}%")


def cmd_quality(args):
    """Run quality checks"""
    dm = DataManager()
    checker = QualityChecker()
    
    restaurants = list(dm.restaurants.values())
    
    if args.restaurant:
        # Check specific restaurant
        restaurant = dm.get_restaurant(args.restaurant)
        if not restaurant:
            print(f"❌ Restaurant '{args.restaurant}' not found")
            return
        
        restaurants = [restaurant]
        print(f"🔍 Quality check for {restaurant.name}")
    else:
        print(f"🔍 Quality check for {len(restaurants)} restaurants")
    
    # Generate quality report
    report = checker.generate_quality_report(restaurants)
    
    print("\n📊 Quality Report")
    print("=" * 30)
    print(f"Quality Score: {report['summary']['quality_score']}/100")
    print(f"Total Issues: {report['summary']['total_issues']}")
    print(f"Restaurants with Issues: {report['summary']['restaurants_with_issues']}")
    
    # Show issues by level
    print("\n📋 Issues by Level:")
    for level, count in report['issues_by_level'].items():
        if count > 0:
            print(f"  {level.upper()}: {count}")
    
    # Show top issues
    if report['top_issues']:
        print("\n🔥 Most Common Issues:")
        for issue in report['top_issues'][:3]:
            print(f"  • {issue['issue']} ({issue['count']} occurrences)")
    
    # Show improvement suggestions
    suggestions = checker.get_improvement_suggestions(restaurants)
    if suggestions:
        print("\n💡 Improvement Suggestions:")
        for suggestion in suggestions:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(suggestion['priority'], "⚪")
            print(f"  {priority_icon} {suggestion['message']}")
    
    # Save detailed report if requested
    if args.export:
        report_file = f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n💾 Detailed report saved to {report_file}")


def cmd_export(args):
    """Export data for website generation"""
    dm = DataManager()
    
    print("📤 Exporting data for website generation...")
    
    # Export enhanced data
    export_data = dm.export_for_website()
    
    # Save to file for website generator
    output_file = args.output or "data/restaurants_export.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Data exported to {output_file}")
    print(f"📊 Exported {export_data['metadata']['total_restaurants']} restaurants")
    print(f"📈 {export_data['metadata']['scraping_stats']['restaurants_with_live_deals']} have live deal data")


def cmd_restaurant(args):
    """Show detailed restaurant information"""
    dm = DataManager()
    
    restaurant = dm.get_restaurant(args.slug)
    if not restaurant:
        print(f"❌ Restaurant '{args.slug}' not found")
        return
    
    print(f"🍽️  {restaurant.name}")
    print("=" * (len(restaurant.name) + 4))
    print(f"District: {restaurant.district}")
    print(f"Neighborhood: {restaurant.neighborhood or 'Not specified'}")
    print(f"Address: {restaurant.address or 'Not specified'}")
    print(f"Cuisine: {restaurant.cuisine or 'Not specified'}")
    print(f"Website: {restaurant.website or 'Not specified'}")
    
    print(f"\n📋 Scraping Configuration:")
    config = restaurant.scraping_config
    print(f"  Enabled: {config.enabled}")
    print(f"  Frequency: Every {config.scraping_frequency_hours} hours")
    print(f"  Last Scraped: {config.last_scraped or 'Never'}")
    print(f"  Last Success: {config.last_success or 'Never'}")
    print(f"  Consecutive Failures: {config.consecutive_failures}")
    
    # Show deals
    current_deals = restaurant.get_current_deals()
    if current_deals:
        print(f"\n🎉 Current Deals ({len(current_deals)}):")
        for deal in current_deals:
            confidence_icon = "🟢" if deal.confidence_score > 0.8 else "🟡" if deal.confidence_score > 0.5 else "🔴"
            print(f"  {confidence_icon} {deal.title}")
            if deal.description:
                print(f"     {deal.description[:80]}{'...' if len(deal.description) > 80 else ''}")
            if deal.start_time and deal.end_time:
                print(f"     Time: {deal.start_time} - {deal.end_time}")
            if deal.price:
                print(f"     Price: {deal.price}")
    else:
        print("\n❌ No current deals available")
    
    # Show quality issues
    checker = QualityChecker()
    issues = checker.check_restaurant_quality(restaurant)
    if issues:
        print(f"\n⚠️  Quality Issues ({len(issues)}):")
        for issue in issues:
            level_icon = {"error": "🔴", "warning": "🟡", "info": "🔵", "critical": "💀"}.get(issue.level.value, "⚪")
            print(f"  {level_icon} {issue.message}")


def cmd_init(args):
    """Initialize enhanced scraping system"""
    print("🔧 Initializing enhanced scraping system...")
    
    setup_directories()
    dm = DataManager()
    
    print("✅ Directories created")
    print("✅ Data manager initialized")
    print(f"📊 Loaded {len(dm.restaurants)} restaurants")
    
    # Show system readiness
    with_websites = len(dm.get_restaurants_with_website())
    print(f"🌐 {with_websites} restaurants ready for scraping")
    
    print("\n🎉 System initialized successfully!")
    print("Next steps:")
    print("  1. Run 'python scraper_cli.py status' to see current state")
    print("  2. Run 'python scraper_cli.py scrape --all' to start scraping")
    print("  3. Run 'python scraper_cli.py quality' to check data quality")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Enhanced Sips and Steals Scraping System")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Run scraping tasks')
    scrape_group = scrape_parser.add_mutually_exclusive_group(required=True)
    scrape_group.add_argument('--restaurant', help='Scrape specific restaurant by slug')
    scrape_group.add_argument('--district', help='Scrape all restaurants in district')
    scrape_group.add_argument('--all', action='store_true', help='Scrape all restaurants needing updates')
    scrape_parser.add_argument('--workers', type=int, default=3, help='Number of concurrent workers')
    
    # Quality command
    quality_parser = subparsers.add_parser('quality', help='Check data quality')
    quality_parser.add_argument('--restaurant', help='Check specific restaurant')
    quality_parser.add_argument('--export', action='store_true', help='Export detailed quality report')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export data for website')
    export_parser.add_argument('--output', help='Output file path')
    
    # Restaurant command
    restaurant_parser = subparsers.add_parser('restaurant', help='Show restaurant details')
    restaurant_parser.add_argument('slug', help='Restaurant slug')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize system')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Ensure directories exist
    setup_directories()
    
    # Route to appropriate command
    if args.command == 'status':
        cmd_status(args)
    elif args.command == 'scrape':
        cmd_scrape(args)
    elif args.command == 'quality':
        cmd_quality(args)
    elif args.command == 'export':
        cmd_export(args)
    elif args.command == 'restaurant':
        cmd_restaurant(args)
    elif args.command == 'init':
        cmd_init(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()