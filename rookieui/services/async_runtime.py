from __future__ import annotations

import asyncio
from collections.abc import Callable
import threading
from typing import Any, TypeVar
from weakref import WeakKeyDictionary


T = TypeVar("T")

WORK_LANE_LIMITS = {
    "provider": 4,
    "extras": 1,
    "controlnet": 1,
}

_LOOP_LANES: WeakKeyDictionary[asyncio.AbstractEventLoop, dict[str, asyncio.Semaphore]] = WeakKeyDictionary()
_LOOP_LANES_LOCK = threading.Lock()
_BACKGROUND_TASKS: set[asyncio.Task[Any]] = set()


def _lane_semaphore(name: str) -> asyncio.Semaphore:
    limit = WORK_LANE_LIMITS.get(name)
    if limit is None:
        raise ValueError(f"Unknown bounded work lane: {name}")
    loop = asyncio.get_running_loop()
    with _LOOP_LANES_LOCK:
        lanes = _LOOP_LANES.setdefault(loop, {})
        semaphore = lanes.get(name)
        if semaphore is None:
            semaphore = asyncio.Semaphore(limit)
            lanes[name] = semaphore
        return semaphore


async def run_bounded_blocking(
    lane: str,
    function: Callable[..., T],
    /,
    *args: Any,
    **kwargs: Any,
) -> T:
    semaphore = _lane_semaphore(lane)
    await semaphore.acquire()
    # IMPORTANT: blocking provider/native/model work must stay off the host aiohttp loop.
    try:
        worker = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    except BaseException:
        semaphore.release()
        raise
    try:
        result = await asyncio.shield(worker)
    except asyncio.CancelledError:
        # CRITICAL: cancelling an HTTP waiter does not stop its native thread; keep the lane
        # occupied until that worker really exits or a new request can overlap unsafe host work.
        async def release_after_worker() -> None:
            try:
                await worker
            except BaseException:
                pass
            finally:
                semaphore.release()

        release_task = asyncio.create_task(release_after_worker())
        _BACKGROUND_TASKS.add(release_task)
        release_task.add_done_callback(_BACKGROUND_TASKS.discard)
        raise
    except BaseException:
        semaphore.release()
        raise
    semaphore.release()
    return result
