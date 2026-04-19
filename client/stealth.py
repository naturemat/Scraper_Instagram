import httpx
import random
import logging
import asyncio

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

class StealthClient:
    def __init__(self, max_retries=3):
        self.max_retries = max_retries
        self.session = httpx.AsyncClient(http2=True, timeout=15.0)

    def get_dynamic_headers(self, referer="https://www.instagram.com/"):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Referer": referer,
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

    async def _request_with_retry(self, method, url, **kwargs):
        if 'headers' not in kwargs:
            kwargs['headers'] = self.get_dynamic_headers()

        for attempt in range(self.max_retries):
            try:
                response = await self.session.request(method, url, **kwargs)
                
                if response.status_code in [429, 403]:
                    logger.warning(f"Rate limited or blocked ({response.status_code}). Attempt {attempt + 1}/{self.max_retries}")
                    if attempt < self.max_retries - 1:
                        sleep_time = (2 ** attempt) + random.uniform(1, 3) 
                        logger.info(f"Sleeping for {sleep_time:.2f} seconds before retrying...")
                        await asyncio.sleep(sleep_time)
                        continue
                    else:
                        response.raise_for_status()

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                # Re-raise if it's the last attempt or not a rate-limit
                if attempt == self.max_retries - 1 or e.response.status_code not in [429, 403]:
                    logger.error(f"HTTP error occurred: {e}")
                    raise
            except httpx.RequestError as e:
                logger.error(f"Request error occurred: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2) # Backoff for connection errors

    async def get(self, url, **kwargs):
        return await self._request_with_retry("GET", url, **kwargs)

    async def close(self):
        await self.session.aclose()
