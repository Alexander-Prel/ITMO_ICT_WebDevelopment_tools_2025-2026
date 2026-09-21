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
