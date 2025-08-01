"""
Simple test script with fixed ChromeDriver path
"""

import os
import glob
from google_business_scraper import GoogleBusinessScraper

def find_chromedriver():
    """Find the correct ChromeDriver executable"""
    # Search for chromedriver.exe in the .wdm directory
    wdm_base = os.path.expanduser("~/.wdm")
    pattern = os.path.join(wdm_base, "drivers", "chromedriver", "**", "chromedriver.exe")
    
    chrome_drivers = glob.glob(pattern, recursive=True)
    
    if chrome_drivers:
        # Return the most recent one (highest version number)
        chrome_drivers.sort(reverse=True)
        return chrome_drivers[0]
    
    return None

def test_scraper_simple():
    """Test the scraper with a simple search"""
    print("Finding ChromeDriver...")
    
    driver_path = find_chromedriver()
    if not driver_path:
        print("ChromeDriver not found! Please run: python diagnose.py")
        return
    
    print(f"Found ChromeDriver at: {driver_path}")
    
    # Monkey patch the ChromeDriverManager to return our found path
    from webdriver_manager.chrome import ChromeDriverManager
    original_install = ChromeDriverManager.install
    
    def patched_install(self):
        return driver_path
    
    ChromeDriverManager.install = patched_install
    
    try:
        print("Testing Google Business Scraper...")
        scraper = GoogleBusinessScraper(headless=True, timeout=15)  # Use headless for initial test
        
        print("Searching for coffee shops...")
        businesses = scraper.search_businesses(
            query="coffee shop",
            location="Seattle",
            max_results=3  # Small number for test
        )
        
        print(f"Found {len(businesses)} businesses:")
        for i, business in enumerate(businesses, 1):
            print(f"{i}. {business.get('name', 'N/A')}")
            print(f"   Rating: {business.get('rating', 'N/A')}")
            print(f"   Address: {business.get('address', 'N/A')}")
        
        scraper.close()
        print("\n✓ Test completed successfully!")
        
        if businesses:
            print("Your scraper is working! You can now run:")
            print("  python demo.py")
            print("  python examples.py")
        
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Make sure Chrome browser is installed")
        print("2. Try running as Administrator")
        print("3. Check your internet connection")
    
    finally:
        # Restore original method
        ChromeDriverManager.install = original_install

if __name__ == "__main__":
    test_scraper_simple()
