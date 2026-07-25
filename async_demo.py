"""A tiny demo proving how async overlaps waiting time.

Run it with:  python async_demo.py

It simulates three slow "LLM calls" (each just waits 2 seconds) and times
how long they take when run one-after-another vs. concurrently with async.
"""

import asyncio
import time


# ---- The SYNCHRONOUS way: each wait blocks the next one ----
def blocking_call(name: str, seconds: float) -> str:
    time.sleep(seconds)  # a real, blocking wait — nothing else can happen
    return name


def run_sync() -> float:
    start = time.perf_counter()
    for name in ["A", "B", "C"]:
        blocking_call(name, 2)  # must finish A before B can start
    return time.perf_counter() - start


# ---- The ASYNC way: the waits overlap ----
async def async_call(name: str, seconds: float) -> str:
    await asyncio.sleep(seconds)  # a *non-blocking* wait — releases the worker
    return name


async def run_async() -> float:
    start = time.perf_counter()
    # gather() starts all three at once and waits for them together.
    await asyncio.gather(
        async_call("A", 2),
        async_call("B", 2),
        async_call("C", 2),
    )
    return time.perf_counter() - start


print("Three tasks, each 'waiting' 2 seconds:\n")
print(f"  Synchronous (one after another): {run_sync():.1f}s")
print(f"  Async (overlapping waits):       {asyncio.run(run_async()):.1f}s")
