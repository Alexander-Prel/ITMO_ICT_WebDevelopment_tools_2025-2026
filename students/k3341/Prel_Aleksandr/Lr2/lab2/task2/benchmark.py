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
