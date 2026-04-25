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
# Añade esta clase después de PsychologyCSVExporter

class RootAnalysisExporter(BaseExporter):
    def export(self, data: dict, filename="root_analysis.json"):
        """Export root profile analysis to JSON."""
        filepath = self.output_dir / filename
        
        root_analysis = data.get("root_analysis", {})
        root_profile = data.get("root", {}).get("profile", {})
        
        if not root_analysis:
            logger.warning("No root analysis data to export.")
            return
        
        export_data = {
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "profile_info": {
                "username": root_profile.get("username"),
                "full_name": root_profile.get("full_name"),
                "bio": root_profile.get("bio"),
                "followers": root_profile.get("followers"),
                "following": root_profile.get("following"),
                "is_private": root_profile.get("is_private", False),
            },
            "analysis": root_analysis
        }
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully exported root analysis to JSON: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export root analysis JSON: {e}")


class RootAnalysisCSVExporter(BaseExporter):
    def export(self, data: dict, filename="root_analysis.csv"):
        """Export root profile analysis to CSV (single row)."""
        filepath = self.output_dir / filename
        
        root_analysis = data.get("root_analysis", {})
        root_profile = data.get("root", {}).get("profile", {})
        
        if not root_analysis:
            logger.warning("No root analysis data to export.")
            return
        
        fieldnames = [
            "username",
            "full_name",
            "followers",
            "following",
            "intereses_principales",
            "estilo_vida",
            "tono_comunicacion",
            "publico_objetivo",
            "finalidad_cuenta",
            "engagement_estimado",
            "avg_likes",
            "avg_comments",
            "engagement_rate",
            "total_posts_analyzed",
            "fortalezas",
            "areas_mejora",
            "recomendaciones",
            "resumen_ejecutivo",
            "analyzed_at"
        ]
        
        row = {
            "username": root_profile.get("username"),
            "full_name": root_profile.get("full_name"),
            "followers": root_profile.get("followers"),
            "following": root_profile.get("following"),
            "intereses_principales": ", ".join(root_analysis.get("intereses_principales", [])),
            "estilo_vida": root_analysis.get("estilo_vida", ""),
            "tono_comunicacion": root_analysis.get("tono_comunicacion", ""),
            "publico_objetivo": root_analysis.get("publico_objetivo", ""),
            "finalidad_cuenta": root_analysis.get("finalidad_cuenta", ""),
            "engagement_estimado": root_analysis.get("engagement_estimado", ""),
            "avg_likes": root_analysis.get("avg_likes", 0),
            "avg_comments": root_analysis.get("avg_comments", 0),
            "engagement_rate": root_analysis.get("engagement_rate", 0),
            "total_posts_analyzed": root_analysis.get("total_posts_analyzed", 0),
            "fortalezas": ", ".join(root_analysis.get("fortalezas", [])),
            "areas_mejora": ", ".join(root_analysis.get("areas_mejora", [])),
            "recomendaciones": ". ".join(root_analysis.get("recomendaciones", [])),
            "resumen_ejecutivo": root_analysis.get("resumen_ejecutivo", ""),
            "analyzed_at": root_analysis.get("analyzed_at", ""),
        }
        
        try:
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(row)
            logger.info(f"Successfully exported root analysis to CSV: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export root analysis CSV: {e}")


class PostsJSONExporter(BaseExporter):
    def export(self, data: dict, filename: str = "posts.json"):
        """Export posts to JSON with metadata and comments."""
        filepath = self.output_dir / filename
        try:
            total_comments = 0
            for post in data.get("posts", []):
                comments_data = post.get("comments_data", [])
                if isinstance(comments_data, list):
                    total_comments += len(comments_data)

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

        # Prepare Target data
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

        # Prepare Followers data
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

        # Prepare Psychology Profiles data
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

        # Prepare Posts data with comments
        posts_by_user = data.get("posts_by_user", {})
        all_posts_data = []
        
        # Also get root posts if available
        root_posts = data.get("root_posts", [])
        if root_posts:
            for post in root_posts:
                comments_list = post.get("comments_data", [])
                comments_text = "; ".join([f"{c.get('username', '')}: {c.get('text', '')[:100]}" for c in comments_list[:3]])
                all_posts_data.append({
                    "username": data.get("root", {}).get("profile", {}).get("username", "root"),
                    "post_url": post.get("url", ""),
                    "shortcode": post.get("shortcode", ""),
                    "caption": post.get("caption", "")[:200],
                    "likes": post.get("likes", 0),
                    "comments_count": post.get("comments_count", post.get("comment_count", 0)),
                    "actual_comments_extracted": len(comments_list),
                    "sample_comments": comments_text,
                    "date": post.get("date", ""),
                    "media_type": post.get("media_type", "")
                })
        
        # Add follower posts
        for username, posts in posts_by_user.items():
            for post in posts:
                comments_list = post.get("comments_data", [])
                comments_text = "; ".join([f"{c.get('username', '')}: {c.get('text', '')[:100]}" for c in comments_list[:3]])
                all_posts_data.append({
                    "username": username,
                    "post_url": post.get("url", ""),
                    "shortcode": post.get("shortcode", ""),
                    "caption": post.get("caption", "")[:200],
                    "likes": post.get("likes", 0),
                    "comments_count": post.get("comments_count", post.get("comment_count", 0)),
                    "actual_comments_extracted": len(comments_list),
                    "sample_comments": comments_text,
                    "date": post.get("date", ""),
                    "media_type": post.get("media_type", "")
                })

        posts_df = pd.DataFrame(all_posts_data)
        
        # Prepare Comments detailed data (one row per comment)
        all_comments_data = []
        for username, posts in posts_by_user.items():
            for post in posts:
                comments_list = post.get("comments_data", [])
                for comment in comments_list:
                    all_comments_data.append({
                        "username": username,
                        "post_url": post.get("url", ""),
                        "post_shortcode": post.get("shortcode", ""),
                        "comment_username": comment.get("username", ""),
                        "comment_text": comment.get("text", ""),
                        "comment_likes": comment.get("likes", 0),
                        "comment_timestamp": comment.get("timestamp", 0),
                    })
        
        # Add root posts comments
        if root_posts:
            for post in root_posts:
                comments_list = post.get("comments_data", [])
                for comment in comments_list:
                    all_comments_data.append({
                        "username": data.get("root", {}).get("profile", {}).get("username", "root"),
                        "post_url": post.get("url", ""),
                        "post_shortcode": post.get("shortcode", ""),
                        "comment_username": comment.get("username", ""),
                        "comment_text": comment.get("text", ""),
                        "comment_likes": comment.get("likes", 0),
                        "comment_timestamp": comment.get("timestamp", 0),
                    })
        
        comments_df = pd.DataFrame(all_comments_data)

        # Export to Excel with multiple sheets
        try:
            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                target_df.to_excel(writer, sheet_name="Target", index=False)
                followers_df.to_excel(writer, sheet_name="Followers", index=False)
                if not psychology_df.empty:
                    psychology_df.to_excel(writer, sheet_name="Psychology", index=False)
                if not posts_df.empty:
                    posts_df.to_excel(writer, sheet_name="Posts", index=False)
                if not comments_df.empty:
                    comments_df.to_excel(writer, sheet_name="Comments", index=False)

            logger.info(
                f"Successfully exported XLSX ({len(followers)} followers, "
                f"{len(psychology_profiles)} profiles, {len(posts_df)} posts, "
                f"{len(comments_df)} comments): {filepath}"
            )
        except Exception as e:
            logger.error(f"Failed to export XLSX: {e}")