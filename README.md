# Instagram Deep Follower Scraper and AI Analyzer

This project is a specialized tool for automated data extraction and analysis of Instagram follower profiles. It combines stealth scraping techniques with artificial intelligence to generate behavioral insights from profile metadata and recent activity.

## Technology Stack

The system is built using high-performance Python libraries for asynchronous operations and data processing:

- HTTPX: Used as the core asynchronous HTTP client, supporting HTTP/2 to mimic modern browser traffic.
- Playwright: Provided for reliable browser automation and handling of dynamic page content where standard HTTP requests are insufficient.
- OpenAI GPT-4: Integrated for the AI Summarizer and Psychology Analyzer modules to process unstructured text and metadata.
- Pandas and Openpyxl: Utilized by the export engine to generate structured reports in spreadsheet formats.
- Python-dotenv: Manages environment-specific configurations and credentials securely.

## System Architecture

The project follows a modular architecture to separate concerns between extraction, logic, and presentation:

- main.py: The central entry point that orchestrates the scraping pipeline and AI analysis.
- ai/: Contains the intelligence layer, including specialized classes for profile summarization and psychological profiling.
- client/: Manages the stealth communication layer, handling session cookies and request headers to minimize detection.
- core/: Houses the business logic, including the ScraperScheduler for concurrency control and the Checkpoint system for session persistence.
- scrapers/: Contains the low-level extraction logic for different Instagram endpoints and data structures.
- exporters/: Responsible for transforming processed data into final output formats.
- output/: The destination directory for all generated data files.

## Execution Instructions

To run the scraper, follow these steps:

1. Environment Setup: Ensure Python 3.9+ is installed. Install dependencies using:
   pip install -r requirements.txt
   playwright install chromium

2. Configuration: Create a .env file based on .env.example. You must provide a valid IG_SESSION_ID from your browser's cookies to enable follower extraction. An OPENAI_API_KEY is required for the AI analysis features.

3. Running the Scraper: Set your target profile in main.py and execute the script:
   python main.py

## Results and Output

The system generates detailed reports based on the scraped profiles and AI-derived insights.

### Output Location
All results are saved in the output/ directory. Each execution overwrites or updates the following files:
- output/results.json
- output/results.csv
- output/results.xlsx

### Data Points Collected
- Profile Metadata: Username, bio, follower count, following count, and verification status.
- AI Summary: A condensed analysis of the user's interests and engagement patterns.
- Psychology Profiles: Behavioral analysis including personality traits and content themes derived from recent posts.
- Activity State: Timestamps of extraction and scraping success status.


venv\Scripts\activate