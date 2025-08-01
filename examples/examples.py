"""
Simple usage examples for the Google Business Scraper
"""

from google_business_scraper import GoogleBusinessScraper
import time


def simple_search_example():
    """Basic search example"""
    scraper = GoogleBusinessScraper(headless=False)
    
    try:
        # Search for restaurants in a specific location
        businesses = scraper.search_businesses(
            query="pizza restaurants",
            location="Chicago",
            max_results=15
        )
        
        # Print results
        print(f"Found {len(businesses)} businesses:")
        for i, business in enumerate(businesses, 1):
            print(f"\n{i}. {business.get('name', 'N/A')}")
            print(f"   Rating: {business.get('rating', 'N/A')}")
            print(f"   Address: {business.get('address', 'N/A')}")
            print(f"   Phone: {business.get('phone', 'N/A')}")
        
        # Save to files
        scraper.save_to_csv(businesses, "pizza_restaurants_chicago.csv")
        scraper.save_to_json(businesses, "pizza_restaurants_chicago.json")
        
    finally:
        scraper.close()


def multiple_searches_example():
    """Example with multiple different searches"""
    scraper = GoogleBusinessScraper(headless=True)  # Headless for faster execution
    
    searches = [
        {"query": "hair salon", "location": "Miami", "max_results": 5},
        {"query": "gym fitness", "location": "Miami", "max_results": 5},
        {"query": "car repair", "location": "Miami", "max_results": 5}
    ]
    
    all_results = []
    
    try:
        for search in searches:
            print(f"Searching for {search['query']} in {search['location']}...")
            
            businesses = scraper.search_businesses(
                query=search['query'],
                location=search['location'],
                max_results=search['max_results']
            )
            
            # Add search metadata to each business
            for business in businesses:
                business['search_query'] = search['query']
                business['search_location'] = search['location']
            
            all_results.extend(businesses)
            print(f"Found {len(businesses)} businesses")
            
            # Small delay between searches
            time.sleep(3)
        
        # Save combined results
        if all_results:
            scraper.save_to_csv(all_results, "miami_businesses_combined.csv")
            print(f"Total businesses found: {len(all_results)}")
        
    finally:
        scraper.close()


def custom_search_example():
    """Example with custom search parameters"""
    
    # Get user input
    query = input("Enter business type to search for: ")
    location = input("Enter location: ")
    max_results = int(input("Enter max number of results (default 10): ") or 10)
    
    scraper = GoogleBusinessScraper(headless=False)
    
    try:
        businesses = scraper.search_businesses(
            query=query,
            location=location,
            max_results=max_results
        )
        
        if businesses:
            print(f"\nFound {len(businesses)} businesses:")
            
            # Display summary
            for business in businesses:
                name = business.get('name', 'Unknown')
                rating = business.get('rating', 'No rating')
                address = business.get('address', 'No address')
                print(f"• {name} - Rating: {rating}")
                print(f"  Address: {address}")
                print()
            
            # Save results
            filename = f"{query.replace(' ', '_')}_{location.replace(' ', '_')}.csv"
            scraper.save_to_csv(businesses, filename)
            print(f"Results saved to {filename}")
        else:
            print("No businesses found for your search.")
    
    finally:
        scraper.close()


if __name__ == "__main__":
    print("Google Business Scraper Examples")
    print("=" * 40)
    print("1. Simple pizza restaurant search")
    print("2. Multiple business types in Miami")
    print("3. Custom search")
    
    choice = input("\nSelect an example (1-3): ")
    
    if choice == "1":
        simple_search_example()
    elif choice == "2":
        multiple_searches_example()
    elif choice == "3":
        custom_search_example()
    else:
        print("Invalid choice. Running simple example...")
        simple_search_example()
