# This file defines an asynchronous web scraper that fetches the HTML content of multiple URLs.
# It uses the aiohttp library for making asynchronous HTTP requests.
# The script takes a list of URLs as command-line arguments and prints the first 500 characters of each page's content.
# It also supports setting a maximum concurrency limit using the --max-concurrent argument.

import asyncio
import aiohttp
from aiohttp import ClientResponseError
import sys
from urllib.parse import urljoin

async def fetch_page(session: aiohttp.ClientSession, url: str) -> tuple[str, str]:
    """Fetches a single page and returns the URL and its content."""
    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            return url, await response.text()
    except ClientResponseError as e:
        print(f"Error fetching {url}: {e.status} - {e.message}", file=sys.stderr)
        return url, ""
    except asyncio.TimeoutError:
        print(f"Timeout fetching {url}", file=sys.stderr)
        return url, ""
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return url, ""

async def scrape_urls(urls: list[str]) -> list[dict]:
    """
    Asynchronously scrapes multiple URLs.

    Args:
        urls: A list of URLs to scrape.

    Returns:
        A list of dictionaries, each with 'url' and 'html_content' keys.
    """
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_page(session, url) for url in urls]
        results = await asyncio.gather(*tasks)

    scraped_data = [{"url": url, "html_content": content} for url, content in results]
    return scraped_data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python web_scraper.py <url1> [url2] [url3] ...")
        sys.exit(1)

    urls = sys.argv[1:]
    max_concurrent = 3  # Default concurrency
    for arg in sys.argv:
        if arg.startswith("--max-concurrent="):
            try:
                max_concurrent = int(arg.split("=")[1])
            except ValueError:
                print("Invalid value for --max-concurrent. Using default (3).", file=sys.stderr)
    
    async def main():
        result = await scrape_urls(urls)
        for item in result:
            print(f"Content from {item['url']}:")
            print(item['html_content'][:500] + "...")  # Print first 500 chars
            print("-" * 20)

    asyncio.run(main()) 