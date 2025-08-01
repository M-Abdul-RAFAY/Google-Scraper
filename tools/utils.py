"""
Utility functions for the Google Business Scraper
"""

import re
import json
import csv
from typing import List, Dict, Any, Optional
import pandas as pd


def clean_phone_number(phone: str) -> str:
    """Clean and format phone number."""
    if not phone:
        return ""
    
    # Remove all non-digit characters except + and -
    cleaned = re.sub(r'[^\d+\-\(\)\s]', '', phone)
    
    # Remove extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def clean_rating(rating: str) -> float:
    """Convert rating string to float."""
    if not rating:
        return 0.0
    
    try:
        # Extract numeric value
        match = re.search(r'(\d+\.?\d*)', rating)
        return float(match.group(1)) if match else 0.0
    except (ValueError, AttributeError):
        return 0.0


def clean_reviews_count(reviews: str) -> int:
    """Extract number of reviews as integer."""
    if not reviews:
        return 0
    
    try:
        # Extract number from strings like "(123)" or "123 reviews"
        match = re.search(r'(\d+)', reviews.replace(',', ''))
        return int(match.group(1)) if match else 0
    except (ValueError, AttributeError):
        return 0


def parse_business_hours(hours_text: str) -> Dict[str, str]:
    """Parse business hours from text into structured format."""
    hours_dict = {}
    
    if not hours_text:
        return hours_dict
    
    # Split by lines
    lines = hours_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                day = parts[0].strip()
                time = parts[1].strip()
                hours_dict[day] = time
    
    return hours_dict


def extract_price_level(price_text: str) -> int:
    """Convert price range symbols to numeric level (1-4)."""
    if not price_text:
        return 0
    
    # Count dollar signs
    dollar_count = price_text.count('$')
    
    if dollar_count == 0:
        return 0
    elif dollar_count <= 4:
        return dollar_count
    else:
        return 4


def validate_business_data(business: Dict) -> bool:
    """Validate that business data contains minimum required fields."""
    required_fields = ['name']
    
    for field in required_fields:
        if not business.get(field):
            return False
    
    return True


def merge_business_data(businesses: List[Dict]) -> List[Dict]:
    """Merge duplicate businesses based on name and address."""
    seen = {}
    merged = []
    
    for business in businesses:
        key = f"{business.get('name', '')}-{business.get('address', '')}"
        
        if key not in seen:
            seen[key] = business
            merged.append(business)
        else:
            # Merge additional data
            existing = seen[key]
            for k, v in business.items():
                if not existing.get(k) and v:
                    existing[k] = v
    
    return merged


def filter_businesses(businesses: List[Dict], filters: Dict) -> List[Dict]:
    """Filter businesses based on criteria."""
    filtered = []
    
    for business in businesses:
        include = True
        
        # Rating filter
        if 'min_rating' in filters:
            rating = clean_rating(business.get('rating', ''))
            if rating < filters['min_rating']:
                include = False
        
        # Reviews count filter
        if 'min_reviews' in filters and include:
            reviews = clean_reviews_count(business.get('reviews_count', ''))
            if reviews < filters['min_reviews']:
                include = False
        
        # Category filter
        if 'categories' in filters and include:
            category = business.get('category', '').lower()
            if not any(cat.lower() in category for cat in filters['categories']):
                include = False
        
        # Location filter
        if 'location_keywords' in filters and include:
            address = business.get('address', '').lower()
            if not any(keyword.lower() in address for keyword in filters['location_keywords']):
                include = False
        
        if include:
            filtered.append(business)
    
    return filtered


def export_to_excel(businesses: List[Dict], filename: str):
    """Export business data to Excel file with multiple sheets."""
    if not businesses:
        return
    
    try:
        # Main data sheet
        df_main = pd.DataFrame(businesses)
        
        # Create summary statistics
        summary_data = {
            'Total Businesses': len(businesses),
            'Businesses with Ratings': len([b for b in businesses if b.get('rating')]),
            'Average Rating': df_main['rating'].apply(clean_rating).mean(),
            'Businesses with Phone': len([b for b in businesses if b.get('phone')]),
            'Businesses with Website': len([b for b in businesses if b.get('website')]),
        }
        
        df_summary = pd.DataFrame([summary_data])
        
        # Write to Excel with multiple sheets
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df_main.to_excel(writer, sheet_name='Businesses', index=False)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        print(f"Data exported to {filename}")
        
    except Exception as e:
        print(f"Error exporting to Excel: {str(e)}")


def generate_report(businesses: List[Dict]) -> Dict:
    """Generate a summary report of scraped businesses."""
    if not businesses:
        return {}
    
    report = {
        'total_businesses': len(businesses),
        'businesses_with_rating': 0,
        'businesses_with_phone': 0,
        'businesses_with_website': 0,
        'businesses_with_hours': 0,
        'average_rating': 0.0,
        'rating_distribution': {'5': 0, '4': 0, '3': 0, '2': 0, '1': 0},
        'categories': {},
        'top_rated': [],
        'most_reviewed': []
    }
    
    ratings = []
    
    for business in businesses:
        # Count businesses with data
        if business.get('rating'):
            report['businesses_with_rating'] += 1
            rating = clean_rating(business.get('rating'))
            ratings.append(rating)
            
            # Rating distribution
            rating_int = int(rating) if rating > 0 else 0
            if rating_int in range(1, 6):
                report['rating_distribution'][str(rating_int)] += 1
        
        if business.get('phone'):
            report['businesses_with_phone'] += 1
        
        if business.get('website'):
            report['businesses_with_website'] += 1
        
        if business.get('hours'):
            report['businesses_with_hours'] += 1
        
        # Category distribution
        category = business.get('category', 'Unknown')
        report['categories'][category] = report['categories'].get(category, 0) + 1
    
    # Calculate average rating
    if ratings:
        report['average_rating'] = sum(ratings) / len(ratings)
    
    # Top rated businesses (rating >= 4.5)
    top_rated = [b for b in businesses if clean_rating(b.get('rating', '')) >= 4.5]
    report['top_rated'] = sorted(top_rated, key=lambda x: clean_rating(x.get('rating', '')), reverse=True)[:10]
    
    # Most reviewed businesses
    most_reviewed = [b for b in businesses if b.get('reviews_count')]
    report['most_reviewed'] = sorted(most_reviewed, key=lambda x: clean_reviews_count(x.get('reviews_count', '')), reverse=True)[:10]
    
    return report


def save_report_to_file(report: Dict, filename: str = "scraping_report.json"):
    """Save the generated report to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        print(f"Report saved to {filename}")
    except Exception as e:
        print(f"Error saving report: {str(e)}")


def print_report_summary(report: Dict):
    """Print a formatted summary of the scraping report."""
    print("\n" + "="*50)
    print("SCRAPING REPORT SUMMARY")
    print("="*50)
    
    print(f"Total Businesses Found: {report.get('total_businesses', 0)}")
    print(f"Businesses with Ratings: {report.get('businesses_with_rating', 0)}")
    print(f"Businesses with Phone Numbers: {report.get('businesses_with_phone', 0)}")
    print(f"Businesses with Websites: {report.get('businesses_with_website', 0)}")
    print(f"Average Rating: {report.get('average_rating', 0):.2f}")
    
    print("\nRating Distribution:")
    for rating, count in report.get('rating_distribution', {}).items():
        print(f"  {rating} stars: {count} businesses")
    
    print("\nTop Categories:")
    categories = report.get('categories', {})
    sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
    for category, count in sorted_categories:
        print(f"  {category}: {count} businesses")
    
    print("\nTop Rated Businesses:")
    for i, business in enumerate(report.get('top_rated', [])[:5], 1):
        name = business.get('name', 'Unknown')
        rating = business.get('rating', 'N/A')
        print(f"  {i}. {name} - {rating} stars")
    
    print("="*50)
