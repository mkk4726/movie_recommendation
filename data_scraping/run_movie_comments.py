"""Script to scrape movie comments."""

import time
import argparse
from typing import Optional

from common import Config, DataStorage, get_logger
from scrapers import MovieCommentsScraper


def main(
    limit: Optional[int] = None,
    delay: float = 2.0,
    config: Optional[Config] = None
) -> None:
    """
    Main function to scrape movie comments.
    
    Args:
        limit: Maximum number of movies to scrape comments for (None for all)
        delay: Delay between requests in seconds
        config: Configuration object
    """
    if config is None:
        config = Config()
    
    logger = get_logger(__name__, level=config.LOG_LEVEL, log_file=config.LOG_FILE)
    storage = DataStorage(config)
    scraper = MovieCommentsScraper(config)
    
    # Get movie IDs that need comment scraping
    movie_ids = storage.get_missing_comment_movie_ids()
    
    if not movie_ids:
        logger.info("No movies need comment scraping")
        return
    
    # Limit if specified
    if limit:
        movie_ids = movie_ids[:limit]
    
    logger.info(f"Starting to scrape comments for {len(movie_ids)} movies")
    
    successful = 0
    failed = 0
    total_comments = 0
    
    for i, movie_id in enumerate(movie_ids, 1):
        try:
            logger.info(f"[{i}/{len(movie_ids)}] Scraping comments for movie: {movie_id}")
            
            comments = scraper.scrape(movie_id)
            
            # Batch save all comments at once (optimized for performance)
            storage.save_movie_comments_batch(movie_id, comments)
            
            total_comments += len(comments)
            successful += 1
            logger.info(f"✓ Successfully scraped {len(comments)} comments")
            
        except Exception as e:
            failed += 1
            logger.error(f"✗ Failed to scrape comments for {movie_id}: {e}")
        
        # Delay between requests
        if i < len(movie_ids):
            time.sleep(delay)
    
    logger.info(f"Scraping complete. Movies: {successful}, Failed: {failed}, Total comments: {total_comments}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape movie comments from Watcha")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of movies to scrape comments for"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds"
    )
    
    args = parser.parse_args()
    
    main(limit=args.limit, delay=args.delay)

