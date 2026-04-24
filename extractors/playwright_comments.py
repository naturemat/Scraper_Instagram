import logging
import asyncio
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext

logger = logging.getLogger(__name__)


class PlaywrightCommentExtractor:
    def __init__(self, session_id: str, csrftoken: str, headless: bool = True):
        self.session_id = session_id
        self.csrftoken = csrftoken
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def _init_browser(self):
        logger.info("Initializing Playwright browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        
        self.context = await self.browser.new_context(
            storage_state={
                "cookies": [
                    {
                        "name": "sessionid",
                        "value": self.session_id,
                        "domain": ".instagram.com",
                        "path": "/"
                    },
                    {
                        "name": "csrftoken",
                        "value": self.csrftoken,
                        "domain": ".instagram.com",
                        "path": "/"
                    }
                ]
            },
            viewport={"width": 1280, "height": 720}
        )
        logger.info("Playwright browser initialized")

    async def get_post_comments(self, shortcode: str, max_comments: int = 5) -> List[Dict]:
        """Get comments using the correct DOM structure with deduplication"""
        if not self.browser:
            await self._init_browser()
        
        page = await self.context.new_page()
        comments = []
        
        try:
            url = f"https://www.instagram.com/p/{shortcode}/"
            logger.info(f"Loading: {url}")
            
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for page to load
            await page.wait_for_timeout(8000)
            
            # Scroll to load comments
            for _ in range(4):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
            
            # Extract comments with deduplication
            comments_data = await page.evaluate(f"""
                () => {{
                    const comments = new Map();
                    const mainContainer = document.querySelector('div.x9f619.x1n2onr6.x1ja2u2z');
                    if (!mainContainer) return [];
                    
                    const commentDivs = mainContainer.querySelectorAll('div.html-div');
                    
                    for (const div of commentDivs) {{
                        const userLink = div.querySelector('a[href^="/"][class*="notranslate"], a[href^="/"]');
                        if (!userLink) continue;
                        
                        const username = userLink.innerText.trim();
                        if (!username || username === '' || username === '_mari1_7') continue;
                        
                        const allSpans = div.querySelectorAll('span');
                        let commentText = '';
                        
                        for (const span of allSpans) {{
                            const text = span.innerText.trim();
                            const isTimestamp = /^\\d+\\s*(sem|w|d|h|min|ago)$/i.test(text);
                            const isAction = text.includes('Me gusta') || text.includes('Responder') || text.includes('Ver traducción');
                            
                            if (text && 
                                text !== username &&
                                !isTimestamp && 
                                !isAction &&
                                text.length > 2) {{
                                commentText = text;
                                break;
                            }}
                        }}
                        
                        if (commentText) {{
                            const key = username + '|' + commentText;
                            if (!comments.has(key) && comments.size < {max_comments}) {{
                                comments.set(key, {{ username: username, text: commentText }});
                            }}
                        }}
                    }}
                    
                    return Array.from(comments.values());
                }}
            """)
            
            for c in comments_data:
                comments.append({
                    "username": c.get("username", ""),
                    "user_id": "",
                    "text": c.get("text", ""),
                    "timestamp": 0,
                    "likes": 0,
                    "has_replies": False
                })
            
            if comments:
                logger.info(f"Found {len(comments)} comments for {shortcode}")
                for i, c in enumerate(comments[:3], 1):
                    logger.info(f"  {i}: @{c['username']}: {c['text'][:50]}")
            else:
                logger.warning(f"No comments found for {shortcode}")
            
        except Exception as e:
            logger.error(f"Error getting comments for {shortcode}: {e}")
        finally:
            await page.close()
        
        return comments

    async def add_comments_to_posts(self, posts: List[Dict], max_comments_per_post: int = 5) -> List[Dict]:
        """Add comments to posts that have comments"""
        if not posts or max_comments_per_post <= 0:
            return posts

        posts_with_comments = [p for p in posts if (p.get('comments', 0) or p.get('comment_count', 0)) > 0]
        
        logger.info(f"Processing {len(posts_with_comments)} posts with comments")
        
        for i, post in enumerate(posts_with_comments):
            shortcode = post.get('shortcode')
            total_comments = post.get('comments', 0) or post.get('comment_count', 0)
            logger.info(f"[{i+1}/{len(posts_with_comments)}] Getting comments for {shortcode} (has {total_comments} total)")
            
            try:
                comments = await self.get_post_comments(shortcode, max_comments_per_post)
                post['comments_data'] = comments
                post['comments_count_actual'] = len(comments)
                logger.info(f"  Extracted {len(comments)} comments")
            except Exception as e:
                logger.error(f"  Failed: {e}")
                post['comments_data'] = []
                post['comments_count_actual'] = 0
            
            await asyncio.sleep(2)
        
        return posts

    async def add_comments_to_posts_by_user(self, posts_by_user: Dict[str, List[Dict]], max_comments_per_post: int = 5) -> Dict[str, List[Dict]]:
        """Add comments to posts grouped by user"""
        if not posts_by_user or max_comments_per_post <= 0:
            return posts_by_user

        for username, posts in posts_by_user.items():
            if posts:
                posts_with_comments = [p for p in posts if (p.get('comments', 0) or p.get('comment_count', 0)) > 0]
                if posts_with_comments:
                    logger.info(f"User {username}: {len(posts_with_comments)} posts have comments")
                    await self.add_comments_to_posts(posts, max_comments_per_post)
        
        return posts_by_user

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright closed")