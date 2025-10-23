"""Debug script to test comment selectors."""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from common import Config
from common.browser_manager import BrowserManager

def debug_comments():
    config = Config()
    browser_manager = BrowserManager(config)
    
    # Use a sample movie ID
    movie_id = "mOVPVyR"
    url = config.get_comments_url(movie_id)
    
    print(f"Opening URL: {url}")
    
    with browser_manager.get_page() as page:
        page.goto(url)
        time.sleep(5)  # Wait for page to load
        
        # Scroll to load comments
        print("\nScrolling page...")
        browser_manager._scroll_to_end(page)
        time.sleep(3)
        
        # Get page HTML for inspection
        print("\n" + "="*80)
        print("Testing NEW selectors for comments:")
        print("="*80)
        
        # XPath selectors from config.py (Updated 2025-10-23)
        new_xpaths = {
            'user_id': config.XPATHS['comment_custom_id_template'],
            'text': config.XPATHS['comment_text_template'],
            'rating': config.XPATHS['comment_rating_template'],
            'likes': config.XPATHS['comment_likes_template'],
            'spoiler_button': config.XPATHS['comment_spoiler_button_template']
        }
        
        print("\nTesting first 3 comments with new XPaths:")
        print("="*80)
        
        for i in range(1, 4):
            print(f"\n--- Comment {i} ---")
            
            # Test user ID
            user_xpath = new_xpaths['user_id'].format(i=i)
            user_elem = page.locator(f"xpath={user_xpath}")
            print(f"User ID link: {user_elem.count()} found")
            if user_elem.count() > 0:
                href = user_elem.get_attribute('href')
                custom_id = href.split('/')[-1] if href else None
                print(f"  → custom_id: {custom_id}")
            
            # Test spoiler button first (if exists, click it)
            spoiler_xpath = new_xpaths['spoiler_button'].format(i=i)
            spoiler_btn = page.locator(f"xpath={spoiler_xpath}")
            if spoiler_btn.count() > 0:
                print(f"Spoiler button: Found! Clicking...")
                try:
                    spoiler_btn.click()
                    time.sleep(0.3)
                except:
                    print("  → Could not click")
            
            # Test comment text
            text_xpath = new_xpaths['text'].format(i=i)
            text_elem = page.locator(f"xpath={text_xpath}")
            print(f"Comment text: {text_elem.count()} found")
            if text_elem.count() > 0:
                text = text_elem.inner_text()
                print(f"  → text: {text[:100]}..." if len(text) > 100 else f"  → text: {text}")
            
            # Test rating
            rating_xpath = new_xpaths['rating'].format(i=i)
            rating_elem = page.locator(f"xpath={rating_xpath}")
            print(f"Rating: {rating_elem.count()} found")
            if rating_elem.count() > 0:
                rating = rating_elem.inner_text()
                print(f"  → rating: {rating}")
            
            # Test likes
            likes_xpath = new_xpaths['likes'].format(i=i)
            likes_elem = page.locator(f"xpath={likes_xpath}")
            print(f"Likes: {likes_elem.count()} found")
            if likes_elem.count() > 0:
                likes = likes_elem.inner_text()
                print(f"  → likes: {likes}")
        
        # Test 7: Get the actual HTML structure
        print("\n" + "="*80)
        print("HTML Structure of comment section:")
        print("="*80)
        section_html = page.locator('section > section').first
        if section_html.count() > 0:
            html = section_html.evaluate('el => el.outerHTML')
            # Print first 2000 characters
            print(html[:2000])
        
        print("\n\nPress any key to close...")
        input()

if __name__ == "__main__":
    debug_comments()

