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
