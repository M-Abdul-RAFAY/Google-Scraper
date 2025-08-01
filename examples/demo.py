"""
Simple demo to test the Google Business Scraper
"""

from google_business_scraper import GoogleBusinessScraper
import json

def demo_search():
    """Demo function to test the scraper with a simple search"""
    print("Google Business Scraper Demo")
    print("=" * 40)
    
    # Get user input
    query = input("Enter the type of business to search for (e.g., 'coffee shops', 'restaurants'): ").strip()
    location = input("Enter the location (e.g., 'New York', 'Seattle'): ").strip()
    
    # Get number of results
    try:
        max_results = int(input("Enter maximum number of results (default 5): ") or 5)
    except ValueError:
        max_results = 5
    
    print(f"\nSearching for '{query}' in '{location}'...")
    print("This may take a few minutes...")
    
    # Initialize scraper with increased timeout
    scraper = GoogleBusinessScraper(headless=False, timeout=15)
    
    try:
        # Test search
        print(f"\nStarting search...")
        businesses = scraper.search_businesses(
            query=query,
            location=location,
            max_results=max_results
        )
        
        print(f"\nFound {len(businesses)} businesses:")
        print("-" * 50)
        
        # Display results
        for i, business in enumerate(businesses, 1):
            name = business.get('name', 'N/A')
            rating = business.get('rating', 'N/A')
            address = business.get('address', 'N/A')
            phone = business.get('phone', 'N/A')
            website = business.get('website', 'N/A')
            
            print(f"{i}. Name: {name}")
            print(f"   Rating: {rating}")
            print(f"   Address: {address}")
            print(f"   Phone: {phone}")
            print(f"   Website: {website}")
            print()
        
        # Save results
        if businesses:
            filename_base = f"{query.replace(' ', '_')}_{location.replace(' ', '_')}"
            csv_file = f"{filename_base}_demo.csv"
            json_file = f"{filename_base}_demo.json"
            
            scraper.save_to_csv(businesses, csv_file)
            scraper.save_to_json(businesses, json_file)
            print(f"Results saved to {csv_file} and {json_file}")
        else:
            print("No businesses found. This might be due to:")
            print("1. No businesses matching your search criteria")
            print("2. Google Maps interface changes")
            print("3. Network connectivity issues")
        
        return businesses
        
    except Exception as e:
        print(f"Error during demo: {str(e)}")
        return []
    
    finally:
        scraper.close()
        print("\nDemo completed!")

if __name__ == "__main__":
    demo_search()
