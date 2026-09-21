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
