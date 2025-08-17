#!/usr/bin/env python3
"""
Enhanced contact information extractor for restaurant websites
Extracts phone numbers, emails, social media handles, operating hours, and service information
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Import models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from models import ContactInfo, DiningInfo, ServiceInfo, BusinessStatus, PriceRange

logger = logging.getLogger(__name__)


class ContactExtractor:
    """Extract comprehensive contact and business information from restaurant websites"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url
        
        # Phone number patterns (US and international)
        self.phone_patterns = [
            r'\((\d{3})\)\s*(\d{3})-(\d{4})',           # (303) 555-1234
            r'(\d{3})-(\d{3})-(\d{4})',                 # 303-555-1234
            r'(\d{3})\.(\d{3})\.(\d{4})',               # 303.555.1234
            r'(\d{3})\s+(\d{3})\s+(\d{4})',             # 303 555 1234
            r'\+1[-.\s]?(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})',  # +1 303 555 1234
            r'(?:phone|call|tel):\s*(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})',  # Phone: 303-555-1234
        ]
        
        # Email patterns
        self.email_patterns = [
            r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',  # General email
            r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # Mailto links
        ]
        
        # Social media patterns
        self.social_patterns = {
            'instagram': [
                r'instagram\.com/([a-zA-Z0-9_.]+)',
                r'@([a-zA-Z0-9_.]+)(?:\s|$)',  # @handle format
                r'ig:?\s*@?([a-zA-Z0-9_.]+)',  # IG: @handle
            ],
            'facebook': [
                r'facebook\.com/([a-zA-Z0-9_.]+)',
                r'fb\.com/([a-zA-Z0-9_.]+)',
            ],
            'twitter': [
                r'twitter\.com/([a-zA-Z0-9_.]+)',
                r'x\.com/([a-zA-Z0-9_.]+)',
            ],
            'tiktok': [
                r'tiktok\.com/@([a-zA-Z0-9_.]+)',
                r'tik\.tok/([a-zA-Z0-9_.]+)',
            ]
        }
        
        # Operating hours patterns
        self.hours_patterns = [
            # "Monday - Friday: 11:00 AM - 10:00 PM"
            r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*-\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday):\s*(\d{1,2}:\d{2}\s*[ap]m)\s*-\s*(\d{1,2}:\d{2}\s*[ap]m)',
            # "Monday: 11:00 AM - 10:00 PM"
            r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday):\s*(\d{1,2}:\d{2}\s*[ap]m)\s*-\s*(\d{1,2}:\d{2}\s*[ap]m)',
            # "Mon-Fri 11am-10pm"
            r'(mon|tue|wed|thu|fri|sat|sun)\s*-\s*(mon|tue|wed|thu|fri|sat|sun)\s+(\d{1,2}(?::\d{2})?\s*[ap]m)\s*-\s*(\d{1,2}(?::\d{2})?\s*[ap]m)',
            # "Hours: 11:00 AM - 10:00 PM"
            r'hours?:\s*(\d{1,2}:\d{2}\s*[ap]m)\s*-\s*(\d{1,2}:\d{2}\s*[ap]m)',
        ]
        
        # Service URL patterns
        self.service_patterns = {
            'opentable': [r'opentable\.com/([^?\s]+)', r'ot\.com/([^?\s]+)'],
            'resy': [r'resy\.com/([^?\s]+)'],
            'doordash': [r'doordash\.com/([^?\s]+)'],
            'ubereats': [r'ubereats\.com/([^?\s]+)', r'uber\.com/([^?\s]+)'],
            'grubhub': [r'grubhub\.com/([^?\s]+)'],
            'tock': [r'exploretock\.com/([^?\s]+)'],
        }
    
    def extract_contact_info(self, soup: BeautifulSoup, text_content: str = None) -> ContactInfo:
        """Extract contact information from parsed HTML"""
        if text_content is None:
            text_content = soup.get_text()
        
        contact = ContactInfo()
        
        # Extract phone numbers
        phones = self._extract_phones(text_content)
        if phones:
            contact.primary_phone = phones[0]  # Use first phone as primary
            if len(phones) > 1:
                contact.reservation_phone = phones[1]  # Second phone for reservations
        
        # Extract emails
        emails = self._extract_emails(text_content, soup)
        if emails:
            # Categorize emails by type
            for email in emails:
                email_lower = email.lower()
                if any(keyword in email_lower for keyword in ['reservation', 'booking', 'table']):
                    contact.reservations_email = email
                elif any(keyword in email_lower for keyword in ['event', 'private', 'party']):
                    contact.events_email = email
                elif not contact.general_email:  # Use first email as general if no specific type found
                    contact.general_email = email
        
        # Extract social media handles
        social_handles = self._extract_social_media(text_content, soup)
        contact.instagram = social_handles.get('instagram')
        contact.facebook = social_handles.get('facebook')
        contact.twitter = social_handles.get('twitter')
        contact.tiktok = social_handles.get('tiktok')
        
        return contact
    
    def extract_service_info(self, soup: BeautifulSoup, text_content: str = None) -> ServiceInfo:
        """Extract service and booking information"""
        if text_content is None:
            text_content = soup.get_text()
        
        service = ServiceInfo()
        
        # Find service URLs in links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            
            # Check for reservation platforms
            if any(pattern in href for pattern in ['opentable', 'ot.com']):
                service.accepts_reservations = True
                service.opentable_url = link.get('href')
            elif 'resy.com' in href:
                service.accepts_reservations = True
                service.resy_url = link.get('href')
            elif any(pattern in href for pattern in ['tock', 'exploretock']):
                service.accepts_reservations = True
                service.direct_reservation_url = link.get('href')
            
            # Check for delivery platforms
            elif 'doordash' in href:
                service.offers_delivery = True
                service.doordash_url = link.get('href')
            elif any(pattern in href for pattern in ['ubereats', 'uber.com']):
                service.offers_delivery = True
                service.ubereats_url = link.get('href')
            elif 'grubhub' in href:
                service.offers_delivery = True
                service.grubhub_url = link.get('href')
        
        # Look for reservation keywords in text
        text_lower = text_content.lower()
        if any(keyword in text_lower for keyword in ['reservation', 'book a table', 'make a reservation']):
            service.accepts_reservations = True
        
        # Look for delivery/takeout keywords
        if any(keyword in text_lower for keyword in ['delivery', 'door dash', 'uber eats']):
            service.offers_delivery = True
        if any(keyword in text_lower for keyword in ['takeout', 'take out', 'to-go', 'pickup']):
            service.offers_takeout = True
        if any(keyword in text_lower for keyword in ['curbside', 'curb side']):
            service.offers_curbside = True
        
        return service
    
    def extract_operating_hours(self, soup: BeautifulSoup, text_content: str = None) -> Dict[str, Dict[str, str]]:
        """Extract operating hours from content"""
        if text_content is None:
            text_content = soup.get_text()
        
        hours = {}
        
        # Look for structured hours in common containers
        hours_containers = soup.find_all(['div', 'section', 'table'], 
                                       class_=lambda x: x and any(keyword in x.lower() for keyword in ['hour', 'time', 'schedule']))
        
        for container in hours_containers:
            container_text = container.get_text()
            extracted = self._parse_hours_text(container_text)
            hours.update(extracted)
        
        # Fallback to full text parsing if no structured hours found
        if not hours:
            hours = self._parse_hours_text(text_content)
        
        return hours
    
    def extract_dining_info(self, soup: BeautifulSoup, text_content: str = None) -> DiningInfo:
        """Extract dining experience information"""
        if text_content is None:
            text_content = soup.get_text()
        
        dining = DiningInfo()
        text_lower = text_content.lower()
        
        # Detect price range from content
        if any(indicator in text_lower for indicator in ['$$$', 'fine dining', 'upscale', 'michelin']):
            dining.price_range = PriceRange.FINE_DINING
        elif any(indicator in text_lower for indicator in ['$$', 'moderate', 'mid-range']):
            dining.price_range = PriceRange.UPSCALE
        elif any(indicator in text_lower for indicator in ['$', 'casual', 'affordable', 'budget']):
            dining.price_range = PriceRange.MODERATE
        
        # Detect atmosphere keywords
        atmosphere_keywords = {
            'romantic': ['romantic', 'intimate', 'date night', 'candlelit'],
            'family_friendly': ['family', 'kids', 'children', 'family-friendly'],
            'business': ['business', 'corporate', 'meeting', 'professional'],
            'casual': ['casual', 'relaxed', 'laid-back', 'informal'],
            'upscale': ['upscale', 'elegant', 'sophisticated', 'refined'],
            'lively': ['lively', 'energetic', 'vibrant', 'bustling'],
            'quiet': ['quiet', 'peaceful', 'tranquil', 'serene']
        }
        
        for atmosphere, keywords in atmosphere_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                dining.atmosphere.append(atmosphere)
        
        # Detect dining style
        if any(keyword in text_lower for keyword in ['fast casual', 'counter service', 'quick service']):
            dining.dining_style = 'fast_casual'
        elif any(keyword in text_lower for keyword in ['food truck', 'truck', 'mobile']):
            dining.dining_style = 'food_truck'
        elif any(keyword in text_lower for keyword in ['bar', 'tavern', 'pub', 'brewery']):
            dining.dining_style = 'bar'
        else:
            dining.dining_style = 'full_service'
        
        # Extract capacity information from text
        capacity_patterns = [
            r'(\d+)\s*seats?',
            r'capacity:?\s*(\d+)',
            r'accommodates?\s*(\d+)',
        ]
        
        for pattern in capacity_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                dining.total_seats = int(matches[0])
                break
        
        return dining
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        phones = []
        
        for pattern in self.phone_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Combine parts into full phone number
                    if len(match) == 3:
                        phone = f"{match[0]}-{match[1]}-{match[2]}"
                    else:
                        phone = ''.join(match)
                else:
                    phone = match
                
                # Validate phone number (must be 10 digits when cleaned)
                clean_phone = re.sub(r'[^\d]', '', phone)
                if len(clean_phone) == 10:
                    formatted_phone = f"{clean_phone[:3]}-{clean_phone[3:6]}-{clean_phone[6:]}"
                    if formatted_phone not in phones:
                        phones.append(formatted_phone)
        
        return phones[:2]  # Return max 2 phone numbers
    
    def _extract_emails(self, text: str, soup: BeautifulSoup) -> List[str]:
        """Extract email addresses from text and mailto links"""
        emails = set()
        
        # Extract from text patterns
        for pattern in self.email_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    emails.add(match[0])
                else:
                    emails.add(match)
        
        # Extract from mailto links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').split('?')[0]  # Remove query params
                emails.add(email)
        
        # Filter out invalid or generic emails
        valid_emails = []
        for email in emails:
            if self._is_valid_email(email):
                valid_emails.append(email)
        
        return valid_emails[:3]  # Return max 3 emails
    
    def _extract_social_media(self, text: str, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract social media handles"""
        social_handles = {}
        
        # Extract from links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            
            for platform, patterns in self.social_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, href, re.IGNORECASE)
                    if match and platform not in social_handles:
                        handle = match.group(1)
                        # Clean up handle
                        handle = handle.rstrip('/')
                        social_handles[platform] = handle
                        break
        
        # Extract from text patterns (for @mentions)
        instagram_mentions = re.findall(r'@([a-zA-Z0-9_.]+)', text)
        if instagram_mentions and 'instagram' not in social_handles:
            # Use first mention that looks like a restaurant handle
            for mention in instagram_mentions:
                if len(mention) > 3 and not mention.isdigit():
                    social_handles['instagram'] = mention
                    break
        
        return social_handles
    
    def _parse_hours_text(self, text: str) -> Dict[str, Dict[str, str]]:
        """Parse operating hours from text"""
        hours = {}
        text_lower = text.lower()
        
        # Define day mappings
        day_mappings = {
            'monday': 'monday', 'mon': 'monday',
            'tuesday': 'tuesday', 'tue': 'tuesday', 'tues': 'tuesday',
            'wednesday': 'wednesday', 'wed': 'wednesday',
            'thursday': 'thursday', 'thu': 'thursday', 'thurs': 'thursday',
            'friday': 'friday', 'fri': 'friday',
            'saturday': 'saturday', 'sat': 'saturday',
            'sunday': 'sunday', 'sun': 'sunday'
        }
        
        for pattern in self.hours_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if len(match) == 4:  # Day range pattern
                    start_day, end_day, open_time, close_time = match
                    
                    # Handle day ranges
                    start_day = day_mappings.get(start_day.lower())
                    end_day = day_mappings.get(end_day.lower())
                    
                    if start_day and end_day:
                        # Get day range
                        day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                        start_idx = day_order.index(start_day)
                        end_idx = day_order.index(end_day)
                        
                        # Handle ranges that might wrap (like Fri-Mon)
                        if start_idx <= end_idx:
                            days_in_range = day_order[start_idx:end_idx + 1]
                        else:
                            days_in_range = day_order[start_idx:] + day_order[:end_idx + 1]
                        
                        for day in days_in_range:
                            hours[day] = {
                                'open': self._normalize_time(open_time),
                                'close': self._normalize_time(close_time),
                                'closed': False
                            }
                
                elif len(match) == 3:  # Single day pattern
                    day, open_time, close_time = match
                    day = day_mappings.get(day.lower())
                    
                    if day:
                        hours[day] = {
                            'open': self._normalize_time(open_time),
                            'close': self._normalize_time(close_time),
                            'closed': False
                        }
        
        # Look for closed days
        closed_patterns = [
            r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday):\s*closed',
            r'closed\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        ]
        
        for pattern in closed_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                day = day_mappings.get(match.lower())
                if day:
                    hours[day] = {'closed': True}
        
        return hours
    
    def _normalize_time(self, time_str: str) -> str:
        """Normalize time string to HH:MM format"""
        if not time_str:
            return None
        
        time_str = time_str.strip()
        
        # Handle "11am" -> "11:00"
        if re.match(r'^\d{1,2}[ap]m$', time_str, re.IGNORECASE):
            hour = int(time_str[:-2])
            ampm = time_str[-2:].upper()
            
            if ampm == 'PM' and hour != 12:
                hour += 12
            elif ampm == 'AM' and hour == 12:
                hour = 0
            
            return f"{hour:02d}:00"
        
        # Handle "11:30am" -> "11:30"
        time_match = re.match(r'^(\d{1,2}):(\d{2})\s*([ap]m)?$', time_str, re.IGNORECASE)
        if time_match:
            hour, minute, ampm = time_match.groups()
            hour = int(hour)
            minute = int(minute)
            
            if ampm:
                ampm = ampm.upper()
                if ampm == 'PM' and hour != 12:
                    hour += 12
                elif ampm == 'AM' and hour == 12:
                    hour = 0
            
            return f"{hour:02d}:{minute:02d}"
        
        return time_str
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email address"""
        # Basic email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return False
        
        # Filter out common non-business emails
        excluded_domains = ['example.com', 'test.com', 'domain.com', 'email.com']
        domain = email.split('@')[1].lower()
        
        return domain not in excluded_domains