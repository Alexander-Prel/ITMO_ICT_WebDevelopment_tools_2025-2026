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
