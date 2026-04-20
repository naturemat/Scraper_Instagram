import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed. AI summarization will be disabled.")


class AISummarizer:
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self._initialize_client()

    def _initialize_client(self):
        if not OPENAI_AVAILABLE:
            logger.warning("Cannot initialize AI client: OpenAI package not available")
            return

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning(
                "OPENAI_API_KEY not found in environment. AI summarization disabled."
            )
            return

        self.client = AsyncOpenAI(api_key=api_key)
        logger.info("AI summarizer client initialized successfully")

    async def summarize_posts(self, posts: list[dict]) -> Optional[str]:
        if not self.client:
            logger.debug("AI client not initialized, skipping summarization")
            return None

        if not posts:
            return None

        captions = []
        for post in posts:
            caption = post.get("caption")
            if caption:
                captions.append(caption)

        if not captions:
            return None

        captions_text = "\n---\n".join(captions[:5])

        system_prompt = """Eres un asistente de análisis de contenido social. 
Analiza las siguientes publicaciones de Instagram y proporciona un resumen temático de menos de 100 palabras.
Identifica los temas principales, el tono general y cualquier patrón en el contenido.
Sé conciso y enfócate en lo más relevante."""

        user_prompt = f"Publicaciones来分析:\n{captions_text}"

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=150,
                temperature=0.7,
            )

            summary = response.choices[0].message.content
            logger.info(f"Generated AI summary: {summary[:50]}...")
            return summary

        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return None

    def is_available(self) -> bool:
        return self.client is not None
