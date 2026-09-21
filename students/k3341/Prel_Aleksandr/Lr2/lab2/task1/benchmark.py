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
