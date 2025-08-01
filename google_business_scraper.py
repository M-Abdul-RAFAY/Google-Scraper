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
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log'),
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
                
                # Wait longer for content to load
                time.sleep(5)
                
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
                                time.sleep(3)
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
        """Extract ALL business data directly from search results."""
        businesses = []
        
        try:
            # Updated selectors for business listings in search results
            business_selectors = [
                'div[role="article"]',  # Article role containers
                '.hfpxzc',  # Main business result containers
                '[data-result-index]',  # Indexed results
                '.Nv2PK',  # Alternative selector
                'a[data-cid]',  # Business links with CID
                '[jsaction*="pane"]',  # Elements with pane actions
                '.VkpGBb',  # Another common selector
                '.bfdHYd',  # Business card containers
                '.section-result',  # Section results
                'div[jsaction*="pane.resultItem"]',  # Interactive result items
                'a[href*="/maps/place/"]'  # Direct place links
            ]
            
            business_elements = []
            for selector in business_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        business_elements.extend(elements)
                        self.logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        break  # Use the first selector that works
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {str(e)}")
                    continue
            
            # Remove duplicates more intelligently
            processed_elements = []
            seen_elements = set()
            
            for element in business_elements:  # Process all found elements
                try:
                    # Use a more comprehensive identifier for deduplication
                    element_id = element.get_attribute('data-cid') or element.get_attribute('data-feature-id') or str(element.location)
                    
                    if element_id not in seen_elements:
                        processed_elements.append(element)
                        seen_elements.add(element_id)
                except:
                    # If we can't get a unique identifier, still try to process
                    processed_elements.append(element)
                    continue
            
            self.logger.info(f"Processing {len(processed_elements)} unique business elements")
            
            # Extract data from each business element
            for i, element in enumerate(processed_elements):
                try:
                    business_data = self._extract_business_data_from_element(element, i + 1)
                    if business_data and business_data.get('name'):  # Only add if we got a name
                        businesses.append(business_data)
                        self.logger.info(f"Extracted business {len(businesses)}: {business_data.get('name', 'Unknown')}")
                            
                except Exception as e:
                    self.logger.error(f"Error extracting data from element {i+1}: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error extracting businesses from results: {str(e)}")
        
        return businesses
    
    def _extract_business_data_from_element(self, element, index: int) -> Optional[Dict]:
        """Extract business data from a single search result element."""
        try:
            # First try to extract basic info directly from the element without clicking
            basic_data = self._extract_basic_data_from_element(element, index)
            
            # If we got some basic data, try clicking for more detailed info
            if basic_data and basic_data.get('name'):
                try:
                    # Click on the element to open the sidebar with detailed info
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    time.sleep(1)
                    self.actions.move_to_element(element).click().perform()
                    time.sleep(3)  # Wait for sidebar to load
                    
                    # Now extract detailed data from the opened sidebar
                    detailed_data = self._extract_detailed_data_from_sidebar()
                    
                    # Merge basic and detailed data
                    business_data = {**basic_data, **detailed_data}
                    return business_data
                    
                except Exception as e:
                    self.logger.warning(f"Could not click element {index} for detailed info: {str(e)}")
                    # Return basic data if clicking fails
                    return basic_data
            else:
                # If no basic data, still try clicking approach
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    time.sleep(1)
                    self.actions.move_to_element(element).click().perform()
                    time.sleep(3)  # Wait for sidebar to load
                    
                    business_data = {
                        'index': index,
                        'name': self._extract_sidebar_name(),
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
                    
                    return business_data
                    
                except Exception as e:
                    self.logger.error(f"Error extracting business data from element {index}: {str(e)}")
                    return None
            
        except Exception as e:
            self.logger.error(f"Error extracting business data from element {index}: {str(e)}")
            return None

    def _extract_basic_data_from_element(self, element, index: int) -> Dict:
        """Extract basic business data directly from search result element."""
        try:
            business_data = {'index': index}
            
            # Try to extract name from various selectors within the element
            name_selectors = [
                '.fontHeadlineSmall',
                '.DUwDvf',
                '[role="heading"]',
                'h3',
                'h2',
                '.qBF1Pd',
                '.fontBodyMedium'
            ]
            
            for selector in name_selectors:
                try:
                    name_elem = element.find_element(By.CSS_SELECTOR, selector)
                    if name_elem and name_elem.text.strip():
                        business_data['name'] = name_elem.text.strip()
                        break
                except:
                    continue
            
            # Try to extract rating
            rating_selectors = [
                '.MW4etd',
                '.fontBodySmall .MW4etd',
                '[aria-label*="stars"]',
                '.review-score'
            ]
            
            for selector in rating_selectors:
                try:
                    rating_elem = element.find_element(By.CSS_SELECTOR, selector)
                    if rating_elem and rating_elem.text.strip():
                        business_data['rating'] = rating_elem.text.strip()
                        break
                except:
                    continue
            
            # Try to extract category
            category_selectors = [
                '.fontBodySmall',
                '.DkEaL',
                '.W4Efsd:nth-child(2)',
                '.W4Efsd'
            ]
            
            for selector in category_selectors:
                try:
                    category_elem = element.find_element(By.CSS_SELECTOR, selector)
                    if category_elem and category_elem.text.strip():
                        # Skip if it looks like a rating
                        text = category_elem.text.strip()
                        if not any(char.isdigit() for char in text[:3]):  # Avoid ratings
                            business_data['category'] = text
                            break
                except:
                    continue
            
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
