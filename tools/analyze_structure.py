"""
Page structure analyzer to understand current Google Maps HTML
"""

from google_business_scraper import GoogleBusinessScraper
import time

def analyze_page_structure():
    """Analyze the current Google Maps page structure to understand selectors"""
    scraper = GoogleBusinessScraper(headless=False, timeout=20)
    
    try:
        # Go to a specific business page
        url = "https://www.google.com/maps/place/Starbucks+Reserve+Roastery+New+York"
        print(f"Analyzing page structure for: {url}")
        
        scraper.driver.get(url)
        time.sleep(5)
        
        print("\n" + "="*50)
        print("ANALYZING PAGE STRUCTURE")
        print("="*50)
        
        # Try to find all h1 elements
        h1_elements = scraper.driver.find_elements("css selector", "h1")
        print(f"\nFound {len(h1_elements)} h1 elements:")
        for i, h1 in enumerate(h1_elements):
            text = h1.text.strip()
            if text:
                print(f"  h1[{i}]: '{text}' (class: {h1.get_attribute('class')})")
        
        # Try to find elements that might contain rating
        rating_elements = scraper.driver.find_elements("css selector", "[aria-label*='star'], [aria-label*='rating'], .F7nice")
        print(f"\nFound {len(rating_elements)} potential rating elements:")
        for i, elem in enumerate(rating_elements[:5]):  # Limit to first 5
            text = elem.text.strip()
            aria_label = elem.get_attribute('aria-label')
            class_name = elem.get_attribute('class')
            print(f"  rating[{i}]: text='{text}' aria-label='{aria_label}' class='{class_name}'")
        
        # Try to find elements that might contain address
        address_elements = scraper.driver.find_elements("css selector", "[aria-label*='address'], [aria-label*='directions'], button[data-value='Directions']")
        print(f"\nFound {len(address_elements)} potential address elements:")
        for i, elem in enumerate(address_elements[:5]):
            text = elem.text.strip()
            aria_label = elem.get_attribute('aria-label')
            class_name = elem.get_attribute('class')
            print(f"  address[{i}]: text='{text}' aria-label='{aria_label}' class='{class_name}'")
        
        # Look for phone elements
        phone_elements = scraper.driver.find_elements("css selector", "[aria-label*='phone'], [aria-label*='call'], a[href^='tel:']")
        print(f"\nFound {len(phone_elements)} potential phone elements:")
        for i, elem in enumerate(phone_elements[:5]):
            text = elem.text.strip()
            aria_label = elem.get_attribute('aria-label')
            href = elem.get_attribute('href')
            class_name = elem.get_attribute('class')
            print(f"  phone[{i}]: text='{text}' aria-label='{aria_label}' href='{href}' class='{class_name}'")
        
        # Get page title
        title = scraper.driver.title
        print(f"\nPage title: {title}")
        
        # Look for specific data structures
        print(f"\nSearching for data-* attributes...")
        data_elements = scraper.driver.find_elements("css selector", "[data-item-id], [data-value]")
        print(f"Found {len(data_elements)} elements with data attributes:")
        for i, elem in enumerate(data_elements[:10]):  # Limit to first 10
            data_item_id = elem.get_attribute('data-item-id')
            data_value = elem.get_attribute('data-value')
            text = elem.text.strip()[:50]  # First 50 chars
            if data_item_id or data_value:
                print(f"  data[{i}]: data-item-id='{data_item_id}' data-value='{data_value}' text='{text}'")
        
        print(f"\n" + "="*50)
        print("ANALYSIS COMPLETE")
        print("="*50)
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
    
    finally:
        # Keep browser open for manual inspection
        input("\nPress Enter to close browser...")
        scraper.close()

if __name__ == "__main__":
    analyze_page_structure()
