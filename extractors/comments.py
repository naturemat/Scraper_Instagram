import logging
import re
import json
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CommentExtractor:
    def __init__(self, client):
        self.client = client
        logger.info(f"CommentExtractor initialized with client: {client is not None}")

    async def get_post_comments(self, shortcode: str, max_comments: int = 5) -> List[Dict]:
        """
        Get comments for a specific post by parsing the HTML page
        """
        logger.debug(f"Getting comments for post: {shortcode} (max={max_comments})")

        if max_comments <= 0:
            return []

        try:
            # First, get the post page HTML
            url = f"https://www.instagram.com/p/{shortcode}/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.instagram.com/",
            }
            
            response = await self.client.get(url, headers=headers)
            
            if not response or response.status_code != 200:
                logger.debug(f"Failed to get post page: {response.status_code if response else 'No response'}")
                return []
            
            html = response.text
            
            # Method 1: Extract comments from window._sharedData
            comments = self._extract_comments_from_shared_data(html, max_comments)
            if comments:
                logger.debug(f"Found {len(comments)} comments via _sharedData for {shortcode}")
                return comments
            
            # Method 2: Extract comments from script tags with GraphQL data
            comments = self._extract_comments_from_script_tags(html, max_comments)
            if comments:
                logger.debug(f"Found {len(comments)} comments via script tags for {shortcode}")
                return comments
            
            # Method 3: Extract using regex patterns from raw HTML
            comments = self._extract_comments_from_html_regex(html, max_comments)
            if comments:
                logger.debug(f"Found {len(comments)} comments via regex for {shortcode}")
                return comments
            
            logger.debug(f"No comments found for {shortcode}")
            return []

        except Exception as e:
            logger.debug(f"Error getting comments for {shortcode}: {e}")
            return []
    
    def _extract_comments_from_shared_data(self, html: str, max_comments: int) -> List[Dict]:
        """Extract comments from window._sharedData JSON"""
        try:
            # Find _sharedData
            pattern = r'window\._sharedData\s*=\s*({.*?});</script>'
            match = re.search(pattern, html, re.DOTALL)
            
            if not match:
                pattern = r'<script[^>]*>window\._sharedData\s*=\s*({.*?});</script>'
                match = re.search(pattern, html, re.DOTALL)
            
            if match:
                data = json.loads(match.group(1))
                
                # Navigate to comments
                entry_data = data.get('entry_data', {})
                post_pages = entry_data.get('PostPage', [])
                
                if post_pages:
                    graphql = post_pages[0].get('graphql', {})
                    shortcode_media = graphql.get('shortcode_media', {})
                    edge_comments = shortcode_media.get('edge_media_to_comment', {})
                    edges = edge_comments.get('edges', [])
                    
                    comments = []
                    for edge in edges[:max_comments]:
                        node = edge.get('node', {})
                        owner = node.get('owner', {})
                        comments.append({
                            "username": owner.get('username', ''),
                            "user_id": owner.get('id', ''),
                            "text": node.get('text', ''),
                            "timestamp": node.get('created_at', 0),
                            "likes": node.get('edge_liked_by', {}).get('count', 0),
                            "has_replies": node.get('edge_threaded_comments', {}).get('count', 0) > 0
                        })
                    
                    return comments
                    
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.debug(f"Error parsing _sharedData for comments: {e}")
        
        return []
    
    def _extract_comments_from_script_tags(self, html: str, max_comments: int) -> List[Dict]:
        """Extract comments from script tags containing JSON data"""
        try:
            # Find all script tags
            script_pattern = r'<script[^>]*>(.*?)</script>'
            scripts = re.findall(script_pattern, html, re.DOTALL)
            
            for script in scripts:
                # Look for edge_media_to_comment
                if 'edge_media_to_comment' in script:
                    # Try to extract JSON containing comments
                    json_pattern = r'\{[^{]*"edge_media_to_comment"[^{]*[^{]*[^}]*[^}]*\}'
                    matches = re.findall(json_pattern, script, re.DOTALL)
                    
                    for match in matches:
                        try:
                            cleaned = self._clean_json_string(match)
                            data = json.loads(cleaned)
                            
                            edges = data.get('edge_media_to_comment', {}).get('edges', [])
                            if not edges:
                                # Try deeper nesting
                                if 'data' in data and 'shortcode_media' in data['data']:
                                    edges = data['data']['shortcode_media'].get('edge_media_to_comment', {}).get('edges', [])
                            
                            if edges:
                                comments = []
                                for edge in edges[:max_comments]:
                                    node = edge.get('node', {})
                                    owner = node.get('owner', {})
                                    comments.append({
                                        "username": owner.get('username', ''),
                                        "user_id": owner.get('id', ''),
                                        "text": node.get('text', ''),
                                        "timestamp": node.get('created_at', 0),
                                        "likes": node.get('edge_liked_by', {}).get('count', 0),
                                        "has_replies": node.get('edge_threaded_comments', {}).get('count', 0) > 0
                                    })
                                
                                if comments:
                                    return comments
                                    
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.debug(f"Error extracting comments from script tags: {e}")
        
        return []
    
    def _extract_comments_from_html_regex(self, html: str, max_comments: int) -> List[Dict]:
        """Extract comments directly from HTML using regex patterns"""
        comments = []
        
        try:
            # Pattern to find comment blocks based on the DOM structure you provided
            # Each comment typically has: username, text, timestamp, likes
            
            # Find username patterns (from the outerHTML you shared)
            username_pattern = r'href="/([^/"]+)/" role="link"[^>]*>.*?<span[^>]*>.*?<span[^>]*dir="auto"[^>]*>([^<]+)</span>'
            username_matches = re.findall(username_pattern, html, re.DOTALL)
            
            # Find comment text patterns
            text_pattern = r'<span class="x1lliihq[^"]*"[^>]*dir="auto"[^>]*>([^<]+(?:<[^>]+>[^<]*</[^>]+>)*[^<]*)</span>'
            text_matches = re.findall(text_pattern, html, re.DOTALL)
            
            # Find timestamp/date patterns
            time_pattern = r'datetime="([^"]+)"'
            time_matches = re.findall(time_pattern, html)
            
            # Find like count patterns
            like_pattern = r'(\d+)\s+likes'
            like_matches = re.findall(like_pattern, html)
            
            # Process the extracted data
            # Based on the DOM structure, extract each comment's components
            comment_blocks = re.findall(
                r'<a[^>]*href="/([^/"]+)/"[^>]*>.*?<span[^>]*dir="auto"[^>]*>([^<]+)</span>.*?(?:<time[^>]*datetime="([^"]+)"[^>]*>.*?</time>)?.*?<span[^>]*dir="auto"[^>]*>([^<]+(?:<[^>]+>[^<]*</[^>]+>)*[^<]*)</span>',
                html,
                re.DOTALL
            )
            
            for i, block in enumerate(comment_blocks[:max_comments]):
                username = block[0] if len(block) > 0 else ""
                timestamp_str = block[2] if len(block) > 2 else ""
                comment_text = self._clean_text(block[3] if len(block) > 3 else "")
                
                # Skip if it's not a real comment (like "Reply" or "View all replies")
                if comment_text.lower() in ['reply', 'view all replies', 'see translation']:
                    continue
                
                # Parse timestamp
                timestamp = 0
                if timestamp_str:
                    try:
                        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamp = int(dt.timestamp())
                    except:
                        pass
                
                comments.append({
                    "username": username,
                    "user_id": "",
                    "text": comment_text,
                    "timestamp": timestamp,
                    "likes": 0,  # Will be updated if found
                    "has_replies": False
                })
            
            # Try to add like counts to comments
            if like_matches and len(like_matches) == len(comments):
                for i, comment in enumerate(comments):
                    comment['likes'] = int(like_matches[i]) if like_matches[i].isdigit() else 0
            
        except Exception as e:
            logger.debug(f"Error in HTML regex extraction: {e}")
        
        return comments
    
    def _clean_json_string(self, json_str: str) -> str:
        """Clean a JSON string that might contain invalid characters"""
        # Remove control characters
        json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
        # Fix common JSON issues
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        return json_str
    
    def _clean_text(self, text: str) -> str:
        """Clean text from HTML entities and extra whitespace"""
        if not text:
            return ""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def add_comments_to_posts(self, posts: List[Dict], max_comments_per_post: int = 5) -> List[Dict]:
        """Add comments to a list of posts"""
        if not posts:
            return posts

        logger.info(f"Adding comments to {len(posts)} posts (max_comments_per_post={max_comments_per_post})")

        for i, post in enumerate(posts):
            shortcode = post.get('shortcode')
            if shortcode:
                try:
                    comments = await self.get_post_comments(shortcode, max_comments_per_post)
                    post['comments_data'] = comments
                    post['comments_count_actual'] = len(comments)
                    if comments:
                        logger.info(f"Post {i+1}/{len(posts)}: {shortcode} - found {len(comments)} comments")
                    else:
                        logger.debug(f"Post {i+1}/{len(posts)}: {shortcode} - no comments found")
                except Exception as e:
                    logger.error(f"Failed to get comments for {shortcode}: {e}")
                    post['comments_data'] = []
                    post['comments_count_actual'] = 0

                import asyncio
                await asyncio.sleep(0.5)
            else:
                post['comments_data'] = []
                post['comments_count_actual'] = 0

        return posts

    async def add_comments_to_posts_by_user(self, posts_by_user: Dict[str, List[Dict]], max_comments_per_post: int = 5) -> Dict[str, List[Dict]]:
        """Add comments to posts grouped by user"""
        if not posts_by_user:
            return posts_by_user

        logger.info(f"Adding comments to posts for {len(posts_by_user)} users")

        for username, posts in posts_by_user.items():
            if posts:
                logger.info(f"Processing comments for user: {username} ({len(posts)} posts)")
                await self.add_comments_to_posts(posts, max_comments_per_post)

        return posts_by_user