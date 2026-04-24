import logging
import sys
import time
from typing import Optional, Dict, Any


# Debug logging configuration
def setup_debug_logging(level=logging.DEBUG):
    """Setup debug logging with formatted output"""
    logger = logging.getLogger("instagram_scraper")
    logger.setLevel(level)

    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Avoid adding handlers multiple times
    if not logger.handlers:
        logger.addHandler(handler)

    return logger


# Debug utilities for logging requests/responses
def log_request_details(
    method: str,
    url: str,
    headers: Dict[str, Any] = None,
    data: Any = None,
    cookies: Dict[str, Any] = None,
):
    """Log detailed request information for debugging"""
    logger = logging.getLogger("instagram_scraper.debug")
    logger.debug(f"=== REQUEST ===")
    logger.debug(f"Method: {method}")
    logger.debug(f"URL: {url}")
    if headers:
        # Filter out sensitive headers
        safe_headers = {
            k: v
            for k, v in headers.items()
            if k.lower() not in ["authorization", "cookie"]
        }
        logger.debug(f"Headers: {safe_headers}")
    if data:
        logger.debug(f"Data: {data}")
    if cookies:
        # Only log cookie names, not values for security
        logger.debug(f"Cookies present: {list(cookies.keys()) if cookies else []}")


def log_response_details(response, duration: float = None):
    """Log detailed response information for debugging"""
    logger = logging.getLogger("instagram_scraper.debug")
    logger.debug(f"=== RESPONSE ===")
    logger.debug(f"Status: {response.status_code}")
    logger.debug(f"Headers: {dict(response.headers)}")
    if duration:
        logger.debug(f"Duration: {duration:.2f}s")
    # Log response size but not content to avoid huge logs
    logger.debug(f"Content length: {len(response.content) if response.content else 0}")


# Cookie validation and session checking functions
def validate_session_cookie(session_id: Optional[str]) -> bool:
    """Validate that session ID is present and properly formatted"""
    if not session_id:
        return False
    # Basic validation - Instagram session IDs are typically long strings
    return len(session_id) > 10 and isinstance(session_id, str)


def get_cookie_dict(session_id: Optional[str]) -> Dict[str, str]:
    """Convert session ID to proper cookie dictionary"""
    if not session_id:
        return {}
    return {"sessionid": session_id}


# Requirements verification functions
def check_requirements() -> Dict[str, bool]:
    """Check if all required packages are installed"""
    required_packages = ["httpx", "openai", "groq", "dotenv", "parsel", "requests"]

    results = {}
    for package in required_packages:
        try:
            __import__(package)
            results[package] = True
        except ImportError:
            results[package] = False

    return results


# Breakpoint-style logging functions for key execution points
def log_breakpoint(point_name: str, details: Dict[str, Any] = None):
    """Log a breakpoint in the execution flow"""
    logger = logging.getLogger("instagram_scraper.breakpoints")
    logger.info(f"=== BREAKPOINT: {point_name} ===")
    if details:
        # Filter out sensitive information
        safe_details = {}
        for k, v in details.items():
            if (
                "token" in k.lower()
                or "key" in k.lower()
                or "password" in k.lower()
                or "session" in k.lower()
            ):
                safe_details[k] = f"{str(v)[:10]}..." if len(str(v)) > 10 else str(v)
            else:
                safe_details[k] = v
        logger.debug(f"Details: {safe_details}")


def create_diagnostic_report(scheduler=None, root_target: str = "") -> Dict[str, Any]:
    """Create a comprehensive diagnostic report"""
    logger = logging.getLogger("instagram_scraper.diagnostic")
    logger.info("=== CREATING DIAGNOSTIC REPORT ===")

    report = {
        "timestamp": time.time(),
        "root_target": root_target,
        "requirements": {},
        "session": {},
        "components": {},
        "connectivity": {},
    }

    # Check requirements
    report["requirements"] = check_requirements()

    # Check session
    from dotenv import load_dotenv
    import os

    load_dotenv()
    session_id = os.getenv("IG_SESSION_ID", "")
    report["session"] = {
        "present": bool(session_id),
        "length": len(session_id) if session_id else 0,
        "valid": validate_session_cookie(session_id) if session_id else False,
    }

    # Check components if scheduler is provided
    if scheduler:
        try:
            report["components"]["scheduler_initialized"] = scheduler is not None
            report["components"]["client_available"] = scheduler.client is not None
            report["components"]["has_session"] = (
                scheduler.client.has_session if scheduler.client else False
            )
        except Exception as e:
            report["components"]["error"] = str(e)

    # Test basic connectivity
    if scheduler and scheduler.client and scheduler.client.has_session:
        try:
            import asyncio

            # We can't actually run async here in a sync function, but we can note that we'd test
            report["connectivity"]["would_test"] = True
        except Exception as e:
            report["connectivity"]["error"] = str(e)
    else:
        report["connectivity"]["skipped"] = "No valid session"

    logger.info("=== DIAGNOSTIC REPORT COMPLETE ===")
    return report
