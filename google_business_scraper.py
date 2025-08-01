import os
import time
import re
import json
import csv
import logging
from typing import List, Dict, Optional
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from selenium.webdriver.common.action_chains import ActionChains


class GoogleBusinessScraper:
    """
    A comprehensive Google Business Listing Scraper that extracts business information
    directly from Google Maps search results page without opening individual listings.
    """
    
    def __init__(self, headless: bool = False, timeout: int = 15):
        """
        Initialize the scraper with Chrome WebDriver settings.
        
        Args:
            headless (bool): Run browser in headless mode
            timeout (int): Default timeout for WebDriver waits
        """
        self.timeout = timeout
        self.ua = UserAgent()
        
        # Setup logging with UTF-8 encoding to handle special characters
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup driver
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, timeout)
        self.actions = ActionChains(self.driver)
    
    def _setup_driver(self, headless: bool) -> webdriver.Chrome:
        """Setup Chrome WebDriver with optimized options."""
        options = Options()
        
        if headless:
            options.add_argument('--headless')
        
        # Chrome options for better performance and stealth
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(f'--user-agent={self.ua.random}')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--remote-debugging-port=9222')
        
        # Setup ChromeDriver with better error handling
        try:
            self.logger.info("Setting up ChromeDriver...")
            
            # Try multiple approaches to get ChromeDriver
            driver_path = None
            
            # Approach 1: Try WebDriver Manager
            try:
                chrome_driver_manager = ChromeDriverManager()
                driver_path = chrome_driver_manager.install()
                
                # Check if the downloaded file is actually chromedriver.exe
                if not driver_path.endswith('.exe'):
                    # Look for chromedriver.exe in the same directory
                    import glob
                    driver_dir = os.path.dirname(driver_path)
                    chromedriver_files = glob.glob(os.path.join(driver_dir, '**/chromedriver.exe'), recursive=True)
                    if chromedriver_files:
                        driver_path = chromedriver_files[0]
                    else:
                        driver_path = None
                        
                if driver_path and os.path.exists(driver_path):
                    self.logger.info(f"ChromeDriver found at: {driver_path}")
                else:
                    driver_path = None
                    
            except Exception as e1:
                self.logger.warning(f"WebDriver Manager failed: {str(e1)}")
                driver_path = None
            
            # Approach 2: Try to find system ChromeDriver
            if not driver_path:
                self.logger.info("Trying to find system ChromeDriver...")
                possible_paths = [
                    r"C:\chromedriver.exe",
                    r"C:\Windows\chromedriver.exe", 
                    r"C:\Program Files\chromedriver.exe",
                    os.path.join(os.getcwd(), "chromedriver.exe")
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        driver_path = path
                        self.logger.info(f"Found system ChromeDriver at: {path}")
                        break
            
            # Approach 3: Try without specifying driver path (if in PATH)
            if driver_path:
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                self.logger.info("Trying ChromeDriver from system PATH...")
                driver = webdriver.Chrome(options=options)
            
            # Execute script to hide webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("ChromeDriver setup successful")
            return driver
            
        except Exception as e:
            self.logger.error(f"Error setting up ChromeDriver: {str(e)}")
            error_msg = f"""
ChromeDriver setup failed: {str(e)}

Solutions to try:
1. Download ChromeDriver manually from https://chromedriver.chromium.org/
2. Place chromedriver.exe in your project folder
3. Add chromedriver.exe to your system PATH
4. Make sure Chrome browser is installed and updated
5. Run as Administrator if permission issues persist
            """
            raise Exception(error_msg)
    
    def search_businesses(self, query: str, location: str = "") -> List[Dict]:
        """
        Search for businesses on Google Maps and extract ALL data from search results.
        Uses endless scrolling to get all available businesses.
        
        Args:
            query (str): Business type or name to search for
            location (str): Location to search in
            
        Returns:
            List[Dict]: List of business information dictionaries
        """
        search_query = f"{query} {location}".strip()
        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        self.logger.info(f"Searching for: {search_query}")
        self.logger.info("Will scrape ALL available businesses using endless scrolling...")
        self.driver.get(url)
        time.sleep(5)
        
        businesses = []
        
        try:
            # Wait for search results to load
            results_container = self._wait_for_results()
            if not results_container:
                self.logger.error("Could not find search results container")
                return businesses
            
            # Scroll to load ALL results (endless scrolling)
            self._scroll_and_load_all_results()
            
            # Extract business data from search results
            businesses = self._extract_all_businesses_from_results()
            
            self.logger.info(f"Successfully scraped {len(businesses)} businesses")
            
        except Exception as e:
            self.logger.error(f"Error during search: {str(e)}")
        
        return businesses
    
    def _wait_for_results(self):
        """Wait for search results to load."""
        result_selectors = [
            '[role="main"]',
            '.m6QErb',
            '[data-value="Search results"]',
            '.section-result'
        ]
        
        for selector in result_selectors:
            try:
                results_container = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                self.logger.info(f"Found results container with selector: {selector}")
                return results_container
            except TimeoutException:
                continue
        
        return None
    
    def _scroll_and_load_all_results(self):
        """Scroll the results panel to load ALL businesses using endless scrolling."""
        try:
            self.logger.info("Starting endless scrolling to load all businesses...")
            
            scrolls = 0
            consecutive_no_change = 0
            max_consecutive_no_change = 8  # More patience for loading
            
            while consecutive_no_change < max_consecutive_no_change:
                # Count current business elements before scrolling
                current_businesses = self.driver.find_elements(By.CSS_SELECTOR, '.hfpxzc')
                current_count = len(current_businesses)
                
                # Get the last business element to scroll to it
                if current_businesses:
                    last_business = current_businesses[-1]
                    
                    try:
                        # Scroll to the last business element
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", last_business)
                        time.sleep(2)
                        
                        # Then scroll down more to trigger loading
                        self.driver.execute_script("window.scrollBy(0, 500);")
                        time.sleep(2)
                        
                        # Also try scrolling within the results container
                        try:
                            results_container = self.driver.find_element(By.CSS_SELECTOR, 'div[role="main"] .m6QErb')
                            self.driver.execute_script("arguments[0].scrollTop += 1000;", results_container)
                        except:
                            pass
                        
                        # Try clicking on the last business to trigger more loading
                        try:
                            self.driver.execute_script("arguments[0].click();", last_business)
                            time.sleep(1)
                            # Press escape to close any popup
                            from selenium.webdriver.common.keys import Keys
                            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(1)
                        except:
                            pass
                            
                    except Exception as e:
                        self.logger.debug(f"Error in scrolling approach: {e}")
                
                # Wait for content to load (reduced for faster scrolling)
                time.sleep(2.5)
                
                # Check for a "Show more results" or similar button
                try:
                    more_results_selectors = [
                        'button[data-value="See more results"]',
                        'button:contains("more")',
                        '.more-results',
                        '[aria-label*="more"]',
                        'button[jsaction*="more"]'
                    ]
                    
                    for selector in more_results_selectors:
                        try:
                            more_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if more_button and more_button.is_displayed():
                                self.driver.execute_script("arguments[0].click();", more_button)
                                self.logger.info("Clicked 'Show more results' button")
                                time.sleep(2)  # Reduced wait time after clicking
                                break
                        except:
                            continue
                except:
                    pass
                
                # Check for "end of list" message to stop scraping
                try:
                    end_of_list_messages = [
                        "You've reached the end of the list.",
                        "You've reached the end",
                        "No more results",
                        "End of results",
                        "That's all we found",
                        "No more places to show"
                    ]
                    
                    # Check for end of list indicators
                    page_text = self.driver.page_source.lower()
                    for end_message in end_of_list_messages:
                        if end_message.lower() in page_text:
                            self.logger.info(f"Found end of list message: '{end_message}' - Stopping scraping")
                            final_count = len(self.driver.find_elements(By.CSS_SELECTOR, '.hfpxzc'))
                            self.logger.info(f"Scraping completed successfully. Total businesses found: {final_count}")
                            return
                    
                    # Also check for visible end-of-list elements
                    end_selectors = [
                        '[data-value*="end"]',
                        '[aria-label*="end"]',
                        '.section-no-result',
                        '.no-more-results',
                        '*:contains("end of the list")',
                        '*:contains("no more results")'
                    ]
                    
                    for selector in end_selectors:
                        try:
                            end_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in end_elements:
                                if element.is_displayed() and element.text:
                                    element_text = element.text.lower()
                                    for end_message in end_of_list_messages:
                                        if end_message.lower() in element_text:
                                            self.logger.info(f"Found end of list element: '{element.text}' - Stopping scraping")
                                            final_count = len(self.driver.find_elements(By.CSS_SELECTOR, '.hfpxzc'))
                                            self.logger.info(f"Scraping completed successfully. Total businesses found: {final_count}")
                                            return
                        except:
                            continue
                            
                except Exception as e:
                    self.logger.debug(f"Error checking for end of list: {e}")
                
                # Count business elements after scrolling
                new_businesses = self.driver.find_elements(By.CSS_SELECTOR, '.hfpxzc')
                new_count = len(new_businesses)
                
                scrolls += 1
                
                # Check if new businesses loaded
                if new_count > current_count:
                    consecutive_no_change = 0  # Reset counter when new content is found
                    new_business_count = new_count - current_count
                    self.logger.info(f"   Scroll {scrolls}: Found {new_business_count} new businesses (total: {new_count})")
                else:
                    consecutive_no_change += 1
                    self.logger.info(f"   Scroll {scrolls}: No new businesses loaded (attempt {consecutive_no_change}/{max_consecutive_no_change})")
                    
                    # If we've had several attempts with no new results, check if we've reached the end
                    if consecutive_no_change >= 3:
                        self.logger.info("Multiple attempts with no new results - checking if we've reached the end...")
                        # Additional check for end-of-list indicators when no new results
                        try:
                            # Check if there are any "Show more" buttons still available
                            more_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[data-value="See more results"]')
                            available_buttons = [btn for btn in more_buttons if btn.is_displayed() and btn.is_enabled()]
                            
                            if not available_buttons:
                                self.logger.info("No more 'Show more results' buttons available - reached end of results")
                                final_count = len(self.driver.find_elements(By.CSS_SELECTOR, '.hfpxzc'))
                                self.logger.info(f"Scraping completed successfully. Total businesses found: {final_count}")
                                break
                                
                        except Exception as e:
                            self.logger.debug(f"Error checking for available buttons: {e}")
                
                # Safety check - prevent infinite scrolling
                if scrolls > 50:
                    self.logger.info("Reached maximum scroll limit (50 scrolls)")
                    break
                    
            final_count = len(self.driver.find_elements(By.CSS_SELECTOR, '.hfpxzc'))
            self.logger.info(f"Scrolling completed after {scrolls} scrolls. Total businesses loaded: {final_count}")
                
        except Exception as e:
            self.logger.warning(f"Error scrolling results: {str(e)}")
    
    def _extract_all_businesses_from_results(self) -> List[Dict]:
        """Extract ALL business data directly from search results with memory-efficient batching."""
        businesses = []
        
        try:
            self.logger.info("Starting business data extraction...")
            
            # Use the most reliable selector
            primary_selector = '.hfpxzc'
            
            # Track extracted businesses to avoid duplicates
            seen_business_names = set()
            
            # Process businesses in smaller batches to prevent memory issues
            batch_size = 20  # Process 20 businesses at a time
            processed_count = 0
            
            while True:
                # Re-find elements each batch to avoid stale references
                business_elements = self.driver.find_elements(By.CSS_SELECTOR, primary_selector)
                
                # Check if we've processed all available elements
                if processed_count >= len(business_elements):
                    self.logger.info(f"Processed all {len(business_elements)} available business elements")
                    break
                
                # Get the next batch
                batch_start = processed_count
                batch_end = min(processed_count + batch_size, len(business_elements))
                current_batch = business_elements[batch_start:batch_end]
                
                self.logger.info(f"Processing batch {batch_start + 1}-{batch_end} of {len(business_elements)} total elements")
                
                # Process each element in the current batch
                for i, element in enumerate(current_batch):
                    try:
                        # Extract basic data first (faster and more reliable)
                        basic_data = self._extract_basic_data_from_element(element, len(businesses) + 1)
                        
                        if basic_data and basic_data.get('name'):
                            business_name = basic_data.get('name', '').strip().lower()
                            
                            # Check for duplicates
                            if business_name and business_name not in seen_business_names:
                                
                                # Try to get additional data by clicking (with extended timing for complete data loading)
                                try:
                                    # Scroll element into view
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                                    time.sleep(0.5)  # Wait for scroll to complete
                                    
                                    # Try clicking for detailed info
                                    element.click()
                                    time.sleep(5.0)  # Wait 5 seconds as requested by user for complete popup loading
                                    
                                    # Wait for sidebar content to fully load with extended timeout
                                    try:
                                        # Wait for sidebar to be present and stable
                                        WebDriverWait(self.driver, 5).until(
                                            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-value='Directions'], .TIHn2, .m6QErb"))
                                        )
                                        time.sleep(2.0)  # Extended wait for all content to render completely
                                    except TimeoutException:
                                        # If sidebar doesn't load normally, still wait extended time
                                        time.sleep(3.0)
                                    
                                    # Try to extract additional data from sidebar
                                    detailed_data = self._extract_quick_sidebar_data()
                                    if detailed_data:
                                        # Merge with basic data
                                        for key, value in detailed_data.items():
                                            if value and (key not in basic_data or not basic_data[key]):
                                                basic_data[key] = value
                                                
                                except Exception as click_error:
                                    self.logger.debug(f"Click failed for {business_name}: {str(click_error)[:50]}...")
                                
                                # Add required fields
                                required_fields = ['rating', 'reviews_count', 'category', 'address', 'phone', 'website', 'business_website_url', 'hours', 'price_range', 'description']
                                for field in required_fields:
                                    if field not in basic_data:
                                        basic_data[field] = ""
                                
                                basic_data['index'] = len(businesses) + 1
                                businesses.append(basic_data)
                                seen_business_names.add(business_name)
                                
                                self.logger.info(f"[{len(businesses)}] Extracted: {basic_data.get('name')} - Rating: {basic_data.get('rating', 'N/A')} - Category: {basic_data.get('category', 'N/A')}")
                                
                            else:
                                self.logger.debug(f"[SKIP] Duplicate business: {basic_data.get('name')}")
                        else:
                            self.logger.debug(f"[SKIP] No valid name from element {batch_start + i + 1}")
                            
                    except Exception as e:
                        self.logger.debug(f"[ERROR] Failed to extract from element {batch_start + i + 1}: {str(e)[:50]}...")
                        continue
                
                processed_count = batch_end
                
                # Memory cleanup every batch
                if len(businesses) % 50 == 0 and len(businesses) > 0:
                    self.logger.info(f"Extracted {len(businesses)} businesses so far...")
                
                # Small delay between batches to prevent overloading
                time.sleep(0.5)
                
        except Exception as e:
            self.logger.error(f"Error in business extraction process: {str(e)}")
        
        self.logger.info(f"Total businesses extracted: {len(businesses)}")
        return businesses
    
    def _extract_quick_sidebar_data(self) -> Optional[Dict]:
        """Extract comprehensive data from sidebar with extended wait for complete loading."""
        try:
            data = {}
            
            # Extended wait for sidebar content to stabilize completely
            time.sleep(1.0)  # Additional stabilization time
            
            # Quick rating extraction with multiple selectors
            try:
                rating_selectors = [
                    '.F7nice span[aria-label*="stars"]',
                    '.F7nice .fontBodyMedium',
                    '[data-value] span',
                    '.aMPvhf-fI6EEc-KVuj8d',
                    'span[role="img"][aria-label*="stars"]'
                ]
                
                for selector in rating_selectors:
                    try:
                        rating_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        rating_text = rating_element.text or rating_element.get_attribute('aria-label') or ""
                        rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                        if rating_match:
                            rating = rating_match.group(1)
                            if 0 <= float(rating) <= 5:
                                data['rating'] = rating
                                break
                    except:
                        continue
            except:
                pass
            
            # Enhanced reviews count extraction with better parsing
            try:
                reviews_selectors = [
                    '.F7nice span[aria-label*="reviews"]',
                    '.F7nice span[aria-label*="review"]',
                    '.UY7F9',
                    'button[aria-label*="reviews"]',
                    'span[aria-label*="review"]'
                ]
                
                for selector in reviews_selectors:
                    try:
                        reviews_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        reviews_text = reviews_element.text or reviews_element.get_attribute('aria-label') or ""
                        # Look for numbers in parentheses, standalone numbers, or comma-separated numbers
                        count_match = re.search(r'[\(\s](\d+,?\d*)[\)\s]|(\d+,?\d+)\s*review|(\d+,?\d+)', reviews_text)
                        if count_match:
                            count = count_match.group(1) or count_match.group(2) or count_match.group(3)
                            data['reviews_count'] = count.replace(',', '')
                            break
                    except:
                        continue
            except:
                pass
            
            # Enhanced category extraction with comprehensive approaches
            try:
                category_selectors = [
                    'button[jsaction*="category"]',
                    '.DkEaL',
                    'button.DkEaL',
                    '.LBgpqf',
                    '[data-value="Categories"] + div',
                    'button[data-value*="category"]',
                    '.skqShb'
                ]
                
                for selector in category_selectors:
                    try:
                        category_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        category_text = category_element.text.strip()
                        if category_text and 'directions' not in category_text.lower() and len(category_text) < 100:
                            data['category'] = category_text
                            break
                    except:
                        continue
                        
                # Enhanced text parsing with longer wait time benefits
                if 'category' not in data:
                    try:
                        # Look for category patterns in the sidebar area specifically
                        sidebar_elements = self.driver.find_elements(By.CSS_SELECTOR, '.TIHn2, .m6QErb, [role="main"]')
                        for sidebar in sidebar_elements:
                            text_content = sidebar.text
                            lines = text_content.split('\n')
                            for line in lines[:30]:  # Check more lines with extended time
                                line = line.strip()
                                if any(cat_word in line.lower() for cat_word in ['restaurant', 'cafe', 'bar', 'grill', 'kitchen', 'diner', 'bistro', 'steakhouse', 'pizzeria', 'bakery']):
                                    if len(line) < 50 and line not in ['Restaurant', 'Restaurants'] and '·' not in line:
                                        data['category'] = line
                                        break
                            if 'category' in data:
                                break
                    except:
                        pass
            except:
                pass
            
            # Enhanced address extraction with more comprehensive selectors
            try:
                address_selectors = [
                    'button[data-item-id="address"] .Io6YTe',
                    'button[aria-label*="Address"]',
                    '.Io6YTe',
                    '.LrzXr',
                    'button[data-item-id="address"]',
                    '[data-item-id="address"]'
                ]
                
                for selector in address_selectors:
                    try:
                        address_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        address_text = address_element.text.strip() or address_element.get_attribute('aria-label')
                        if address_text:
                            if 'Address:' in address_text:
                                address_clean = address_text.replace('Address:', '').strip()
                                if len(address_clean) > 10:
                                    data['address'] = address_clean
                                    break
                            elif any(addr_word in address_text.lower() for addr_word in ['street', 'st ', ' st', 'ave', 'avenue', 'ny ', 'new york', 'broadway', 'road', 'rd']) and len(address_text) > 10:
                                data['address'] = address_text
                                break
                    except:
                        continue
            except:
                pass
            
            # Enhanced phone extraction with extended selectors
            try:
                phone_selectors = [
                    'button[data-item-id*="phone"] .Io6YTe',
                    'button[aria-label*="Phone"]',
                    'button[aria-label*="Call"]',
                    '[data-item-id="phone"]',
                    'button[data-item-id="phone"]'
                ]
                
                for selector in phone_selectors:
                    try:
                        phone_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        phone_text = phone_element.text.strip() or phone_element.get_attribute('aria-label')
                        if phone_text:
                            if 'Phone:' in phone_text:
                                phone_clean = phone_text.replace('Phone:', '').strip()
                                if self._is_valid_phone(phone_clean):
                                    data['phone'] = phone_clean
                                    break
                            elif self._is_valid_phone(phone_text):
                                data['phone'] = phone_text
                                break
                    except:
                        continue
            except:
                pass
            
            # Enhanced website extraction with focus on actual business websites
            try:
                website_selectors = [
                    'button[data-item-id*="website"] .Io6YTe',
                    'button[aria-label*="Website"]',
                    'button[data-item-id="website"]',
                    '[data-item-id="website"]',
                    'button[data-item-id="website"] span',
                    'a[href*="http"]',
                    'button[aria-label*="website"]'
                ]
                
                for selector in website_selectors:
                    try:
                        website_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        website_text = website_element.text.strip() or website_element.get_attribute('href') or website_element.get_attribute('aria-label')
                        
                        if website_text:
                            # Clean up website text
                            if 'Website:' in website_text:
                                website_text = website_text.replace('Website:', '').strip()
                            
                            # Store Google Maps URL as website
                            if ('http' in website_text or '.com' in website_text or '.org' in website_text or '.net' in website_text):
                                data['website'] = website_text
                                break
                    except:
                        continue
                        
                # Extract business website URL from the specific HTML structure provided
                try:
                    # Look for the specific structure: .AeaXub .rogA2c .gSkmPd containing the business website
                    business_website_elements = self.driver.find_elements(By.CSS_SELECTOR, '.AeaXub .rogA2c .gSkmPd.fontBodySmall.DshQNd')
                    for elem in business_website_elements:
                        website_text = elem.text.strip()
                        if website_text and ('.com' in website_text or '.org' in website_text or '.net' in website_text or '.edu' in website_text):
                            # Validate it's a business website (not Google)
                            if 'google.com' not in website_text and 'maps' not in website_text:
                                data['business_website_url'] = website_text
                                break
                    
                    # Alternative selector for business website
                    if 'business_website_url' not in data:
                        alt_selectors = [
                            '.gSkmPd.fontBodySmall.DshQNd',
                            '.rogA2c .gSkmPd',
                            '.Io6YTe + .HMy2Jf + .gSkmPd'
                        ]
                        for selector in alt_selectors:
                            try:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for elem in elements:
                                    text = elem.text.strip()
                                    if text and any(domain in text for domain in ['.com', '.org', '.net', '.edu']) and 'google.com' not in text:
                                        data['business_website_url'] = text
                                        break
                                if 'business_website_url' in data:
                                    break
                            except:
                                continue
                except:
                    pass
                        
                # If no website found with selectors, try to find website links in the sidebar text
                if 'website' not in data:
                    try:
                        sidebar_elements = self.driver.find_elements(By.CSS_SELECTOR, '.TIHn2, .m6QErb, [role="main"]')
                        for sidebar in sidebar_elements:
                            # Look for clickable website elements
                            website_links = sidebar.find_elements(By.CSS_SELECTOR, 'a[href*="http"]')
                            for link in website_links:
                                href = link.get_attribute('href')
                                if href:
                                    data['website'] = href
                                    break
                            if 'website' in data:
                                break
                                
                            # Also check for website buttons that might contain the URL
                            website_buttons = sidebar.find_elements(By.CSS_SELECTOR, 'button[data-item-id*="website"], button[aria-label*="Website"]')
                            for button in website_buttons:
                                button_text = button.text.strip()
                                if button_text and any(domain in button_text for domain in ['.com', '.org', '.net', '.edu', '.gov']):
                                    data['website'] = button_text
                                    break
                            if 'website' in data:
                                break
                    except:
                        pass
            except:
                pass
            
            # Enhanced hours extraction with extended wait benefits
            try:
                hours_selectors = [
                    'button[data-item-id*="hours"]',
                    'button[aria-label*="Hours"]',
                    '[data-item-id="hours"]',
                    '.t39EBf'
                ]
                
                for selector in hours_selectors:
                    try:
                        hours_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        hours_text = hours_element.text.strip() or hours_element.get_attribute('aria-label')
                        if hours_text and any(time_word in hours_text.lower() for time_word in ['am', 'pm', 'open', 'closed', 'hours']):
                            if len(hours_text) < 200:  # Reasonable hours length
                                data['hours'] = hours_text
                                break
                    except:
                        continue
            except:
                pass
            
            return data if data else None
            
        except Exception as e:
            self.logger.debug(f"Enhanced sidebar extraction failed: {e}")
            return None
    
    def _extract_business_data_from_element(self, element, index: int) -> Optional[Dict]:
        """Extract business data from a single search result element with enhanced robustness."""
        try:
            self.logger.debug(f"Extracting data from element {index}")
            
            # First attempt: Extract basic info directly from the element
            basic_data = self._extract_basic_data_from_element(element, index)
            
            # Initialize with basic data
            business_data = basic_data.copy() if basic_data else {'index': index}
            
            # Attempt to click for detailed information
            detailed_data = None
            click_successful = False
            
            try:
                # Ensure element is in view and clickable
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.3)  # Brief pause for scrolling
                
                # Multiple click strategies
                click_methods = [
                    lambda: element.click(),
                    lambda: self.actions.move_to_element(element).click().perform(),
                    lambda: self.driver.execute_script("arguments[0].click();", element)
                ]
                
                for method in click_methods:
                    try:
                        method()
                        click_successful = True
                        self.logger.debug(f"✓ Click successful for element {index}")
                        break
                    except Exception as click_error:
                        self.logger.debug(f"Click method failed: {click_error}")
                        continue
                
                if click_successful:
                    # Wait for sidebar to load and extract detailed data
                    self._wait_for_sidebar_to_load()
                    detailed_data = self._extract_detailed_data_from_sidebar()
                    
                    # If we got a name from sidebar, use it
                    sidebar_name = self._extract_sidebar_name()
                    if sidebar_name:
                        business_data['name'] = sidebar_name
                    
                    # Merge detailed data
                    if detailed_data:
                        business_data.update({k: v for k, v in detailed_data.items() if v})
                        
            except Exception as click_error:
                self.logger.warning(f"Could not click element {index} for detailed info: {click_error}")
            
            # Validation and enhancement of extracted data
            if not business_data.get('name'):
                # Try alternative name extraction methods
                name_attempts = [
                    lambda: element.get_attribute('aria-label'),
                    lambda: element.get_attribute('title'),
                    lambda: element.text.strip(),
                ]
                
                for method in name_attempts:
                    try:
                        name = method()
                        if name and len(name.strip()) > 1:
                            business_data['name'] = name.strip()
                            break
                    except:
                        continue
            
            # If we still don't have a name, extract from any text content
            if not business_data.get('name'):
                try:
                    # Look for any text content in the element
                    text_elements = element.find_elements(By.XPATH, ".//*[text()]")
                    for text_elem in text_elements[:3]:  # Check first few text elements
                        text = text_elem.text.strip()
                        if text and len(text) > 2 and not text.isdigit():
                            business_data['name'] = text
                            break
                except:
                    pass
            
            # Last resort - use element attributes or create placeholder
            if not business_data.get('name'):
                data_cid = element.get_attribute('data-cid')
                if data_cid:
                    business_data['name'] = f"Business_CID_{data_cid}"
                else:
                    business_data['name'] = f"Business_Element_{index}"
                self.logger.warning(f"Used fallback name for element {index}: {business_data['name']}")
            
            # Ensure all expected fields exist
            expected_fields = ['rating', 'reviews_count', 'category', 'address', 'phone', 'website', 'hours', 'price_range', 'description']
            for field in expected_fields:
                if field not in business_data:
                    business_data[field] = ""
            
            # Final validation
            if business_data.get('name') and len(business_data['name'].strip()) > 0:
                self.logger.debug(f"[SUCCESS] Successfully extracted data for: {business_data['name']}")
                return business_data
            else:
                self.logger.warning(f"[FAIL] Failed to extract valid business data from element {index}")
                return None
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error extracting business data from element {index}: {str(e)}")
            # Return a placeholder to maintain count
            return {
                'index': index,
                'name': f"Extraction_Failed_{index}",
                'rating': '',
                'reviews_count': '',
                'category': '',
                'address': '',
                'phone': '',
                'website': '',
                'hours': '',
                'price_range': '',
                'description': f"Data extraction failed: {str(e)}"
            }

    def _wait_for_sidebar_to_load(self):
        """Wait for the sidebar to fully load with business content."""
        try:
            # Wait for sidebar container to appear
            sidebar_selectors = [
                '[role="main"] > div:nth-child(2)',  # Main sidebar container
                '.m6QErb[data-value]',  # Sidebar with data
                '[data-attrid="title"]',  # Business title in sidebar
                '.DUwDvf.lfPIob',  # Business name
                '.fontHeadlineSmall'  # Alternative business name
            ]
            
            sidebar_loaded = False
            max_wait_time = 3.0  # Maximum 3 seconds wait
            start_time = time.time()
            
            while not sidebar_loaded and (time.time() - start_time) < max_wait_time:
                for selector in sidebar_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element and element.is_displayed():
                            # Additional check: make sure it has actual content
                            if selector in ['[data-attrid="title"]', '.DUwDvf.lfPIob', '.fontHeadlineSmall']:
                                if element.text.strip():  # Has actual text content
                                    sidebar_loaded = True
                                    break
                            else:
                                sidebar_loaded = True
                                break
                    except:
                        continue
                
                if not sidebar_loaded:
                    time.sleep(0.1)  # Small incremental wait
            
            # Additional small wait to ensure content is stable
            time.sleep(1.3)  # As requested by user
            
        except Exception as e:
            self.logger.debug(f"Error waiting for sidebar: {e}")
            time.sleep(2)  # Fallback wait

    def _extract_basic_data_from_element(self, element, index: int) -> Dict:
        """Extract comprehensive business data directly from search result element with enhanced extraction."""
        try:
            business_data = {'index': index}
            
            # Enhanced name extraction with more selectors and fallbacks
            name_selectors = [
                '.fontHeadlineSmall',
                '.DUwDvf',
                '[role="heading"]',
                'h3',
                'h2',
                '.qBF1Pd',
                '.fontBodyMedium',
                'div.fontBodyMedium > span',
                '.section-result-title',
                'a[data-value]'
            ]
            
            name_found = False
            for selector in name_selectors:
                try:
                    name_elements = element.find_elements(By.CSS_SELECTOR, selector)
                    for name_elem in name_elements:
                        if name_elem and name_elem.text.strip():
                            text = name_elem.text.strip()
                            # Filter out obvious non-business names
                            if len(text) > 1 and not text.isdigit() and 'directions' not in text.lower():
                                business_data['name'] = text
                                name_found = True
                                break
                    if name_found:
                        break
                except:
                    continue
            
            # Fallback name extraction from attributes
            if not name_found:
                try:
                    aria_label = element.get_attribute('aria-label')
                    if aria_label and len(aria_label.strip()) > 1:
                        business_data['name'] = aria_label.strip()
                        name_found = True
                except:
                    pass
            
            # Enhanced rating extraction with more comprehensive search
            rating_selectors = [
                '.MW4etd',
                '.fontBodySmall .MW4etd',
                '[aria-label*="stars"]',
                '.review-score',
                'span[aria-label*="star"]',
                '.F7nice span',
                '.fontBodySmall span:first-child'
            ]
            
            for selector in rating_selectors:
                try:
                    rating_elements = element.find_elements(By.CSS_SELECTOR, selector)
                    for rating_elem in rating_elements:
                        text = rating_elem.text.strip() or rating_elem.get_attribute('aria-label') or ""
                        if text:
                            # Extract numeric rating
                            rating_match = re.search(r'(\d+\.?\d*)', text)
                            if rating_match:
                                rating = rating_match.group(1)
                                try:
                                    rating_float = float(rating)
                                    if 0 <= rating_float <= 5:
                                        business_data['rating'] = rating
                                        break
                                except ValueError:
                                    continue
                except:
                    continue
                    
            # Try to extract reviews count from various locations
            reviews_selectors = [
                'span[aria-label*="reviews"]',
                'button[aria-label*="reviews"]',
                '.fontBodySmall span:contains("(")',
                '.F7nice .fontBodySmall'
            ]
            
            for selector in reviews_selectors:
                try:
                    reviews_elements = element.find_elements(By.CSS_SELECTOR, selector)
                    for reviews_elem in reviews_elements:
                        text = reviews_elem.text or reviews_elem.get_attribute('aria-label') or ""
                        if text:
                            # Extract number from text like "(860)" or "860 reviews"
                            count_match = re.search(r'[\(\s](\d+)[\)\s]', text)
                            if count_match:
                                business_data['reviews_count'] = count_match.group(1)
                                break
                            # Also try simple number extraction
                            simple_match = re.search(r'(\d+)', text)
                            if simple_match and len(simple_match.group(1)) > 1:  # At least 2 digits
                                business_data['reviews_count'] = simple_match.group(1)
                                break
                except:
                    continue
            
            # Enhanced category extraction
            category_selectors = [
                '.fontBodySmall',
                '.DkEaL',
                '.W4Efsd:nth-child(2)',
                '.W4Efsd',
                'button.DkEaL',
                '.section-result-category',
                '.fontBodySmall:not(:has(.MW4etd))'  # Exclude elements with ratings
            ]
            
            for selector in category_selectors:
                try:
                    category_elements = element.find_elements(By.CSS_SELECTOR, selector)
                    for category_elem in category_elements:
                        if category_elem and category_elem.text.strip():
                            text = category_elem.text.strip()
                            # More sophisticated filtering
                            if (len(text) > 2 and 
                                not text.replace('.', '').replace(',', '').isdigit() and  # Not just numbers
                                'directions' not in text.lower() and
                                not re.match(r'^\d+\.\d+\s', text) and  # Not rating format
                                not re.match(r'^\(\d+\)', text) and  # Not review count format
                                len(text) < 100 and  # Not too long description
                                not any(char in text for char in ['$', '$$', '$$$', '$$$$'])):  # Not price range
                                business_data['category'] = text
                                break
                except:
                    continue
            
            # Enhanced website URL extraction from element links and text
            try:
                # First try to find actual clickable website links (keep Google Maps URLs)
                website_links = element.find_elements(By.CSS_SELECTOR, 'a[href*="http"]')
                for link in website_links:
                    href = link.get_attribute('href')
                    if href:
                        business_data['website'] = href
                        break
                        
                # Extract business website from specific HTML structure (.gSkmPd elements)
                try:
                    business_website_elements = element.find_elements(By.CSS_SELECTOR, '.gSkmPd.fontBodySmall.DshQNd, .gSkmPd')
                    for elem in business_website_elements:
                        text = elem.text.strip()
                        if text and any(domain in text for domain in ['.com', '.org', '.net', '.edu']) and 'google.com' not in text:
                            business_data['business_website_url'] = text
                            break
                except:
                    pass
                        
                # Also look for website text patterns in element
                if 'business_website_url' not in business_data:
                    website_text_elements = element.find_elements(By.XPATH, ".//*[contains(text(), '.com') or contains(text(), '.org') or contains(text(), '.net')]")
                    for elem in website_text_elements:
                        text = elem.text.strip()
                        if text and 'google.com' not in text and 'maps' not in text and len(text) < 100:
                            # Validate it looks like a business website
                            if re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text) or any(domain in text for domain in ['.com', '.org', '.net']):
                                business_data['business_website_url'] = text
                                break
            except:
                pass
            
            # Try to extract additional info from the element's text content
            try:
                full_text = element.text
                if full_text:
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    
                    # Process each line to extract different data types
                    for line_idx, line in enumerate(lines):
                        if not line:
                            continue
                        
                        # Skip the business name line (usually first)
                        if line_idx == 0 and business_data.get('name') and line in business_data['name']:
                            continue
                            
                        # Look for rating patterns (e.g., "4.5", "4.5 stars")
                        if 'rating' not in business_data or not business_data['rating']:
                            rating_match = re.search(r'^(\d+\.?\d*)\s*(?:stars?)?$', line)
                            if rating_match:
                                rating = rating_match.group(1)
                                if 0 <= float(rating) <= 5:
                                    business_data['rating'] = rating
                                    continue
                        
                        # Look for review count patterns (e.g., "(1,234)", "1,234 reviews")
                        if 'reviews_count' not in business_data or not business_data['reviews_count']:
                            review_match = re.search(r'[\(\s]?(\d{1,3}(?:,\d{3})*|\d+)[\)\s]?\s*(?:reviews?)?', line)
                            if review_match and len(review_match.group(1).replace(',', '')) >= 2:  # At least 2 digits
                                business_data['reviews_count'] = review_match.group(1).replace(',', '')
                                continue
                        
                        # Look for category patterns (restaurant types, etc.)
                        if ('category' not in business_data or not business_data['category']) and len(line) < 100:
                            # Common restaurant/business categories
                            category_keywords = ['restaurant', 'cafe', 'bar', 'grill', 'kitchen', 'bistro', 'steakhouse', 'diner', 'eatery', 'bakery', 'pizzeria', 'shop', 'store', 'market']
                            if (any(keyword in line.lower() for keyword in category_keywords) or
                                (len(line) > 5 and len(line) < 50 and 
                                 not any(char.isdigit() for char in line) and 
                                 not any(symbol in line for symbol in ['$', '(', ')', '•', '★']) and
                                 'open' not in line.lower() and 'close' not in line.lower())):
                                business_data['category'] = line
                                continue
                        
                        # Look for price range indicators
                        if ('price_range' not in business_data or not business_data['price_range']):
                            if any(price in line for price in ['$', '$$', '$$$', '$$$$']) and len(line) < 20:
                                business_data['price_range'] = line
                                continue
                        
                        # Look for address patterns
                        if ('address' not in business_data or not business_data['address']):
                            if ((any(word in line.lower() for word in ['street', 'st', 'ave', 'avenue', 'road', 'rd', 'blvd', 'way', 'place', 'drive', 'dr']) or
                                 re.search(r'\d+.*\w+.*(?:\d{5}|NY|New York)', line)) and
                                len(line) > 15 and len(line) < 200):
                                business_data['address'] = line
                                continue
                            
                        # Look for hours
                        if ('hours' not in business_data or not business_data['hours']):
                            if (any(time_word in line.lower() for time_word in ['open', 'close', 'hours', 'pm', 'am']) and
                                len(line) < 100):
                                business_data['hours'] = line
                                continue
                                
                        # Look for website URLs
                        if ('website' not in business_data or not business_data['website']):
                            if (('http' in line or '.com' in line or '.org' in line or '.net' in line) and 
                                len(line) < 200):
                                business_data['website'] = line
                                continue
                                
                        # Look for business website URLs (excluding Google URLs)
                        if ('business_website_url' not in business_data or not business_data['business_website_url']):
                            if (('.com' in line or '.org' in line or '.net' in line or '.edu' in line) and 
                                'google.com' not in line and 'maps' not in line and len(line) < 100):
                                business_data['business_website_url'] = line
                                continue
                                
            except Exception as e:
                self.logger.debug(f"Error parsing element text: {e}")
            
            return business_data
            
        except Exception as e:
            self.logger.debug(f"Error extracting basic data from element {index}: {str(e)}")
            return {'index': index}

    def _extract_detailed_data_from_sidebar(self) -> Dict:
        """Extract detailed business data from the opened sidebar."""
        return {
            'rating': self._extract_sidebar_rating(),
            'reviews_count': self._extract_sidebar_reviews_count(),
            'category': self._extract_sidebar_category(),
            'address': self._extract_sidebar_address(),
            'phone': self._extract_sidebar_phone(),
            'website': self._extract_sidebar_website(),
            'hours': self._extract_sidebar_hours(),
            'price_range': self._extract_sidebar_price_range(),
            'description': self._extract_sidebar_description()
        }
    
    def _extract_sidebar_name(self) -> str:
        """Extract business name from the sidebar."""
        selectors = [
            'h1.DUwDvf',
            'h1[data-attrid="title"]',
            '.DUwDvf.lfPIob',
            '[role="main"] h1',
            '.fontHeadlineSmall',
            'h1'
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text and len(text) > 1 and 'Directions' not in text:
                    return text
            except NoSuchElementException:
                continue
        
        return ""
    
    def _extract_sidebar_rating(self) -> str:
        """Extract business rating from the sidebar."""
        selectors = [
            '.F7nice span[aria-label*="stars"]',
            '.F7nice .fontBodyMedium',
            'span[aria-label*="star"]',
            '.F7nice span',
            '.dmRWX .F7nice'
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text or element.get_attribute('aria-label') or ""
                if text:
                    # Extract numeric rating
                    rating_match = re.search(r'(\d+\.?\d*)', text)
                    if rating_match:
                        rating = rating_match.group(1)
                        try:
                            rating_float = float(rating)
                            if 0 <= rating_float <= 5:
                                return rating
                        except ValueError:
                            continue
            except NoSuchElementException:
                continue
        
        return ""
    
    def _extract_sidebar_reviews_count(self) -> str:
        """Extract number of reviews from the sidebar."""
        selectors = [
            '.F7nice span[aria-label*="reviews"]',
            'span[aria-label*="reviews"]',
            'button[aria-label*="reviews"]'
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text or element.get_attribute('aria-label')
                if text:
                    # Extract number from text like "(860)" or "860 reviews"
                    count_match = re.search(r'[\(\s](\d+)[\)\s]', text)
                    if count_match:
                        return count_match.group(1)
            except NoSuchElementException:
                continue
        
        return ""
    
    def _extract_sidebar_category(self) -> str:
        """Extract business category from the sidebar."""
        selectors = [
            'button[jsaction*="category"]',
            '.DkEaL',
            'button.DkEaL',
            '.skqShb button'
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text and 'directions' not in text.lower():
                    return text
            except NoSuchElementException:
                continue
        
        return ""
    
    def _extract_sidebar_address(self) -> str:
        """Extract business address from the sidebar."""
        selectors = [
            'button[data-item-id="address"]',
            'button[aria-label*="Address"]',
            '.Io6YTe.fontBodyMedium.kR99db.fdkmkc',
            'button.CsEnBe[aria-label*="Address"]'
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                aria_label = element.get_attribute('aria-label') or ""
                if 'Address:' in aria_label:
                    address = aria_label.replace('Address:', '').strip()
                    if address and len(address) > 10:
                        return address
                
                # Try inner text
                text_element = element.find_element(By.CSS_SELECTOR, '.Io6YTe')
                text = text_element.text.strip()
                if text and len(text) > 10:
                    return text
                    
            except NoSuchElementException:
                continue
        
        return ""
    
    def _extract_sidebar_phone(self) -> str:
        """Extract business phone number from the sidebar."""
        selectors = [
            'button[data-item-id*="phone"]',
            'button[aria-label*="Phone"]',
            'a[href^="tel:"]',
            'button[aria-label*="Call"]'
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                
                # Try aria-label first
                aria_label = element.get_attribute('aria-label') or ""
                if 'Phone:' in aria_label:
                    phone = aria_label.replace('Phone:', '').strip()
                    if self._is_valid_phone(phone):
                        return phone
                
                # Try href for tel: links
                href = element.get_attribute('href') or ""
                if href.startswith('tel:'):
                    phone = href.replace('tel:', '').strip()
                    if self._is_valid_phone(phone):
                        return phone
                
                # Try inner text
                text_element = element.find_element(By.CSS_SELECTOR, '.Io6YTe')
                text = text_element.text.strip()
                if self._is_valid_phone(text):
                    return text
                    
            except NoSuchElementException:
                continue
        
        return ""
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Check if a string looks like a valid phone number."""
        if not phone:
            return False
        # Check for basic phone patterns
        phone_pattern = r'[\+\(\)\-\s\d]{10,}'
        return bool(re.search(phone_pattern, phone)) and len(re.findall(r'\d', phone)) >= 10
    
    def _extract_sidebar_website(self) -> str:
        """Extract business website from the sidebar."""
        selectors = [
            'a[data-item-id="authority"]',
            'a[href^="http"]:not([href*="google"])',
            'button[aria-label*="website"] + div a'
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                href = element.get_attribute('href')
                if href and not 'google' in href.lower() and href.startswith('http'):
                    return href
            except NoSuchElementException:
                continue
        
        return ""
    
    def _extract_sidebar_hours(self) -> str:
        """Extract business hours from the sidebar."""
        selectors = [
            'button[data-item-id="oh"]',
            'button[aria-label*="hours"]',
            '.Io6YTe.fontBodyMedium.kR99db.fdkmkc'
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text_element = element.find_element(By.CSS_SELECTOR, '.Io6YTe')
                text = text_element.text.strip()
                if text and ('open' in text.lower() or 'closed' in text.lower() or ':' in text):
                    return text
            except NoSuchElementException:
                continue
        
        return ""
    
    def _extract_sidebar_price_range(self) -> str:
        """Extract price range from the sidebar."""
        try:
            # Look for price indicators like $ $$ $$$
            price_elements = self.driver.find_elements(By.CSS_SELECTOR, '[aria-label*="Price"], .price, [data-price]')
            for element in price_elements:
                text = element.text or element.get_attribute('aria-label')
                if text and ('$' in text or 'price' in text.lower()):
                    return text.strip()
        except Exception as e:
            self.logger.debug(f"Error extracting price range: {str(e)}")
        
        return ""
    
    def _extract_sidebar_description(self) -> str:
        """Extract business description from the sidebar."""
        selectors = [
            '.wiI7pd',
            '.VpMB0',
            '.section-editorial-quote',
            '.section-editorial-text'
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text and len(text) > 20 and 'ago' not in text.lower():
                    return text[:500]  # Limit description length
            except NoSuchElementException:
                continue
        
        return ""
    
    def save_to_csv(self, businesses: List[Dict], filename: str = None):
        """Save scraped business data to CSV file."""
        if not filename:
            filename = f"google_businesses_{int(time.time())}.csv"
        
        if not businesses:
            self.logger.warning("No business data to save")
            return
        
        try:
            df = pd.DataFrame(businesses)
            df.to_csv(filename, index=False, encoding='utf-8')
            self.logger.info(f"Saved {len(businesses)} businesses to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving to CSV: {str(e)}")
    
    def save_to_json(self, businesses: List[Dict], filename: str = None):
        """Save scraped business data to JSON file."""
        if not filename:
            filename = f"google_businesses_{int(time.time())}.json"
        
        if not businesses:
            self.logger.warning("No business data to save")
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(businesses, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved {len(businesses)} businesses to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving to JSON: {str(e)}")
    
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            self.logger.info("WebDriver closed")


def main():
    """Main function to run the Google Business Scraper."""
    print("=" * 60)
    print("         Google Business Listing Scraper")
    print("=" * 60)
    
    # Get user input
    query = input("\nEnter business type (e.g., restaurants, coffee shops, dentist): ").strip()
    if not query:
        print("ERROR: Business type is required!")
        return
    
    location = input("Enter location (e.g., New York, San Francisco): ").strip()
    if not location:
        print("ERROR: Location is required!")
        return
    
    headless = input("Run in headless mode? (y/n, default n): ").strip().lower() == 'y'
    
    print(f"\nStarting scraper with endless scrolling...")
    print(f"   Query: {query}")
    print(f"   Location: {location}")
    print(f"   Mode: Scrape ALL results (endless scrolling)")
    print(f"   Headless: {headless}")
    print("-" * 60)
    
    scraper = GoogleBusinessScraper(headless=headless)
    
    try:
        # Search for businesses (will scrape all results)
        businesses = scraper.search_businesses(
            query=query,
            location=location
        )
        
        if businesses:
            print(f"\nSUCCESS: Successfully scraped {len(businesses)} businesses!")
            
            # Display results
            print("\nResults Summary:")
            for i, business in enumerate(businesses[:5], 1):  # Show first 5
                name = business.get('name', 'Unknown')
                rating = business.get('rating', 'N/A')
                category = business.get('category', 'N/A')
                print(f"   {i}. {name} - Rating: {rating} - Category: {category}")
            
            if len(businesses) > 5:
                print(f"   ... and {len(businesses) - 5} more businesses")
            
            # Save results
            timestamp = int(time.time())
            safe_query = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')
            safe_location = re.sub(r'[^\w\s-]', '', location).strip().replace(' ', '_')
            
            csv_filename = f"{safe_query}_{safe_location}_{timestamp}.csv"
            json_filename = f"{safe_query}_{safe_location}_{timestamp}.json"
            
            scraper.save_to_csv(businesses, csv_filename)
            scraper.save_to_json(businesses, json_filename)
            
            print(f"\nResults saved to:")
            print(f"   {csv_filename}")
            print(f"   {json_filename}")
        else:
            print("\nERROR: No businesses found. Please try a different search query or location.")
    
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
    except Exception as e:
        print(f"\nERROR: Error during scraping: {str(e)}")
    finally:
        scraper.close()
        print("\nScraper closed. Thank you for using Google Business Scraper!")


if __name__ == "__main__":
    main()
