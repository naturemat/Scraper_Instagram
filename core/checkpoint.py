import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoint persistence for resumable scraping runs."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, username: str) -> Path:
        return self.output_dir / f"checkpoint_{username}.json"

    def save(
        self,
        username: str,
        root_profile: dict,
        followers_discovered: list[str],
        followers_completed: list[str],
        followers_data: list[dict],
    ):
        """Save current scraping progress to a checkpoint file."""
        checkpoint = {
            "root_username": username,
            "root_profile": root_profile,
            "followers_discovered": followers_discovered,
            "followers_completed": followers_completed,
            "followers_data": followers_data,
        }
        path = self._get_path(username)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
            logger.debug(
                f"Checkpoint saved: {len(followers_completed)}/{len(followers_discovered)} followers complete"
            )
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load(self, username: str) -> Optional[dict]:
        """Load an existing checkpoint for the given username.

        Returns None if no checkpoint exists.
        """
        path = self._get_path(username)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
            logger.info(
                f"Checkpoint loaded: "
                f"{len(checkpoint.get('followers_completed', []))}/"
                f"{len(checkpoint.get('followers_discovered', []))} followers complete"
            )
            return checkpoint
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    @staticmethod
    def get_remaining(checkpoint: dict) -> list[str]:
        """Compute which follower usernames still need scraping."""
        discovered = set(checkpoint.get("followers_discovered", []))
        completed = set(checkpoint.get("followers_completed", []))
        remaining = [u for u in checkpoint.get("followers_discovered", []) if u not in completed]
        logger.info(f"Remaining followers to scrape: {len(remaining)}")
        return remaining

    def delete(self, username: str):
        """Remove checkpoint file after successful completion."""
        path = self._get_path(username)
        if path.exists():
            path.unlink()
            logger.info(f"Checkpoint file removed: {path}")
