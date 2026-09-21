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
