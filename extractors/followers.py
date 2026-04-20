import re
import json
import random
import asyncio
import logging
from typing import Optional
from parsel import Selector

logger = logging.getLogger(__name__)

# Known query_hash values for edge_followed_by (followers).
# Instagram rotates these periodically. If the primary fails, try fallbacks.
FOLLOWER_QUERY_HASHES = [
    "c76146de99bb02f6415203be841dd25a",
    "37479f2b8209594dde7facb0d904896a",
    "5aefa9893005572d237da5068082d8d5",
]


class FollowerExtractor:
    """Extracts follower usernames from Instagram via GraphQL pagination."""

    @staticmethod
    def extract_user_id(html: str) -> Optional[str]:
        """Extract the numeric Instagram user ID from the profile page HTML.

        Instagram embeds the user ID in several places:
        - In script tags as profilePage_<user_id>
        - In the page source as "id":"<user_id>"
        - In the logging params
        """
        sel = Selector(text=html)

        # Method 1: Look for profilePage_ pattern in script tags
        scripts = sel.xpath("//script/text()").getall()
        for script in scripts:
            match = re.search(r'"profilePage_(\d+)"', script)
            if match:
                user_id = match.group(1)
                logger.info(f"Found user_id via profilePage_ pattern: {user_id}")
                return user_id

        # Method 2: Look for "id":"12345" near username context
        for script in scripts:
            match = re.search(r'"user":\s*\{[^}]*"id":\s*"(\d+)"', script)
            if match:
                user_id = match.group(1)
                logger.info(f"Found user_id via user object pattern: {user_id}")
                return user_id

        # Method 3: Look for logging_page_id
        for script in scripts:
            match = re.search(r'"logging_page_id":\s*"profilePage_(\d+)"', script)
            if match:
                user_id = match.group(1)
                logger.info(f"Found user_id via logging_page_id: {user_id}")
                return user_id

        # Method 4: Look in meta tags or data attributes
        content = sel.xpath('//body').get() or ""
        match = re.search(r'data-id="(\d+)"', content)
        if match:
            user_id = match.group(1)
            logger.info(f"Found user_id via data-id attribute: {user_id}")
            return user_id

        logger.warning("Could not extract user ID from profile HTML")
        return None

    @staticmethod
    async def paginate_followers(
        client,
        user_id: str,
        target_count: int = 150,
        delay_range: tuple = (3, 7),
    ) -> list[str]:
        """Paginate Instagram's GraphQL edge_followed_by endpoint.

        Args:
            client: StealthClient instance with a valid session cookie.
            user_id: Numeric Instagram user ID of the target profile.
            target_count: Minimum number of followers to collect.
            delay_range: (min, max) seconds between pagination requests.

        Returns:
            List of follower username strings.
        """
        followers = []
        end_cursor = None
        has_next_page = True
        page_size = 50  # Instagram's default batch size
        page_num = 0

        while has_next_page and len(followers) < target_count:
            page_num += 1

            # Try each query_hash until one works
            response_data = None
            for i, query_hash in enumerate(FOLLOWER_QUERY_HASHES):
                try:
                    variables = {
                        "id": user_id,
                        "include_reel": False,
                        "fetch_mutual": False,
                        "first": page_size,
                    }
                    if end_cursor:
                        variables["after"] = end_cursor

                    logger.info(
                        f"Fetching followers page {page_num} "
                        f"(collected: {len(followers)}/{target_count}, "
                        f"hash: ...{query_hash[-8:]})"
                    )

                    response = await client.graphql_get(
                        query_hash=query_hash,
                        variables=variables,
                        referer=f"https://www.instagram.com/",
                    )

                    response_data = response.json()

                    # Check if we got valid data
                    if "data" not in response_data:
                        if "message" in response_data:
                            logger.warning(
                                f"GraphQL error with hash {query_hash[-8:]}: "
                                f"{response_data['message']}"
                            )
                            if i < len(FOLLOWER_QUERY_HASHES) - 1:
                                continue  # Try next hash
                            else:
                                logger.error("All query hashes failed")
                                return followers
                        continue

                    # Successfully got data, proceed
                    break

                except Exception as e:
                    logger.warning(f"Query hash {query_hash[-8:]} failed: {e}")
                    if i < len(FOLLOWER_QUERY_HASHES) - 1:
                        continue
                    else:
                        logger.error("All query hashes exhausted. Cannot fetch followers.")
                        return followers

            if not response_data or "data" not in response_data:
                logger.error("No valid response data received")
                break

            # Parse the response
            try:
                edge_followed_by = (
                    response_data.get("data", {})
                    .get("user", {})
                    .get("edge_followed_by", {})
                )

                page_info = edge_followed_by.get("page_info", {})
                has_next_page = page_info.get("has_next_page", False)
                end_cursor = page_info.get("end_cursor")

                edges = edge_followed_by.get("edges", [])
                for edge in edges:
                    node = edge.get("node", {})
                    username = node.get("username")
                    if username:
                        followers.append(username)

                logger.info(
                    f"Page {page_num}: got {len(edges)} followers "
                    f"(total: {len(followers)}, has_next: {has_next_page})"
                )

                if not edges:
                    logger.info("No more followers found in response")
                    break

            except Exception as e:
                logger.error(f"Error parsing follower response: {e}", exc_info=True)
                break

            # Delay between pagination requests
            if has_next_page and len(followers) < target_count:
                delay = random.uniform(*delay_range)
                logger.info(f"Waiting {delay:.2f}s before next page...")
                await asyncio.sleep(delay)

        logger.info(f"Follower pagination complete. Total collected: {len(followers)}")
        return followers
