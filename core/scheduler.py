import asyncio
import random
import logging
from client.stealth import StealthClient, SessionExpiredError
from extractors.parser import ProfileExtractor, PostsExtractor
from extractors.followers import FollowerExtractor
from core.checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


class ScraperScheduler:
    def __init__(self, max_concurrent=3):
        self.client = StealthClient()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.checkpoint = CheckpointManager()

    @staticmethod
    def get_random_delay(min_sec=3, max_sec=7):
        return random.uniform(min_sec, max_sec)

    async def _fetch_profile(self, username: str) -> dict:
        """Fetch and parse a single profile's public page."""
        async with self.semaphore:
            delay = self.get_random_delay()
            logger.info(f"[{username}] Waiting {delay:.2f}s before processing...")
            await asyncio.sleep(delay)

            url = f"https://www.instagram.com/{username}/"
            logger.info(f"[{username}] Downloading profile...")
            try:
                response = await self.client.get(url)
                html = response.text

                logger.info(f"[{username}] Extracting profile data...")
                profile_data = ProfileExtractor.extract(html)

                if not profile_data.get("username"):
                    profile_data["username"] = username

                return {
                    "target": username,
                    "profile": profile_data,
                    "html": html,
                    "status": "success",
                }

            except Exception as e:
                logger.error(f"[{username}] Failed to process: {e}")
                return {
                    "target": username,
                    "profile": {"username": username, "is_private": None},
                    "html": "",
                    "status": f"error: {str(e)}",
                }

    async def run_deep(
        self,
        root_username: str,
        max_followers: int = 150,
        summarizer=None,
        close_client: bool = False,
    ) -> dict:
        """Two-phase deep scraping pipeline with checkpoint resume.

        Phase 1: Fetch root profile + paginate followers via GraphQL.
        Phase 2: Visit each follower's profile page to extract metadata.

        Args:
            root_username: Instagram username to scrape
            max_followers: Maximum number of followers to fetch (discover and process)
            summarizer: AI summarizer instance (optional)
            close_client: If True, close client after completion (default False)

        Returns:
            dict with 'root' and 'followers' keys.
        """
        try:
            # Check for existing checkpoint
            existing = self.checkpoint.load(root_username)

            if existing:
                logger.info(f"Resuming from checkpoint for {root_username}")
                root_profile = existing["root_profile"]
                followers_discovered_all = existing["followers_discovered"]
                # Limit discovered followers to max_followers
                followers_discovered = followers_discovered_all[:max_followers]
                followers_completed = existing["followers_completed"]
                followers_data = existing["followers_data"]
                remaining = self.checkpoint.get_remaining(existing)
                # Filter remaining to respect max_followers
                remaining = [f for f in remaining if f in followers_discovered]
            else:
                # === PHASE 1: Root profile + follower enumeration ===
                logger.info(f"=== PHASE 1: Fetching root profile: {root_username} ===")

                root_result = await self._fetch_profile(root_username)
                root_profile = root_result

                if root_result["status"] != "success":
                    logger.error(f"Failed to fetch root profile. Aborting.")
                    return {"root": root_result, "followers": []}

                # Extract user_id for GraphQL
                html = root_result.get("html", "")
                user_id = FollowerExtractor.extract_user_id(html)

                followers_discovered_all = []
                if user_id and self.client.has_session:
                    logger.info(f"User ID: {user_id}. Starting follower pagination...")
                    followers_discovered_all = await FollowerExtractor.paginate_followers(
                        client=self.client,
                        user_id=user_id,
                        target_count=max_followers,  # Discover up to max_followers
                    )
                    logger.info(f"Discovered {len(followers_discovered_all)} followers")
                elif not self.client.has_session:
                    logger.warning(
                        "No IG_SESSION_ID set — cannot extract follower list. "
                        "Only root profile will be returned."
                    )
                elif not user_id:
                    logger.warning(
                        "Could not extract user_id from profile HTML — "
                        "cannot paginate followers."
                    )
                
                # Limit discovered followers to max_followers
                followers_discovered = followers_discovered_all[:max_followers]
                logger.info(f"Limiting to {len(followers_discovered)} followers (max_followers={max_followers})")

                followers_completed = []
                followers_data = []

                # Remove html from root_profile before saving (large)
                root_profile_clean = {
                    k: v for k, v in root_result.items() if k != "html"
                }

                # Save Phase 1 checkpoint
                self.checkpoint.save(
                    username=root_username,
                    root_profile=root_profile_clean,
                    followers_discovered=followers_discovered,
                    followers_completed=followers_completed,
                    followers_data=followers_data,
                )
                remaining = followers_discovered.copy()

            # === PHASE 2: Scrape each follower's profile (only up to max_followers) ===
            if remaining:
                total = len(followers_discovered)
                done_count = len(followers_completed)
                logger.info(
                    f"=== PHASE 2: Scraping {len(remaining)} follower profiles "
                    f"({done_count}/{total} already done) ==="
                )

                for i, follower_username in enumerate(remaining, start=1):
                    logger.info(
                        f"[{done_count + i}/{total}] Scraping follower: {follower_username}"
                    )

                    result = await self._fetch_profile(follower_username)
                    # Remove html from result
                    result_clean = {k: v for k, v in result.items() if k != "html"}

                    # AI summarization (if available, skip for private)
                    if (
                        summarizer
                        and summarizer.is_available()
                        and result.get("status") == "success"
                        and not result.get("profile", {}).get("is_private")
                    ):
                        html = result.get("html", "")
                        posts = PostsExtractor.extract(html, limit=5)
                        if posts:
                            logger.info(f"[{follower_username}] Generating AI summary...")
                            ai_summary = await summarizer.summarize_posts(posts)
                            if result_clean.get("profile"):
                                result_clean["profile"]["ai_summary"] = ai_summary

                    followers_data.append(result_clean)
                    followers_completed.append(follower_username)

                    # Update checkpoint after each follower
                    root_profile_for_save = (
                        existing["root_profile"] if existing
                        else {k: v for k, v in root_profile.items() if k != "html"}
                    )
                    self.checkpoint.save(
                        username=root_username,
                        root_profile=root_profile_for_save,
                        followers_discovered=followers_discovered,
                        followers_completed=followers_completed,
                        followers_data=followers_data,
                    )
            else:
                if not followers_discovered:
                    logger.info("No followers to scrape.")
                else:
                    logger.info("All followers already scraped (resumed from checkpoint).")

            # Build final result
            final_root = (
                existing["root_profile"] if existing
                else {k: v for k, v in root_profile.items() if k != "html"}
            )

            return {
                "root": final_root,
                "followers": followers_data,
            }

        except SessionExpiredError as e:
            logger.error(f"Session expired: {e}")
            raise
        finally:
            if close_client:
                await self.client.close()