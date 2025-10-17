"""Master script to run all scraping tasks in sequence."""

import argparse
from typing import Optional

from common import Config, get_logger
from run_movie_info import main as run_movie_info
from run_movie_comments import main as run_movie_comments
from run_custom_rating import main as run_custom_rating


def main(
    limit: Optional[int] = None,
    delay: float = 2.0,
    skip_movie_info: bool = False,
    skip_comments: bool = False,
    skip_ratings: bool = False
) -> None:
    """
    Run all scraping tasks in sequence.
    
    Args:
        limit: Maximum number of items to scrape per task
        delay: Delay between requests in seconds
        skip_movie_info: Skip movie info scraping
        skip_comments: Skip movie comments scraping
        skip_ratings: Skip custom ratings scraping
    """
    config = Config()
    logger = get_logger(__name__, level=config.LOG_LEVEL, log_file=config.LOG_FILE)
    
    logger.info("=" * 60)
    logger.info("Starting full scraping pipeline")
    logger.info("=" * 60)
    
    # Step 1: Scrape movie info
    if not skip_movie_info:
        logger.info("\n[STEP 1/3] Scraping movie information...")
        try:
            run_movie_info(limit=limit, delay=delay, config=config)
        except Exception as e:
            logger.error(f"Movie info scraping failed: {e}")
    else:
        logger.info("\n[STEP 1/3] Skipping movie info scraping")
    
    # Step 2: Scrape movie comments
    if not skip_comments:
        logger.info("\n[STEP 2/3] Scraping movie comments...")
        try:
            run_movie_comments(limit=limit, delay=delay, config=config)
        except Exception as e:
            logger.error(f"Movie comments scraping failed: {e}")
    else:
        logger.info("\n[STEP 2/3] Skipping movie comments scraping")
    
    # Step 3: Scrape custom ratings
    if not skip_ratings:
        logger.info("\n[STEP 3/3] Scraping custom user ratings...")
        try:
            run_custom_rating(limit=limit, delay=delay, config=config)
        except Exception as e:
            logger.error(f"Custom rating scraping failed: {e}")
    else:
        logger.info("\n[STEP 3/3] Skipping custom rating scraping")
    
    logger.info("\n" + "=" * 60)
    logger.info("Scraping pipeline complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all scraping tasks")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of items to scrape per task"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds"
    )
    parser.add_argument(
        "--skip-movie-info",
        action="store_true",
        help="Skip movie info scraping"
    )
    parser.add_argument(
        "--skip-comments",
        action="store_true",
        help="Skip movie comments scraping"
    )
    parser.add_argument(
        "--skip-ratings",
        action="store_true",
        help="Skip custom ratings scraping"
    )
    
    args = parser.parse_args()
    
    main(
        limit=args.limit,
        delay=args.delay,
        skip_movie_info=args.skip_movie_info,
        skip_comments=args.skip_comments,
        skip_ratings=args.skip_ratings
    )

