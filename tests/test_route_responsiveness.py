from __future__ import annotations

import asyncio
import time
import unittest
from unittest import mock

from rookieui.api import routes


class _FakeJsonRequest:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    async def json(self) -> dict[str, object]:
        return self._payload


class _ExtrasResult:
    def to_payload(self) -> dict[str, object]:
        return {
            "mode": "single_image",
            "output_assets": [],
            "preview_asset": "",
            "preview_data_url": "",
            "warnings": [],
            "diagnostics": [],
        }


class RouteResponsivenessTests(unittest.TestCase):
    def _assert_health_responsive(self, route_coro_factory) -> None:
        self._work_started_at = None

        async def scenario() -> float:
            # Warm the per-loop executor so this test measures route blocking, not first-import/thread startup.
            await asyncio.to_thread(lambda: None)
            self._test_loop = asyncio.get_running_loop()
            self._work_started_event = asyncio.Event()
            route_task = asyncio.create_task(route_coro_factory())
            await asyncio.wait_for(self._work_started_event.wait(), timeout=0.6)
            self.assertIsNotNone(getattr(self, "_work_started_at", None))
            health = await asyncio.wait_for(routes.health(None), timeout=0.05)
            health_elapsed = time.perf_counter() - self._work_started_at
            await route_task
            self.assertEqual(health["status"], 200)
            return health_elapsed

        self.assertLess(asyncio.run(scenario()), 0.25)

    def test_health_remains_responsive_during_provider_work(self) -> None:
        def delayed_provider(_payload):
            self._work_started_at = time.perf_counter()
            self._test_loop.call_soon_threadsafe(self._work_started_event.set)
            time.sleep(0.35)
            return {"contract": {}, "provider_id": "test", "translated_text": "ok"}

        with mock.patch.object(routes, "execute_prompt_workbench_translate", side_effect=delayed_provider):
            self._assert_health_responsive(
                lambda: routes.prompt_tools_translate(_FakeJsonRequest({"text": "hello"}))
            )

    def test_health_remains_responsive_during_extras_work(self) -> None:
        def delayed_extras(_normalized):
            self._work_started_at = time.perf_counter()
            self._test_loop.call_soon_threadsafe(self._work_started_event.set)
            time.sleep(0.35)
            return _ExtrasResult()

        with (
            mock.patch.object(routes, "normalize_extras_request", return_value=object()),
            mock.patch.object(routes, "execute_extras_request", side_effect=delayed_extras),
        ):
            self._assert_health_responsive(
                lambda: routes.extras_run(_FakeJsonRequest({"mode": "single_image"}))
            )

    def test_z_health_remains_responsive_during_controlnet_work(self) -> None:
        def delayed_controlnet(_payload):
            self._work_started_at = time.perf_counter()
            self._test_loop.call_soon_threadsafe(self._work_started_event.set)
            time.sleep(0.35)
            return {
                "source": "rookieui",
                "detect_backend": "test",
                "processor": "none",
                "requested_controlnet_model": "",
                "warning_codes": [],
                "images": [],
            }

        with mock.patch.object(routes, "build_controlnet_detect_payload", side_effect=delayed_controlnet):
            self._assert_health_responsive(
                lambda: routes.controlnet_detect(
                    _FakeJsonRequest({"controlnet_module": "none", "image": "fixture"})
                )
            )


if __name__ == "__main__":
    unittest.main()
