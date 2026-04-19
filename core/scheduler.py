import asyncio
import random
import logging
from client.stealth import StealthClient
from extractors.parser import ProfileExtractor, PostsExtractor

logger = logging.getLogger(__name__)

class ScraperScheduler:
    def __init__(self, max_concurrent=3):
        self.client = StealthClient()
        self.semaphore = asyncio.Semaphore(max_concurrent)

    @staticmethod
    def get_random_delay(min_sec=3, max_sec=7):
        return random.uniform(min_sec, max_sec)

    async def _process_target(self, username: str) -> dict:
        async with self.semaphore:
            delay = self.get_random_delay()
            logger.info(f"[{username}] Waiting {delay:.2f}s before processing...")
            await asyncio.sleep(delay)

            url = f"https://www.instagram.com/{username}/"
            logger.info(f"[{username}] Downloading profile...")
            try:
                response = await self.client.get(url)
                html = response.text

                logger.info(f"[{username}] Extracting data...")
                profile_data = ProfileExtractor.extract(html)
                posts_data = PostsExtractor.extract(html)

                # Use original username if extractor failed to find it
                if not profile_data.get('username'):
                    profile_data['username'] = username

                return {
                    "target": username,
                    "profile": profile_data,
                    "posts": posts_data,
                    "status": "success"
                }

            except Exception as e:
                logger.error(f"[{username}] Failed to process: {e}")
                return {
                    "target": username,
                    "profile": None,
                    "posts": [],
                    "status": f"error: {str(e)}"
                }

    async def run(self, usernames: list) -> list:
        try:
            tasks = [self._process_target(username) for username in usernames]
            results = await asyncio.gather(*tasks)
            return results
        finally:
            await self.client.close()
