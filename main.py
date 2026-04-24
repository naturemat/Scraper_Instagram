import asyncio
import time
import logging
import random
import os
import json
from pathlib import Path
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
from extractors.playwright_comments import PlaywrightCommentExtractor
from debug_utils import (
    setup_debug_logging, 
    validate_session_cookie,
    get_cookie_dict,
    check_requirements,
)

load_dotenv()

# Ensure output directory exists
output_dir = Path("output")
output_dir.mkdir(parents=True, exist_ok=True)

checkpoint_dir = Path("checkpoints")
checkpoint_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

debug_logger = setup_debug_logging(logging.DEBUG)
logger = logging.getLogger(__name__)

# Global variable to store comment extractor for cleanup
comment_extractor_instance = None


async def scrape_root_target_posts(
    client, root_target: str, max_posts: int = 10, max_comments: int = 0, 
    session_id: str = "", csrftoken: str = ""
) -> list[dict]:
    debug_logger.info(f"Starting root target post scrape for {root_target}")

    if not client or not client.has_session:
        debug_logger.error("No valid session available for post scraping")
        return []

    try:
        post_extractor = PostExtractor(client=client)
        debug_logger.info(f"Created PostExtractor for {root_target}")

        posts = await post_extractor.run_posts(root_target, max_pages=3, max_posts=max_posts)
        
        if max_comments > 0 and posts:
            debug_logger.info(f"Adding comments to root posts (max_comments={max_comments})")
            global comment_extractor_instance
            comment_extractor_instance = PlaywrightCommentExtractor(
                session_id=session_id, 
                csrftoken=csrftoken, 
                headless=True
            )
            posts = await comment_extractor_instance.add_comments_to_posts(posts, max_comments)

        debug_logger.info(f"Scraped {len(posts)} posts for {root_target}")
        return posts

    except Exception as e:
        debug_logger.error(f"Error scraping root target posts: {e}", exc_info=True)
        return []


async def scrape_posts_for_followers(
    client, followers: list, max_posts: int = 10, max_comments: int = 0, 
    max_followers_to_process: int = 10, session_id: str = "", csrftoken: str = ""
) -> dict:
    posts_by_user = {}
    
    follower_usernames = []
    for follower in followers:
        if isinstance(follower, dict):
            username = follower.get('username') or follower.get('profile', {}).get('username')
            if username:
                follower_usernames.append(username)
        elif isinstance(follower, str):
            follower_usernames.append(follower)
    
    follower_usernames = follower_usernames[:max_followers_to_process]
    logger.info(f"Scraping posts for {len(follower_usernames)} followers (max_posts={max_posts}, max_comments={max_comments})")
    
    post_extractor = PostExtractor(client=client)
    
    # Initialize Playwright comment extractor if needed
    playwright_extractor = None
    if max_comments > 0:
        global comment_extractor_instance
        if comment_extractor_instance is None:
            comment_extractor_instance = PlaywrightCommentExtractor(
                session_id=session_id, 
                csrftoken=csrftoken, 
                headless=False
            )
        playwright_extractor = comment_extractor_instance
    
    for idx, username in enumerate(follower_usernames, 1):
        try:
            logger.info(f"[{idx}/{len(follower_usernames)}] Scraping posts for: {username}")
            posts = await post_extractor.run_posts(username, max_pages=2, max_posts=max_posts)
            
            if max_comments > 0 and posts and playwright_extractor:
                logger.debug(f"Adding {max_comments} comments to {len(posts)} posts for {username}")
                posts = await playwright_extractor.add_comments_to_posts(posts, max_comments)
            
            posts_by_user[username] = posts
            if posts:
                total_comments = sum(len(p.get('comments_data', [])) for p in posts)
                logger.info(f"Got {len(posts)} posts with {total_comments} comments")
            else:
                logger.info(f"No posts found")
        except Exception as e:
            logger.error(f"Error for {username}: {e}")
            posts_by_user[username] = []
        
        if idx < len(follower_usernames):
            await asyncio.sleep(random.uniform(1.5, 3.0))
    
    return posts_by_user


def save_checkpoint_with_posts(results: dict, root_target: str):
    try:
        checkpoint_file = checkpoint_dir / f"{root_target}_checkpoint.json"
        
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
            "root_posts": results.get("root_posts", []),
            "psychology_profiles": results.get("psychology_profiles", [])
        }
        
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Checkpoint saved: {checkpoint_file}")
        return str(checkpoint_file)
    except Exception as e:
        logger.error(f"Failed to save checkpoint: {e}")
        return None


async def main():
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Instagram Deep Follower Scraper")
    logger.info("=" * 60)

    root_target = os.getenv("IG_ROOT_TARGET", "default_user")
    max_followers = int(os.getenv("IG_MAX_FOLLOWERS", "10"))
    max_posts = int(os.getenv("IG_MAX_POSTS", "5"))
    max_comments = int(os.getenv("IG_MAX_COMMENTS", "0"))
    session_id = os.getenv("IG_SESSION_ID", "")
    csrftoken = os.getenv("IG_CSRFTOKEN", "")

    logger.info(f"Configuration: root={root_target}, max_followers={max_followers}, max_posts={max_posts}, max_comments={max_comments}")

    scheduler = ScraperScheduler()
    summarizer = AISummarizer()

    debug_logger.info("=== DEBUG MODE ENABLED ===")

    requirements = check_requirements()
    missing_reqs = [pkg for pkg, installed in requirements.items() if not installed]
    if missing_reqs:
        debug_logger.warning(f"Missing requirements: {missing_reqs}")
    else:
        debug_logger.info("All requirements satisfied")

    cookie_valid = validate_session_cookie(session_id)
    if cookie_valid:
        debug_logger.info("Session cookie validation: PASSED")
    else:
        debug_logger.warning("Session cookie validation: FAILED")

    results = {}
    try:
        if scheduler and max_followers > 0:
            logger.info(f"Target: {root_target} | Max followers: {max_followers}")
            logger.info("-" * 60)

            results = await scheduler.run_deep(
                root_username=root_target,
                max_followers=max_followers,
                summarizer=summarizer,
                close_client=False,
            )
            
            if results.get("followers"):
                results["followers"] = results["followers"][:max_followers]
            
            logger.info(f"Deep scraper completed: {len(results.get('followers', []))} followers found")
            logger.info(f"Results keys: {list(results.keys())}")
    except Exception as e:
        logger.error(f"Error in deep scraper: {e}", exc_info=True)
        results = {"followers": [], "root": {"status": "error"}}

    client = scheduler.client if scheduler else None

    root_posts = []
    if client and client.has_session:
        logger.info("-" * 60)
        logger.info(f"Scraping root target posts for: {root_target}")
        root_posts = await scrape_root_target_posts(
            client, root_target, 
            max_posts=max_posts, 
            max_comments=max_comments,
            session_id=session_id,
            csrftoken=csrftoken
        )
        
        if root_posts:
            logger.info(f"Root posts fetched: {len(root_posts)} posts")
            results["root_posts"] = root_posts
            if results.get("root"):
                results["root"]["posts"] = root_posts
        else:
            logger.warning("No root posts fetched")

    posts_by_user = {}
    if client and client.has_session and results.get("followers") and max_posts > 0:
        logger.info("-" * 60)
        logger.info(f"Scraping posts for followers")
        
        posts_by_user = await scrape_posts_for_followers(
            client=client,
            followers=results.get("followers", []),
            max_posts=max_posts,
            max_comments=max_comments,
            max_followers_to_process=max_followers,
            session_id=session_id,
            csrftoken=csrftoken
        )
        
        results["posts_by_user"] = posts_by_user
        
        total_posts = sum(len(posts) for posts in posts_by_user.values())
        total_comments = sum(
            sum(len(post.get("comments_data", [])) for post in posts)
            for posts in posts_by_user.values()
        )
        users_with_posts = sum(1 for posts in posts_by_user.values() if posts)
        
        logger.info(f"Post scraping completed:")
        logger.info(f"   Total posts: {total_posts}")
        logger.info(f"   Total comments: {total_comments}")
        logger.info(f"   Users with posts: {users_with_posts}/{len(posts_by_user)}")

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
            logger.info("Psychology analyzer: DISABLED")
    except Exception as e:
        logger.error(f"Error in psychology analysis: {e}")

    try:
        checkpoint_file = save_checkpoint_with_posts(results, root_target)
        if checkpoint_file:
            logger.info(f"Checkpoint saved: {checkpoint_file}")
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}")

    try:
        logger.info("-" * 60)
        logger.info("Exporting results")

        json_exporter = JSONExporter()
        json_exporter.export(results)
        logger.info("JSON export completed - check output/results.json")
        
        csv_exporter = CSVExporter()
        csv_exporter.export(results)
        logger.info("CSV export completed - check output/results.csv")
        
        xlsx_exporter = XLSXExporter()
        xlsx_exporter.export(results)
        logger.info("XLSX export completed - check output/results.xlsx")

        if results.get("psychology_profiles"):
            psych_exporter = PsychologyCSVExporter()
            psych_exporter.export(results)
            logger.info("Psychology CSV export completed")

        logger.info("All exports completed")
        
        output_files = list(output_dir.glob("*"))
        logger.info(f"Files in output directory: {[f.name for f in output_files]}")
        
    except Exception as e:
        logger.error(f"Error exporting results: {e}", exc_info=True)

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
    logger.info("=" * 60)

    # Cleanup
    if client:
        await client.close()
    
    global comment_extractor_instance
    if comment_extractor_instance:
        await comment_extractor_instance.close()
        logger.info("Playwright comment extractor closed")


if __name__ == "__main__":
    asyncio.run(main())