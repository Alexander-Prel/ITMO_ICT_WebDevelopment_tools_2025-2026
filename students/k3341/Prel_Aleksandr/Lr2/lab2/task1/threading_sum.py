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
