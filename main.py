import asyncio
import logging
from core.scheduler import ScraperScheduler
from exporters.export import JSONExporter, CSVExporter

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    logger.info("Initializing Instagram Scraper...")
    
    # Target profiles
    targets = ["instagram", "google"]
    
    scheduler = ScraperScheduler(max_concurrent=2)
    results = await scheduler.run(targets)
    
    logger.info("Scraping completed. Exporting results...")
    
    # Export to JSON
    json_exporter = JSONExporter()
    json_exporter.export(results)
    
    # Export to CSV
    csv_exporter = CSVExporter()
    csv_exporter.export(results)

if __name__ == "__main__":
    asyncio.run(main())
