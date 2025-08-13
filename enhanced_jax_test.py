#!/usr/bin/env python3
"""
Test script to find the weekly specials JSON data
"""

import requests
from bs4 import BeautifulSoup
import json

def find_weekly_specials():
    url = "https://www.jaxfishhouse.com/location/jax-fish-house-oyster-bar-lodo/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("=== SEARCHING FOR MENU JSON-LD DATA ===")
        
        # Look for JSON-LD structured data
        scripts = soup.find_all('script', type='application/ld+json')
        print(f"Found {len(scripts)} JSON-LD scripts")
        
        for i, script in enumerate(scripts):
            try:
                data = json.loads(script.string)
                
                if data.get('@type') == 'Menu':
                    menu_name = data.get('name', 'Unknown')
                    print(f"\n📋 Menu {i+1}: {menu_name}")
                    
                    # Look for weekly specials section
                    sections = data.get('hasMenuSection', [])
                    for section in sections:
                        if isinstance(section, dict):
                            section_name = section.get('name', '')
                            print(f"  Section: {section_name}")
                            
                            if 'weekly' in section_name.lower() or 'special' in section_name.lower():
                                print(f"  🎯 FOUND WEEKLY SPECIALS SECTION!")
                                
                                # Get all menu items in this section
                                items = section.get('hasMenuItem', [])
                                if isinstance(items, list):
                                    for item in items:
                                        if isinstance(item, dict):
                                            name = item.get('name', '')
                                            desc = item.get('description', '')
                                            offers = item.get('offers', {})
                                            
                                            print(f"    🍽️ {name}")
                                            if desc:
                                                print(f"       {desc}")
                                            if isinstance(offers, dict) and 'price' in offers:
                                                print(f"       💰 ${offers['price']}")
                                            print()
                
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_weekly_specials()