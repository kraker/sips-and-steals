# JavaScript Support Research for Future Implementation

## Problem Statement
City O' City (and other Squarespace sites) use heavy JavaScript content loading, making BeautifulSoup insufficient for parsing dynamic content. Our current scraper gets fragmented text like "happy hour food\n\n\n\nfried ravioli**" because it only sees the initial HTML served by the server.

## Root Cause Analysis
- **Squarespace Architecture**: Dynamic content loading with extensive JavaScript frameworks
- **BeautifulSoup Limitation**: Only parses initial server-rendered HTML, misses JS-populated content
- **Content Structure**: Menu items loaded via JavaScript after page load, not present in static HTML

## Research Findings (August 2025)

### Lightweight JavaScript Execution Options

#### Option 1: DrissionPage (Recommended for Scraping)
- **Weight**: ~200MB (Chrome binary)
- **Setup**: `pip install DrissionPage`
- **Pros**:
  - Hybrid HTTP/Browser mode switching
  - Designed specifically for scraping scenarios
  - Undetectable by most anti-bot systems
  - Familiar requests-like API
- **Cons**: Less mature ecosystem
- **Best for**: Prototype simplicity

#### Option 2: Playwright (Most Robust)
- **Weight**: ~200MB (browser binary)
- **Setup**: `pip install playwright` + `playwright install chromium`
- **Pros**:
  - Fastest execution (290ms vs Selenium's 536ms)
  - Microsoft-backed, actively maintained
  - Excellent stealth capabilities
  - Multiple browser support
- **Cons**: More complex setup
- **Best for**: Production long-term

#### Option 3: Pyppeteer (Familiar API)
- **Weight**: ~200MB (Chrome binary)
- **Setup**: `pip install pyppeteer`
- **Pros**:
  - Most similar to deprecated requests-html
  - Direct Chrome DevTools Protocol
  - Fastest for short scripts (30% faster than Playwright)
- **Cons**: 
  - Chrome/Chromium only
  - Unofficial Python port (maintenance concerns)
- **Best for**: requests-html migration

#### Option 4: Selenium (Traditional)
- **Weight**: ~250MB+
- **Setup**: Most complex (WebDriver management)
- **Pros**: Mature ecosystem, widely known
- **Cons**: Slowest performance, heaviest setup
- **Best for**: Not recommended for our use case

### Key Insights
- **All JS-capable options require browser binary (~200MB)** - there's no truly "lightweight" solution
- **Performance differences are in runtime**, not download size
- **requests-html is deprecated/archived** as of 2025
- **Hybrid approach possible**: Use BeautifulSoup for 90% of sites, JS execution for edge cases

## Recommended Implementation Strategy (Future)

### Phase 1: Detection & Fallback
```python
# Add to restaurant config
requires_javascript: true  # For known JS-heavy sites like City O' City

# Auto-detection fallback
if scraping_fails_or_fragmented_content():
    fallback_to_javascript_execution()
```

### Phase 2: Hybrid Integration
- Keep BeautifulSoup for fast static content (most restaurants)
- Add JavaScript execution only when needed
- Maintain performance for existing restaurants

### Phase 3: Site-Specific Optimization
- Configure wait conditions for Squarespace sites
- Add selectors for dynamic content containers
- Implement proper error handling and timeouts

## Current City O' City Status
- **Website**: https://www.cityocitydenver.com/happyhour
- **Issue**: Squarespace dynamic content loading
- **Current Output**: Fragmented descriptions with excessive whitespace
- **Needed**: JavaScript execution to wait for menu content to load
- **Expected Result**: Clean descriptions with "EVERY DAY 3-6PM & 9-10pm", drink specials ($3 well spirits, $7 City Mule), food items (Fried ravioli $8, Pretzel $8, etc.)

## Files Modified During Research
- `/config/scrapers/city-o-city.yaml` - Custom scraping config with exclude patterns
- `/src/scrapers/base.py` - Enhanced description cleaning logic
- This was sufficient to improve descriptions slightly but didn't solve the core JS issue

## Next Steps (When Ready)
1. Choose between DrissionPage (simplicity) or Playwright (robustness)
2. Add `requires_javascript` config flag to restaurant schema
3. Implement hybrid scraper with automatic fallback detection
4. Test with City O' City and other problematic sites
5. Monitor performance impact and resource usage

## Cost-Benefit Analysis
- **Cost**: ~200MB download, added complexity, slower execution for JS sites
- **Benefit**: Access to 10-15% of restaurants that are currently unscrappable
- **Decision**: Prototype can continue with current limitations; implement when needed for production

---
*Research conducted August 16, 2025*
*Status: Documented for future implementation*