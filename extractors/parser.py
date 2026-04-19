import re
import json
import logging
from parsel import Selector

logger = logging.getLogger(__name__)

class ProfileExtractor:
    @staticmethod
    def extract(html: str) -> dict:
        sel = Selector(text=html)
        profile_data = {
            "username": None,
            "bio": None,
            "followers": None,
            "following": None,
            "full_name": None
        }

        try:
            # Attempt 1: Extract from meta tags (og:description and og:title)
            og_title = sel.xpath('//meta[@property="og:title"]/@content').get()
            if og_title:
                # Format: "Name (@username) • Instagram photos and videos"
                match = re.search(r'^(.*?) \(@(.*?)\)', og_title)
                if match:
                    profile_data["full_name"] = match.group(1).strip()
                    profile_data["username"] = match.group(2).strip()

            og_desc = sel.xpath('//meta[@property="og:description"]/@content').get()
            if og_desc:
                # Format: "X Followers, Y Following, Z Posts - See Instagram photos and videos from [Name] (@[username])"
                # Or sometimes includes bio.
                stats_match = re.search(r'([\d\.,km]+)\s+Followers,\s+([\d\.,km]+)\s+Following', og_desc, re.IGNORECASE)
                if stats_match:
                    profile_data["followers"] = stats_match.group(1)
                    profile_data["following"] = stats_match.group(2)

            # Attempt 2: Extract from JSON-LD schema if available
            schema_scripts = sel.xpath('//script[@type="application/ld+json"]/text()').getall()
            for script in schema_scripts:
                try:
                    data = json.loads(script)
                    if isinstance(data, dict):
                        if data.get('@type') == 'Person' or data.get('@type') == 'Organization':
                            if data.get('interactionStatistic'):
                                for stat in data['interactionStatistic']:
                                    if stat.get('interactionType') == 'http://schema.org/FollowAction':
                                        profile_data['followers'] = stat.get('userInteractionCount')
                            if data.get('description'):
                                profile_data['bio'] = data.get('description')
                            if data.get('alternateName') and not profile_data['username']:
                                profile_data['username'] = data.get('alternateName')
                            if data.get('name') and not profile_data['full_name']:
                                profile_data['full_name'] = data.get('name')
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.error(f"Error extracting profile data: {e}", exc_info=True)

        return profile_data


class PostsExtractor:
    @staticmethod
    def extract(html: str) -> list:
        sel = Selector(text=html)
        posts = []

        try:
            # Given Instagram's DOM changes, JSON extraction from embedded scripts is usually more stable for posts
            # Looking for typical state objects in scripts e.g., require("...").ServerRenderedData or similar
            script_tags = sel.xpath('//script/text()').getall()
            
            # Simple fallback using meta tags if JSON is entirely obfuscated (very rare, usually requires login though)
            # Without login, Instagram serves limited HTML. We attempt to extract from any embedded deep JSON.
            found_json = False
            for script_content in script_tags:
                if 'edge_owner_to_timeline_media' in script_content:
                    # Very rough regex to extract the dict or JSON block
                    # Normally it resides in window._sharedData
                    match = re.search(r'window\._sharedData\s*=\s*({.+?});<\/script>', script_content + ';</script>')
                    if match:
                        try:
                            shared_data = json.loads(match.group(1))
                            user_data = shared_data.get('entry_data', {}).get('ProfilePage', [{}])[0].get('graphql', {}).get('user', {})
                            edges = user_data.get('edge_owner_to_timeline_media', {}).get('edges', [])
                            for edge in edges:
                                node = edge.get('node', {})
                                posts.append({
                                    "url": f"https://www.instagram.com/p/{node.get('shortcode')}/",
                                    "caption": node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text') if node.get('edge_media_to_caption', {}).get('edges') else None,
                                    "likes": node.get('edge_liked_by', {}).get('count'),
                                    "comments": node.get('edge_media_to_comment', {}).get('count')
                                })
                            found_json = True
                            break
                        except Exception as e:
                            logger.debug(f"Failed to parse sharedData JSON: {e}")

            if not found_json:
                logger.warning("Could not find standard post timeline JSON data in the page source.")
                
        except Exception as e:
            logger.error(f"Error extracting posts: {e}", exc_info=True)

        return posts
