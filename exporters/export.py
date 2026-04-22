import json
import csv
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseExporter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, data):
        raise NotImplementedError


class JSONExporter(BaseExporter):
    def export(self, data: dict, filename="results.json"):
        """Export deep scraping results to JSON.

        Args:
            data: dict with 'root' and 'followers' keys.
        """
        filepath = self.output_dir / filename
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully exported data to JSON: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")


class CSVExporter(BaseExporter):
    def export(self, data: dict, filename="results.csv"):
        """Export deep scraping results to CSV.

        Creates a flat table with one row per profile (root + followers).

        Args:
            data: dict with 'root' and 'followers' keys.
        """
        filepath = self.output_dir / filename
        rows = []

        fieldnames = [
            "role",
            "username",
            "full_name",
            "bio",
            "followers",
            "following",
            "is_private",
            "status",
            "ai_summary",
        ]

        # Root profile row
        root = data.get("root", {})
        root_profile = root.get("profile", {}) or {}
        rows.append(
            {
                "role": "target",
                "username": root_profile.get("username"),
                "full_name": root_profile.get("full_name"),
                "bio": root_profile.get("bio"),
                "followers": root_profile.get("followers"),
                "following": root_profile.get("following"),
                "is_private": root_profile.get("is_private", False),
                "status": root.get("status"),
                "ai_summary": root_profile.get("ai_summary"),
            }
        )

        # Follower rows
        for item in data.get("followers", []):
            profile = item.get("profile", {}) or {}
            rows.append(
                {
                    "role": "follower",
                    "username": profile.get("username"),
                    "full_name": profile.get("full_name"),
                    "bio": profile.get("bio"),
                    "followers": profile.get("followers"),
                    "following": profile.get("following"),
                    "is_private": profile.get("is_private", False),
                    "status": item.get("status"),
                    "ai_summary": profile.get("ai_summary"),
                }
            )

        if not rows:
            logger.warning("No data to export to CSV.")
            return

        try:
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            logger.info(f"Successfully exported {len(rows)} rows to CSV: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")


class PsychologyCSVExporter(BaseExporter):
    def export(self, data: dict, filename="psychology_profiles.csv"):
        """Export psychology profiles to CSV.

        Args:
            data: dict with 'psychology_profiles' key.
        """
        filepath = self.output_dir / filename
        profiles = data.get("psychology_profiles", [])

        if not profiles:
            logger.warning("No psychology profiles to export.")
            return

        fieldnames = [
            "username",
            "profile_summary",
            "value_hierarchy",
            "emotional_tone",
            "confidence",
            "posts_per_week",
            "consistency_score",
            "peak_hours",
            "content_types",
            "engagement_recommendations",
            "analyzed_at",
        ]

        rows = []
        for profile in profiles:
            freq = profile.get("frequency_metrics", {})
            rows.append(
                {
                    "username": profile.get("username"),
                    "profile_summary": profile.get("profile_summary", ""),
                    "value_hierarchy": ", ".join(profile.get("value_hierarchy", [])),
                    "emotional_tone": profile.get("emotional_tone", ""),
                    "confidence": profile.get("confidence", ""),
                    "posts_per_week": freq.get("posts_per_week", 0),
                    "consistency_score": freq.get("consistency_score", ""),
                    "peak_hours": ", ".join(freq.get("peak_hours", [])),
                    "content_types": ", ".join(freq.get("content_types", [])),
                    "engagement_recommendations": ", ".join(
                        profile.get("engagement_recommendations", [])
                    ),
                    "analyzed_at": profile.get("analyzed_at", ""),
                }
            )

        try:
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            logger.info(f"Successfully exported {len(rows)} psychology profiles to CSV")
        except Exception as e:
            logger.error(f"Failed to export psychology CSV: {e}")


class PostsJSONExporter(BaseExporter):
    def export(self, data: dict, filename: str = "posts.json"):
        """Export posts to JSON with metadata.

        Args:
            data: dict containing 'username' and 'posts' keys.
            filename: output filename (default: posts.json).
        """
        filepath = self.output_dir / filename
        try:
            export_data = {
                "username": data.get("username", ""),
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "posts": data.get("posts", []),
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully exported posts to JSON: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export posts JSON: {e}")

    def export(self, data: dict, filename="results.xlsx"):
        """Export deep scraping results to Excel XLSX with multiple sheets.

        Sheet 1 ("Target"): Single row with root profile metadata.
        Sheet 2 ("Followers"): One row per follower profile.
        Sheet 3 ("Psychology"): Psychology profiles if available.

        Args:
            data: dict with 'root', 'followers', and optionally 'psychology_profiles' keys.
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas is not installed. Run: pip install pandas")
            return

        filepath = self.output_dir / filename
        columns = [
            "username",
            "full_name",
            "bio",
            "followers",
            "following",
            "is_private",
            "status",
            "ai_summary",
        ]

        # === Prepare Target data ===
        root = data.get("root", {})
        root_profile = root.get("profile", {}) or {}
        target_row = [
            {
                "username": root_profile.get("username"),
                "full_name": root_profile.get("full_name"),
                "bio": root_profile.get("bio"),
                "followers": root_profile.get("followers"),
                "following": root_profile.get("following"),
                "is_private": root_profile.get("is_private", False),
                "status": root.get("status"),
                "ai_summary": root_profile.get("ai_summary"),
            }
        ]
        target_df = pd.DataFrame(target_row, columns=columns)

        # === Prepare Followers data ===
        followers = data.get("followers", [])
        follower_rows = []
        for item in followers:
            profile = item.get("profile", {}) or {}
            follower_rows.append(
                {
                    "username": profile.get("username"),
                    "full_name": profile.get("full_name"),
                    "bio": profile.get("bio"),
                    "followers": profile.get("followers"),
                    "following": profile.get("following"),
                    "is_private": profile.get("is_private", False),
                    "status": item.get("status"),
                    "ai_summary": profile.get("ai_summary"),
                }
            )
        followers_df = pd.DataFrame(follower_rows, columns=columns)

        # === Prepare Psychology Profiles data ===
        psychology_profiles = data.get("psychology_profiles", [])
        psych_columns = [
            "username",
            "profile_summary",
            "value_hierarchy",
            "emotional_tone",
            "confidence",
            "posts_per_week",
            "consistency_score",
            "engagement_recommendations",
            "analyzed_at",
        ]
        psych_rows = []
        for profile in psychology_profiles:
            freq_metrics = profile.get("frequency_metrics", {})
            psych_rows.append(
                {
                    "username": profile.get("username"),
                    "profile_summary": profile.get("profile_summary", ""),
                    "value_hierarchy": ", ".join(profile.get("value_hierarchy", [])),
                    "emotional_tone": profile.get("emotional_tone", ""),
                    "confidence": profile.get("confidence", ""),
                    "posts_per_week": freq_metrics.get("posts_per_week", 0),
                    "consistency_score": freq_metrics.get("consistency_score", ""),
                    "engagement_recommendations": ", ".join(
                        profile.get("engagement_recommendations", [])
                    ),
                    "analyzed_at": profile.get("analyzed_at", ""),
                }
            )
        psychology_df = pd.DataFrame(psych_rows, columns=psych_columns)

        # === Export to Excel with multiple sheets ===
        try:
            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                target_df.to_excel(writer, sheet_name="Target", index=False)
                followers_df.to_excel(writer, sheet_name="Followers", index=False)
                if not psychology_df.empty:
                    psychology_df.to_excel(writer, sheet_name="Psychology", index=False)

            logger.info(
                f"Successfully exported XLSX ({len(followers)} followers, "
                f"{len(psychology_profiles)} profiles): {filepath}"
            )
        except Exception as e:
            logger.error(f"Failed to export XLSX: {e}")
