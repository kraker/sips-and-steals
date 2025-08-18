"""
Scrapy settings for Sips and Steals project

Optimized for respectful, efficient restaurant website crawling
with focus on discovery and content extraction.
"""

# Basic project settings
BOT_NAME = 'src'
SPIDER_MODULES = ['src.spiders']
NEWSPIDER_MODULE = 'src.spiders'

# Respectful crawling - be a good web citizen
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 2  # 2 seconds between requests
RANDOMIZE_DOWNLOAD_DELAY = 0.5  # 0.5 * to 1.5 * DOWNLOAD_DELAY
CONCURRENT_REQUESTS = 8  # Conservative concurrency
CONCURRENT_REQUESTS_PER_DOMAIN = 2  # Max 2 requests per domain simultaneously

# Auto-throttling for adaptive delays
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False  # Enable to see throttling stats

# User agent - identify ourselves properly
USER_AGENT = 'src (+https://sips-and-steals.com)'

# Request/Response handling
DOWNLOAD_TIMEOUT = 15  # 15 second timeout for faster testing
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Duplicate filtering
DUPEFILTER_DEBUG = False
DUPEFILTER_CLASS = 'scrapy.dupefilters.RFPDupeFilter'

# Enable useful extensions
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,  # Disable telnet
    'scrapy.extensions.logstats.LogStats': 500,  # Log stats every 500 items
}

# Configure pipelines
ITEM_PIPELINES = {
    'src.pipelines.DealValidationPipeline': 100,
    'src.pipelines.RestaurantProfilePipeline': 150,  # Process restaurant profiles
    'src.pipelines.MenuPricingPipeline': 175,  # Process menu pricing data
    'src.pipelines.HappyHourDealsPipeline': 180,  # Process happy hour deals
    'src.pipelines.SemanticAnalysisPipeline': 200,
    'src.pipelines.JSONExportPipeline': 300,
}

# Configure middlewares
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': 100,
    'scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware': 110,
    'scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware': 350,
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': 400,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 500,
    'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': 550,
    'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware': 580,
    'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
    'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 700,
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 750,
    'scrapy.downloadermiddlewares.stats.DownloaderStats': 850,
    'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': 900,
}

# Default request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
}

# HTTP caching for development (disable in production)
HTTPCACHE_ENABLED = False  # Set to True for development
HTTPCACHE_EXPIRATION_SECS = 3600  # 1 hour cache
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = [503, 504, 505, 500, 403, 404, 408, 429]

# Logging configuration
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/scrapy.log'

# Custom settings for our use case
RESTAURANT_DATA_FILE = 'data/restaurants.json'
DEALS_OUTPUT_FILE = 'data/deals.json'
DISCOVERY_OUTPUT_FILE = 'data/discovered_pages.json'

# Happy hour detection settings
HAPPY_HOUR_KEYWORDS = [
    'happy hour', 'happy-hour', 'happyhour',
    'specials', 'daily specials', 'drink specials',
    'deals', 'daily deals', 'food deals',
    'après', 'apres', 'after work',
    'early bird', 'late night',
    'weekday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday'
]

# Discovery settings
MAX_CRAWL_DEPTH = 3  # How deep to crawl from restaurant homepage
DISCOVERY_FOLLOW_PATTERNS = [
    r'.*happy.*hour.*',
    r'.*specials.*',
    r'.*deals.*',
    r'.*menu.*',
    r'.*drink.*',
    r'.*food.*',
    r'.*après.*',
    r'.*apres.*',
]

# Export settings
FEED_EXPORT_ENCODING = 'utf-8'
FEED_EXPORT_FIELDS = [
    'title', 'description', 'start_time', 'end_time', 'days_of_week',
    'confidence_score', 'restaurant_slug', 'source_url', 'scraped_at'
]

# Memory usage optimization
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 512  # Limit memory usage to 512MB
MEMUSAGE_WARNING_MB = 400  # Warn at 400MB

# Stats collection
STATS_CLASS = 'scrapy.statscollectors.MemoryStatsCollector'