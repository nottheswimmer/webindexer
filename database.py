import re
import warnings
from collections import Counter
from urllib.parse import urlparse, urljoin, urldefrag
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import requests
from bs4 import BeautifulSoup


class Database:
    def __init__(self, max_depth: int = 1, timeout: int = 10, max_workers: int = 10):
        """
        Initializes a new database.
        """
        self._max_depth = max_depth
        self._timeout = timeout
        self._max_workers = max_workers
        self._token_count_index: dict[str, Counter] = {}
        self._outbound_url_index: dict[str, set[str]] = {}

    def store_url(self, url: str, _depth: int = 0, content_type: Optional[str] = None,
                  _executor: Optional[ThreadPoolExecutor] = None) -> None:
        """
        Downloads the content at url and stores it in the database.
        """
        url = self._normalize_url(url)
        if self.has_url(url):
            return
        try:
            response = requests.get(url, timeout=self._timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            warnings.warn(f"Bad response from {url}: {e}")
            return
        except requests.exceptions.RequestException as e:
            warnings.warn(f"Error downloading {url}: {e}")
            return
        if content_type is None:
            content_type = response.headers["content-type"]
        if content_type.startswith("text/html"):
            self.store_html(url=url, html=response.text, _depth=_depth, _executor=_executor)
        elif content_type.startswith("text/plain"):
            self.store_text(url=url, text=response.text)
        else:
            warnings.warn(f"Unsupported content type `{content_type}` for url `{url}`")

    def count(self, url: str, term: str, _depth: int = 0) -> int:
        """
        Counts the number of times term appears in the indexed html.
        """
        term = next(iter(self._tokenize_text(term)))
        return sum(self._token_count_index[key][term] for key in
                   self._get_urls(url, _depth) if key in self._token_count_index)

    def has_url(self, url: str) -> bool:
        """
        Returns True if the url is in the database.
        """
        url = self._normalize_url(url)
        return url in self._token_count_index

    def store_html(self, url: str, html: str, _depth: int = 0, _executor: Optional[ThreadPoolExecutor] = None) -> None:
        """
        Parses the html and stores the urls in the database.
        """
        soup = BeautifulSoup(html, "lxml")
        self._store_tokens(uri=url, tokens=self._tokenize_soup(soup))
        self._store_outbound_urls(url=url, outbound=self._parse_outbound_urls(url, soup), _depth=_depth,
                                  _executor=_executor)

    def store_text(self, url: str, text: str) -> None:
        """
        Stores the text in the database.
        """
        self._store_tokens(uri=url, tokens=self._tokenize_text(text))

    def _store_urls(self, urls: set[str], _depth: int = 0, _executor: Optional[ThreadPoolExecutor] = None) -> None:
        """
        Stores the urls in the database.
        """
        if _executor is None:
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                self._store_urls(urls=urls, _depth=_depth, _executor=executor)
        else:
            for url in urls:
                _executor.submit(self.store_url, url, _depth)

    def _store_tokens(self, uri: str, tokens: list[str]) -> None:
        """
        Stores the tokens in the database.
        """
        self._token_count_index[uri] = Counter(tokens)

    def _tokenize_soup(self, soup: BeautifulSoup) -> list[str]:
        """
        Tokenizes the parsed html.
        """
        tokens = []
        body = soup.find("body")
        for tag in body.find_all(string=True):
            tokens.extend(self._tokenize_text(tag))
        return tokens

    def _tokenize_text(self, text: str) -> list[str]:
        """
        Tokenizes the text.
        """
        text = text.casefold()
        text = re.sub(r"\W", " ", text)
        return [token for token in text.split() if token]

    def _normalize_url(self, url: str, parent: Optional[str] = None) -> str:
        """
        Normalizes the url by removing the fragment, converting it to an absolute URL, and forcing a scheme if necessary.
        """
        if parent is not None:
            url = urljoin(parent, url)
        return urldefrag(urlparse(url, "http").geturl())[0]

    def _get_urls(self, url: str, _depth: int = 0) -> set[str]:
        """
        Returns the given URL and URLs that are max_depth levels deep from the given URL.
        """
        urls = {url}
        if _depth < self._max_depth:
            if url not in self._outbound_url_index:
                self.store_url(url=url, _depth=_depth + 1)
            for outbound in self._outbound_url_index[url]:
                urls.update(self._get_urls(outbound, _depth + 1))
        return urls

    def _parse_outbound_urls(self, parent_url: str, soup: BeautifulSoup) -> set[str]:
        """
        Parses the outbound urls from the parsed html and the parent url.
        """
        urls = set()
        for link in soup.find_all("a"):
            href = link.get("href")
            if href is None:
                continue
            url = self._normalize_url(href, parent_url)
            if url and url != parent_url:
                urls.add(url)
        return urls

    def _store_outbound_urls(self, url: str, outbound: set[str], _depth: int = 0,
                             _executor: Optional[ThreadPoolExecutor] = None) -> None:
        """
        Stores the outbound urls in the database.
        """
        self._outbound_url_index[url] = outbound
        if _depth < self._max_depth:
            self._store_urls(urls=outbound, _depth=_depth + 1, _executor=_executor)
