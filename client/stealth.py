import httpx
import os
import random
import logging
import asyncio

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# Instagram's internal app ID (public, embedded in their JS bundles)
IG_APP_ID = "936619743392459"


class SessionExpiredError(Exception):
    """Raised when the Instagram session cookie is invalid or expired."""
    pass


class StealthClient:
    def __init__(self, max_retries=3, session_id: str = None):
        self.max_retries = max_retries
        self.session_id = session_id or os.getenv("IG_SESSION_ID", "")

        cookies = None
        if self.session_id:
            cookies = httpx.Cookies()
            cookies.set("sessionid", self.session_id, domain=".instagram.com")
            logger.info("Session cookie loaded from environment")
        else:
            logger.warning("No IG_SESSION_ID found — GraphQL follower extraction will be unavailable")

        self.session = httpx.AsyncClient(
            http2=True,
            timeout=15.0,
            cookies=cookies,
            follow_redirects=True,
        )

    @property
    def has_session(self) -> bool:
        return bool(self.session_id)

    def get_dynamic_headers(self, referer="https://www.instagram.com/"):
        ua = random.choice(USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Referer": referer,
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

    def _get_graphql_headers(self, referer="https://www.instagram.com/"):
        ua = random.choice(USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": referer,
            "X-Requested-With": "XMLHttpRequest",
            "X-IG-App-ID": IG_APP_ID,
            "X-IG-WWW-Claim": "0",
            "X-ASBD-ID": "129477",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    async def _request_with_retry(self, method, url, **kwargs):
        if "headers" not in kwargs:
            kwargs["headers"] = self.get_dynamic_headers()

        for attempt in range(self.max_retries):
            try:
                response = await self.session.request(method, url, **kwargs)

                # Detect session expiration on GraphQL endpoints
                if response.status_code == 401 or (
                    response.status_code == 302
                    and "/accounts/login" in response.headers.get("location", "")
                ):
                    raise SessionExpiredError(
                        "Instagram session cookie is expired or invalid. "
                        "Please update IG_SESSION_ID in your .env file."
                    )

                if response.status_code in [429, 403]:
                    logger.warning(
                        f"Rate limited or blocked ({response.status_code}). "
                        f"Attempt {attempt + 1}/{self.max_retries}"
                    )
                    if attempt < self.max_retries - 1:
                        sleep_time = (2 ** attempt) + random.uniform(1, 3)
                        logger.info(f"Sleeping for {sleep_time:.2f}s before retrying...")
                        await asyncio.sleep(sleep_time)
                        continue
                    else:
                        response.raise_for_status()

                response.raise_for_status()
                return response

            except (SessionExpiredError, httpx.HTTPStatusError) as e:
                if isinstance(e, SessionExpiredError):
                    raise
                if attempt == self.max_retries - 1 or e.response.status_code not in [429, 403]:
                    logger.error(f"HTTP error occurred: {e}")
                    raise
            except httpx.RequestError as e:
                logger.error(f"Request error occurred: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2)

    async def get(self, url, **kwargs):
        return await self._request_with_retry("GET", url, **kwargs)

    async def graphql_get(self, query_hash: str, variables: dict, referer: str = "https://www.instagram.com/"):
        """Hit Instagram's internal GraphQL endpoint with authenticated headers."""
        import json as _json

        if not self.has_session:
            raise SessionExpiredError(
                "GraphQL requests require IG_SESSION_ID. Set it in your .env file."
            )

        url = "https://www.instagram.com/graphql/query/"
        params = {
            "query_hash": query_hash,
            "variables": _json.dumps(variables),
        }
        headers = self._get_graphql_headers(referer=referer)

        return await self._request_with_retry("GET", url, params=params, headers=headers)

    async def close(self):
        await self.session.aclose()
