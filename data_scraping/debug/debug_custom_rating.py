"""Debug script to test custom rating selectors.

New XPath selectors (updated 2025-10-21):
- movie_id: //*[@id="root"]/div[1]/section/section/ul/li[{i}]/a (href 속성 추출)
- movie_name: //*[@id="root"]/div[1]/section/section/ul/li[{i}]/a/div[2]/div[1]
- rating: //*[@id="root"]/div[1]/section/section/ul/li[{i}]/a/div[2]/div[2]
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common import Config
from common.browser_manager import BrowserManager

def debug_custom_rating():
    config = Config()
    browser_manager = BrowserManager(config)
    
    # Use a sample custom_id (you can change this to any user ID)
    custom_id = "K6ExjPmww6vX1"  # Replace with actual user ID
    url = config.get_user_ratings_url(custom_id)
    
    print(f"Opening URL: {url}")
    print("="*80)
    
    with browser_manager.get_page() as page:
        page.goto(url)
        time.sleep(5)  # Wait for page to load
        
        # Scroll to load more ratings
        print("\nScrolling page...")
        browser_manager._scroll_to_end(page)
        time.sleep(3)
        
        # Get page HTML for inspection
        print("\n" + "="*80)
        print("Testing NEW selectors for custom user ratings:")
        print("="*80)
        
        # New XPath selectors (simplified)
        new_xpaths = {
            'movie_id': '//*[@id="root"]/div[1]/section/section/ul/li[{i}]/a',
            'movie_name': '//*[@id="root"]/div[1]/section/section/ul/li[{i}]/a/div[2]/div[1]',
            'rating': '//*[@id="root"]/div[1]/section/section/ul/li[{i}]/a/div[2]/div[2]',
        }
        
        # Also show old XPath from config for comparison
        old_xpaths = {
            'movie_id': config.get_xpath('user_movie_id_template'),
            'movie_name': config.get_xpath('user_movie_name_template'),
            'rating': config.get_xpath('user_movie_rating_template'),
        }
        
        print("\n[OLD XPath templates from config:]")
        for key, value in old_xpaths.items():
            print(f"  {key}: {value}")
        
        print("\n[NEW XPath templates being tested:]")
        for key, value in new_xpaths.items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*80)
        print("Testing first 5 ratings with NEW XPaths:")
        print("="*80)
        
        for i in range(1, 6):
            print(f"\n--- Rating {i} ---")
            
            # Test movie ID (from href attribute)
            try:
                movie_id_xpath = new_xpaths['movie_id'].format(i=i)
                movie_id_elem = page.locator(f'xpath={movie_id_xpath}')
                print(f"Movie link: {movie_id_elem.count()} found")
                if movie_id_elem.count() > 0:
                    href = movie_id_elem.get_attribute('href')
                    movie_id = href.split('/')[-1] if href else None
                    print(f"  → movie_id: {movie_id}")
                    print(f"  → full href: {href}")
            except Exception as e:
                print(f"  ✗ Error extracting movie ID: {e}")
            
            # Test movie name
            try:
                name_xpath = new_xpaths['movie_name'].format(i=i)
                name_elem = page.locator(f'xpath={name_xpath}')
                print(f"Movie name: {name_elem.count()} found")
                if name_elem.count() > 0:
                    movie_name = name_elem.inner_text()
                    print(f"  → movie_name: {movie_name}")
            except Exception as e:
                print(f"  ✗ Error extracting movie name: {e}")
            
            # Test rating
            try:
                rating_xpath = new_xpaths['rating'].format(i=i)
                rating_elem = page.locator(f'xpath={rating_xpath}')
                print(f"Rating: {rating_elem.count()} found")
                if rating_elem.count() > 0:
                    rating_text = rating_elem.inner_text()
                    print(f"  → rating: {rating_text}")
            except Exception as e:
                print(f"  ✗ Error extracting rating: {e}")
        
        # Test: Count total ratings visible
        print("\n" + "="*80)
        print("Counting total ratings on page:")
        print("="*80)
        
        # Try OLD xpath
        old_total = page.locator('xpath=//*[@id="root"]/div[1]/section/section/div[1]/section/div[1]/div/ul/li').count()
        print(f"Total rating items found (OLD XPath): {old_total}")
        
        # Try NEW xpath
        new_total = page.locator('xpath=//*[@id="root"]/div[1]/section/section/ul/li').count()
        print(f"Total rating items found (NEW XPath): {new_total}")
        
        # Test: Get the actual HTML structure
        print("\n" + "="*80)
        print("HTML Structure of ratings section:")
        print("="*80)
        try:
            section_html = page.locator('section section').first
            if section_html.count() > 0:
                html = section_html.evaluate('el => el.outerHTML')
                # Print first 3000 characters
                print(html[:3000])
                if len(html) > 3000:
                    print(f"\n... (truncated, total length: {len(html)} characters)")
        except Exception as e:
            print(f"Could not extract HTML: {e}")
        
        print("\n" + "="*80)
        print("Testing Complete!")
        print("="*80)
        print("\nIf NEW XPath selectors work correctly, update config.py:")
        print("  user_movie_id_template: '//*[@id=\"root\"]/div[1]/section/section/ul/li[{i}]/a/@href'")
        print("  user_movie_name_template: '//*[@id=\"root\"]/div[1]/section/section/ul/li[{i}]/a/div[2]/div[1]/text()'")
        print("  user_movie_rating_template: '//*[@id=\"root\"]/div[1]/section/section/ul/li[{i}]/a/div[2]/div[2]/text()'")
        print("\nPress Enter to close...")
        input()

if __name__ == "__main__":
    debug_custom_rating()

