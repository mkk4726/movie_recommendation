"""Debug script to test movie info selectors.

This script tests the XPath selectors used for extracting movie information
from Watcha movie pages. Updated for new page structure.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common import Config
from common.browser_manager import BrowserManager

# New XPath selectors (updated for new page structure)
NEW_XPATHS = {
    # Movie info page - updated paths (without /text() for Playwright)
    "movie_title": '/html/body/main/div[1]/section/div/div[2]/div/div/div[1]/div[2]/div/h1',
    "movie_basic_info": '/html/body/main/div[1]/section/div/div[2]/div/div/div[1]/div[2]/div/div[2]',
    "movie_additional_info": '/html/body/main/div[1]/section/div/div[2]/div/div/div[1]/div[2]/div/div[3]',
    "movie_synopsis": '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[3]/p',
    "movie_avg_rating": '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[1]/div[2]/div/div[1][1]',
    "movie_n_rating": '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[1]/div[2]/div/div[2][2]',
    "movie_n_comments": '/html/body/main/div[1]/section/div/div[2]/section/section[3]/header/span',
    
    # Cast and crew (dynamic index)
    "cast_name_template": '//*[@id="content_credits"]/section/div[1]/ul/li[{i}]/a/div[2]/div[1]/div[1]',
    "cast_role_template": '//*[@id="content_credits"]/section/div[1]/ul/li[{i}]/a/div[2]/div[1]/div[2]',
}

def debug_movie_info():
    config = Config()
    # Set headless to False for debugging
    config.BROWSER_HEADLESS = True
    browser_manager = BrowserManager(config)
    
    # Check if auth state exists
    from pathlib import Path
    auth_file = Path(config.AUTH_STATE_FILE)
    if auth_file.exists():
        print(f"✅ Auth state found: {auth_file}")
    else:
        print(f"❌ No auth state found: {auth_file}")
        print("Please run login_watcha.py first to authenticate")
        return
    
    # Use a sample movie ID (you can change this to any movie ID)
    movie_id = "mOVPVyR"  # Replace with actual movie ID
    url = config.get_movie_url(movie_id)
    
    print(f"Opening URL: {url}")
    print("="*80)
    
    with browser_manager.get_page() as page:
        page.goto(url)
        time.sleep(5)  # Wait for page to load
        
        # Check if we're logged in by looking for login elements
        print("\n🔍 Checking login status...")
        try:
            # Look for elements that indicate we're not logged in
            login_button = page.locator('text=로그인')
            if login_button.count() > 0:
                print("❌ Not logged in - login button found")
                print("Please run login_watcha.py first to authenticate")
                return
            else:
                print("✅ Appears to be logged in (no login button found)")
        except Exception as e:
            print(f"⚠️ Could not check login status: {e}")
        
        # Scroll to load all content
        print("\nScrolling page...")
        browser_manager._scroll_to_end(page)
        time.sleep(3)
        
        # Test NEW XPath selectors
        print("\n" + "="*80)
        print("Testing NEW XPath selectors for movie info:")
        print("="*80)
        
        # Store extracted data for summary
        extracted_data = {}
        
        for key, xpath in NEW_XPATHS.items():
            if key.endswith('_template'):
                continue  # Skip template selectors for now
                
            print(f"\n--- {key.upper()} ---")
            print(f"XPath: {xpath}")
            
            try:
                if key == 'n_rating':
                    # For n_rating, we need to get the second occurrence (index=1)
                    elements = page.locator(f'xpath={xpath}')
                    count = elements.count()
                    print(f"Elements found: {count}")
                    if count > 1:
                        text = elements.nth(1).inner_text()
                        print(f"  → text (index 1): {text}")
                        extracted_data[key] = text
                    elif count == 1:
                        text = elements.first.inner_text()
                        print(f"  → text (only one): {text}")
                        extracted_data[key] = text
                    else:
                        print("  → No elements found")
                        extracted_data[key] = None
                else:
                    element = page.locator(f'xpath={xpath}')
                    count = element.count()
                    print(f"Elements found: {count}")
                    if count > 0:
                        text = element.inner_text()
                        print(f"  → text: {text[:200]}..." if len(text) > 200 else f"  → text: {text}")
                        extracted_data[key] = text
                    else:
                        print("  → No elements found")
                        extracted_data[key] = None
            except Exception as e:
                print(f"  ✗ Error: {e}")
                extracted_data[key] = None
        
        # Special debugging for problematic selectors
        print("\n" + "="*80)
        print("SPECIAL DEBUGGING FOR PROBLEMATIC SELECTORS:")
        print("="*80)
        
        # Test synopsis with different approaches
        print("\n--- SYNOPSIS DEBUGGING ---")
        synopsis_xpaths = [
            '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[2]/p',
            '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[3]/p',
            '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[1]/p',
            '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/div[2]/p',
            '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/div[3]/p',
        ]
        
        for i, xpath in enumerate(synopsis_xpaths, 1):
            print(f"\nSynopsis Test {i}: {xpath}")
            try:
                element = page.locator(f'xpath={xpath}')
                count = element.count()
                print(f"  Elements found: {count}")
                if count > 0:
                    text = element.inner_text()
                    print(f"  → text: {text[:100]}..." if len(text) > 100 else f"  → text: {text}")
                    if text and text.strip():
                        extracted_data['movie_synopsis'] = text
                        break
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        # Test rating with different approaches
        print("\n--- RATING DEBUGGING ---")
        rating_xpaths = [
            '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[1]/div[2]/div/div[1]',
            '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[1]/div[2]/div/div[2]',
            '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[1]/div[1]/div/div[1]',
            '/html/body/main/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[1]/div[1]/div/div[2]',
        ]
        
        for i, xpath in enumerate(rating_xpaths, 1):
            print(f"\nRating Test {i}: {xpath}")
            try:
                element = page.locator(f'xpath={xpath}')
                count = element.count()
                print(f"  Elements found: {count}")
                if count > 0:
                    text = element.inner_text()
                    print(f"  → text: {text}")
                    if text and text.strip():
                        if i == 1:
                            extracted_data['movie_avg_rating'] = text
                        elif i == 2:
                            extracted_data['movie_n_rating'] = text
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        # Try to find rating elements by text content
        print("\n--- RATING BY TEXT CONTENT ---")
        try:
            # Look for elements containing rating numbers
            rating_elements = page.locator('text=/\\d+\\.\\d+/')
            count = rating_elements.count()
            print(f"Elements with rating pattern found: {count}")
            for i in range(min(count, 3)):
                try:
                    text = rating_elements.nth(i).inner_text()
                    print(f"  Rating {i+1}: {text}")
                except Exception:
                    pass
            
            # Look for elements containing "평균" text
            avg_rating_elements = page.locator('text=/평균/')
            avg_count = avg_rating_elements.count()
            print(f"Elements with '평균' text found: {avg_count}")
            for i in range(min(avg_count, 3)):
                try:
                    text = avg_rating_elements.nth(i).inner_text()
                    print(f"  Average rating {i+1}: {text}")
                    
                    # Parse "평균 3.8(1,358명)" format
                    if "평균" in text and "(" in text and ")" in text:
                        # Extract rating number
                        import re
                        rating_match = re.search(r'평균\s+(\d+\.\d+)', text)
                        if rating_match:
                            avg_rating = rating_match.group(1)
                            print(f"    → Extracted avg rating: {avg_rating}")
                            extracted_data['movie_avg_rating'] = avg_rating
                        
                        # Extract rating count
                        count_match = re.search(r'\((\d+(?:,\d+)*)명\)', text)
                        if count_match:
                            rating_count = count_match.group(1).replace(',', '')
                            print(f"    → Extracted rating count: {rating_count}")
                            extracted_data['movie_n_rating'] = rating_count
                        break
                except Exception:
                    pass
        except Exception as e:
            print(f"Error searching for rating pattern: {e}")
        
        # Try to find synopsis by text content
        print("\n--- SYNOPSIS BY TEXT CONTENT ---")
        try:
            # Look for long text elements that might be synopsis
            long_text_elements = page.locator('p')
            count = long_text_elements.count()
            print(f"P elements found: {count}")
            for i in range(min(count, 5)):
                try:
                    text = long_text_elements.nth(i).inner_text()
                    if len(text) > 50:  # Look for long text
                        print(f"  Long text {i+1}: {text[:100]}...")
                        if not extracted_data.get('movie_synopsis'):
                            extracted_data['movie_synopsis'] = text
                except Exception:
                    pass
        except Exception as e:
            print(f"Error searching for synopsis: {e}")
        
        # Test cast and crew selectors (NEW)
        print("\n" + "="*80)
        print("Testing cast and crew selectors:")
        print("="*80)
        
        # Test first cast member
        name_xpath = NEW_XPATHS['cast_name_template'].format(i=1)
        role_xpath = NEW_XPATHS['cast_role_template'].format(i=1)
        
        print("\n--- CAST NAME ---")
        print(f"XPath: {name_xpath}")
        try:
            element = page.locator(f'xpath={name_xpath}')
            count = element.count()
            print(f"Elements found: {count}")
            if count > 0:
                text = element.inner_text()
                print(f"  → text: {text}")
            else:
                print("  → No elements found")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        print("\n--- CAST ROLE ---")
        print(f"XPath: {role_xpath}")
        try:
            element = page.locator(f'xpath={role_xpath}')
            count = element.count()
            print(f"Elements found: {count}")
            if count > 0:
                text = element.inner_text()
                print(f"  → text: {text}")
            else:
                print("  → No elements found")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Test multiple cast members (NEW)
        print("\n--- Testing multiple cast members ---")
        cast_list = []
        for i in range(1, 6):  # Test first 5 cast members
            name_xpath = NEW_XPATHS['cast_name_template'].format(i=i)
            role_xpath = NEW_XPATHS['cast_role_template'].format(i=i)
            
            try:
                name_elem = page.locator(f'xpath={name_xpath}')
                role_elem = page.locator(f'xpath={role_xpath}')
                
                name_count = name_elem.count()
                role_count = role_elem.count()
                
                if name_count > 0 and role_count > 0:
                    name = name_elem.inner_text()
                    role = role_elem.inner_text()
                    print(f"  Cast {i}: {name} - {role}")
                    cast_list.append((name, role))
                else:
                    print(f"  Cast {i}: Not found (name: {name_count}, role: {role_count})")
                    break
            except Exception as e:
                print(f"  Cast {i}: Error - {e}")
                break
        
        extracted_data['cast_production'] = cast_list
        
        # Parse extracted data using the same logic as the scraper
        print("\n" + "="*80)
        print("PARSING EXTRACTED DATA:")
        print("="*80)
        
        # Parse basic info (year, genre, country)
        basic_info_text = extracted_data.get('movie_basic_info', '')
        print(f"\n📅 BASIC INFO RAW: {basic_info_text}")
        year, genre, country = None, None, None
        if basic_info_text:
            # Split by dots (·)
            items = basic_info_text.split('·')
            items = [item.strip() for item in items if item.strip()]
            print(f"  → Parsed items: {items}")
            if len(items) >= 3:
                year = items[0]
                genre = items[1]
                country = items[2]
                print(f"  → Year: {year}")
                print(f"  → Genre: {genre}")
                print(f"  → Country: {country}")
        
        # Parse additional info (runtime, age)
        additional_info_text = extracted_data.get('movie_additional_info', '')
        print(f"\n⏱️ ADDITIONAL INFO RAW: {additional_info_text}")
        runtime, age = None, None
        if additional_info_text:
            items = additional_info_text.split('·')
            items = [item.strip() for item in items if item.strip()]
            print(f"  → Parsed items: {items}")
            if len(items) >= 1:
                runtime = items[0]
                print(f"  → Runtime: {runtime}")
                # Try to parse as minutes
                try:
                    runtime_num = int(runtime)
                    print(f"  → Runtime (minutes): {runtime_num}")
                except ValueError:
                    print(f"  → Runtime (text): {runtime}")
            if len(items) >= 2:
                age = items[1]
                print(f"  → Age rating: {age}")
        
        # Parse cast info
        print("\n🎭 CAST INFO:")
        if cast_list:
            print(f"  → Found {len(cast_list)} cast members:")
            for i, (name, role) in enumerate(cast_list, 1):
                print(f"    {i}. {name} - {role}")
        else:
            print("  → No cast members found")
        
        # Show processed data as it would appear in .txt file
        print("\n" + "="*80)
        print("PROCESSED DATA (as it would appear in .txt file):")
        print("="*80)
        
        # Get other data
        title = extracted_data.get('movie_title', '')
        synopsis = extracted_data.get('movie_synopsis', '')
        avg_rating = extracted_data.get('movie_avg_rating', '')
        n_rating = extracted_data.get('movie_n_rating', '')
        n_comments = extracted_data.get('movie_n_comments', '')
        
        # Format cast list as it appears in the file
        cast_str = str(cast_list) if cast_list else '[]'
        
        # Create the line as it would appear in the .txt file
        txt_line = f"{movie_id}/{title}/{year}/{genre}/{country}/{runtime}/{age}/{cast_str}/{synopsis}/{avg_rating}/{n_rating}/{n_comments}"
        
        print("\n📄 TXT FILE FORMAT:")
        print(f"Movie ID: {movie_id}")
        print(f"Title: {title}")
        print(f"Year: {year}")
        print(f"Genre: {genre}")
        print(f"Country: {country}")
        print(f"Runtime: {runtime}")
        print(f"Age: {age}")
        print(f"Cast: {cast_str}")
        print(f"Synopsis: {synopsis[:100]}..." if synopsis and len(synopsis) > 100 else f"Synopsis: {synopsis}")
        print(f"Avg Rating: {avg_rating}")
        print(f"N Rating: {n_rating}")
        print(f"N Comments: {n_comments}")
        
        print("\n📄 FULL TXT LINE:")
        print(txt_line)
        
        # Display final extracted data summary
        print("\n" + "="*80)
        print("FINAL EXTRACTED DATA SUMMARY:")
        print("="*80)
        
        print(f"\n📽️  MOVIE TITLE: {extracted_data.get('movie_title', 'Not found')}")
        print(f"📅  BASIC INFO: {extracted_data.get('movie_basic_info', 'Not found')}")
        print(f"⏱️  ADDITIONAL INFO: {extracted_data.get('movie_additional_info', 'Not found')}")
        print(f"📝  SYNOPSIS: {extracted_data.get('movie_synopsis', 'Not found')[:100]}..." if extracted_data.get('movie_synopsis') and len(extracted_data.get('movie_synopsis', '')) > 100 else f"📝  SYNOPSIS: {extracted_data.get('movie_synopsis', 'Not found')}")
        print(f"⭐  AVERAGE RATING: {extracted_data.get('movie_avg_rating', 'Not found')}")
        print(f"👥  NUMBER OF RATINGS: {extracted_data.get('movie_n_rating', 'Not found')}")
        print(f"💬  NUMBER OF COMMENTS: {extracted_data.get('movie_n_comments', 'Not found')}")
        
        if extracted_data.get('cast_production'):
            print(f"\n🎭  CAST & CREW ({len(extracted_data['cast_production'])} members):")
            for i, (name, role) in enumerate(extracted_data['cast_production'], 1):
                print(f"    {i}. {name} - {role}")
        else:
            print("\n🎭  CAST & CREW: Not found")
        
        print("\n" + "="*80)
        print("Testing Complete!")
        print("="*80)
        print("\nPress Enter to close...")
        input()

if __name__ == "__main__":
    debug_movie_info()