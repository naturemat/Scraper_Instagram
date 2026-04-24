import asyncio
import time
import logging
import random
from dotenv import load_dotenv
from core.scheduler import ScraperScheduler
from exporters.export import (
    JSONExporter,
    CSVExporter,
    XLSXExporter,
    PsychologyCSVExporter,
    PostsJSONExporter,
)
from ai.summarizer import AISummarizer
from ai.psychology_analyzer import PsychologyAnalyzer
from extractors.posts import PostExtractor
from extractors.comments import CommentExtractor
from debug_utils import (
    setup_debug_logging, 
    validate_session_cookie,
    get_cookie_dict,
    check_requirements,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Setup debug logging
debug_logger = setup_debug_logging(logging.DEBUG)
logger = logging.getLogger(__name__)


async def scrape_root_target_posts(
    client, root_target: str, max_posts: int = 10, max_comments: int = 0
) -> list[dict]:
    """Scrape only the root target's posts using POST method"""
    debug_logger.info(f"=== Starting root target post scrape for {root_target} ===")

    if not client or not client.has_session:
        debug_logger.error("No valid session available for post scraping")
        return []

    try:
        post_extractor = PostExtractor(client=client)
        debug_logger.info(f"Created PostExtractor for {root_target}")

        posts = await post_extractor.run_posts(root_target, max_pages=3, max_posts=max_posts)
        
        # Add comments if requested
        if max_comments > 0 and posts:
            debug_logger.info(f"Adding comments to root posts (max_comments={max_comments})")
            comment_extractor = CommentExtractor(client=client)
            posts = await comment_extractor.add_comments_to_posts(posts, max_comments)
        
        debug_logger.info(f"Scraped {len(posts)} posts for {root_target}")
        return posts

    except Exception as e:
        debug_logger.error(f"Error scraping root target posts: {e}", exc_info=True)
        return []


async def scrape_posts_for_followers(client, followers: list, max_posts: int = 10, max_comments: int = 0, max_followers_to_process: int = 10) -> dict:
    """Scrape posts for a list of followers"""
    posts_by_user = {}
    
    # Extract usernames from followers
    follower_usernames = []
    for follower in followers:
        if isinstance(follower, dict):
            username = follower.get('username') or follower.get('profile', {}).get('username')
            if username:
                follower_usernames.append(username)
        elif isinstance(follower, str):
            follower_usernames.append(follower)
    
    # Limit to max_followers_to_process
    follower_usernames = follower_usernames[:max_followers_to_process]
    logger.info(f"Scraping posts for {len(follower_usernames)} followers (max_posts={max_posts}, max_comments={max_comments})")
    
    post_extractor = PostExtractor(client=client)
    comment_extractor = CommentExtractor(client=client) if max_comments > 0 else None
    
    for idx, username in enumerate(follower_usernames, 1):
        try:
            logger.info(f"[{idx}/{len(follower_usernames)}] Scraping posts for: {username}")
            posts = await post_extractor.run_posts(username, max_pages=2, max_posts=max_posts)
            
            # Add comments if requested
            if max_comments > 0 and posts and comment_extractor:
                logger.debug(f"Adding {max_comments} comments to {len(posts)} posts for {username}")
                posts = await comment_extractor.add_comments_to_posts(posts, max_comments)
            
            posts_by_user[username] = posts
            if posts:
                total_comments = sum(len(p.get('comments_data', [])) for p in posts)
                logger.info(f"   Got {len(posts)} posts with {total_comments} comments")
            else:
                logger.info(f"   No posts found")
        except Exception as e:
            logger.error(f"   Error for {username}: {e}")
            posts_by_user[username] = []
        
        # Delay between users
        if idx < len(follower_usernames):
            await asyncio.sleep(random.uniform(1.5, 3.0))
    
    return posts_by_user


def save_checkpoint_with_posts(results: dict, root_target: str):
    """Save checkpoint including posts"""
    try:
        import json
        from pathlib import Path
        
        checkpoint_dir = Path("checkpoints")
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint_file = checkpoint_dir / f"{root_target}_checkpoint.json"
        
        # Prepare checkpoint data
        checkpoint_data = {
            "root_target": root_target,
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "followers_count": len(results.get("followers", [])),
            "posts_count": sum(len(posts) for posts in results.get("posts_by_user", {}).values()),
            "comments_count": sum(
                sum(len(post.get("comments_data", [])) for post in posts)
                for posts in results.get("posts_by_user", {}).values()
            ),
            "followers": results.get("followers", []),
            "posts_by_user": results.get("posts_by_user", {}),
            "root": results.get("root", {}),
            "psychology_profiles": results.get("psychology_profiles", [])
        }
        
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Checkpoint saved with posts to: {checkpoint_file}")
        return str(checkpoint_file)
    except Exception as e:
        logger.error(f"Failed to save checkpoint with posts: {e}")
        return None


async def main():
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Instagram Deep Follower Scraper")
    logger.info("=" * 60)

    # Load configuration from environment
    import os

    root_target = os.getenv("IG_ROOT_TARGET", "default_user")
    max_followers = int(os.getenv("IG_MAX_FOLLOWERS", "10"))
    max_posts = int(os.getenv("IG_MAX_POSTS", "5"))
    max_comments = int(os.getenv("IG_MAX_COMMENTS", "0"))

    logger.info(f"Configuration: root={root_target}, max_followers={max_followers}, max_posts={max_posts}, max_comments={max_comments}")

    # Initialize components
    scheduler = ScraperScheduler()
    summarizer = AISummarizer()

    # --- Debugging Setup ---
    debug_logger.info("=== DEBUG MODE ENABLED ===")

    # Check requirements
    requirements = check_requirements()
    missing_reqs = [pkg for pkg, installed in requirements.items() if not installed]
    if missing_reqs:
        debug_logger.warning(f"Missing requirements: {missing_reqs}")
    else:
        debug_logger.info("All requirements satisfied")

    # Validate session
    session_id = os.getenv("IG_SESSION_ID", "")
    cookie_valid = validate_session_cookie(session_id)
    if cookie_valid:
        debug_logger.info("Session cookie validation: PASSED")
    else:
        debug_logger.warning("Session cookie validation: FAILED - Check IG_SESSION_ID in .env")

    # --- Deep Scraper - Get followers (with close_client=False) ---
    results = {}
    try:
        if scheduler and max_followers > 0:
            logger.info(f"Target: {root_target} | Max followers: {max_followers}")
            logger.info("-" * 60)

            results = await scheduler.run_deep(
                root_username=root_target,
                max_followers=max_followers,
                summarizer=summarizer,
                close_client=False,  # IMPORTANT: Do not close client
            )
            
            # Limit followers to max_followers
            if results.get("followers"):
                results["followers"] = results["followers"][:max_followers]
            
            logger.info(f"Deep scraper completed: {len(results.get('followers', []))} followers found")
    except Exception as e:
        logger.error(f"Error in deep scraper: {e}")
        results = {"followers": [], "root": {"status": "error"}}

    # Get client from scheduler (still open)
    client = scheduler.client if scheduler else None

    # --- Root Target Posts ---
    root_posts = []
    if client and client.has_session:
        logger.info("-" * 60)
        logger.info(f"Scraping root target posts for: {root_target}")
        root_posts = await scrape_root_target_posts(client, root_target, max_posts=max_posts, max_comments=max_comments)
        
        if root_posts:
            logger.info(f"Root posts fetched: {len(root_posts)} posts")
            results["root_posts"] = root_posts
            if results.get("root"):
                results["root"]["posts"] = root_posts
        else:
            logger.warning("No root posts fetched - check if account is public")

    # --- Followers Posts ---
    posts_by_user = {}
    if client and client.has_session and results.get("followers") and max_posts > 0:
        logger.info("-" * 60)
        logger.info(f"Scraping posts for followers")
        
        posts_by_user = await scrape_posts_for_followers(
            client=client,
            followers=results.get("followers", []),
            max_posts=max_posts,
            max_comments=max_comments,
            max_followers_to_process=max_followers
        )
        
        results["posts_by_user"] = posts_by_user
        
        total_posts = sum(len(posts) for posts in posts_by_user.values())
        total_comments = sum(
            sum(len(post.get("comments_data", [])) for post in posts)
            for posts in posts_by_user.values()
        )
        users_with_posts = sum(1 for posts in posts_by_user.values() if posts)
        
        logger.info(f"Post scraping completed:")
        logger.info(f"   - Total posts: {total_posts}")
        logger.info(f"   - Total comments: {total_comments}")
        logger.info(f"   - Users with posts: {users_with_posts}/{len(posts_by_user)}")

        # Export posts to JSON
        if total_posts > 0:
            all_posts = []
            for posts in posts_by_user.values():
                all_posts.extend(posts)
                
            posts_exporter = PostsJSONExporter()
            posts_exporter.export(
                {
                    "username": root_target,
                    "posts": all_posts,
                    "posts_by_user": posts_by_user,
                }
            )
            logger.info(f"Posts exported to output/posts.json")

    # --- Psychology Analysis ---
    try:
        logger.info("-" * 60)
        logger.info("Running psychology analysis on followers")

        psychology_analyzer = PsychologyAnalyzer()
        psychology_results = []

        if psychology_analyzer.is_available():
            logger.info("Psychology analyzer: ENABLED")

            followers = results.get("followers", [])[:max_followers]
            logger.info(f"Analyzing {len(followers)} followers")

            for follower in followers:
                profile = follower.get("profile", {})
                username = profile.get("username", "")

                try:
                    logger.info(f"Analyzing: {username}")
                    posts = posts_by_user.get(username, [])
                    
                    analysis = await psychology_analyzer.analyze_follower(follower, posts)

                    if analysis:
                        psychology_results.append(analysis)
                except Exception as e:
                    logger.warning(f"Failed to analyze {username}: {e}")

            results["psychology_profiles"] = psychology_results
            logger.info(f"Generated {len(psychology_results)} psychology profiles")
        else:
            logger.info("Psychology analyzer: DISABLED (no API key)")
    except Exception as e:
        logger.error(f"Error in psychology analysis: {e}")

    # --- Save Checkpoint with Posts ---
    try:
        checkpoint_file = save_checkpoint_with_posts(results, root_target)
        if checkpoint_file:
            logger.info(f"Checkpoint with posts saved to: {checkpoint_file}")
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}")

    # --- Export results ---
    try:
        logger.info("-" * 60)
        logger.info("Exporting results")

        json_exporter = JSONExporter()
        json_exporter.export(results)
        
        csv_exporter = CSVExporter()
        csv_exporter.export(results)
        
        xlsx_exporter = XLSXExporter()
        xlsx_exporter.export(results)

        if results.get("psychology_profiles"):
            psych_exporter = PsychologyCSVExporter()
            psych_exporter.export(results)

        logger.info("All exports completed")
    except Exception as e:
        logger.error(f"Error exporting results: {e}")

    # --- Summary ---
    try:
        elapsed = time.time() - start_time
        follower_count = len(results.get("followers", []))
        root_status = results.get("root", {}).get("status", "unknown")
        posts_count = sum(len(posts) for posts in results.get("posts_by_user", {}).values())
        comments_count = sum(
            sum(len(post.get("comments_data", [])) for post in posts)
            for posts in results.get("posts_by_user", {}).values()
        )
        root_posts_count = len(results.get("root_posts", []))

        logger.info("=" * 60)
        logger.info("SCRAPING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"  Root profile: {root_target} ({root_status})")
        logger.info(f"  Root posts: {root_posts_count}")
        logger.info(f"  Followers scraped: {follower_count}")
        logger.info(f"  Posts scraped from followers: {posts_count}")
        logger.info(f"  Comments scraped: {comments_count}")
        logger.info(f"  Time elapsed: {elapsed:.1f}s ({elapsed / 60:.1f} min)")
        logger.info(f"  Output files:")
        logger.info(f"    - output/results.json")
        logger.info(f"    - output/results.csv")
        logger.info(f"    - output/results.xlsx")
        if results.get("psychology_profiles"):
            logger.info(f"    - output/psychology_profiles.csv")
        if posts_count > 0 or root_posts_count > 0:
            logger.info(f"    - output/posts.json")
        logger.info(f"    - checkpoints/{root_target}_checkpoint.json")
        logger.info("=" * 60)
        
        # Show sample posts from root
        if root_posts_count > 0:
            logger.info("Sample root posts:")
            for i, post in enumerate(root_posts[:3], 1):
                logger.info(f"  {i}. {post.get('url')} (Likes: {post.get('likes')})")
        
        # Show sample posts from followers
        if posts_count > 0:
            logger.info("Sample follower posts:")
            sample_shown = 0
            for username, posts in results.get("posts_by_user", {}).items():
                if posts and sample_shown < 5:
                    comments_count_sample = len(posts[0].get('comments_data', []))
                    logger.info(f"  @{username}: {posts[0].get('url')} (Likes: {posts[0].get('likes')}, Comments: {comments_count_sample})")
                    sample_shown += 1
                    
    except Exception as e:
        logger.error(f"Error in summary: {e}")

    # Close client at the very end
    if client:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())