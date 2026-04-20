import json
import csv
import logging
from pathlib import Path

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


class XLSXExporter(BaseExporter):
    def export(self, data: dict, filename="results.xlsx"):
        """Export deep scraping results to Excel XLSX with two sheets using pandas.

        Sheet 1 ("Target"): Single row with root profile metadata.
        Sheet 2 ("Followers"): One row per follower profile.

        Args:
            data: dict with 'root' and 'followers' keys.
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

        # === Export to Excel with two sheets ===
        try:
            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                target_df.to_excel(writer, sheet_name="Target", index=False)
                followers_df.to_excel(writer, sheet_name="Followers", index=False)

            logger.info(
                f"Successfully exported XLSX ({len(followers)} followers): {filepath}"
            )
        except Exception as e:
            logger.error(f"Failed to export XLSX: {e}")
