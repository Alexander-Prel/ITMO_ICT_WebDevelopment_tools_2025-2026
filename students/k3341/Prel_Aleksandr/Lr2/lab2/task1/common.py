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
