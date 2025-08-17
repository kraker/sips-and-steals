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
    
    # Show failure reasons breakdown
    failure_reasons = {}
    robots_blocked = []
    for restaurant in dm.restaurants.values():
        if hasattr(restaurant, 'scraping_config') and restaurant.scraping_config.last_failure_reason:
            reason = restaurant.scraping_config.last_failure_reason
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            if reason == "robots_txt":
                robots_blocked.append(restaurant.name)
    
    if failure_reasons:
        print(f"\n🚫 Scraping failure reasons:")
        for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True):
            icon = {"robots_txt": "🤖", "timeout": "⏱️", "not_found": "🔍", "no_content": "📄", "connection_error": "🔌"}.get(reason, "❓")
            print(f"  {icon} {reason}: {count} restaurants")
        
        if robots_blocked:
            print(f"\n🤖 Robots.txt blocked sites ({len(robots_blocked)}):")
            for name in robots_blocked[:5]:
                print(f"  • {name}")
            if len(robots_blocked) > 5:
                print(f"  ... and {len(robots_blocked) - 5} more")


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
    
    elif args.neighborhood:
        # Scrape all restaurants in neighborhood
        print(f"🏘️  Scraping all restaurants in {args.neighborhood}...")
        scheduled = scheduler.schedule_neighborhood(args.neighborhood, TaskPriority.HIGH)
        print(f"📋 Scheduled {scheduled} restaurants")
    
    elif args.all:
        # Scrape all restaurants needing updates
        print("🔄 Scraping all restaurants needing updates...")
        scheduled = scheduler.schedule_all_needing_update()
        print(f"📋 Scheduled {scheduled} restaurants")
    
    else:
        print("❌ Please specify --restaurant, --district, --neighborhood, or --all")
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
    if config.last_failure_reason:
        failure_icon = {"robots_txt": "🤖", "timeout": "⏱️", "not_found": "🔍", "no_content": "📄", "connection_error": "🔌"}.get(config.last_failure_reason, "❓")
        print(f"  Last Failure Reason: {failure_icon} {config.last_failure_reason}")
    
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
            if deal.prices:
                print(f"     Price: {', '.join(deal.prices)}")
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


async def cmd_contact_async(args):
    """Async version of contact extraction for batch operations"""
    import asyncio
    from src.scrapers.async_contact_extractor import AsyncContactExtractor
    
    data_manager = DataManager()
    
    # Determine which restaurants to update
    restaurants_to_update = []
    
    if args.missing_only:
        # Restaurants missing contact data
        for slug, restaurant in data_manager.restaurants.items():
            # Check for missing phone, email, or operating hours
            has_phone = restaurant.phone or (hasattr(restaurant, 'contact_info') and restaurant.contact_info and restaurant.contact_info.primary_phone)
            has_email = hasattr(restaurant, 'contact_info') and restaurant.contact_info and restaurant.contact_info.general_email
            has_hours = hasattr(restaurant, 'operating_hours') and restaurant.operating_hours and any(restaurant.operating_hours.values())
            
            if not has_phone or not has_email or not has_hours:
                restaurants_to_update.append(slug)
    elif args.all:
        # All restaurants
        restaurants_to_update = list(data_manager.restaurants.keys())
    
    if not restaurants_to_update:
        print("✅ All restaurants already have complete contact information!")
        return
    
    print(f"🚀 Processing {len(restaurants_to_update)} restaurants concurrently...")
    
    # Use async extractor for batch processing
    extractor = AsyncContactExtractor(data_manager)
    
    # Process restaurants with controlled concurrency
    batch_size = getattr(args, 'workers', 5)  # Default to 5 concurrent workers
    results = await extractor.extract_batch(restaurants_to_update, batch_size=batch_size)
    
    # Analyze results
    successful = sum(1 for r in results if r.get('status') == 'success')
    no_changes = sum(1 for r in results if r.get('status') == 'no_changes')
    permanent_errors = sum(1 for r in results if r.get('status') == 'permanent_error')
    temporary_errors = sum(1 for r in results if r.get('status') == 'temporary_error')
    other_errors = sum(1 for r in results if r.get('status') not in ['success', 'no_changes', 'permanent_error', 'temporary_error'])
    
    print(f"\n🎉 Batch processing completed!")
    print(f"✅ Successfully updated: {successful}")
    print(f"⚪ No changes needed: {no_changes}")
    print(f"❌ Permanent errors: {permanent_errors}")
    print(f"⚠️  Temporary errors: {temporary_errors}")
    if other_errors > 0:
        print(f"❓ Other errors: {other_errors}")
    
    # Show error breakdown if there are failures
    if permanent_errors > 0 or temporary_errors > 0:
        print(f"\n📋 Error breakdown:")
        error_types = {}
        for result in results:
            if result.get('status') in ['permanent_error', 'temporary_error']:
                error_type = result.get('error_type', 'unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            icon = {"robots_txt": "🤖", "timeout": "⏱️", "not_found": "🔍", "no_content": "📄", "connection_error": "🔌"}.get(error_type, "❓")
            print(f"  {icon} {error_type}: {count} restaurants")


def cmd_contact(args):
    """Update contact information for restaurants"""
    from src.scrapers.core.base import ConfigBasedScraper
    from src.models import Restaurant, ContactInfo, DiningInfo, ServiceInfo, BusinessStatus
    
    data_manager = DataManager()
    
    # Determine which restaurants to update
    restaurants_to_update = []
    
    if args.restaurant:
        # Single restaurant
        if args.restaurant in data_manager.restaurants:
            restaurants_to_update.append(args.restaurant)
        else:
            print(f"❌ Restaurant '{args.restaurant}' not found")
            return
    elif args.missing_only:
        # Restaurants missing contact data
        for slug, restaurant in data_manager.restaurants.items():
            # Check for missing phone, email, or operating hours
            has_phone = restaurant.phone or (hasattr(restaurant, 'contact_info') and restaurant.contact_info and restaurant.contact_info.primary_phone)
            has_email = hasattr(restaurant, 'contact_info') and restaurant.contact_info and restaurant.contact_info.general_email
            has_hours = hasattr(restaurant, 'operating_hours') and restaurant.operating_hours
            
            if not has_phone or not has_email or not has_hours:
                restaurants_to_update.append(slug)
    elif args.all:
        # All restaurants
        restaurants_to_update = list(data_manager.restaurants.keys())
    
    print(f"🎯 Updating contact information for {len(restaurants_to_update)} restaurants...")
    
    updated_count = 0
    
    for slug in restaurants_to_update:
        restaurant = data_manager.restaurants[slug]
        
        try:
            print(f"📞 Processing {restaurant.name}...")
            
            # Update scraping timestamp
            if hasattr(restaurant, 'scraping_config'):
                restaurant.scraping_config.last_scraped = datetime.now()
            
            # Use ConfigBasedScraper to extract restaurant info
            scraper = ConfigBasedScraper(restaurant)
            restaurant_info = scraper.scrape_restaurant_info()
            
            # Check if we got any meaningful data
            has_meaningful_data = any([
                restaurant_info.get('contact_info', {}).get('primary_phone'),
                restaurant_info.get('contact_info', {}).get('general_email'),
                restaurant_info.get('operating_hours'),
                restaurant_info.get('service_info', {}).get('accepts_reservations'),
                restaurant_info.get('service_info', {}).get('offers_delivery')
            ])
            
            # Update restaurant object with extracted info
            updated = False
            
            if restaurant_info.get('contact_info'):
                contact_info_dict = restaurant_info['contact_info']
                
                # Update phone if missing or improve existing
                if contact_info_dict.get('primary_phone') and not restaurant.phone:
                    restaurant.phone = contact_info_dict['primary_phone']
                    updated = True
                
                # Update contact info object
                if hasattr(restaurant, 'contact_info') and restaurant.contact_info:
                    # Update existing contact info
                    for key, value in contact_info_dict.items():
                        if value and hasattr(restaurant.contact_info, key):
                            setattr(restaurant.contact_info, key, value)
                            updated = True
                else:
                    # Create new contact info object from dict values
                    restaurant.contact_info = ContactInfo(
                        primary_phone=contact_info_dict.get('primary_phone'),
                        reservation_phone=contact_info_dict.get('reservation_phone'),
                        general_email=contact_info_dict.get('general_email'),
                        reservations_email=contact_info_dict.get('reservations_email'),
                        events_email=contact_info_dict.get('events_email'),
                        instagram=contact_info_dict.get('instagram'),
                        facebook=contact_info_dict.get('facebook'),
                        twitter=contact_info_dict.get('twitter'),
                        tiktok=contact_info_dict.get('tiktok')
                    )
                    updated = True
            
            if restaurant_info.get('operating_hours'):
                restaurant.operating_hours = restaurant_info['operating_hours']
                updated = True
            
            if restaurant_info.get('service_info'):
                service_info_dict = restaurant_info['service_info']
                if hasattr(restaurant, 'service_info'):
                    # Create new service info object from dict values
                    restaurant.service_info = ServiceInfo(
                        accepts_reservations=service_info_dict.get('accepts_reservations', False),
                        offers_delivery=service_info_dict.get('offers_delivery', False),
                        offers_takeout=service_info_dict.get('offers_takeout', False),
                        offers_curbside=service_info_dict.get('offers_curbside', False),
                        opentable_url=service_info_dict.get('opentable_url'),
                        resy_url=service_info_dict.get('resy_url'),
                        direct_reservation_url=service_info_dict.get('direct_reservation_url'),
                        doordash_url=service_info_dict.get('doordash_url'),
                        ubereats_url=service_info_dict.get('ubereats_url'),
                        grubhub_url=service_info_dict.get('grubhub_url')
                    )
                    updated = True
            
            if restaurant_info.get('dining_info'):
                dining_info_dict = restaurant_info['dining_info']
                if hasattr(restaurant, 'dining_info'):
                    # Create new dining info object from dict values
                    restaurant.dining_info = DiningInfo(
                        price_range=dining_info_dict.get('price_range'),
                        dress_code=dining_info_dict.get('dress_code'),
                        atmosphere=dining_info_dict.get('atmosphere', []),
                        dining_style=dining_info_dict.get('dining_style'),
                        total_seats=dining_info_dict.get('total_seats'),
                        bar_seats=dining_info_dict.get('bar_seats'),
                        outdoor_seats=dining_info_dict.get('outdoor_seats')
                    )
                    updated = True
            
            if restaurant_info.get('business_status'):
                if hasattr(restaurant, 'business_status'):
                    restaurant.business_status = BusinessStatus(restaurant_info['business_status'])
                    updated = True
            
            if updated:
                restaurant.last_updated = datetime.now()
                # Update scraping success tracking
                if hasattr(restaurant, 'scraping_config'):
                    restaurant.scraping_config.last_success = datetime.now()
                    restaurant.scraping_config.consecutive_failures = 0
                    restaurant.scraping_config.last_failure_reason = None
                updated_count += 1
                print(f"  ✅ Updated {restaurant.name}")
            elif has_meaningful_data:
                # We got some data but it wasn't new/different
                if hasattr(restaurant, 'scraping_config'):
                    restaurant.scraping_config.last_success = datetime.now()
                    restaurant.scraping_config.consecutive_failures = 0
                    restaurant.scraping_config.last_failure_reason = None
                print(f"  ⚪ No new data for {restaurant.name}")
            else:
                # We didn't get meaningful data - this is a soft failure
                if hasattr(restaurant, 'scraping_config'):
                    restaurant.scraping_config.consecutive_failures += 1
                    restaurant.scraping_config.last_failure_reason = "no_content"
                print(f"  ⚠️  No meaningful data extracted for {restaurant.name}")
                
        except Exception as e:
            error_str = str(e).lower()
            failure_reason = "unknown"
            
            # Categorize the failure reason
            if "robots.txt" in error_str:
                failure_reason = "robots_txt"
            elif "timeout" in error_str:
                failure_reason = "timeout" 
            elif "404" in error_str:
                failure_reason = "not_found"
            elif "no valid content" in error_str:
                failure_reason = "no_content"
            elif "connection" in error_str:
                failure_reason = "connection_error"
            
            # Update scraping failure tracking
            if hasattr(restaurant, 'scraping_config'):
                restaurant.scraping_config.consecutive_failures += 1
                restaurant.scraping_config.last_failure_reason = failure_reason
            
            print(f"  ❌ Failed to update {restaurant.name}: {e}")
            logger.exception(f"Error updating contact info for {restaurant.name}")
        
        # Be respectful with delays
        import time
        time.sleep(1)
    
    # Always save data to persist scraping metadata (failure reasons, timestamps, etc.)
    data_manager.save_data()
    
    if updated_count > 0:
        print(f"\n🎉 Successfully updated contact information for {updated_count} restaurants!")
    else:
        print(f"\n⚪ No restaurants were updated, but scraping metadata has been saved.")


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
    scrape_group.add_argument('--neighborhood', help='Scrape all restaurants in neighborhood')
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
    
    # Contact command
    contact_parser = subparsers.add_parser('contact', help='Scrape contact information for restaurants')
    contact_group = contact_parser.add_mutually_exclusive_group(required=True)
    contact_group.add_argument('--restaurant', help='Update contact info for specific restaurant by slug')
    contact_group.add_argument('--missing-only', action='store_true', help='Update all restaurants missing contact data')
    contact_group.add_argument('--all', action='store_true', help='Update contact info for all restaurants')
    contact_parser.add_argument('--workers', type=int, default=2, help='Number of concurrent workers')
    
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
    elif args.command == 'contact':
        # Use async for batch operations, sync for single restaurant
        if args.missing_only or args.all:
            # Async batch processing
            import asyncio
            asyncio.run(cmd_contact_async(args))
        else:
            # Single restaurant - use sync version
            cmd_contact(args)
    elif args.command == 'init':
        cmd_init(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()