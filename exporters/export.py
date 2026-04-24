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
        filepath = self.output_dir / filename
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully exported data to JSON: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")


class CSVExporter(BaseExporter):
    def export(self, data: dict, filename="results.csv"):
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
        filepath = self.output_dir / filename
        profiles = data.get("psychology_profiles", [])

        if not profiles:
            logger.warning("No psychology profiles to export.")
            return

        fieldnames = [
            "username",
            "profile_summary",
            "intereses",
            "estilo",
            "tono",
            "resumen",
            "analyzed_at",
        ]

        rows = []
        for profile in profiles:
            rows.append({
                "username": profile.get("username", ""),
                "profile_summary": profile.get("profile_summary", profile.get("resumen", "")),
                "intereses": ", ".join(profile.get("intereses", [])),
                "estilo": profile.get("estilo", ""),
                "tono": profile.get("tono", ""),
                "resumen": profile.get("resumen", ""),
                "analyzed_at": profile.get("analyzed_at", ""),
            })

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
        filepath = self.output_dir / filename
        try:
            total_comments = 0
            for post in data.get("posts", []):
                total_comments += len(post.get("comments_data", []))

            export_data = {
                "username": data.get("username", ""),
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "total_posts": len(data.get("posts", [])),
                "total_comments": total_comments,
                "posts": data.get("posts", []),
            }

            if "posts_by_user" in data:
                export_data["posts_by_user"] = data.get("posts_by_user", {})

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)

            logger.info(f"Successfully exported {export_data['total_posts']} posts with {total_comments} comments to JSON: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export posts JSON: {e}")


class XLSXExporter(BaseExporter):
    def export(self, data: dict, filename="results.xlsx"):
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

        psychology_profiles = data.get("psychology_profiles", [])
        psych_columns = [
            "username",
            "profile_summary",
            "intereses",
            "estilo",
            "tono",
            "analyzed_at",
        ]
        psych_rows = []
        for profile in psychology_profiles:
            psych_rows.append(
                {
                    "username": profile.get("username", ""),
                    "profile_summary": profile.get("profile_summary", profile.get("resumen", "")),
                    "intereses": ", ".join(profile.get("intereses", [])),
                    "estilo": profile.get("estilo", ""),
                    "tono": profile.get("tono", ""),
                    "analyzed_at": profile.get("analyzed_at", ""),
                }
            )
        psychology_df = pd.DataFrame(psych_rows, columns=psych_columns)

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