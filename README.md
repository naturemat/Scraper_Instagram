# Instagram Deep Follower Scraper & AI Analyzer

A powerful, stealthy, and intelligent tool designed for deep data extraction from Instagram. This project not only scrapes profile data and posts but also utilizes AI to perform psychological and behavioral analysis on followers.

## 🚀 Actual Functionality
The scraper extracts comprehensive information from a target Instagram profile and its followers. It goes beyond simple data collection by:
- **Recursive Extraction**: Getting followers of a profile and then diving into each follower's recent activity.
- **Deep Content Scraping**: Capturing posts, captions, likes, and comments.
- **AI Analysis**: Using LLMs (GPT-4 or Groq) to analyze the "psychology" of followers based on their biographies and post content.
- **Stealth Operation**: Mimicking human-like behavior using advanced headers, HTTP/2, and browser automation to minimize detection risks.

## 🛠 Technology Stack
- **Language**: Python 3.12+
- **HTTP Client**: `HTTPX` (with HTTP/2 support for stealth).
- **Automation**: `Playwright` (for handling dynamic content and session validation).
- **Parsing**: `Parsel` (for efficient HTML and CSS selector extraction).
- **Data Handling**: `Pandas` & `Openpyxl` (for CSV and XLSX exports).
- **AI Engine**: `OpenAI` & `Groq` (for summarization and psychological profiling).
- **Environment**: `python-dotenv` for secure configuration.

## 🏗 System Architecture
The project is built with a modular design to ensure scalability and maintainability:

- **`main.py`**: The orchestrator. It manages the full lifecycle: config loading, component initialization, scraping flow, and final exports.
- **`core/`**: Contains the `ScraperScheduler` which handles the logic of traversing followers and managing concurrency.
- **`client/`**: The communication layer. Houses the `StealthClient` which manages sessions, cookies, and request headers.
- **`extractors/`**: Specialized modules for different data types:
    - `posts.py`: Extracts post metadata and media info.
    - `comments.py`: Scrapes comments using multiple fallback methods (SharedData, GraphQL, Regex).
    - `followers.py`: Handles the extraction of follower lists.
- **`ai/`**: The intelligence layer.
    - `summarizer.py`: Creates concise summaries of profile bios.
    - `psychology_analyzer.py`: Generates behavioral insights and personality profiles.
- **`exporters/`**: Transforms internal data structures into user-friendly formats (JSON, CSV, XLSX).

## 🔄 Execution Flow
1. **Initialization**: Loads `.env` variables and validates the Instagram session.
2. **Root Scraping**: Extracts profile details and recent posts from the `IG_ROOT_TARGET`.
3. **Follower Discovery**: Retrieves the list of followers (up to `IG_MAX_FOLLOWERS`).
4. **Deep Scraping**: For each follower, the system scrapes their recent posts and comments.
5. **AI Processing**: Profiles and posts are sent to the AI modules for summarization and psychological analysis.
6. **Checkpointing**: Saves the current state in `checkpoints/` to prevent data loss.
7. **Export**: Generates final reports in the `output/` directory.

## ⚙️ Configuration (.env)
All operational variables are configured in the `.env` file. You can find a template in `.env.example`.

| Variable | Description |
|----------|-------------|
| `IG_ROOT_TARGET` | The username of the Instagram profile to scrape. |
| `IG_MAX_FOLLOWERS` | Limit of followers to extract and analyze. |
| `IG_MAX_POSTS` | Maximum posts to scrape per user. |
| `IG_MAX_COMMENTS` | Maximum comments to scrape per post. |
| `IG_SESSION_ID` | Your active Instagram session ID (from cookies). |
| `IG_CSRFTOKEN` | Your Instagram CSRF token (from cookies). |
| `OPENAI_API_KEY` | API key for AI Summarization (Optional). |
| `GROQ_API_KEY` | API key for Psychology Analysis (Optional). |

## 📦 Setup & Execution

### 1. Virtual Environment
It is highly recommended to use a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configuration
Copy the example environment file and fill in your details:
```bash
cp .env.example .env
```
*Note: Make sure to provide a valid `sessionid` and `csrftoken` from your browser.*

### 4. Run the Project
```bash
python main.py
```

## 📊 Output & Results
You can find the extracted data in the `output/` directory:
- **`output/results.json`**: Full raw data dump.
- **`output/results.xlsx` / `results.csv`**: Structured data including profile metrics and AI summaries.
- **`output/psychology_profiles.csv`**: Detailed behavioral analysis of the followers.
- **`output/posts.json`**: All scraped posts and their respective comments.

**Example Structure of Obtained Data:**
```json
{
  "username": "follower_user",
  "profile": { "bio": "...", "followers": 1200, "following": 800 },
  "ai_summary": "User interested in technology and photography...",
  "psychology_analysis": {
    "traits": ["Creative", "Extrovert"],
    "interests": ["Travel", "Art"]
  },
  "posts": [
    { "url": "...", "likes": 45, "comments_data": [...] }
  ]
}
```

---
*Disclaimer: This tool is for educational and research purposes only. Always respect Instagram's Terms of Service.*