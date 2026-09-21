# Исходный код ЛР2

Пути указаны от папки `Lr2`.

## `lab2/common.py`

```python
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


def split_ranges(n: int, workers: int) -> list[tuple[int, int]]:
    """Inclusive ranges covering 1..n exactly, with sizes differing by at most 1."""


    if n < 1 or not 1 <= workers <= 64:
        raise ValueError("n must be positive; workers must be between 1 and 64")

    count = min(n, workers)

    size, remainder = divmod(n, count)
    start = 1
    ranges = []
    for index in range(count):

        end = start + size + (index < remainder) - 1
        ranges.append((start, end))
        start = end + 1
    return ranges


def split_items(items: Sequence[T], workers: int) -> list[list[T]]:


    if not items:
        raise ValueError("The URL list is empty")
    return [list(items[start - 1:end]) for start, end in split_ranges(len(items), workers)]
```

## `lab2/task1/async_sum.py`

```python
import asyncio

from lab2.common import split_ranges
from lab2.task1.common import cli, sum_range


async def calculate_sum(start: int, end: int) -> int:
    total = 0


    for block_start in range(start, end + 1, 100_000):
        total += sum_range(block_start, min(block_start + 99_999, end))


        await asyncio.sleep(0)
    return total


async def run_async(n: int, workers: int = 4) -> int:


    tasks = [asyncio.create_task(calculate_sum(start, end)) for start, end in split_ranges(n, workers)]


    return sum(await asyncio.gather(*tasks))


def run(n: int, workers: int = 4) -> int:


    return asyncio.run(run_async(n, workers))


if __name__ == "__main__":
    cli(run, "asyncio")
```

## `lab2/task1/benchmark.py`

```python
import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from time import perf_counter

from lab2.task1 import async_sum, multiprocessing_sum, threading_sum
from lab2.task1.common import ASSIGNMENT_N, LONG_RUN_LIMIT


def main() -> None:


    parser = argparse.ArgumentParser(description="Compare the same workload, including worker startup and shutdown")
    parser.add_argument("--n", type=int, default=ASSIGNMENT_N)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("lab2/results/cpu_full.json"))
    parser.add_argument("--allow-long-run", action="store_true")
    args = parser.parse_args()
    if args.n < 1 or not 1 <= args.workers <= 64 or not 1 <= args.repeats <= 10:
        parser.error("Use positive n, workers=1..64 and repeats=1..10")
    if args.n > LONG_RUN_LIMIT and not args.allow_long_run:
        parser.error("Full iteration may take days: pass --allow-long-run explicitly")
    if args.n != ASSIGNMENT_N and args.output == Path("lab2/results/cpu_full.json"):
        parser.error("A smoke check requires a separate --output, not cpu_full.json")
    if args.output.exists():

        parser.error("Output already exists; choose a new file to preserve previous measurements")
    runners = [("threading", threading_sum.run), ("multiprocessing", multiprocessing_sum.run), ("asyncio", async_sum.run)]
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
              "platform": platform.platform(), "repeats": args.repeats, "n": args.n,
              "full_assignment": args.n == ASSIGNMENT_N, "complete": False, "rows": [], "runs": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    samples = {name: [] for name, _ in runners}
    totals = {}
    rows = []
    for repeat in range(args.repeats):

        for name, run in runners[repeat % len(runners):] + runners[:repeat % len(runners)]:
            print(f"Starting {name}, repeat {repeat + 1}/{args.repeats}, n={args.n}", flush=True)
            started = perf_counter()
            total = run(args.n, args.workers)
            elapsed = perf_counter() - started

            if total != args.n * (args.n + 1) // 2:
                raise AssertionError(f"Incorrect sum from {name}")
            samples[name].append(elapsed)
            totals[name] = total
            report["runs"].append({"approach": name, "repeat": repeat + 1, "seconds": elapsed, "sum": total})
            report["measured_at"] = datetime.now(timezone.utc).isoformat()


            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(f"Finished {name}: {elapsed:.6f}s", flush=True)
    for name, _ in runners:
        rows.append({"approach": name, "method": "iterate", "n": args.n, "sum": totals[name],
                     "workers": args.workers, "samples_seconds": samples[name],
                     "median_seconds": median(samples[name])})


    report.update(rows=rows, complete=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
```

## `lab2/task1/common.py`

```python
import argparse
import json
from time import perf_counter

ASSIGNMENT_N = 10_000_000_000_000

LONG_RUN_LIMIT = 100_000_000


def sum_range(start: int, end: int) -> int:


    total = 0

    for value in range(start, end + 1):
        total += value
    return total


def cli(run, approach: str) -> None:


    parser = argparse.ArgumentParser(description="Sum inclusive range 1..n")
    parser.add_argument("--n", type=int, default=ASSIGNMENT_N)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--allow-long-run", action="store_true")
    args = parser.parse_args()

    if args.n > LONG_RUN_LIMIT and not args.allow_long_run:
        parser.error("Full iteration may take days: pass --allow-long-run explicitly; use --n 10 only for a smoke check")
    if args.n < 1 or not 1 <= args.workers <= 64:
        parser.error("n must be positive; workers must be between 1 and 64")
    print(f"Starting {approach}: iterating 1..{args.n} with {args.workers} workers", flush=True)


    started = perf_counter()
    result = run(args.n, args.workers)
    elapsed = perf_counter() - started


    if result != args.n * (args.n + 1) // 2:
        raise AssertionError("Incorrect iterative sum")
    print(json.dumps({"approach": approach, "method": "iterate", "n": args.n,
                      "full_assignment": args.n == ASSIGNMENT_N,
                      "workers": args.workers, "sum": result, "seconds": elapsed}, indent=2))
```

## `lab2/task1/multiprocessing_sum.py`

```python
import multiprocessing

from lab2.common import split_ranges
from lab2.task1.common import cli, sum_range


def calculate_sum(start: int, end: int) -> int:


    return sum_range(start, end)


def run(n: int, workers: int = 4) -> int:
    ranges = split_ranges(n, workers)


    with multiprocessing.get_context("spawn").Pool(len(ranges)) as pool:


        values = pool.starmap(calculate_sum, ranges)


    return sum(values)


if __name__ == "__main__":
    cli(run, "multiprocessing")
```

## `lab2/task1/threading_sum.py`

```python
import threading
from queue import Queue

from lab2.common import split_ranges
from lab2.task1.common import cli, sum_range


def calculate_sum(start: int, end: int) -> int:


    return sum_range(start, end)


def run(n: int, workers: int = 4) -> int:


    ranges = split_ranges(n, workers)


    results: Queue = Queue()

    def worker(start, end):
        try:
            results.put(calculate_sum(start, end))
        except Exception as error:


            results.put(error)


    threads = [threading.Thread(target=worker, args=interval) for interval in ranges]
    for thread in threads:
        thread.start()


    for thread in threads:
        thread.join()


    values = [results.get_nowait() for _ in threads]
    for value in values:
        if isinstance(value, Exception):
            raise value
    return sum(values)


if __name__ == "__main__":


    cli(run, "threading")
```

## `lab2/task2/async_parser.py`

```python
import asyncio
import ssl

import aiohttp
import certifi
from sqlalchemy.ext.asyncio import AsyncSession

from lab2.common import split_items
from lab2.task2.common import HEADERS, MAX_BYTES, TIMEOUT, Outcome, cli, emit, extract_page, validate_url
from lab2.task2.database import async_engine, save_record


async def parse_and_save(url: str, *, client=None, engine=None) -> Outcome:


    if client is None or engine is None:
        return (await run_async([url], workers=1))[0]
    try:
        validate_url(url)


        async with client.get(url, allow_redirects=False) as response:
            if response.status != 200:
                raise ValueError(f"HTTP {response.status}")
            html = bytearray()


            async for chunk in response.content.iter_chunked(65_536):
                html.extend(chunk)
                if len(html) > MAX_BYTES:
                    raise ValueError("Page exceeds 2 MB")


        data = extract_page(url, bytes(html))


        async with AsyncSession(engine) as session, session.begin():


            result = await session.run_sync(save_record, data)
    except Exception as error:
        result = Outcome(url=url, ok=False, error=type(error).__name__ + ": " + str(error)[:160])

    return emit(result)


async def run_async(urls: list[str], workers: int = 3) -> list[Outcome]:
    batches = split_items(urls, workers)
    engine = async_engine()


    connector = aiohttp.TCPConnector(limit=len(batches), ssl=ssl.create_default_context(cafile=certifi.where()), force_close=True)
    try:
        async with aiohttp.ClientSession(connector=connector, headers=HEADERS,
                                         timeout=aiohttp.ClientTimeout(total=TIMEOUT), trust_env=True) as client:
            async def worker(batch):


                return [await parse_and_save(url, client=client, engine=engine) for url in batch]


            grouped = await asyncio.gather(*(worker(batch) for batch in batches))
            return [result for batch in grouped for result in batch]
    finally:

        await engine.dispose()


def run(urls: list[str], workers: int = 3) -> list[Outcome]:

    return asyncio.run(run_async(urls, workers))


if __name__ == "__main__":
    cli(run, "asyncio")
```

## `lab2/task2/benchmark.py`

```python
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
from statistics import median
from time import perf_counter, sleep

from lab2.task2 import async_parser, multiprocessing_parser, threading_parser
from lab2.task2.common import load_urls
from lab2.task2.database import dispose_engine, prepare_database


def main() -> None:


    parser = argparse.ArgumentParser(description="Compare complete download/parse/commit workflows")
    parser.add_argument("--urls", type=Path)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("lab2/results/io.json"))
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10:
        parser.error("repeats must be between 1 and 10")
    urls = load_urls(args.urls)
    prepare_database()
    dispose_engine()
    runners = [("threading", threading_parser.run), ("multiprocessing", multiprocessing_parser.run), ("asyncio", async_parser.run)]


    warmup = threading_parser.run(urls, args.workers)
    if not all(outcome.ok for outcome in warmup):
        raise SystemExit("Warmup failed; no comparison reported")
    samples = {name: [] for name, _ in runners}
    runs = []
    for repeat in range(args.repeats):


        for name, run in runners[repeat % 3:] + runners[:repeat % 3]:
            sleep(1)
            started = perf_counter()
            outcomes = run(urls, args.workers)


            elapsed = perf_counter() - started
            samples[name].append(elapsed)
            runs.append({"approach": name, "repeat": repeat + 1, "seconds": elapsed,
                         "outcomes": [asdict(value) for value in outcomes]})
            if not all(outcome.ok for outcome in outcomes):
                raise SystemExit(f"{name} failed; no successful comparison reported")


    report = {"measured_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
              "platform": platform.platform(), "workers": args.workers, "urls": urls,
              "repeats": args.repeats, "warmup": "One unmeasured threading pass; measured runs update existing pages",
              "rows": [{"approach": name, "median_seconds": median(samples[name]), "samples_seconds": samples[name]} for name, _ in runners],
              "runs": runs}
    args.output.parent.mkdir(parents=True, exist_ok=True)


    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    for row in report["rows"]:
        print(f"{row['approach']:16}: {row['median_seconds']:.6f}s", flush=True)


if __name__ == "__main__":
    main()
```

## `lab2/task2/common.py`

```python
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
```

## `lab2/task2/database.py`

```python
from functools import lru_cache
import os
import re
import secrets

from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.core.time import utc_now
from app.models import Book, ParsedPage, User
from lab2.task2.common import Outcome, PageData

IMPORT_EMAIL = "bookcrossing-parser@example.invalid"


def schema_name() -> str:

    schema = os.getenv("LAB2_DB_SCHEMA", "public")
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
        raise ValueError("Invalid PostgreSQL schema")
    return schema


@lru_cache(maxsize=1)
def get_engine():


    return create_engine(settings.database_url, connect_args={"options": f"-csearch_path={schema_name()}"})


def async_engine():

    url = make_url(settings.database_url).set(drivername="postgresql+asyncpg")
    return create_async_engine(url, connect_args={"server_settings": {"search_path": schema_name()}})


def dispose_engine() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
        get_engine.cache_clear()


def importer_id(session: Session) -> int:
    user_id = session.execute(select(User.id).where(User.email == IMPORT_EMAIL)).scalar_one_or_none()
    if user_id is None:

        session.execute(insert(User).values(
            name="BookCrossing importer", email=IMPORT_EMAIL,
            hashed_password=hash_password(secrets.token_urlsafe(32)), created_at=utc_now(),
        ).on_conflict_do_nothing(index_elements=[User.email]))
        user_id = session.execute(select(User.id).where(User.email == IMPORT_EMAIL)).scalar_one()
    return user_id


def prepare_database() -> None:


    with Session(get_engine()) as session, session.begin():
        session.execute(select(ParsedPage.id).limit(1))
        importer_id(session)


def save_record(session: Session, data: PageData) -> Outcome:


    session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:url, 0))"), {"url": data.url})
    page = session.execute(select(ParsedPage).where(ParsedPage.url == data.url)).scalar_one_or_none()
    if page is None:
        page = ParsedPage(url=data.url, title=data.title, source_host=data.source_host)
        session.add(page)
    page.title = data.title
    page.fetched_at = utc_now()


    if data.book_title and page.book_id is None:
        book = Book(title=data.book_title, author="Not specified by source",
                    description=f"Imported from {data.url}", created_by_id=importer_id(session))
        session.add(book)

        session.flush()
        page.book_id = book.id
    session.flush()
    return Outcome(url=data.url, ok=True, title=page.title, page_id=page.id, book_id=page.book_id)


def save_page(data: PageData) -> Outcome:


    with Session(get_engine()) as session, session.begin():
        return save_record(session, data)
```

## `lab2/task2/multiprocessing_parser.py`

```python
import multiprocessing

from lab2.common import split_items
from lab2.task2.common import Outcome, cli, download, emit, extract_page
from lab2.task2.database import save_page


def parse_and_save(url: str) -> Outcome:
    try:


        result = save_page(extract_page(url, download(url)))
    except Exception as error:


        result = Outcome(url=url, ok=False, error=type(error).__name__ + ": " + str(error)[:160])
    return emit(result)


def parse_batch(urls: list[str]) -> list[Outcome]:


    return [parse_and_save(url) for url in urls]


def run(urls: list[str], workers: int = 3) -> list[Outcome]:
    batches = split_items(urls, workers)


    with multiprocessing.get_context("spawn").Pool(len(batches)) as pool:


        grouped = pool.map(parse_batch, batches)

    return [outcome for batch in grouped for outcome in batch]


if __name__ == "__main__":

    cli(run, "multiprocessing")
```

## `lab2/task2/threading_parser.py`

```python
import threading
from queue import Queue

from lab2.common import split_items
from lab2.task2.common import Outcome, cli, download, emit, extract_page
from lab2.task2.database import dispose_engine, get_engine, save_page


def parse_and_save(url: str) -> Outcome:
    try:


        result = save_page(extract_page(url, download(url)))
    except Exception as error:

        result = Outcome(url=url, ok=False, error=type(error).__name__ + ": " + str(error)[:160])


    return emit(result)


def run(urls: list[str], workers: int = 3) -> list[Outcome]:


    batches = split_items(urls, workers)
    results: Queue = Queue()


    get_engine()

    def worker(batch):


        for url in batch:
            results.put(parse_and_save(url))

    threads = [threading.Thread(target=worker, args=(batch,)) for batch in batches]
    try:

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        return [results.get_nowait() for _ in urls]
    finally:


        dispose_engine()


if __name__ == "__main__":
    cli(run, "threading")
```
