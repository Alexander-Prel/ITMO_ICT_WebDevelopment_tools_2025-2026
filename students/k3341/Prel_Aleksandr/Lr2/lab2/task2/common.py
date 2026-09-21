import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
import requests

MAX_BYTES = 2_000_000
TIMEOUT = 20
HEADERS = {"User-Agent": "BookCrossingCourseLab/1.0 (educational parser)"}


@dataclass(frozen=True)
class PageData:


    url: str
    title: str
    source_host: str
    book_title: str | None = None


@dataclass(frozen=True)
class Outcome:


    url: str
    ok: bool
    title: str | None = None
    page_id: int | None = None
    book_id: int | None = None
    error: str | None = None


def validate_url(url: str) -> None:


    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("Expected an HTTP(S) URL without credentials")


def extract_page(url: str, html: bytes) -> PageData:


    validate_url(url)
    soup = BeautifulSoup(html, "html.parser")
    title = " ".join(soup.title.get_text(" ", strip=True).split()) if soup.title else ""
    if not title:
        raise ValueError("Page has no non-empty HTML title")


    heading = soup.select_one(".product_main h1")
    book_title = heading.get_text(" ", strip=True) if heading else None
    return PageData(url, title, urlsplit(url).hostname, book_title)


def download(url: str) -> bytes:
    validate_url(url)


    with requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True, allow_redirects=False) as response:
        if response.status_code != 200:
            raise ValueError(f"HTTP {response.status_code}")
        data = bytearray()
        for chunk in response.iter_content(chunk_size=65_536):
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise ValueError("Page exceeds 2 MB")
        return bytes(data)


def emit(outcome: Outcome) -> Outcome:


    print(json.dumps(asdict(outcome), ensure_ascii=False), flush=True)
    return outcome


def load_urls(path: Path | None = None) -> list[str]:


    source = path or Path(__file__).with_name("urls.txt")
    urls = [line.strip() for line in source.read_text().splitlines() if line.strip() and not line.startswith("#")]
    if not urls:
        raise ValueError("No URLs found")
    for url in urls:
        validate_url(url)
    return urls


def cli(run, approach: str) -> None:


    from lab2.task2.database import prepare_database
    parser = argparse.ArgumentParser(description="Download page titles and save them to the LR1 PostgreSQL database")
    parser.add_argument("--urls", type=Path)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    urls = load_urls(args.urls)

    prepare_database()
    started = perf_counter()
    outcomes = run(urls, args.workers)
    print(json.dumps({"approach": approach, "urls": len(urls), "seconds": perf_counter() - started,
                      "successful": sum(result.ok for result in outcomes)}))
    if not all(result.ok for result in outcomes):


        raise SystemExit(1)
