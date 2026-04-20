import re
import json
import logging
from parsel import Selector

logger = logging.getLogger(__name__)


class ProfileExtractor:
    @staticmethod
    def extract(html: str, is_root: bool = False) -> dict:
        sel = Selector(text=html)
        profile_data = {
            "username": None,
            "bio": None,
            "followers": None,
            "following": None,
            "full_name": None,
            "is_private": False,
            "followers_list": [],
        }

        try:
            private_indicator = sel.xpath(
                '//*[contains(text(), "is private")]/text()'
            ).get()
            if (
                private_indicator
                or sel.xpath('//*[contains(@class, "private")]/text()').get()
            ):
                logger.info("Profile is private, returning stub data")
                profile_data["is_private"] = True
                return profile_data

            og_title = sel.xpath('//meta[@property="og:title"]/@content').get()
            if og_title:
                match = re.search(r"^(.*?) \(@(.*?)\)", og_title)
                if match:
                    profile_data["full_name"] = match.group(1).strip()
                    profile_data["username"] = match.group(2).strip()

            og_desc = sel.xpath('//meta[@property="og:description"]/@content').get()
            if og_desc:
                stats_match = re.search(
                    r"([\d\.,km]+)\s+Followers,\s+([\d\.,km]+)\s+Following",
                    og_desc,
                    re.IGNORECASE,
                )
                if stats_match:
                    profile_data["followers"] = stats_match.group(1)
                    profile_data["following"] = stats_match.group(2)

            schema_scripts = sel.xpath(
                '//script[@type="application/ld+json"]/text()'
            ).getall()
            for script in schema_scripts:
                try:
                    data = json.loads(script)
                    if isinstance(data, dict):
                        if (
                            data.get("@type") == "Person"
                            or data.get("@type") == "Organization"
                        ):
                            if data.get("interactionStatistic"):
                                for stat in data["interactionStatistic"]:
                                    if (
                                        stat.get("interactionType")
                                        == "http://schema.org/FollowAction"
                                    ):
                                        profile_data["followers"] = stat.get(
                                            "userInteractionCount"
                                        )
                            if data.get("description"):
                                profile_data["bio"] = data.get("description")
                            if (
                                data.get("alternateName")
                                and not profile_data["username"]
                            ):
                                profile_data["username"] = data.get("alternateName")
                            if data.get("name") and not profile_data["full_name"]:
                                profile_data["full_name"] = data.get("name")

                            if is_root:
                                graphql = data.get("graphql", {})
                                if graphql:
                                    user = graphql.get("user", {})
                                    edge_followed_by = user.get("edge_followed_by", {})
                                    if edge_followed_by:
                                        count = edge_followed_by.get("count", 0)
                                        logger.info(
                                            f"Root profile has {count} followers"
                                        )

                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.error(f"Error extracting profile data: {e}", exc_info=True)

        return profile_data


class PostsExtractor:
    MAX_POSTS = 5

    @staticmethod
    def extract(html: str, limit: int = None) -> list:
        sel = Selector(text=html)
        posts = []
        max_posts = limit if limit is not None else PostsExtractor.MAX_POSTS

        try:
            script_tags = sel.xpath("//script/text()").getall()

            found_json = False
            for script_content in script_tags:
                if "edge_owner_to_timeline_media" in script_content:
                    match = re.search(
                        r"window\._sharedData\s*=\s*({.+?});<\/script>",
                        script_content + ";</script>",
                    )
                    if match:
                        try:
                            shared_data = json.loads(match.group(1))
                            user_data = (
                                shared_data.get("entry_data", {})
                                .get("ProfilePage", [{}])[0]
                                .get("graphql", {})
                                .get("user", {})
                            )
                            edges = user_data.get(
                                "edge_owner_to_timeline_media", {}
                            ).get("edges", [])
                            for edge in edges[:max_posts]:
                                node = edge.get("node", {})
                                posts.append(
                                    {
                                        "url": f"https://www.instagram.com/p/{node.get('shortcode')}/",
                                        "caption": node.get("edge_media_to_caption", {})
                                        .get("edges", [{}])[0]
                                        .get("node", {})
                                        .get("text")
                                        if node.get("edge_media_to_caption", {}).get(
                                            "edges"
                                        )
                                        else None,
                                        "likes": node.get("edge_liked_by", {}).get(
                                            "count"
                                        ),
                                        "comments": node.get(
                                            "edge_media_to_comment", {}
                                        ).get("count"),
                                    }
                                )
                            found_json = True
                            break
                        except Exception as e:
                            logger.debug(f"Failed to parse sharedData JSON: {e}")

            if not found_json:
                logger.warning(
                    "Could not find standard post timeline JSON data in the page source."
                )

        except Exception as e:
            logger.error(f"Error extracting posts: {e}", exc_info=True)

        return posts
