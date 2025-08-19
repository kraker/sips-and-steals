#!/usr/bin/env python3
"""
Restaurant URL Fixer

Validates and fixes broken restaurant URLs by testing accessibility
and suggesting common URL patterns when sites are unreachable.
"""

import json
import logging
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RestaurantUrlFixer:
    """Fixes broken restaurant URLs by testing accessibility"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.fixes_applied = 0
        self.restaurants_checked = 0
        
        # Common URL patterns to try when main URL fails
        self.url_patterns = [
            '',  # Original URL
            '/menu',
            '/specials',
            '/happy-hour',
            '/deals',
            '/events'
        ]
    
    def test_url(self, url: str, timeout: int = 10) -> bool:
        """Test if a URL is accessible"""
        try:
            response = self.session.head(url, timeout=timeout, allow_redirects=True)
            return response.status_code == 200
        except Exception:
            return False
    
    def check_and_fix_url(self, restaurant_slug: str, website: str) -> Optional[str]:
        """
        Check if a restaurant URL works, and if not, try common patterns.
        
        Args:
            restaurant_slug: Restaurant identifier
            website: Current website URL
            
        Returns:
            Fixed URL if found, original URL if working, None if no fix available
        """
        if not website:
            return None
        
        logger.info(f"Checking URL for {restaurant_slug}: {website}")
        
        # Test current URL
        if self.test_url(website):
            logger.info(f"✅ {restaurant_slug}: Current URL works")
            return website
        
        logger.warning(f"❌ {restaurant_slug}: Current URL failed")
        
        # URL is broken, try alternatives
        parsed = urlparse(website)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        
        logger.info(f"🔍 Trying alternatives for {restaurant_slug} from {base_domain}")
        
        # Try common URL patterns
        for pattern in self.url_patterns[1:]:  # Skip empty pattern (already tested)
            test_url = urljoin(base_domain, pattern)
            if self.test_url(test_url):
                logger.info(f"🎯 Found working URL for {restaurant_slug}: {test_url}")
                return test_url
            time.sleep(0.5)  # Be respectful
        
        # Try just the base domain as last resort
        if self.test_url(base_domain):
            logger.info(f"🏠 Using base domain for {restaurant_slug}: {base_domain}")
            return base_domain
        
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