"""Script to scrape custom user ratings.

Note: XPath selectors updated on 2025-10-21 to match new Watcha page structure.
"""

import time
import argparse
from typing import Optional

from common import Config, DataStorage, get_logger
from scrapers import CustomRatingScraper


def main(
    limit: Optional[int] = None,
    delay: float = 2.0,
    config: Optional[Config] = None
) -> None:
    """
    Main function to scrape custom user ratings.
    
    Args:
        limit: Maximum number of users to scrape ratings for (None for all)
        delay: Delay between requests in seconds
        config: Configuration object
    """
    if config is None:
        config = Config()
    
    logger = get_logger(__name__, level=config.LOG_LEVEL, log_file=config.LOG_FILE)
    storage = DataStorage(config)
    scraper = CustomRatingScraper(config)
    
    # Get custom IDs that need rating scraping
    custom_ids = storage.get_missing_custom_ids()
    
    if not custom_ids:
        logger.info("No users need rating scraping")
        return
    
    # Limit if specified
    if limit:
        custom_ids = custom_ids[:limit]
    
    logger.info(f"Starting to scrape ratings for {len(custom_ids)} users")
    
    successful = 0
    failed = 0
    total_ratings = 0
    
    for i, custom_id in enumerate(custom_ids, 1):
        try:
            logger.info(f"[{i}/{len(custom_ids)}] Scraping ratings for user: {custom_id}")
            
            ratings = scraper.scrape(custom_id)
            
            # Save each rating
            for rating_data in ratings:
                storage.save_custom_rating(custom_id, rating_data)
            
            total_ratings += len(ratings)
            successful += 1
            logger.info(f"✓ Successfully scraped {len(ratings)} ratings")
            
        except Exception as e:
            failed += 1
            logger.error(f"✗ Failed to scrape ratings for {custom_id}: {e}")
        
        # Delay between requests
        if i < len(custom_ids):
            time.sleep(delay)
    
    logger.info(f"Scraping complete. Users: {successful}, Failed: {failed}, Total ratings: {total_ratings}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape custom user ratings from Watcha")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of users to scrape ratings for"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds"
    )
    
    args = parser.parse_args()
    
    main(limit=args.limit, delay=args.delay)

