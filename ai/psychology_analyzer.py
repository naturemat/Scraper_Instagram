import os
import json
import asyncio
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed.")

try:
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("GROQ package not installed.")


PSYCHOLOGIST_SYSTEM_PROMPT = """Eres un analista simple de perfiles de Instagram. Analiza el perfil y determina:

1. **Intereses principales**: Que le gusta? (viajes, moda, comida, gym, tecnologia, etc)
2. **Estilo de vida**: Como es su estilo de vida? (saludable, activo, social, creativo, etc)
3. **Tono**: Como se expresa? (divertido, serio, inspirador, positivo, etc)

Responde en JSON simple:
{
  "intereses": ["interes1", "interes2"],
  "estilo": "descripcion breve",
  "tono": "tono principal",
  "resumen": "1-2 oraciones"
}"""


class PsychologyAnalyzer:
    def __init__(self, model: str = "llama-3.1-8b-instant"):
        self.groq_client: Optional[AsyncGroq] = None
        self.openai_client: Optional[AsyncOpenAI] = None
        self.model = model
        self._initialize_clients()

    def _initialize_clients(self):
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key and GROQ_AVAILABLE:
            self.groq_client = AsyncGroq(api_key=groq_key)
            logger.info("GROQ client initialized as primary")
            return

        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and OPENAI_AVAILABLE:
            self.openai_client = AsyncOpenAI(api_key=openai_key)
            self.model = "gpt-3.5-turbo"
            logger.info("OpenAI client initialized as fallback")
            return

        logger.warning("No AI client available. Psychology analyzer disabled.")

    async def analyze_follower(
        self, follower_data: dict, posts: Optional[list] = None
    ) -> Optional[dict]:
        if not self.groq_client and not self.openai_client:
            logger.debug("AI client not initialized, skipping analysis")
            return None

        profile = follower_data.get("profile", {})
        username = profile.get("username") or follower_data.get("target") or "unknown"
        bio = profile.get("bio", "")
        full_name = profile.get("full_name", "")

        if not bio and not posts:
            return {
                "username": username,
                "intereses": [],
                "estilo": "sin datos",
                "tono": "-",
                "resumen": "Sin bio ni posts para analizar",
                "profile_summary": "Sin bio ni posts para analizar",
            }

        posts_text = ""
        if posts:
            posts_text = self._prepare_posts_text(posts)

        user_prompt = f"""Analiza este perfil de Instagram:

Username: {username}
Nombre: {full_name}
Bio: {bio}

{posts_text}

Responde SOLO con JSON:
{{"intereses": ["interes1"], "estilo": "descripcion", "tono": "tono", "resumen": "oracion"}}"""

        try:
            if self.groq_client:
                response = await self.groq_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": PSYCHOLOGIST_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.7,
                )
            else:
                response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": PSYCHOLOGIST_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )

            content = response.choices[0].message.content

            try:
                analysis = json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response as JSON: {content}")
                return self._create_default_analysis(username)

            analysis["username"] = username
            analysis["profile_summary"] = analysis.get("resumen", "")
            analysis["analyzed_at"] = datetime.utcnow().isoformat() + "Z"

            logger.info(f"Generated psychology profile for {username}")
            return analysis

        except Exception as e:
            logger.error(f"Error generating psychology analysis: {e}")
            return None

    async def analyze_batch_with_posts(
        self, followers_data: list[dict], posts_by_user: dict[str, list[dict]]
    ) -> list[dict]:
        analyses = []

        for follower_data in followers_data:
            profile = follower_data.get("profile", {})
            username = profile.get("username", "")

            if not username:
                continue

            posts = posts_by_user.get(username, [])

            try:
                analysis = await self.analyze_follower(follower_data, posts)
                if analysis:
                    if posts:
                        analysis["frequency_metrics"] = (
                            self._calculate_frequency_metrics(posts)
                        )
                    analyses.append(analysis)
            except Exception as e:
                logger.warning(f"Error analyzing {username}: {e}")
                analyses.append(self._create_default_analysis(username))

            await asyncio.sleep(0.5)

        return analyses

    async def analyze_follower_with_posts(
        self, username: str, bio: str, posts: list[dict]
    ) -> Optional[dict]:
        if not self.groq_client and not self.openai_client:
            logger.debug("AI client not initialized, skipping analysis")
            return None

        if not bio and not posts:
            return {
                "username": username,
                "intereses": [],
                "estilo": "sin datos",
                "tono": "-",
                "resumen": "Sin bio ni posts para analizar",
                "profile_summary": "Sin bio ni posts para analizar",
            }

        posts_text = ""
        if posts:
            posts_text = self._prepare_posts_text(posts)

        user_prompt = f"""Analiza este perfil de Instagram:

Username: {username}
Bio: {bio}

{posts_text}

Responde SOLO con JSON:
{{"intereses": ["interes1"], "estilo": "descripcion", "tono": "tono", "resumen": "oracion"}}"""

        try:
            if self.groq_client:
                response = await self.groq_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": PSYCHOLOGIST_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.7,
                )
            else:
                response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": PSYCHOLOGIST_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )

            content = response.choices[0].message.content

            try:
                analysis = json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response as JSON: {content}")
                return self._create_default_analysis(username)

            analysis["username"] = username
            analysis["profile_summary"] = analysis.get("resumen", "")
            analysis["analyzed_at"] = datetime.utcnow().isoformat() + "Z"

            if posts:
                analysis["frequency_metrics"] = self._calculate_frequency_metrics(posts)

            logger.info(f"Generated psychology profile for {username}")
            return analysis

        except Exception as e:
            logger.error(f"Error generating psychology analysis: {e}")
            return None

    def _prepare_posts_text(self, posts: list) -> str:
        captions = []
        for i, post in enumerate(posts[:10]):
            caption = post.get("caption", "")
            if caption:
                captions.append(f"Post {i + 1}: {caption}")

        return "\n---\n".join(captions) if captions else "No captions available"

    def _calculate_frequency_metrics(self, posts: list) -> dict:
        if not posts:
            return {
                "posts_per_week": 0.0,
                "consistency_score": "bajo",
                "peak_hours": [],
                "content_types": [],
            }

        timestamps = []
        content_types = []

        for post in posts:
            ts = post.get("timestamp")
            if ts:
                try:
                    dt = datetime.fromtimestamp(ts) if isinstance(ts, (int, float)) else None
                    if dt:
                        timestamps.append(dt)
                except:
                    pass

            media_type = post.get("media_type", "")
            if media_type:
                content_types.append(media_type)

        if len(timestamps) < 2:
            posts_per_week = len(posts) / 4.0
            consistency = "medio"
        else:
            time_span = (max(timestamps) - min(timestamps)).days
            if time_span > 0:
                posts_per_week = len(posts) / (time_span / 7)
            else:
                posts_per_week = len(posts)

            if posts_per_week >= 3:
                consistency = "alto"
            elif posts_per_week >= 1:
                consistency = "medio"
            else:
                consistency = "bajo"

        hours = [ts.hour for ts in timestamps]
        peak_hours = []
        if hours:
            morning = sum(1 for h in range(6, 12) if h in hours)
            afternoon = sum(1 for h in range(12, 18) if h in hours)
            evening = sum(1 for h in range(18, 24) if h in hours)
            night = sum(1 for h in range(0, 6) if h in hours)

            if max(morning, afternoon, evening, night) > 0:
                if morning == max(morning, afternoon, evening, night):
                    peak_hours.append("manana")
                if afternoon == max(morning, afternoon, evening, night):
                    peak_hours.append("tarde")
                if evening == max(morning, afternoon, evening, night):
                    peak_hours.append("noche")
                if night == max(morning, afternoon, evening, night):
                    peak_hours.append("madrugada")

        unique_types = list(set(content_types)) if content_types else ["unknown"]

        return {
            "posts_per_week": round(posts_per_week, 1),
            "consistency_score": consistency,
            "peak_hours": peak_hours,
            "content_types": unique_types,
        }

    def _create_default_analysis(self, username: str) -> dict:
        return {
            "username": username,
            "intereses": [],
            "estilo": "no detectado",
            "tono": "desconocido",
            "resumen": "Sin datos suficientes",
            "profile_summary": "Sin datos suficientes",
        }

    def is_available(self) -> bool:
        return self.groq_client is not None or self.openai_client is not None