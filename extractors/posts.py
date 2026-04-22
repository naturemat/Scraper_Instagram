import re
import json
import random
import asyncio
import logging
from typing import Optional
from parsel import Selector
from datetime import datetime

logger = logging.getLogger(__name__)

POST_QUERY_HASHES = [
    "e540c3384ecef4bc28e9b30f64f9d9dd",
    "2884f5b11f7327d2cbcf55b281b34f83",
]


class PostExtractor:
    """Extracts posts from Instagram user profiles via GraphQL pagination."""

    @staticmethod
    async def resolve_user_id(client, username: str) -> Optional[str]:
        """Resolve username to numeric user ID via profile page."""
        try:
            url = f"https://www.instagram.com/{username}/"
            headers = client.get_dynamic_headers()
            response = await client.get(url, headers=headers)
            html = response.text

            sel = Selector(text=html)
            scripts = sel.xpath("//script/text()").getall()

            for script in scripts:
                match = re.search(r'"profilePage_(\d+)"', script)
                if match:
                    user_id = match.group(1)
                    logger.info(f"Resolved {username} -> user_id: {user_id}")
                    return user_id

            for script in scripts:
                match = re.search(r'"user":\s*\{[^}]*"id":\s*"(\d+)"', script)
                if match:
                    user_id = match.group(1)
                    logger.info(f"Resolved {username} -> user_id: {user_id}")
                    return user_id

            logger.warning(f"Could not resolve user_id for {username}")
            return None

        except Exception as e:
            logger.error(f"Error resolving username {username}: {e}")
            return None

    @staticmethod
    async def paginate_posts(
        client,
        user_id: str,
        target_count: int = 10,
        delay_range: tuple = (2, 5),
    ) -> list[dict]:
        """Paginate Instagram's edge_media_preview_like endpoint.

        Args:
            client: StealthClient instance with a valid session cookie.
            user_id: Numeric Instagram user ID of the target profile.
            target_count: Minimum number of posts to collect.
            delay_range: (min, max) seconds between pagination requests.

        Returns:
            List of post dictionaries with id, caption, like_count, etc.
        """
        posts = []
        end_cursor = None
        has_next_page = True
        page_size = 50
        page_num = 0
        consecutive_failures = 0

        while has_next_page and len(posts) < target_count:
            page_num += 1
            consecutive_failures += 1
            response_data = None

            for i, query_hash in enumerate(POST_QUERY_HASHES):
                try:
                    variables = {
                        "id": user_id,
                        "first": page_size,
                    }
                    if end_cursor:
                        variables["after"] = end_cursor

                    logger.info(
                        f"Fetching posts page {page_num} "
                        f"(collected: {len(posts)}/{target_count}, "
                        f"hash: ...{query_hash[-8:]})"
                    )

                    response = await client.graphql_get(
                        query_hash=query_hash,
                        variables=variables,
                        referer=f"https://www.instagram.com/",
                    )

                    response_data = response.json()

                    if "data" not in response_data:
                        if "message" in response_data:
                            logger.warning(
                                f"GraphQL error with hash {query_hash[-8:]}: "
                                f"{response_data['message']}"
                            )
                            if i < len(POST_QUERY_HASHES) - 1:
                                continue
                            else:
                                logger.error("All post query hashes failed")
                                return posts
                        continue

                    break

                except Exception as e:
                    logger.warning(f"Query hash {query_hash[-8:]} failed: {e}")
                    if i < len(POST_QUERY_HASHES) - 1:
                        continue
                    else:
                        logger.error("All post query hashes exhausted")
                        return posts

            if not response_data or "data" not in response_data:
                logger.error("No valid response data received")
                break

            try:
                edge_media = (
                    response_data.get("data", {})
                    .get("user", {})
                    .get("edge_media_preview_like", {})
                )

                page_info = edge_media.get("page_info", {})
                has_next_page = page_info.get("has_next_page", False)
                end_cursor = page_info.get("end_cursor")

                edges = edge_media.get("edges", [])

                if not edges:
                    logger.info("No more posts found in response")
                    break

                for edge in edges:
                    node = edge.get("node", {})
                    post = PostExtractor._parse_post(node)
                    if post:
                        posts.append(post)
                        consecutive_failures = 0

                logger.info(
                    f"Page {page_num}: got {len(edges)} posts "
                    f"(total: {len(posts)}, has_next: {has_next_page})"
                )

            except Exception as e:
                logger.error(f"Error parsing post response: {e}", exc_info=True)
                break

            if consecutive_failures >= 3:
                logger.warning("Too many consecutive failures, stopping pagination")
                break

            if has_next_page and len(posts) < target_count:
                delay = random.uniform(*delay_range)
                logger.info(f"Waiting {delay:.2f}s before next page...")
                await asyncio.sleep(delay)

        logger.info(f"Post pagination complete. Total collected: {len(posts)}")
        return posts

    @staticmethod
    def _parse_post(node: dict) -> Optional[dict]:
        """Parse a single post node into a structured dictionary."""
        try:
            display_url = node.get("display_url", "")
            dimensions = node.get("dimensions", {})

            media_items = []
            if display_url:
                media_items.append(display_url)

            edge_sidecar_to_children = node.get("edge_sidecar_to_children", {})
            if edge_sidecar_to_children:
                edges = edge_sidecar_to_children.get("edges", [])
                for edge in edges:
                    child = edge.get("node", {})
                    url = child.get("display_url")
                    if url:
                        media_items.append(url)

            caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
            caption = ""
            if caption_edges:
                caption = caption_edges[0].get("node", {}).get("text", "")

            location = node.get("location", {})
            location_name = location.get("name", "") if location else ""

            return {
                "id": node.get("id", ""),
                "caption": caption,
                "like_count": node.get("like_count", 0),
                "comment_count": node.get("comment_count", 0),
                "timestamp": node.get("taken_at_timestamp", ""),
                "media_url": media_items[0] if media_items else "",
                "media_urls": media_items,
                "display_url": display_url,
                "width": dimensions.get("width", 0),
                "height": dimensions.get("height", 0),
                "location": location_name,
            }

        except Exception as e:
            logger.warning(f"Error parsing post node: {e}")
            return None
