"""
Quick test script to verify data extraction is working
"""

from google_business_scraper import GoogleBusinessScraper
import time

def test_single_business():
    """Test data extraction on a single known business"""
    scraper = GoogleBusinessScraper(headless=False, timeout=20)
    
    try:
        # Test with a well-known business
        print("Testing data extraction on a single business...")
        
        # Search for Starbucks which should have complete data
        businesses = scraper.search_businesses(
            query="Starbucks",
            location="New York",
            max_results=1
        )
        
        if businesses:
            business = businesses[0]
            print(f"\nExtracted data for: {business['url']}")
            print("-" * 50)
            
            for key, value in business.items():
                if key != 'url':
                    print(f"{key.title()}: {value}")
            
            # Check how much data we actually got
            non_empty_fields = sum(1 for k, v in business.items() if v and k != 'url')
            total_fields = len(business) - 1  # Exclude URL
            
            print(f"\nData extraction success rate: {non_empty_fields}/{total_fields} fields populated")
            
            if non_empty_fields > 2:
                print("✅ Data extraction is working!")
            else:
                print("⚠️ Data extraction needs improvement")
        else:
            print("❌ No businesses found")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    finally:
        scraper.close()

if __name__ == "__main__":
    test_single_business()
