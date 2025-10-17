"""Script to scrape movie information."""

import time
import argparse
from typing import Optional

from common import Config, DataStorage, get_logger
from scrapers import MovieInfoScraper


def main(
    limit: Optional[int] = None,
    delay: float = 2.0,
    config: Optional[Config] = None
) -> None:
    """
    Main function to scrape movie information.
    
    Args:
        limit: Maximum number of movies to scrape (None for all)
        delay: Delay between requests in seconds
        config: Configuration object
    """
    if config is None:
        config = Config()
    
    logger = get_logger(__name__, level=config.LOG_LEVEL, log_file=config.LOG_FILE)
    storage = DataStorage(config)
    scraper = MovieInfoScraper(config)
    
    # Get movie IDs that need scraping
    movie_ids = storage.get_missing_movie_ids()
    
    if not movie_ids:
        logger.info("No movies need info scraping")
        return
    
    # Limit if specified
    if limit:
        movie_ids = movie_ids[:limit]
    
    logger.info(f"Starting to scrape {len(movie_ids)} movies")
    
    successful = 0
    failed = 0
    
    for i, movie_id in enumerate(movie_ids, 1):
        try:
            logger.info(f"[{i}/{len(movie_ids)}] Scraping movie: {movie_id}")
            
            movie_data = scraper.scrape(movie_id)
            storage.save_movie_info(movie_data)
            
            successful += 1
            logger.info(f"✓ Successfully scraped: {movie_data.get('title')}")
            
        except Exception as e:
            failed += 1
            logger.error(f"✗ Failed to scrape {movie_id}: {e}")
        
        # Delay between requests
        if i < len(movie_ids):
            time.sleep(delay)
    
    logger.info(f"Scraping complete. Success: {successful}, Failed: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape movie information from Watcha")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of movies to scrape"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds"
    )
    
    args = parser.parse_args()
    
    main(limit=args.limit, delay=args.delay)

