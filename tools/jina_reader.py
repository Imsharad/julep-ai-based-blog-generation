import requests
from typing import Optional

class JinaReaderAPI:
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://r.jina.ai/"
        self.headers = {
            "Accept": "text/plain",
            "User-Agent": "Python-Jina-Reader/1.0"
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def read_url(self, url: str, timeout: int = 30) -> str:
        """
        Convert a URL to LLM-friendly text using Jina Reader API
        Args:
            url: Target URL to process (e.g., "https://example.com")
            timeout: Request timeout in seconds
        Returns:
            Clean text content of the webpage
        """
        try:
            response = requests.get(
                f"{self.base_url}{url}",
                headers=self.headers,
                timeout=timeout
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            raise

    def read_url_post(self, url: str, timeout: int = 30) -> str:
        """
        Alternative POST method implementation
        """
        response = requests.post(
            self.base_url,
            headers=self.headers,
            json={"url": url},
            timeout=timeout
        )
        return response.text 