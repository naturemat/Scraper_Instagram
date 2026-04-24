import json
import random
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Configuración Global
GRAPHQL_URL = "https://www.instagram.com/graphql/query"
DOC_ID = "27621586024097412"

BASE_DATA = (
    "av=17841478027466950&__d=www&__user=0&__a=1&__req=5&"
    "__hs=20560.HYP%3Ainstagram_web_pkg.2.1...0&dpr=1&__ccg=GOOD&__rev=1037589879"
)


class PostExtractor:
    def __init__(self, client):
        self.client = client
        logger.info(f"PostExtractor initialized with client: {client is not None}")

    async def run_posts(self, username: str, max_pages: int = 3, max_posts: int = 10) -> List[Dict]:
        """
        Extrae posts usando POST a GraphQL (método probado que funciona)
        
        Args:
            username: Nombre de usuario de Instagram
            max_pages: Máximo número de páginas a scrapear
            max_posts: Máximo número de posts a devolver
        
        Returns:
            Lista de diccionarios con información de los posts
        """
        logger.info(f"[{username}] Starting post extraction with POST method (max_posts={max_posts})")
        
        if not self.client.has_session:
            logger.error(f"[{username}] No session available")
            return []

        after = None
        all_posts = []
        seen = set()

        for page in range(max_pages):
            logger.debug(f"[{username}] Fetching page {page + 1}/{max_pages}")
            
            # Construir headers
            headers = self._build_headers(username)
            
            # Construir data del POST
            data = self._build_data(username, after)
            
            try:
                # Hacer POST request al GraphQL
                response = await self.client.post(
                    GRAPHQL_URL,
                    headers=headers,
                    data=data
                )
                
                if not response:
                    logger.error(f"[{username}] No response from server")
                    break
                
                logger.debug(f"[{username}] Response status: {response.status_code}")
                
                # Rate limit
                if response.status_code == 429:
                    logger.warning(f"[{username}] Rate limit, waiting 8s...")
                    await asyncio.sleep(8)
                    continue
                
                # Verificar texto de respuesta
                text_lower = response.text.lower()
                
                if "checkpoint" in text_lower:
                    logger.warning(f"[{username}] Instagram checkpoint required")
                    break
                
                if "login" in text_lower:
                    logger.warning(f"[{username}] Invalid session")
                    break
                
                # Parsear JSON
                try:
                    result = response.json()
                except Exception as e:
                    logger.error(f"[{username}] Error parsing JSON: {e}")
                    break
                
                data_json = result.get("data")
                
                if not data_json:
                    logger.warning(f"[{username}] No data in response")
                    errors = result.get("errors", [])
                    if errors:
                        logger.warning(f"[{username}] GraphQL errors: {errors}")
                    break
                
                # Extraer timeline
                timeline = (
                    data_json.get("xdt_api__v1__feed__user_timeline_graphql_connection")
                    or (data_json.get("user") or {}).get("edge_owner_to_timeline_media")
                    or data_json.get("user")
                    or {}
                )
                
                if not timeline:
                    logger.debug(f"[{username}] Timeline not found")
                    break
                
                edges = timeline.get("edges", [])
                
                if not edges:
                    logger.debug(f"[{username}] No posts found on page {page + 1}")
                    break
                
                # Procesar posts
                page_posts = 0
                for edge in edges:
                    node = edge.get("node")
                    if not node:
                        continue
                    
                    code = node.get("code") or node.get("shortcode")
                    
                    if code in seen:
                        continue
                    
                    seen.add(code)
                    
                    post = self._parse_post(node)
                    if post:
                        all_posts.append(post)
                        page_posts += 1
                        
                        if len(all_posts) >= max_posts:
                            logger.info(f"[{username}] Reached max posts ({max_posts})")
                            return all_posts[:max_posts]
                
                logger.debug(f"[{username}] Page {page + 1}: got {page_posts} new posts (total: {len(all_posts)})")
                
                # Verificar si hay más páginas
                page_info = timeline.get("page_info", {})
                
                if not page_info.get("has_next_page"):
                    logger.debug(f"[{username}] No more pages available")
                    break
                
                after = page_info.get("end_cursor")
                
                # Delay humano
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
            except Exception as e:
                logger.error(f"[{username}] Error on page {page + 1}: {e}", exc_info=True)
                break
        
        logger.info(f"[{username}] Total posts extracted: {len(all_posts)}")
        return all_posts[:max_posts]

    def _build_headers(self, username: str) -> Dict[str, str]:
        """Construye headers para la petición POST"""
        # Obtener csrftoken
        csrftoken = getattr(self.client, 'csrftoken', '') or ""
        
        # Si no hay csrftoken, intentar obtenerlo de las cookies
        if not csrftoken and hasattr(self.client, 'session') and self.client.session.cookies:
            for cookie in self.client.session.cookies:
                if cookie.name == "csrftoken":
                    csrftoken = cookie.value
                    logger.debug(f"Found csrftoken in cookies: {csrftoken[:10]}...")
                    break
        
        headers = {
            "accept": "*/*",
            "accept-language": "es-US,es-419;q=0.9,es;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.instagram.com",
            "referer": f"https://www.instagram.com/{username}/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-asbd-id": "359341",
            "x-bloks-version-id": "f0fd53409d7667526e529854656fe20159af8b76db89f40c333e593b51a2ce10",
            "x-csrftoken": csrftoken,
            "x-fb-friendly-name": "PolarisProfilePostsQuery",
            "x-fb-lsd": "AVo1234567890",
            "x-ig-app-id": "936619743392459",
            "x-ig-max-touch-points": "0",
            "x-root-field-name": "xdt_api__v1__feed__user_timeline_graphql_connection",
        }
        
        logger.debug(f"[{username}] Headers built, csrftoken: {csrftoken[:10] if csrftoken else 'MISSING'}...")
        return headers

    def _build_data(self, username: str, after: Optional[str] = None) -> str:
        """Construye el data del POST"""
        variables = {
            "data": {
                "count": 12,
                "include_reel_media_seen_timestamp": True,
                "include_relationship_info": True,
                "latest_besties_reel_media": True,
                "latest_reel_media": True,
            },
            "username": username,
            "__relay_internal__pv__PolarisImmersiveFeedChainingEnabledrelayprovider": False,
        }
        
        if after:
            variables["after"] = after
        
        json_vars = quote(json.dumps(variables))
        return f"{BASE_DATA}&variables={json_vars}&doc_id={DOC_ID}"

    def _parse_post(self, node: dict) -> Optional[dict]:
        """Parsea un post individual"""
        try:
            taken_at = node.get("taken_at") or node.get("taken_at_timestamp")
            
            date_str = "N/A"
            if taken_at:
                try:
                    date_str = datetime.fromtimestamp(taken_at).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass
            
            caption = node.get("caption") or {}
            caption_text = caption.get("text", "") if isinstance(caption, dict) else ""
            
            if not caption_text:
                caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                if caption_edges:
                    caption_text = caption_edges[0].get("node", {}).get("text", "")
            
            hashtags = [word for word in caption_text.split() if word.startswith("#")]
            
            code = node.get("code") or node.get("shortcode")
            if not code:
                return None
            
            return {
                "url": f"https://www.instagram.com/p/{code}/",
                "shortcode": code,
                "caption": caption_text,
                "hashtags": hashtags,
                "likes": node.get("like_count", 0),
                "comments": node.get("comment_count", 0),
                "views": node.get("play_count", "N/A"),
                "timestamp": taken_at,
                "date": date_str,
                "media_type": node.get("__typename", "unknown")
            }
            
        except Exception as e:
            logger.debug(f"Error parsing post: {e}")
            return None

    # Métodos de compatibilidad
    async def fetch_posts_for_followers(self, followers: List[str], max_posts: int = 10) -> Dict[str, List[Dict]]:
        """Método de compatibilidad - llama a run_posts para cada follower"""
        posts_by_user = {}
        
        if isinstance(followers, str):
            followers = [followers]

        for username in followers:
            try:
                posts = await self.run_posts(username, max_pages=2, max_posts=max_posts)
                posts_by_user[username] = posts
                logger.info(f"✅ {username}: {len(posts)} posts")
            except Exception as e:
                logger.error(f"❌ {username}: {e}")
                posts_by_user[username] = []

            await asyncio.sleep(random.uniform(1.5, 3.0))

        return posts_by_user

    async def fetch_user_posts(self, username: str, max_posts: int = 10) -> List[Dict]:
        """Método de compatibilidad"""
        return await self.run_posts(username, max_pages=2, max_posts=max_posts)