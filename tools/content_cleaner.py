from bs4 import BeautifulSoup
import lxml
import sys

def clean_html(scraped_content):
    """
    Cleans HTML content and extracts the main text.

    Args:
        scraped_content: A list of dictionaries, each containing 'url' and 'html_content'.

    Returns:
        A list of dictionaries, each containing 'url' and 'text'.
    """
    cleaned_content = []
    for item in scraped_content:
        try:
            soup = BeautifulSoup(item['html_content'], 'lxml')
            # Remove script and style tags
            for script in soup(["script", "style"]):
                script.extract()

            # Get text
            text = soup.get_text(separator='\n', strip=True)
            cleaned_content.append({"url": item['url'], "text": text})
        except Exception as e:
            print(f"Error cleaning HTML for {item['url']}: {e}", file=sys.stderr)
            cleaned_content.append({"url": item['url'], "text": ""})
    return cleaned_content 