# Scraper Configuration System

This directory contains YAML-based configuration files that enable rapid restaurant onboarding without writing custom Python code. The config-based approach allows pattern-driven scraping of restaurant websites for happy hour deals.

## Quick Start

Create a new restaurant scraper in 3 steps:
1. Add restaurant to `data/restaurants.json`
2. Create config file: `config/scrapers/restaurant-slug.yaml`
3. Test: `python scraper_cli.py scrape --restaurant "restaurant-slug"`

## Configuration Schema

### Basic Structure
```yaml
restaurant_name: "Restaurant Name"
scraper_type: "config_based"
enabled: true
urls:
  - "https://restaurant.com/happy-hour"
  - "https://restaurant.com/specials"  # Multiple URLs supported

scraping_patterns:
  time_patterns:    # Extract start/end times
  day_patterns:     # Extract days of week  
  deal_patterns:    # Extract prices and items

post_processing:    # Optional deal consolidation
confidence_threshold: 0.7
retry_attempts: 3
delay_between_requests: 1
```

### Pattern Types

#### Time Patterns
Extract start and end times from text:
```yaml
time_patterns:
  - pattern: "Monday - Friday: (\\d{1,2}[ap]m) - (\\d{1,2}[ap]m)"
    groups: [start_time, end_time]
    confidence: 0.9
  - pattern: "Open - (\\d{1,2}[ap]m)"
    groups: [end_time]
    confidence: 0.8
```

**Common Time Formats:**
- `"3pm - 6pm"` → `"(\\d{1,2}[ap]m) - (\\d{1,2}[ap]m)"`
- `"3:00 PM - 6:00 PM"` → `"(\\d{1,2}:\\d{2} [AP]M) - (\\d{1,2}:\\d{2} [AP]M)"`
- `"Open until 6pm"` → `"Open until (\\d{1,2}[ap]m)"`

#### Day Patterns
Extract days of week (must use capture groups):
```yaml
day_patterns:
  - pattern: "(Monday - Friday)"
    groups: [days]
    confidence: 0.9
  - pattern: "(Daily)"
    groups: [days]
    confidence: 0.8
```

**Important**: Patterns must include parentheses for capture groups even for simple matches.

#### Deal Patterns
Extract pricing and item information:
```yaml
deal_patterns:
  - pattern: "\\$(\\d+) ([A-Z][^\\$\\n]{2,})"
    groups: [price, item_name]
    confidence: 0.8
  - pattern: "(\\d+)% off"
    groups: [discount]
    confidence: 0.7
```

### Advanced Configuration

#### Content Targeting
Focus scraping on specific page sections:
```yaml
scraping_config:
  custom_selectors:
    happy_hour: ".happy-hour-section"
    specials: "#weekly-specials"
  
  content_containers:
    - ".menu-section"
    - "#deals-container"
  
  exclude_patterns:
    - "catering"
    - "private events"
```

#### Deal Consolidation
Combine multiple extracted deals into organized groups:
```yaml
post_processing:
  deal_consolidation:
    - title: "Weekday Happy Hour"
      description: "Monday-Friday 3pm-6pm specials"
      combine_similar: true
    - title: "Weekend Specials"
      description: "Saturday-Sunday deals"
      combine_similar: false
```

## Working Examples

### Simple Restaurant (American Elm)
```yaml
restaurant_name: "American Elm"
scraper_type: "config_based"
enabled: true
urls:
  - "https://www.amelm.com/happyhour"

scraping_patterns:
  time_patterns:
    - pattern: "Monday - Friday: Open - (\\d{1,2}[ap]m)"
      groups: [end_time]
      confidence: 0.9
  
  day_patterns:
    - pattern: "(Monday - Friday)"
      groups: [days]
      confidence: 0.9
  
  deal_patterns:
    - pattern: "(\\d+)\\s+Old Fashioned"
      groups: [price]
      confidence: 0.8
```

### Complex Restaurant (Wild Taco)
```yaml
restaurant_name: "Wild Taco"
scraper_type: "config_based"
enabled: true
urls:
  - "https://wildtacodenver.com/denver-govs-park-wild-taco-denver-menu-berkeley"

scraping_patterns:
  time_patterns:
    - pattern: "All Day Monday \\| Tuesday - Friday (\\d{1,2}[ap]m) - (\\d{1,2}[ap]m)"
      groups: [start_time, end_time]
      confidence: 0.9
  
  day_patterns:
    - pattern: "All Day Monday"
      groups: [days]
      confidence: 0.9
    - pattern: "Tuesday - Friday"
      groups: [days]
      confidence: 0.9
  
  deal_patterns:
    - pattern: "\\$(\\d+)(?:\\.\\d{2})? ([A-Z][^\\$\\n]{2,})"
      groups: [price, item_name]
      confidence: 0.8

post_processing:
  deal_consolidation:
    - title: "Happy Hour Specials"
      description: "Monday all day, Tuesday-Friday 3pm-6pm"
      combine_similar: true
```

## Pattern Development Tips

### 1. **Test Patterns Incrementally**
Start with simple patterns and build complexity:
```bash
# Test just one restaurant
python scraper_cli.py scrape --restaurant "restaurant-slug"

# Check extracted deals
grep -A 10 "restaurant-slug" data/deals.json
```

### 2. **Use Confidence Scores**
- `0.9+`: Highly specific patterns (exact text matches)
- `0.8`: Good patterns with minor variations
- `0.7`: Broader patterns that might catch false positives
- Below 0.7: Usually filtered out

### 3. **Handle Edge Cases**
```yaml
# Multiple time formats
time_patterns:
  - pattern: "(\\d{1,2}[ap]m) - (\\d{1,2}[ap]m)"
    groups: [start_time, end_time]
    confidence: 0.9
  - pattern: "(\\d{1,2}:\\d{2}[ap]m) - (\\d{1,2}:\\d{2}[ap]m)"
    groups: [start_time, end_time]
    confidence: 0.9
```

### 4. **Debug with Verbose Output**
```bash
python scraper_cli.py --verbose scrape --restaurant "restaurant-slug"
```

## Common Patterns Library

### Days of Week
```yaml
# Monday through Friday
- pattern: "(Monday - Friday|Mon - Fri|Weekdays)"
  groups: [days]

# All week
- pattern: "(Daily|Every Day|7 Days)"
  groups: [days]

# Weekends
- pattern: "(Saturday - Sunday|Weekends)"
  groups: [days]
```

### Time Formats
```yaml
# 12-hour format
- pattern: "(\\d{1,2}[ap]m) - (\\d{1,2}[ap]m)"
  groups: [start_time, end_time]

# With minutes
- pattern: "(\\d{1,2}:\\d{2}[ap]m) - (\\d{1,2}:\\d{2}[ap]m)"
  groups: [start_time, end_time]

# Open until
- pattern: "until (\\d{1,2}[ap]m)"
  groups: [end_time]
```

### Price Formats
```yaml
# Simple dollar amounts
- pattern: "\\$(\\d+)"
  groups: [price]

# With items
- pattern: "\\$(\\d+) ([A-Z][^\\$\\n]+)"
  groups: [price, item_name]

# Percentages
- pattern: "(\\d+)% off"
  groups: [discount]
```

## Troubleshooting

### No Deals Extracted
1. Check if patterns match actual website content
2. Verify capture groups use parentheses
3. Test patterns individually
4. Check confidence threshold

### Invalid Deals
1. Review day pattern extraction - deals need valid days
2. Check time format parsing
3. Verify deal validation in logs

### Performance Issues
1. Reduce `retry_attempts` for slow sites
2. Increase `delay_between_requests` for rate limiting
3. Use `custom_selectors` to target specific content areas

## Next Steps

1. **Create config**: Copy an existing config and modify patterns
2. **Test locally**: Verify deal extraction with CLI
3. **Monitor quality**: Check confidence scores and validation
4. **Iterate**: Refine patterns based on results

For advanced scraping needs, consider creating a custom scraper in `src/scrapers/restaurant_scrapers/`.