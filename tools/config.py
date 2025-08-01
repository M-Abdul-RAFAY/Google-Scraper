# Configuration file for the Google Business Scraper

# Default scraper settings
DEFAULT_HEADLESS = False
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_RESULTS = 20

# Browser settings
USER_AGENT_ROTATION = True
DISABLE_IMAGES = True
DISABLE_JAVASCRIPT = False

# Rate limiting settings
DEFAULT_DELAY_BETWEEN_REQUESTS = 2  # seconds
SCROLL_DELAY = 2  # seconds
PAGE_LOAD_DELAY = 3  # seconds

# Output settings
DEFAULT_CSV_FILENAME = "google_businesses_{timestamp}.csv"
DEFAULT_JSON_FILENAME = "google_businesses_{timestamp}.json"

# Logging settings
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = True
LOG_FILENAME = "scraper.log"

# Search settings
MAX_SCROLLS_DEFAULT = 10
RESULTS_PER_SCROLL = 5

# Data extraction settings
MAX_IMAGES_PER_BUSINESS = 5
EXTRACT_REVIEWS = False  # Set to True to extract review text (slower)
EXTRACT_POPULAR_TIMES = False  # Set to True to extract popular times data

# Selectors (can be updated if Google changes their HTML structure)
SELECTORS = {
    'search_results': '[data-value="Search results"]',
    'business_name': 'h1',
    'rating': '[data-value="Rating"]',
    'reviews_count': '[data-value="Reviews"]',
    'address': '[data-item-id="address"]',
    'phone': '[data-item-id="phone"]',
    'website': '[data-item-id="authority"]',
    'hours': '[aria-label*="hours"]',
    'category': '[data-value="Category"]'
}
