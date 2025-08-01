"""
Advanced scraper with additional features like review extraction and popular times
"""

from google_business_scraper import GoogleBusinessScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
from typing import List, Dict, Optional


class AdvancedGoogleBusinessScraper(GoogleBusinessScraper):
    """
    Extended version of the Google Business Scraper with additional features:
    - Review extraction
    - Popular times data
    - Menu information
    - Q&A section
    - More detailed business attributes
    """
    
    def __init__(self, headless: bool = False, timeout: int = 15):
        super().__init__(headless, timeout)
    
    def extract_business_reviews(self, url: str, max_reviews: int = 10) -> List[Dict]:
        """Extract reviews from a business page."""
        reviews = []
        
        try:
            self.driver.get(url)
            time.sleep(3)
            
            # Click on reviews tab
            try:
                reviews_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-value="Sort reviews"]'))
                )
                reviews_button.click()
                time.sleep(2)
            except TimeoutException:
                self.logger.warning("Could not find reviews section")
                return reviews
            
            # Scroll to load more reviews
            self._scroll_reviews(max_reviews)
            
            # Extract individual reviews
            review_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-review-id]')
            
            for element in review_elements[:max_reviews]:
                try:
                    review_data = {
                        'author': self._safe_extract_text_from_element(element, '[aria-label*="Photo of"]'),
                        'rating': self._extract_review_rating(element),
                        'date': self._safe_extract_text_from_element(element, '.rsqaWe'),
                        'text': self._extract_review_text(element),
                        'helpful_count': self._extract_helpful_count(element)
                    }
                    reviews.append(review_data)
                except Exception as e:
                    self.logger.debug(f"Error extracting review: {str(e)}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error extracting reviews: {str(e)}")
        
        return reviews
    
    def _scroll_reviews(self, max_reviews: int):
        """Scroll the reviews section to load more reviews."""
        try:
            reviews_container = self.driver.find_element(By.CSS_SELECTOR, '[data-value="Sort reviews"]')
            parent = reviews_container.find_element(By.XPATH, './..')
            
            last_count = 0
            scroll_attempts = 0
            max_scroll_attempts = max_reviews // 3
            
            while scroll_attempts < max_scroll_attempts:
                # Scroll down in the reviews container
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", parent)
                time.sleep(2)
                
                # Check if new reviews loaded
                current_reviews = len(self.driver.find_elements(By.CSS_SELECTOR, '[data-review-id]'))
                if current_reviews == last_count:
                    break
                
                last_count = current_reviews
                scroll_attempts += 1
                
        except Exception as e:
            self.logger.debug(f"Error scrolling reviews: {str(e)}")
    
    def _extract_review_rating(self, review_element) -> str:
        """Extract rating from a review element."""
        try:
            rating_element = review_element.find_element(By.CSS_SELECTOR, '[aria-label*="star"]')
            aria_label = rating_element.get_attribute('aria-label')
            if aria_label:
                import re
                rating_match = re.search(r'(\d+)', aria_label)
                return rating_match.group(1) if rating_match else ""
        except NoSuchElementException:
            pass
        return ""
    
    def _extract_review_text(self, review_element) -> str:
        """Extract review text, handling 'more' buttons."""
        try:
            # Try to click "more" button if present
            try:
                more_button = review_element.find_element(By.CSS_SELECTOR, 'button[aria-label="See more"]')
                more_button.click()
                time.sleep(1)
            except NoSuchElementException:
                pass
            
            # Extract the review text
            text_element = review_element.find_element(By.CSS_SELECTOR, '.wiI7pd')
            return text_element.text.strip()
        except NoSuchElementException:
            return ""
    
    def _extract_helpful_count(self, review_element) -> str:
        """Extract helpful count from review."""
        try:
            helpful_element = review_element.find_element(By.CSS_SELECTOR, '[aria-label*="helpful"]')
            return helpful_element.get_attribute('aria-label') or ""
        except NoSuchElementException:
            return ""
    
    def _safe_extract_text_from_element(self, parent_element, selector: str) -> str:
        """Safely extract text from an element within a parent element."""
        try:
            element = parent_element.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except NoSuchElementException:
            return ""
    
    def extract_popular_times(self, url: str) -> Dict:
        """Extract popular times data from business page."""
        popular_times = {}
        
        try:
            self.driver.get(url)
            time.sleep(3)
            
            # Look for popular times section
            try:
                popular_times_section = self.driver.find_element(
                    By.CSS_SELECTOR, '[aria-label*="Popular times"]'
                )
                
                # Extract day-by-day data
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                for day in days:
                    try:
                        day_element = popular_times_section.find_element(
                            By.CSS_SELECTOR, f'[aria-label*="{day}"]'
                        )
                        popular_times[day] = day_element.get_attribute('aria-label')
                    except NoSuchElementException:
                        popular_times[day] = "No data"
                        
            except NoSuchElementException:
                self.logger.debug("Popular times section not found")
                
        except Exception as e:
            self.logger.error(f"Error extracting popular times: {str(e)}")
        
        return popular_times
    
    def extract_menu_info(self, url: str) -> List[Dict]:
        """Extract menu information if available."""
        menu_items = []
        
        try:
            self.driver.get(url)
            time.sleep(3)
            
            # Look for menu section
            try:
                menu_button = self.driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Menu"]')
                menu_button.click()
                time.sleep(2)
                
                # Extract menu items
                menu_elements = self.driver.find_elements(By.CSS_SELECTOR, '.section-layout-flex-vertical')
                
                for element in menu_elements:
                    try:
                        item_name = self._safe_extract_text_from_element(element, '.section-layout-title')
                        item_price = self._safe_extract_text_from_element(element, '.section-layout-price')
                        item_description = self._safe_extract_text_from_element(element, '.section-layout-description')
                        
                        if item_name:
                            menu_items.append({
                                'name': item_name,
                                'price': item_price,
                                'description': item_description
                            })
                    except Exception as e:
                        self.logger.debug(f"Error extracting menu item: {str(e)}")
                        continue
                        
            except NoSuchElementException:
                self.logger.debug("Menu section not found")
                
        except Exception as e:
            self.logger.error(f"Error extracting menu: {str(e)}")
        
        return menu_items
    
    def extract_qa_section(self, url: str) -> List[Dict]:
        """Extract Q&A section data."""
        qa_data = []
        
        try:
            self.driver.get(url)
            time.sleep(3)
            
            # Look for Q&A section
            try:
                qa_button = self.driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Questions"]')
                qa_button.click()
                time.sleep(2)
                
                # Extract Q&A items
                qa_elements = self.driver.find_elements(By.CSS_SELECTOR, '.section-layout-root')
                
                for element in qa_elements:
                    try:
                        question = self._safe_extract_text_from_element(element, '.section-layout-question')
                        answer = self._safe_extract_text_from_element(element, '.section-layout-answer')
                        
                        if question:
                            qa_data.append({
                                'question': question,
                                'answer': answer
                            })
                    except Exception as e:
                        self.logger.debug(f"Error extracting Q&A item: {str(e)}")
                        continue
                        
            except NoSuchElementException:
                self.logger.debug("Q&A section not found")
                
        except Exception as e:
            self.logger.error(f"Error extracting Q&A: {str(e)}")
        
        return qa_data
    
    def get_comprehensive_business_data(self, url: str, include_reviews: bool = False, 
                                      include_menu: bool = False, max_reviews: int = 10) -> Dict:
        """
        Get comprehensive business data including all available information.
        
        Args:
            url (str): Business page URL
            include_reviews (bool): Whether to extract reviews
            include_menu (bool): Whether to extract menu information
            max_reviews (int): Maximum number of reviews to extract
            
        Returns:
            Dict: Comprehensive business data
        """
        # Get basic business data
        business_data = self._extract_business_details(url)
        
        if not business_data:
            return {}
        
        # Add advanced features
        try:
            if include_reviews:
                self.logger.info(f"Extracting reviews for {business_data.get('name', 'Unknown')}")
                business_data['reviews'] = self.extract_business_reviews(url, max_reviews)
            
            if include_menu:
                self.logger.info(f"Extracting menu for {business_data.get('name', 'Unknown')}")
                business_data['menu'] = self.extract_menu_info(url)
            
            # Always try to get popular times and Q&A
            business_data['popular_times'] = self.extract_popular_times(url)
            business_data['qa'] = self.extract_qa_section(url)
            
        except Exception as e:
            self.logger.error(f"Error extracting advanced data: {str(e)}")
        
        return business_data


def main():
    """Example usage of the Advanced Google Business Scraper."""
    scraper = AdvancedGoogleBusinessScraper(headless=False)
    
    try:
        # Search for businesses
        businesses = scraper.search_businesses(
            query="italian restaurants",
            location="Boston",
            max_results=5
        )
        
        # Get comprehensive data for each business
        comprehensive_data = []
        
        for i, business in enumerate(businesses):
            print(f"Getting comprehensive data for business {i+1}: {business.get('name', 'Unknown')}")
            
            comprehensive_business = scraper.get_comprehensive_business_data(
                url=business['url'],
                include_reviews=True,
                include_menu=True,
                max_reviews=5
            )
            
            if comprehensive_business:
                comprehensive_data.append(comprehensive_business)
        
        # Save comprehensive results
        scraper.save_to_json(comprehensive_data, "comprehensive_business_data.json")
        
        print(f"\nExtracted comprehensive data for {len(comprehensive_data)} businesses")
        print("Results saved to comprehensive_business_data.json")
        
    except Exception as e:
        print(f"Error during advanced scraping: {str(e)}")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
