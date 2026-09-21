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
