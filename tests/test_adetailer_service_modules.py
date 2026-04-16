from __future__ import annotations

import unittest


class ADetailerServiceModuleTests(unittest.TestCase):
    def test_vertical_modules_import_cleanly(self) -> None:
        import rookieui.services.adetailer_catalog as adetailer_catalog
        import rookieui.services.adetailer_normalization as adetailer_normalization
        import rookieui.services.adetailer_refinement as adetailer_refinement
        import rookieui.services.adetailer_warnings as adetailer_warnings

        self.assertTrue(callable(adetailer_catalog.build_detector_entries))
        self.assertTrue(callable(adetailer_catalog.build_adetailer_catalog_payload))
        self.assertTrue(callable(adetailer_normalization.normalize_adetailer_payload))
        self.assertTrue(callable(adetailer_refinement.build_normalized_unit_request))
        self.assertTrue(callable(adetailer_warnings.build_adetailer_warning_code_payload))

    def test_adetailer_facade_keeps_public_entrypoints(self) -> None:
        import rookieui.services.adetailer as adetailer

        self.assertTrue(callable(adetailer.build_adetailer_warning_code_payload))
        self.assertTrue(callable(adetailer.build_adetailer_availability_payload))
        self.assertTrue(callable(adetailer.build_adetailer_catalog_payload))
        self.assertTrue(callable(adetailer.build_adetailer_capability_payload))
        self.assertTrue(callable(adetailer.normalize_adetailer_payload))
