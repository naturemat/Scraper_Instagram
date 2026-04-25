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


# Prompt mejorado para análisis profesional de cuentas de Instagram
PROFESSIONAL_ANALYSIS_PROMPT = """Eres un analista profesional de redes sociales especializado en Instagram. 
Analiza el perfil y sus posts para proporcionar un análisis detallado.

Responde en formato JSON con la siguiente estructura exacta:

{
  "intereses_principales": ["lista", "de", "intereses", "detectados"],
  "estilo_vida": "descripcion del estilo de vida que refleja",
  "tono_comunicacion": "tono predominante en sus publicaciones",
  "publico_objetivo": "descripcion del tipo de audiencia al que apunta",
  "finalidad_cuenta": "propósito principal de la cuenta (personal, negocio, influencer, etc.)",
  "engagement_estimado": "nivel de engagement (bajo, medio, alto) basado en likes/comentarios",
  "resumen_ejecutivo": "analisis completo de 2-3 parrafos sobre la cuenta",
  "fortalezas": ["lista", "de", "fortalezas"],
  "areas_mejora": ["lista", "de", "areas", "de", "mejora"],
  "recomendaciones": ["recomendacion1", "recomendacion2", "recomendacion3"]
}"""

# Prompt simplificado para análisis de seguidores
FOLLOWER_ANALYSIS_PROMPT = """Eres un analista de perfiles de Instagram. Analiza el perfil y determina:

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

    async def analyze_root_profile(
        self, profile_data: dict, posts: Optional[list] = None
    ) -> Optional[dict]:
        """Análisis profesional para el perfil root target"""
        if not self.groq_client and not self.openai_client:
            logger.debug("AI client not initialized, skipping analysis")
            return None

        profile = profile_data.get("profile", {})
        username = profile.get("username") or profile_data.get("target") or "unknown"
        bio = profile.get("bio", "")
        full_name = profile.get("full_name", "")
        followers = profile.get("followers", "0")
        following = profile.get("following", "0")

        if not bio and not posts:
            return self._create_default_root_analysis(username)

        posts_text = ""
        if posts:
            posts_text = self._prepare_posts_text_advanced(posts)

        # Calcular métricas básicas de engagement
        engagement_metrics = self._calculate_engagement_metrics(posts) if posts else {}

        user_prompt = f"""Analiza profesionalmente esta cuenta de Instagram:

Username: {username}
Nombre: {full_name}
Bio: {bio}
Seguidores: {followers}
Siguiendo: {following}

Métricas de posts (últimos {len(posts) if posts else 0} posts):
- Likes promedio: {engagement_metrics.get('avg_likes', 0)}
- Comentarios promedio: {engagement_metrics.get('avg_comments', 0)}
- Ratio engagement: {engagement_metrics.get('engagement_ratio', 0)}%

{posts_text}

Responde SOLO con el JSON solicitado, con un análisis profesional y detallado."""

        try:
            if self.groq_client:
                response = await self.groq_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": PROFESSIONAL_ANALYSIS_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=1500,
                    temperature=0.7,
                )
            else:
                response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": PROFESSIONAL_ANALYSIS_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=1500,
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )

            content = response.choices[0].message.content

            try:
                analysis = json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response as JSON: {content}")
                return self._create_default_root_analysis(username)

            # Añadir campos adicionales
            analysis["username"] = username
            analysis["full_name"] = full_name
            analysis["followers"] = followers
            analysis["following"] = following
            analysis["total_posts_analyzed"] = len(posts) if posts else 0
            analysis["avg_likes"] = engagement_metrics.get('avg_likes', 0)
            analysis["avg_comments"] = engagement_metrics.get('avg_comments', 0)
            analysis["engagement_rate"] = engagement_metrics.get('engagement_ratio', 0)
            analysis["analyzed_at"] = datetime.utcnow().isoformat() + "Z"

            logger.info(f"Generated professional analysis for root profile: {username}")
            return analysis

        except Exception as e:
            logger.error(f"Error generating root profile analysis: {e}")
            return self._create_default_root_analysis(username)

    async def analyze_follower(
        self, follower_data: dict, posts: Optional[list] = None
    ) -> Optional[dict]:
        """Análisis simplificado para seguidores"""
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
                        {"role": "system", "content": FOLLOWER_ANALYSIS_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.7,
                )
            else:
                response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": FOLLOWER_ANALYSIS_PROMPT},
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

    def _prepare_posts_text(self, posts: list) -> str:
        captions = []
        for i, post in enumerate(posts[:10]):
            caption = post.get("caption", "")
            if caption:
                captions.append(f"Post {i + 1}: {caption[:200]}")

        return "\n---\n".join(captions) if captions else "No captions available"

    def _prepare_posts_text_advanced(self, posts: list) -> str:
        """Preparación avanzada de posts para análisis profesional"""
        posts_info = []
        for i, post in enumerate(posts[:15]):
            caption = post.get("caption", "")[:300]
            likes = post.get("likes", 0)
            comments = post.get("comments", 0)
            date = post.get("date", "")
            posts_info.append(
                f"Post {i + 1} (Fecha: {date}, Likes: {likes}, Comments: {comments}):\n{caption}"
            )
        return "\n---\n".join(posts_info) if posts_info else "No posts available"

    def _calculate_engagement_metrics(self, posts: list) -> dict:
        """Calcula métricas de engagement para el análisis profesional"""
        if not posts:
            return {"avg_likes": 0, "avg_comments": 0, "engagement_ratio": 0}

        total_likes = sum(p.get("likes", 0) for p in posts)
        total_comments = sum(p.get("comments", 0) for p in posts)
        avg_likes = total_likes / len(posts)
        avg_comments = total_comments / len(posts)

        # Ratio de engagement estimado (fórmula simplificada)
        engagement_ratio = ((total_likes + total_comments) / len(posts)) / 100 if total_likes > 0 else 0

        return {
            "avg_likes": round(avg_likes, 1),
            "avg_comments": round(avg_comments, 1),
            "engagement_ratio": round(engagement_ratio, 2),
            "total_posts": len(posts),
            "total_likes": total_likes,
            "total_comments": total_comments
        }

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

    def _create_default_root_analysis(self, username: str) -> dict:
        return {
            "username": username,
            "intereses_principales": [],
            "estilo_vida": "no detectado",
            "tono_comunicacion": "desconocido",
            "publico_objetivo": "no determinado",
            "finalidad_cuenta": "no determinada",
            "engagement_estimado": "bajo",
            "resumen_ejecutivo": "No hay suficientes datos para generar un análisis completo.",
            "fortalezas": [],
            "areas_mejora": [],
            "recomendaciones": ["Publicar más contenido para análisis", "Completar la biografía del perfil"]
        }

    def is_available(self) -> bool:
        return self.groq_client is not None or self.openai_client is not None