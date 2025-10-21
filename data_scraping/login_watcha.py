"""Helper script to login to Watcha and save authentication state."""

import time
from common import Config, BrowserManager, get_logger
from playwright.sync_api import sync_playwright


def main():
    """
    Open Watcha login page and save authentication after manual login.
    
    Instructions:
    1. This script will open a browser window
    2. Manually login to Watcha
    3. After successful login, press Enter in the terminal
    4. Your authentication session will be saved
    """
    config = Config()
    logger = get_logger(__name__, level=config.LOG_LEVEL, log_file=config.LOG_FILE)
    browser_manager = BrowserManager(config)
    
    logger.info("Starting Watcha login process...")
    logger.info("A browser window will open. Please login manually.")
    
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)  # Force visible browser
        context = browser.new_context(user_agent=config.USER_AGENT)
        page = context.new_page()
        
        try:
            # Open Watcha homepage
            logger.info(f"Opening {config.WATCHA_BASE_URL}")
            page.goto(config.WATCHA_BASE_URL)
            
            print("\n" + "="*60)
            print("WATCHA LOGIN")
            print("="*60)
            print("\n1. Please login to Watcha in the browser window")
            print("2. After successful login, press Enter here")
            print("\nWaiting for your login...")
            
            # Wait for user to login
            input("\nPress Enter after you've logged in successfully: ")
            
            # Save authentication state
            logger.info("Saving authentication state...")
            browser_manager.config = config
            browser_manager.save_auth_state(context)
            
            print("\n✓ Authentication saved successfully!")
            print(f"✓ Session saved to: {config.AUTH_STATE_FILE}")
            print("\nYou can now run the scraping scripts and they will use this login session.")
            
        except Exception as e:
            logger.error(f"Failed to save authentication: {e}")
            print(f"\n✗ Error: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()

