# Instagram Intelligence & Behavioral Analytics System

## Introduction
This project is a high-performance, modular intelligence system designed for deep extraction and psychological analysis of Instagram data. It operates through a multi-stage pipeline that discovers followers, extracts their recent activities, and applies Large Language Models (LLMs) to generate behavioral profiles.

## Project Importance and Utility
In the modern digital landscape, raw data is only as valuable as the insights it provides. This system bridges the gap between data collection and strategic analysis:
- **Strategic Intelligence**: Provides a detailed map of an audience's interests, sentiment, and personality traits.
- **Behavioral Profiling**: Goes beyond metrics to understand the "why" behind user interaction through AI-driven psychology analysis.
- **Market Research**: Enables brands and researchers to identify niche communities and micro-influencers with precision.
- **Automation Efficiency**: Replaces hundreds of hours of manual research with an automated, resilient extraction engine.

## Core Capabilities
- **Recursive Extraction**: Deep traversal of follower networks to build comprehensive datasets.
- **Deep Content Analysis**: Extraction of captions, engagement metrics, and structured comment data.
- **AI-Driven Analytics**: Integration with GPT-4 and Groq for profile summarization and behavioral psychology analysis.
- **Resilient Architecture**: Built with stealth protocols and checkpoint systems to handle large-scale operations.

## Technology Stack
- **HTTP Client**: HTTPX with HTTP/2 support for high-performance, stealthy requests.
- **Automation Engine**: Playwright (specifically and exclusively utilized for the Comments Module to handle dynamic loading).
- **Parsing Engine**: Parsel for high-speed CSS and XPath extraction.
- **AI Integration**: OpenAI and Groq for advanced linguistic and behavioral analysis.
- **Data Engineering**: Pandas and Openpyxl for structured data processing and multi-format exports.

## Configuration and Environment
System behavior is controlled through the `.env` file. Proper configuration is critical for the success of the extraction process.

| Variable | Description |
|----------|-------------|
| `IG_ROOT_TARGET` | The starting Instagram username for the scraping process. |
| `IG_MAX_FOLLOWERS` | The maximum number of followers to extract from the root target. |
| `IG_MAX_POSTS` | Limits the number of recent posts scraped per identified user. |
| `IG_MAX_COMMENTS` | Limits the number of comments extracted per post (requires Playwright). |
| `IG_SESSION_ID` | Session identifier from browser cookies (essential for authentication). |
| `IG_CSRFTOKEN` | Cross-Site Request Forgery token from browser cookies. |
| `IG_DS_USER_ID` | Numeric User ID associated with the authenticated session. |
| `OPENAI_API_KEY` | Credentials for profile summarization services. |
| `GROQ_API_KEY` | Credentials for high-speed psychology analysis. |
| `MAX_CONCURRENT` | Controls the level of parallelism to avoid rate-limiting. |

## Execution Checkpoints
The system implements a robust checkpoint mechanism located in the `checkpoints/` directory. 
- **Purpose**: To prevent data loss during long-running operations or unexpected interruptions.
- **Functionality**: The current state, including scraped followers, posts, and AI analysis, is periodically serialized to JSON.
- **Resume Capability**: Upon restart, the system can reference these checkpoints to avoid redundant operations and ensure data integrity.

## System Maintenance and Limitations
The stability of this system is directly tied to the Instagram DOM structure. Users must be aware of the following:

### Component Selector Vulnerability
Instagram frequently updates its front-end architecture. If the extraction fails to return data, it is likely that the "root" selectors in the following files require manual updates:
- `extractors/posts.py`
- `extractors/followers.py`
- `extractors/parser.py`

### XLSX Export Considerations
The extraction to `.xlsx` files may encounter errors if the data volume exceeds Excel's cell limits or if the AI-generated content contains characters incompatible with the `openpyxl` engine. In such cases:
- Refer to `output/results.json` for the raw, complete dataset.
- Ensure all dependencies (`pandas`, `openpyxl`) are updated to their latest versions.

## Setup Requirements
1. **Environment Initialization**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. **Dependency Installation**:
   ```powershell
   pip install -r requirements.txt
   playwright install chromium
   ```
3. **Execution**:
   ```powershell
   python main.py
   ```

## Output Data Structure
Results are generated in the `output/` directory:
- `results.json`: Full hierarchical data dump.
- `results.csv` / `results.xlsx`: Structured profile and engagement metrics.
- `psychology_profiles.csv`: AI-generated behavioral insights for all analyzed users.
- `posts.json`: Granular post and comment data extracted via Playwright.

---
*Disclaimer: This tool is intended for research and educational purposes. Usage must comply with applicable data protection laws and platform terms of service.*