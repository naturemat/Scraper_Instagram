import json
import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class BaseExporter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, data: list):
        raise NotImplementedError

class JSONExporter(BaseExporter):
    def export(self, data: list, filename="results.json"):
        filepath = self.output_dir / filename
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully exported data to JSON: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")

class CSVExporter(BaseExporter):
    def export(self, data: list, filename="results.csv"):
        filepath = self.output_dir / filename
        flattened_data = []

        for item in data:
            profile = item.get("profile", {}) or {}
            posts = item.get("posts", [])

            # Base profile info for all rows
            base_row = {
                "username": profile.get("username"),
                "full_name": profile.get("full_name"),
                "bio": profile.get("bio"),
                "followers": profile.get("followers"),
                "following": profile.get("following"),
                "status": item.get("status")
            }

            if not posts:
                # Add one row just for the profile if no posts
                row = base_row.copy()
                row.update({
                    "post_url": None,
                    "post_caption": None,
                    "post_likes": None,
                    "post_comments": None
                })
                flattened_data.append(row)
            else:
                for post in posts:
                    row = base_row.copy()
                    row.update({
                        "post_url": post.get("url"),
                        "post_caption": post.get("caption"),
                        "post_likes": post.get("likes"),
                        "post_comments": post.get("comments")
                    })
                    flattened_data.append(row)

        if not flattened_data:
            logger.warning("No data to export to CSV.")
            return

        fieldnames = list(flattened_data[0].keys())

        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flattened_data)
            logger.info(f"Successfully exported data to CSV: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
