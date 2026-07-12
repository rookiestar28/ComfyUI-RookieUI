from __future__ import annotations

import asyncio
import importlib.util
import threading
import time
import unittest


class AsyncRuntimeTests(unittest.TestCase):
    def test_named_worker_lanes_have_bounded_limits_and_serialize_host_work(self) -> None:
        spec = importlib.util.find_spec("rookieui.services.async_runtime")
        self.assertIsNotNone(spec, "bounded async runtime module is required")
        if spec is None:
            return

        from rookieui.services import async_runtime

        self.assertEqual(async_runtime.WORK_LANE_LIMITS, {"provider": 4, "extras": 1, "controlnet": 1})

        async def exercise(lane: str, task_count: int) -> int:
            active = 0
            maximum = 0
            guard = threading.Lock()

            def delayed_work() -> None:
                nonlocal active, maximum
                with guard:
                    active += 1
                    maximum = max(maximum, active)
                time.sleep(0.03)
                with guard:
                    active -= 1

            await asyncio.gather(
                *(async_runtime.run_bounded_blocking(lane, delayed_work) for _ in range(task_count))
            )
            return maximum

        self.assertEqual(asyncio.run(exercise("extras", 3)), 1)
        self.assertEqual(asyncio.run(exercise("controlnet", 3)), 1)
        provider_maximum = asyncio.run(exercise("provider", 8))
        self.assertGreater(provider_maximum, 1)
        self.assertLessEqual(provider_maximum, 4)

    def test_unknown_lane_fails_closed(self) -> None:
        spec = importlib.util.find_spec("rookieui.services.async_runtime")
        self.assertIsNotNone(spec, "bounded async runtime module is required")
        if spec is None:
            return

        from rookieui.services import async_runtime

        async def run() -> None:
            with self.assertRaises(ValueError):
                await async_runtime.run_bounded_blocking("unknown", lambda: None)

        asyncio.run(run())

    def test_cancelled_request_keeps_serial_lane_held_until_worker_finishes(self) -> None:
        spec = importlib.util.find_spec("rookieui.services.async_runtime")
        self.assertIsNotNone(spec, "bounded async runtime module is required")
        if spec is None:
            return

        from rookieui.services import async_runtime

        first_started = threading.Event()
        first_release = threading.Event()
        second_started = threading.Event()

        def first_work() -> None:
            first_started.set()
            first_release.wait(1.0)

        def second_work() -> None:
            second_started.set()

        async def run() -> None:
            first_task = asyncio.create_task(
                async_runtime.run_bounded_blocking("extras", first_work)
            )
            await asyncio.to_thread(first_started.wait, 0.5)
            first_task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first_task

            second_task = asyncio.create_task(
                async_runtime.run_bounded_blocking("extras", second_work)
            )
            await asyncio.sleep(0.05)
            self.assertFalse(second_started.is_set())
            first_release.set()
            await asyncio.wait_for(second_task, timeout=0.5)
            self.assertTrue(second_started.is_set())

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
