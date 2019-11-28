# eo-scraping-toolkit
This is a collection of functions to gently scrape data from EtternaOnline. Gently because the EO servers are not particularly resilient. I easily brought them to their knees when I was scraping user scores with 50 threads in parallel. This has heavy rate-limiting and request caching.

**main.py** is a simple test file for the scraper functions. It's not used for the scraping itself

**eo_scraping.py** has the scraping logic

**util.py** contains utility functions <sup>(wow!)</sup>, including a wrapper for the `requests` GET and POST functions that have rate-limiting and request-caching

## Dependencies:
- **requests** for HTTP requests
- **joblib** for request caching
- **bs4** for HTML parsing
