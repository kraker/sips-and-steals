#!/usr/bin/env python3
"""
Restaurant URL Fixer

Automatically discovers and fixes broken restaurant URLs using the enhanced
URL discovery system. Updates restaurant data with working URLs.
"""

import json
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse
import sys

# Add src to path for imports
sys.path.append('./src')
from scrapers.url_discovery import HappyHourUrlDiscovery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RestaurantUrlFixer:
    """Fixes broken restaurant URLs using intelligent discovery"""
    
    def __init__(self):
        self.discovery = HappyHourUrlDiscovery()
        self.fixes_applied = 0
        self.restaurants_checked = 0
    
    def check_and_fix_url(self, restaurant_slug: str, website: str) -> Optional[str]:
        """
        Check if a restaurant URL works, and if not, find a better one.
        
        Args:
            restaurant_slug: Restaurant identifier
            website: Current website URL
            
        Returns:
            Fixed URL if found, None if no fix available
        """
        if not website:
            return None
        
        logger.info(f"Checking URL for {restaurant_slug}: {website}")
        
        try:
            # Test current URL
            response = self.discovery.session.head(website)
            if response.status_code == 200:
                logger.info(f"✅ {restaurant_slug}: Current URL works")
                return website
        except Exception as e:
            logger.warning(f"❌ {restaurant_slug}: Current URL failed: {e}")
        
        # URL is broken, try to discover alternatives
        parsed = urlparse(website)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        
        logger.info(f"🔍 Discovering alternatives for {restaurant_slug} from {base_domain}")
        
        # Use our URL discovery system
        discovered = self.discovery.discover_urls(base_domain)
        
        if discovered and discovered[0]['score'] > 0.1:  # Lower threshold for fixes
            best_url = discovered[0]['url']
            logger.info(f"🎯 Found better URL for {restaurant_slug}: {best_url} (score: {discovered[0]['score']:.2f})")
            return best_url
        
        # Try just the base domain as last resort
        try:
            response = self.discovery.session.head(base_domain)
            if response.status_code == 200:
                logger.info(f"🏠 Using base domain for {restaurant_slug}: {base_domain}")
                return base_domain
        except:
            pass
        
        logger.warning(f"❌ No working URL found for {restaurant_slug}")
        return None
    
    def fix_restaurants_file(self, dry_run: bool = True) -> Dict[str, str]:
        """
        Fix broken URLs in the restaurants.json file.
        
        Args:
            dry_run: If True, only report fixes without applying them
            
        Returns:
            Dictionary of applied fixes {restaurant_slug: new_url}
        """
        fixes = {}
        
        # Load restaurant data
        with open('data/restaurants.json', 'r') as f:
            data = json.load(f)
        
        restaurants = data['restaurants']
        total_restaurants = len(restaurants)
        
        logger.info(f"🔧 Checking {total_restaurants} restaurants for URL issues...")
        
        for restaurant_slug, restaurant_data in restaurants.items():
            self.restaurants_checked += 1
            website = restaurant_data.get('website')
            
            if not website:
                logger.info(f"⚠️  {restaurant_slug}: No website URL")
                continue
            
            # Check and potentially fix the URL
            fixed_url = self.check_and_fix_url(restaurant_slug, website)
            
            if fixed_url and fixed_url != website:
                fixes[restaurant_slug] = fixed_url
                self.fixes_applied += 1
                
                if not dry_run:
                    # Apply the fix
                    restaurants[restaurant_slug]['website'] = fixed_url
                    logger.info(f"✅ FIXED {restaurant_slug}: {website} → {fixed_url}")
                else:
                    logger.info(f"🔄 WOULD FIX {restaurant_slug}: {website} → {fixed_url}")
        
        # Save updated data if not dry run
        if not dry_run and fixes:
            # Create backup first
            import shutil
            from datetime import datetime
            backup_name = f"data/backups/restaurants_pre_url_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            shutil.copy('data/restaurants.json', backup_name)
            logger.info(f"📁 Created backup: {backup_name}")
            
            # Save updated data
            with open('data/restaurants.json', 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("💾 Updated restaurants.json with fixed URLs")
        
        return fixes
    
    def report_results(self, fixes: Dict[str, str]):
        """Generate a summary report of URL fixes"""
        print("\n" + "="*60)
        print("🔧 RESTAURANT URL FIX SUMMARY")
        print("="*60)
        print(f"📊 Restaurants checked: {self.restaurants_checked}")
        print(f"🔄 Fixes applied: {self.fixes_applied}")
        print(f"✅ Success rate: {((self.restaurants_checked - self.fixes_applied) / self.restaurants_checked * 100):.1f}% working URLs")
        
        if fixes:
            print(f"\n🎯 FIXES APPLIED ({len(fixes)}):")
            for restaurant_slug, new_url in fixes.items():
                print(f"   • {restaurant_slug}: {new_url}")
        else:
            print("\n✅ No URL fixes needed - all URLs working!")
        
        print("="*60)


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix broken restaurant URLs")
    parser.add_argument('--apply', action='store_true', 
                       help='Apply fixes (default is dry-run)')
    parser.add_argument('--restaurant', type=str,
                       help='Fix specific restaurant only')
    
    args = parser.parse_args()
    
    fixer = RestaurantUrlFixer()
    
    if args.restaurant:
        # Fix specific restaurant
        with open('data/restaurants.json', 'r') as f:
            data = json.load(f)
        
        if args.restaurant in data['restaurants']:
            restaurant = data['restaurants'][args.restaurant]
            website = restaurant.get('website')
            fixed_url = fixer.check_and_fix_url(args.restaurant, website)
            
            if fixed_url and fixed_url != website:
                print(f"🔄 Suggested fix for {args.restaurant}: {website} → {fixed_url}")
                if args.apply:
                    restaurant['website'] = fixed_url
                    with open('data/restaurants.json', 'w') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print("✅ Fix applied!")
            else:
                print(f"✅ URL already working for {args.restaurant}")
        else:
            print(f"❌ Restaurant '{args.restaurant}' not found")
    
    else:
        # Fix all restaurants
        dry_run = not args.apply
        
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            print("Use --apply to actually fix the URLs")
        else:
            print("🔧 APPLYING FIXES - URLs will be updated")
        
        fixes = fixer.fix_restaurants_file(dry_run=dry_run)
        fixer.report_results(fixes)


if __name__ == "__main__":
    main()