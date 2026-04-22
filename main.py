import asyncio
import time
import logging
from dotenv import load_dotenv
from core.scheduler import ScraperScheduler
from exporters.export import (
    JSONExporter,
    CSVExporter,
   #  XLSXExporter,
    PsychologyCSVExporter,
    PostsJSONExporter,
)
from ai.summarizer import AISummarizer
from ai.psychology_analyzer import PsychologyAnalyzer
from extractors.posts import PostExtractor

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Instagram Deep Follower Scraper")
    logger.info("=" * 60)

    # --- Configuration ---
    root_target = "thiss.mate"
    max_followers = 10
    max_posts = 10

    # Initialize components
    scheduler = ScraperScheduler(max_concurrent=3)
    summarizer = AISummarizer()

    if summarizer.is_available():
        logger.info("AI summarizer: ENABLED")
    else:
        logger.info("AI summarizer: DISABLED (no API key)")

    if scheduler.client.has_session:
        logger.info("Session cookie: LOADED")
    else:
        logger.warning("Session cookie: MISSING — follower list extraction unavailable")

    # --- Run the deep scraper ---
    logger.info(f"Target: {root_target} | Max followers: {max_followers}")
    logger.info("-" * 60)

    results = await scheduler.run_deep(
        root_username=root_target,
        max_followers=max_followers,
        summarizer=summarizer,
    )

    # --- Post Scraping ---
    if max_posts > 0 and scheduler.client.has_session:
        logger.info("-" * 60)
        logger.info(f"Scraping posts for {root_target} (max_posts={max_posts})...")

        try:
            user_id = await PostExtractor.resolve_user_id(scheduler.client, root_target)
            if user_id:
                posts = await PostExtractor.paginate_posts(
                    scheduler.client,
                    user_id=user_id,
                    target_count=max_posts,
                )
                results["posts"] = posts
                logger.info(f"Scraped {len(posts)} posts")

                posts_exporter = PostsJSONExporter()
                posts_exporter.export({"username": root_target, "posts": posts})
                logger.info("Posts exported to output/posts.json")
            else:
                logger.warning(f"Could not resolve user_id for {root_target}")
        except Exception as e:
            logger.error(f"Error scraping posts: {e}")

    # --- Psychology Analysis ---
    logger.info("-" * 60)
    logger.info("Running psychology analysis on followers...")

    psychology_analyzer = PsychologyAnalyzer()

    psychology_results = []

    if psychology_analyzer.is_available():
        logger.info("Psychology analyzer: ENABLED")

        followers = results.get("followers", [])
        posts_data = results.get("posts", [])
        logger.info(f"Analyzing {len(followers)} followers for psychology profiles")

        analyze_count = min(len(followers), max_followers)
        for i in range(analyze_count):
            follower = followers[i]
            profile = follower.get("profile", {})

            try:
                logger.info(f"Analyzing: {profile.get('username')}")
                analysis = await psychology_analyzer.analyze_follower(
                    follower, posts_data
                )

                if analysis:
                    psychology_results.append(analysis)
                    logger.info(
                        f"Profile: {profile.get('username')} - {analysis.get('resumen', '')[:50]}"
                    )
            except Exception as e:
                logger.warning(f"Failed to analyze {profile.get('username')}: {e}")

        results["psychology_profiles"] = psychology_results
        logger.info(f"Generated {len(psychology_results)} psychology profiles")
    else:
        logger.info("Psychology analyzer: DISABLED (no API key)")

    # --- Export results ---
    logger.info("-" * 60)
    logger.info("Exporting results...")

    json_exporter = JSONExporter()
    json_exporter.export(results)

    csv_exporter = CSVExporter()
    csv_exporter.export(results)

    xlsx_exporter = XLSXExporter()
    xlsx_exporter.export(results)

    if psychology_results:
        psych_exporter = PsychologyCSVExporter()
        psych_exporter.export(results)

    # --- Summary ---
    elapsed = time.time() - start_time
    follower_count = len(results.get("followers", []))
    root_status = results.get("root", {}).get("status", "unknown")

    logger.info("=" * 60)
    logger.info("SCRAPING COMPLETE")
    logger.info(f"  Root profile: {root_target} ({root_status})")
    logger.info(f"  Followers scraped: {follower_count}")
    logger.info(f"  Time elapsed: {elapsed:.1f}s ({elapsed / 60:.1f} min)")
    logger.info(f"  Output files:")
    logger.info(f"    - output/results.json")
    logger.info(f"    - output/results.csv")
    logger.info(f"    - output/results.xlsx")
    if psychology_results:
        logger.info(f"    - output/psychology_profiles.csv")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
