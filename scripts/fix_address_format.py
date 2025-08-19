#!/usr/bin/env python3
"""
Address Format Fixer

Fixes the malformed address fields in restaurants.json where addresses
are stored as dictionary objects instead of clean formatted strings.
"""

import json
from datetime import datetime


def fix_address_format():
    """Fix address format issues in restaurants.json"""
    
    with open('data/restaurants.json', 'r') as f:
        data = json.load(f)
    
    fixed_count = 0
    
    print("🔧 FIXING ADDRESS FORMAT ISSUES")
    print("=" * 50)
    
    for slug, restaurant in data['restaurants'].items():
        address = restaurant.get('address')
        name = restaurant.get('name', slug)
        
        # Check if address is a dict (problematic format)
        if isinstance(address, dict):
            # Try to extract formatted address
            formatted = address.get('formatted_address')
            
            if formatted:
                # Use the pre-formatted address
                restaurant['address'] = formatted
                print(f"✅ Fixed {name}: \"{formatted}\"")
            else:
                # Construct address from components
                parts = []
                
                street_num = address.get('street_number')
                street_name = address.get('street_name')
                if street_num and street_name:
                    parts.append(f"{street_num} {street_name}")
                elif street_name:
                    parts.append(street_name)
                
                city = address.get('city')
                if city:
                    parts.append(city)
                
                state = address.get('state')
                if state:
                    parts.append(state)
                
                zip_code = address.get('zip_code')
                if zip_code:
                    parts.append(zip_code)
                
                if parts:
                    constructed_address = ', '.join(parts)
                    restaurant['address'] = constructed_address
                    print(f"🔨 Constructed {name}: \"{constructed_address}\"")
                else:
                    # Fallback to neighborhood + city
                    neighborhood = restaurant.get('neighborhood', '')
                    fallback = f"{neighborhood}, Denver, CO" if neighborhood else "Denver, CO"
                    restaurant['address'] = fallback
                    print(f"⚠️ Fallback {name}: \"{fallback}\"")
            
            fixed_count += 1
            restaurant['last_updated'] = datetime.now().isoformat()
        
        elif not address:
            # Handle completely missing addresses
            neighborhood = restaurant.get('neighborhood', '')
            fallback = f"{neighborhood}, Denver, CO" if neighborhood else "Denver, CO"
            restaurant['address'] = fallback
            print(f"➕ Added missing address for {name}: \"{fallback}\"")
            fixed_count += 1
            restaurant['last_updated'] = datetime.now().isoformat()
    
    # Save the fixed data
    with open('data/restaurants.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Fixed {fixed_count} address format issues")
    print("🎯 All addresses now in clean string format!")


if __name__ == "__main__":
    fix_address_format()