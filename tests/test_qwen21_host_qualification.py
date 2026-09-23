from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any
from unittest import mock

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from rookieui.contracts.models import ModelInventorySnapshot
from rookieui.services import generation_metadata, pnginfo
from rookieui.services.img2img import normalize_img2img_request
from rookieui.services.txt2img import normalize_txt2img_request
from rookieui.services.workflow_translation import translate_img2img_request, translate_txt2img_request


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_qwen21_host_qualification.py"
SPEC = importlib.util.spec_from_file_location("qwen21_host_qualification", SCRIPT)
assert SPEC and SPEC.loader
qualification = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qualification
SPEC.loader.exec_module(qualification)

DIFFUSION = "Qwen_Image\\qwen_image_2.1_int8_convrot.safetensors"
DIFFUSION_SHA256 = "cb74113cb03faecd79611b01fd7fd642f0aa60d6f0b95086abee214d75eaa57d"  # pragma: allowlist secret - public artifact digest
DIFFUSION_SIZE = 7256783064
ENCODER = "qwen3vl_8b_int8_convrot.safetensors"
VAE = "qwen_image_2.1_vae_bf16.safetensors"
TREE = "e7b429d7f2e73bb5b97a0aa70336960489bbe6b9"  # pragma: allowlist secret - public Git tree id
CORE = "e638023d54497dbe0579565e5de4bb7076899592"  # pragma: allowlist secret - public Git commit id
FRONTEND_H1 = "38f822ff4d165ccc57e39587761928f95ab63e96c9cbff53041e91bf68f395cc"  # pragma: allowlist secret - public artifact digest
FRONTEND_H2 = "646c7d93ee00987398471b5abd58a17a238017a5385917a2394a2d05635b8302"  # pragma: allowlist secret - public artifact digest


def _png(size: tuple[int, int], color: tuple[int, int, int, int], info: PngInfo | None = None) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, format="PNG", pnginfo=info)
    return buffer.getvalue()


def valid_config(root: Path) -> dict[str, Any]:
    digest = "a" * 64
    fixtures = root / "fixtures"
    fixtures.mkdir(exist_ok=True)
    entries = []
    for index, name in enumerate([f"ref_{i:02d}" for i in range(1, 11)] + ["remove_background"]):
        data = _png((512, 512), (index * 20, 40, 200 - index * 10, 255))
        (fixtures / f"{name}.png").write_bytes(data)
        entries.append({"id": name, "filename": f"{name}.png", "sha256": hashlib.sha256(data).hexdigest()})
    (fixtures / "manifest.json").write_text(json.dumps(entries), encoding="utf-8")
    selectors = {"diffusion_primary": DIFFUSION, "encoder_int8": ENCODER, "vae_bf16": VAE}
    return {
        "schema": "Qwen21HostConfigV1",
        "host": "H1",
        "base_url": "http://127.0.0.1:8188/",
        "candidate_tree": TREE,
        "core_root": str(root / "core"),
        "rookieui_install_root": str(root / "core" / "custom_nodes" / "comfyui-rookieui"),
        "host_output_root": str(root / "host-output"),
        "core_head": CORE,
        "frontend_index_sha256": FRONTEND_H1,
        "fixture_manifest": str(fixtures / "manifest.json"),
        "fixture_manifest_sha256": digest,
        "process_pid": 123,
        "process_created_utc": "2026-09-22T11:00:00.0000000Z",
        "process_command_sha256": digest,
        "budgets": {"request_timeout_seconds": 30, "poll_timeout_seconds": 300},
        "models": {
            role: {
                "selector": selectors[role], "path": str(root / role),
                "sha256": DIFFUSION_SHA256 if role == "diffusion_primary" else digest,
                "size": DIFFUSION_SIZE if role == "diffusion_primary" else 1,
            }
            for role in ("diffusion_primary", "encoder_int8", "vae_bf16")
        },
        "legacy_controls": [{
            "id": "sdxl-txt2img", "profile": "sdxl", "route": "txt2img",
            "request": {"width": 1024, "height": 1024, "steps": 4},
            "assets": {"checkpoint_name": {
                "selector": "SDXL\\synthetic.safetensors", "path": str(root / "sdxl"), "sha256": digest,
                "size": 1, "catalogs": ["checkpoints"],
            }},
            "expected_width": 1024, "expected_height": 1024,
        }],
        "legacy_unavailable": [{"id": "sd15-txt2img", "profile": "sd15", "reason": "asset_not_installed"}],
    }


def load(root: Path, **overrides: Any) -> Any:
    payload = valid_config(root)
    payload.update(overrides)
    path = root / "config.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return qualification.load_config(path)


class FakeHost:
    """Answers runner requests with the repository's real Qwen 2.1 normalization and graph builders."""

    def __init__(self, config: Any) -> None:
        self.config = config
        self.input_root = config.rookieui_install_root / ".rookieui_runtime" / "input"
        self.input_root.mkdir(parents=True, exist_ok=True)
        config.host_output_root.mkdir(parents=True, exist_ok=True)
        self.posts: list[tuple[str, dict[str, Any]]] = []
        self.jobs: dict[str, dict[str, Any]] = {}
        self.queue_queries: list[tuple[str, str]] = []
        self.output_size = (512, 512)
        self.output_color = (220, 30, 30, 255)

    def _inventory(self) -> ModelInventorySnapshot:
        return ModelInventorySnapshot(source="host", diffusion_models=[DIFFUSION], text_encoders=[ENCODER], vae=[VAE])

    def _store(self, data_url: str) -> str:
        data = base64.b64decode(data_url.split(",", 1)[1])
        handle = f"rookieui_{hashlib.sha256(data).hexdigest()[:16]}.png"
        (self.input_root / handle).write_bytes(data)
        return handle

    def post(self, config: Any, route: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        self.posts.append((route, json.loads(json.dumps(payload))))
        body = dict(payload)
        dry_run = bool(body.pop("dry_run", False))
        client_id = body.pop("client_id", None)
        if "reference_images" in body:
            body["reference_images"] = [
                {"image_asset": ref["image_asset"]} if "image_asset" in ref else {"image_asset": self._store(ref["image_data"])}
                for ref in body["reference_images"]
            ]
        try:
            with mock.patch("rookieui.services.img2img.discover_model_inventory", return_value=self._inventory()), \
                    mock.patch("rookieui.services.txt2img.discover_model_inventory", return_value=self._inventory()), \
                    mock.patch("rookieui.services.img2img.resolve_asset_path", return_value=Path("synthetic.png")):
                if route.endswith("txt2img"):
                    translation = translate_txt2img_request(normalize_txt2img_request(body))
                else:
                    translation = translate_img2img_request(normalize_img2img_request(body))
        except ValueError:
            return 400, {"status": "invalid-request"}
        response = translation.to_payload()
        if dry_run:
            response["submission"] = {"accepted": False, "mode": "dry-run"}
            return 200, response
        prompt_id = str(uuid.uuid4())
        filename = f"RookieUI_{len(self.jobs):05d}_.png"
        (self.config.host_output_root / filename).write_bytes(_png(self.output_size, self.output_color))
        self.jobs[prompt_id] = {"id": prompt_id, "client_id": client_id, "status": "completed",
                                "reusable_outputs": [filename], "output_filenames": [filename]}
        response.update({"mode": "queued", "submission": {"prompt_id": prompt_id}})
        return 200, response

    def queue_job(self, config: Any, prompt_id: str, client_id: str) -> dict[str, Any] | None:
        self.queue_queries.append((prompt_id, client_id))
        job = self.jobs.get(prompt_id)
        return job if job and job["client_id"] == client_id else None

    def job_count(self, config: Any, client_id: str) -> int:
        return sum(job["client_id"] == client_id for job in self.jobs.values())

    def get_bytes(self, config: Any, route: str, *, limit: int = 0) -> bytes:
        filename = route.split("filename=", 1)[1].split("&", 1)[0]
        return (self.config.host_output_root / filename).read_bytes()

    def patches(self) -> list[Any]:
        return [
            mock.patch.object(qualification, "_post_json", side_effect=self.post),
            mock.patch.object(qualification, "_get_json", return_value={"queue_running": [], "queue_pending": []}),
            mock.patch.object(qualification, "_queue_job", side_effect=self.queue_job),
            mock.patch.object(qualification, "_client_job_count", side_effect=self.job_count),
            mock.patch.object(qualification, "_get_bytes", side_effect=self.get_bytes),
            mock.patch.object(qualification, "_vram_free", return_value=qualification.MINIMUM_FREE_VRAM_BYTES),
            mock.patch.object(qualification.time, "sleep"),
        ]


class HostQualificationConfigTests(unittest.TestCase):
    def test_config_uses_exact_convrot_primary_and_rejects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = load(root)
            self.assertEqual(config.models["diffusion_primary"].selector, DIFFUSION)
            self.assertEqual(config.models["diffusion_primary"].sha256, DIFFUSION_SHA256)
            self.assertEqual(config.models["diffusion_primary"].size, DIFFUSION_SIZE)
            for field, value in (("selector", "Qwen_Image\\qwen_image_2.1_bf16.safetensors"),
                                 ("sha256", "b" * 64), ("size", DIFFUSION_SIZE + 1)):
                payload = valid_config(root)
                payload["models"]["diffusion_primary"][field] = value
                with self.subTest(field=field), self.assertRaisesRegex(qualification.QualificationError,
                                                                       "config_primary_diffusion_identity"):
                    path = root / f"wrong-{field}.json"
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    qualification.load_config(path)

    def test_config_accepts_real_sha1_git_object_ids(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            config = load(Path(folder))
        self.assertEqual((config.candidate_tree, config.core_head), (TREE, CORE))

    def test_config_rejects_malformed_git_object_ids(self) -> None:
        for value in (TREE[:-1], TREE.upper(), TREE + "0", "g" * 40):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as folder:
                with self.assertRaisesRegex(qualification.QualificationError, "config_candidate"):
                    load(Path(folder), candidate_tree=value)

    def test_config_pins_frontend_digest_to_host_identity(self) -> None:
        for host, digest in (("H1", FRONTEND_H2), ("H2", FRONTEND_H1)):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as folder:
                with self.assertRaisesRegex(qualification.QualificationError, "config_frontend_identity"):
                    load(Path(folder), host=host, frontend_index_sha256=digest)
        for host, digest in (("H1", FRONTEND_H1), ("H2", FRONTEND_H2)):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as folder:
                self.assertEqual(load(Path(folder), host=host, frontend_index_sha256=digest).host, host)

    def test_config_rejects_remote_or_credentialed_host(self) -> None:
        for url in ("https://example.com:8188", "http://user:pass@127.0.0.1:8188", "http://127.0.0.1:8189"):  # pragma: allowlist secret
            with self.subTest(url=url), tempfile.TemporaryDirectory() as folder:
                with self.assertRaisesRegex(qualification.QualificationError, "config_url"):
                    load(Path(folder), base_url=url)

    def test_legacy_control_cannot_override_runner_owned_fields(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            payload = valid_config(Path(folder))
            for key in ("prompt", "seed", "client_id", "checkpoint_name"):
                control = dict(payload["legacy_controls"][0], request={"steps": 4, key: "x"})
                with self.subTest(key=key), self.assertRaisesRegex(qualification.QualificationError, "config_legacy_request"):
                    load(Path(folder), legacy_controls=[control])

    def test_standard_int8_variant_is_not_part_of_the_required_case_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(qualification.expected_case_ids(load(root)), qualification.CASE_IDS)
            self.assertFalse(any("INT8" in case_id for case_id in qualification.expected_case_ids(load(root))))
            variant = {"diffusion_int8": {"selector": "Qwen_Image\\qwen_image_2.1_int8.safetensors",
                                          "path": str(root / "int8"), "sha256": "b" * 64, "size": 1}}
            with self.assertRaisesRegex(qualification.QualificationError, "config_variants"):
                load(root, variants=variant)

    def test_script_path_invocation_can_import_repository_package(self) -> None:
        probe = (
            "import runpy, sys\n"
            f"sys.path[:] = [p for p in sys.path if p not in ('', {str(ROOT)!r})]\n"
            f"sys.path.insert(0, {str(SCRIPT.parent)!r})\n"
            f"runpy.run_path({str(SCRIPT)!r})\n"
            "import rookieui.services.version\n"
        )
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-c", probe], cwd=folder, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace")[-400:])


class HostQualificationResultTests(unittest.TestCase):
    def test_existing_result_is_never_overwritten_or_host_contacted(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            load(root)
            output = root / "result.json"
            output.write_bytes(b"preserved")
            with mock.patch.object(qualification, "preflight") as preflight:
                code = qualification.main(["--config", str(root / "config.json"), "--phase", "preflight", "--output", str(output)])
            self.assertEqual(code, 1)
            preflight.assert_not_called()
            self.assertEqual(output.read_bytes(), b"preserved")

    def test_failed_preflight_result_contains_only_safe_code(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            load(root)
            output = root / "result.json"
            with mock.patch.object(qualification, "preflight", side_effect=RuntimeError("private prompt and host path")):
                code = qualification.main(["--config", str(root / "config.json"), "--phase", "preflight", "--output", str(output)])
            self.assertEqual(code, 1)
            text = output.read_text(encoding="utf-8")
            self.assertEqual(json.loads(text)["error_code"], "unexpected_runtimeerror")
            self.assertNotIn("private prompt", text)

    def test_execute_cannot_report_pass_without_complete_cases(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            load(root)
            output = root / "result.json"
            with mock.patch.object(qualification, "preflight", return_value={}), \
                    mock.patch.object(qualification, "execute_cases", return_value=[]):
                code = qualification.main(["--config", str(root / "config.json"), "--phase", "execute", "--output", str(output)])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["error_code"], "case_matrix_not_accepted")

    def test_reviewable_execute_is_pending_not_pass(self) -> None:
        rows = [dict(qualification._new_row(case), status="PENDING_REVIEW" if case in qualification.SEMANTIC_CHECKLISTS else "PASS",
                     child_exit=0) for case in qualification.CASE_IDS]
        self.assertEqual(qualification._aggregate(rows, qualification.CASE_IDS), "PENDING_REVIEW")
        rows[-1]["child_exit"] = 1
        self.assertEqual(qualification._aggregate(rows, qualification.CASE_IDS), "FAIL")

    def test_candidate_mismatch_blocks_host_contact(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            config = load(Path(folder))
            with mock.patch.object(qualification, "_git", return_value="b" * 40), \
                    mock.patch.object(qualification, "_get_bytes") as request:
                with self.assertRaisesRegex(qualification.QualificationError, "candidate_tree_mismatch"):
                    qualification.preflight(config)
            request.assert_not_called()


class HostQualificationCaseTests(unittest.TestCase):
    def test_generation_capacity_requires_idle_queue_and_minimum_vram(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            config = load(Path(folder))
            minimum = qualification.MINIMUM_FREE_VRAM_BYTES
            with mock.patch.object(qualification, "_get_json", return_value={"queue_running": [], "queue_pending": []}), \
                    mock.patch.object(qualification, "_vram_free", return_value=minimum):
                self.assertEqual(qualification._assert_generation_capacity(config), minimum)
            with mock.patch.object(qualification, "_get_json", return_value={"queue_running": [{}], "queue_pending": []}), \
                    mock.patch.object(qualification, "_vram_free") as vram:
                with self.assertRaisesRegex(qualification.QualificationError, "host_queue_busy"):
                    qualification._assert_generation_capacity(config)
                vram.assert_not_called()
            with mock.patch.object(qualification, "_get_json", return_value={"queue_running": [], "queue_pending": []}), \
                    mock.patch.object(qualification, "_vram_free", return_value=minimum - 1):
                with self.assertRaisesRegex(qualification.QualificationError, "host_vram_low"):
                    qualification._assert_generation_capacity(config)
            with mock.patch.object(qualification, "_get_json", return_value={"queue_running": [], "queue_pending": []}), \
                    mock.patch.object(qualification, "_vram_free", return_value=None):
                with self.assertRaisesRegex(qualification.QualificationError, "host_vram_unavailable"):
                    qualification._assert_generation_capacity(config)
            with mock.patch.object(qualification, "_get_json", return_value={"queue_running": [], "queue_pending": []}), \
                    mock.patch.object(qualification, "_vram_free", return_value=True):
                with self.assertRaisesRegex(qualification.QualificationError, "host_vram_unavailable"):
                    qualification._assert_generation_capacity(config)

    def test_completed_generation_requires_post_run_vram_observation(self) -> None:
        for after in (None, True):
            with self.subTest(after=after), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                config = load(root)
                host = FakeHost(config)
                plan = qualification._case_plan(config, "Q21-T2I-SQUARE", "fresh-client")
                host.output_size = (plan.width, plan.height)
                row = qualification._new_row("Q21-T2I-SQUARE")
                patches = host.patches() + [mock.patch.object(qualification, "_vram_free",
                                                               side_effect=[qualification.MINIMUM_FREE_VRAM_BYTES, after])]
                for patch in patches:
                    patch.start()
                try:
                    with self.assertRaisesRegex(qualification.QualificationError, "host_vram_unavailable"):
                        qualification._submit_and_collect(
                            config, plan.route, plan.payload, "fresh-client", (plan.width, plan.height),
                            root / "images" / "Q21-T2I-SQUARE.png", row,
                        )
                finally:
                    for patch in reversed(patches):
                        patch.stop()

    def test_generation_uses_exact_client_job_when_snapshot_history_is_capped(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = load(root)
            host = FakeHost(config)
            plan = qualification._case_plan(config, "Q21-T2I-SQUARE", "fresh-client")
            host.output_size = (plan.width, plan.height)
            row = qualification._new_row("Q21-T2I-SQUARE")
            host_patches = host.patches()
            for patch in host_patches:
                patch.start()
            # Model the aggregate page omitting this completed job while exact prompt lookup works.
            count_patch = mock.patch.object(qualification, "_client_job_count", return_value=0)
            count_mock = count_patch.start()
            try:
                job, _image, original = qualification._submit_and_collect(
                    config,
                    plan.route,
                    plan.payload,
                    "fresh-client",
                    (plan.width, plan.height),
                    root / "images" / "Q21-T2I-SQUARE.png",
                    row,
                )
            finally:
                count_patch.stop()
                for patch in reversed(host_patches):
                    patch.stop()

            self.assertEqual(job["id"], row["prompt_id"])
            self.assertEqual(row["terminal_status"], "completed")
            self.assertTrue(row["history_matched"])
            self.assertTrue(row["original_decoded"])
            self.assertEqual(hashlib.sha256(original).hexdigest(), row["original_sha256"])
            self.assertEqual(row["vram_free_after"], qualification.MINIMUM_FREE_VRAM_BYTES)
            self.assertEqual(host.queue_queries[0], (job["id"], "fresh-client"))
            self.assertEqual(host.queue_queries[-1][0], job["id"])
            self.assertNotEqual(host.queue_queries[-1][1], "fresh-client")
            self.assertEqual(count_mock.call_count, 1)

    def test_submission_rejects_a_nonfresh_client_before_enqueue(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            config = load(Path(folder))
            row = qualification._new_row("Q21-T2I-SQUARE")
            with mock.patch.object(qualification, "_client_job_count", return_value=1), \
                    mock.patch.object(qualification, "_assert_generation_capacity", create=True) as guard, \
                    mock.patch.object(qualification, "_post_json") as post:
                with self.assertRaisesRegex(qualification.QualificationError, "client_id_not_fresh"):
                    qualification._submit_and_collect(
                        config,
                        "/rookieui/generate/txt2img",
                        {},
                        "reused-client",
                        (512, 512),
                        Path(folder) / "image.png",
                        row,
                    )
            guard.assert_not_called()
            post.assert_not_called()

    def test_submission_runs_capacity_guard_before_posting(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            config = load(Path(folder))
            row = qualification._new_row("Q21-T2I-SQUARE")
            with mock.patch.object(qualification, "_client_job_count", return_value=0), \
                    mock.patch.object(qualification, "_assert_generation_capacity", create=True,
                                      side_effect=qualification.QualificationError("host_queue_busy")) as guard, \
                    mock.patch.object(qualification, "_post_json") as post:
                with self.assertRaisesRegex(qualification.QualificationError, "host_queue_busy"):
                    qualification._submit_and_collect(
                        config, "/rookieui/generate/txt2img", {}, "fresh-client", (512, 512),
                        Path(folder) / "image.png", row,
                    )
                guard.assert_called_once_with(config)
                post.assert_not_called()

    def test_graph_rejects_lexical_reference_reordering(self) -> None:
        required = ("UNETLoader", "CLIPLoader", "VAELoader", "KSampler", "VAEDecode", "EmptyLatentImage")
        graph = {str(index): {"class_type": name, "inputs": {"width": 512, "height": 512} if name == "EmptyLatentImage" else {}}
                 for index, name in enumerate(required)}
        graph["99"] = {"class_type": "TextEncodeQwenImage21",
                       "inputs": {f"images.image_{index}": [str(index), 0] for index in (1, 10, 2, 3, 4, 5, 6, 7, 8, 9)}}
        self.assertEqual(qualification._validate_graph({"workflow": graph}, 10, 512, 512), ["workflow_reference_order"])

    def test_background_gate_rejects_opaque_background(self) -> None:
        with self.assertRaisesRegex(qualification.QualificationError, "background_alpha_gate"):
            qualification._background_alpha_gate(Image.new("RGBA", (512, 512), (215, 38, 45, 255)))

    def test_ten_reference_payload_preserves_numeric_order(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            config = load(Path(folder))
            with mock.patch.object(qualification, "_fixture_data_url", side_effect=lambda _config, name: name):
                plan = qualification._case_plan(config, "Q21-EDIT-10-REF", "client")
        self.assertEqual((plan.route, plan.width, plan.height), ("/rookieui/generate/img2img", 512, 512))
        self.assertEqual([entry["image_data"] for entry in plan.payload["reference_images"]],
                         [f"ref_{index:02d}" for index in range(1, 11)])

    def test_real_builder_graphs_satisfy_case_contracts(self) -> None:
        for case_id in qualification.CASE_IDS:
            if case_id not in qualification.IMAGE_CASES:
                continue
            with self.subTest(case_id=case_id), tempfile.TemporaryDirectory() as folder:
                config = load(Path(folder))
                host = FakeHost(config)
                plan = qualification._case_plan(config, case_id, "client")
                self.assertEqual(plan.payload["checkpoint_name"], config.models["diffusion_primary"].selector)
                status, response = host.post(config, plan.route, {**plan.payload, "dry_run": True})
                self.assertEqual(status, 200)
                self.assertEqual(qualification._validate_graph(response, len(plan.fixtures), plan.width, plan.height,
                                                               config=config, case_id=case_id), [])

    def test_graph_rejects_swapped_conditioning_slots(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            config = load(Path(folder))
            plan = qualification._case_plan(config, "Q21-T2I-SQUARE", "client")
            _, response = FakeHost(config).post(config, plan.route, {**plan.payload, "dry_run": True})
            sampler = next(node for node in response["workflow"].values() if node["class_type"] == "KSampler")
            sampler["inputs"]["positive"], sampler["inputs"]["negative"] = sampler["inputs"]["negative"], sampler["inputs"]["positive"]
            self.assertEqual(qualification._validate_graph(response, 0, 1024, 1024, config=config, case_id="Q21-T2I-SQUARE"),
                             ["workflow_conditioning_slots"])

    def test_primary_promotion_submits_reference_two_as_image_one(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            config = load(Path(folder))
            host = FakeHost(config)
            row = qualification._new_row("Q21-EDIT-2-REF")
            patches = host.patches()
            for patch in patches:
                patch.start()
            try:
                qualification._run_image_case(config, "Q21-EDIT-2-REF", Path(folder) / "images", row)
            finally:
                for patch in reversed(patches):
                    patch.stop()
            self.assertEqual(row["status"], "PENDING_REVIEW", row.get("error_code"))
            ref_1 = hashlib.sha256(qualification._fixture_bytes(config, "ref_01")).hexdigest()[:16]
            ref_2 = hashlib.sha256(qualification._fixture_bytes(config, "ref_02")).hexdigest()[:16]
            self.assertEqual(row["input_handles"], [f"rookieui_{ref_2}.png", f"rookieui_{ref_1}.png"])
            submitted = [payload for _, payload in host.posts if not payload.get("dry_run")]
            self.assertEqual(len(submitted), 1)
            self.assertEqual(submitted[0]["reference_images"], [{"image_asset": handle} for handle in row["input_handles"]])
            self.assertEqual(submitted[0]["main_reference_index"], 0)
            self.assertEqual(row["semantic_checklist"], list(qualification.SEMANTIC_CHECKLISTS["Q21-EDIT-2-REF"]))

    def test_negative_rows_are_rejected_by_real_normalization_before_enqueue(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            config = load(Path(folder))
            host = FakeHost(config)
            row = qualification._new_row("Q21-NEGATIVE")
            patches = host.patches() + [mock.patch.object(qualification, "_get_json",
                                                          return_value={"clip": [ENCODER], "text_encoders": [ENCODER]})]
            for patch in patches:
                patch.start()
            try:
                qualification._run_negative_case(config, row)
            finally:
                for patch in reversed(patches):
                    patch.stop()
            self.assertEqual(row["status"], "PASS", row.get("error_code"))
            self.assertEqual(len(row["rejections"]), 9)
            self.assertFalse(host.jobs)
            self.assertTrue(all(not payload.get("dry_run") for _, payload in host.posts))

    def test_negative_row_fails_closed_when_a_bad_request_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            config = load(Path(folder))
            with mock.patch.object(qualification, "_get_json", return_value={"clip": [], "text_encoders": []}), \
                    mock.patch.object(qualification, "_post_json", return_value=(200, {"mode": "queued"})), \
                    mock.patch.object(qualification, "_client_job_count", return_value=1):
                with self.assertRaisesRegex(qualification.QualificationError, "negative_wrong_diffusion_role"):
                    qualification._run_negative_case(config, qualification._new_row("Q21-NEGATIVE"))

    def test_transfer_accepts_rookieui_a1111_infotext_and_binds_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = load(root)
            host = FakeHost(config)
            request = {"profile": "qwen_image_21_edit", "prompt": qualification.BACKGROUND_REMOVAL_INSTRUCTION,
                       "negative_prompt": "", "steps": 25, "sampler_name": "euler", "scheduler_name": "simple",
                       "cfg_scale": 1.0, "seed": qualification.SEED, "output_size_mode": "reference",
                       "checkpoint_name": DIFFUSION, "vae_name": VAE, "mode": "img2img", "denoise_strength": 1.0,
                       "reference_image_assets": ["a.png"], "reference_resolution": 0, "edit_task": "background_removal"}
            metadata = generation_metadata.build_generation_metadata_payload(request, workflow_kind="img2img",
                                                                              profile="qwen_image_21_edit")
            info = PngInfo()
            info.add_text("parameters", metadata["parameters"])
            for key, value in metadata["extra_pnginfo"].items():
                info.add_text(key, json.dumps(value))
            original = _png((512, 512), (200, 20, 20, 90), info)
            config.host_output_root.mkdir(parents=True, exist_ok=True)
            (config.host_output_root / "RookieUI_00001_.png").write_bytes(original)
            image_path = root / "Q21-REMOVE-BG.png"
            image_path.write_bytes(original)
            source = {"case_id": "Q21-REMOVE-BG", "status": "PENDING_REVIEW", "width": 512, "height": 512,
                      "original_sha256": hashlib.sha256(original).hexdigest(), "output_handle": "RookieUI_00001_.png"}

            def inspect(route: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
                with mock.patch("rookieui.services.asset_store._INPUT_ROOT", host.input_root), \
                        mock.patch("rookieui.services.asset_store._ensure_runtime_dirs"):
                    return 200, {"status": "ok", **pnginfo.parse_pnginfo_payload(payload).to_payload()}

            def post(config_arg: Any, route: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
                return inspect(route, payload) if route.endswith("pnginfo/inspect") else host.post(config_arg, route, payload)

            row = qualification._new_row("Q21-TRANSFER")
            with mock.patch.object(qualification, "_post_json", side_effect=post):
                qualification._run_transfer_case(config, source, image_path, row)
            self.assertEqual(row["status"], "PASS")
            self.assertEqual(row["alpha_summary"]["min"], 90)
            self.assertEqual(row["input_handles"][1], "RookieUI_00001_.png")

            comfy_only = dict(inspect("", {"image_data": "data:image/png;base64," + base64.b64encode(original).decode()})[1],
                              source_type="comfyui")
            with mock.patch.object(qualification, "_post_json", return_value=(200, comfy_only)), \
                    self.assertRaisesRegex(qualification.QualificationError, "pnginfo_interpretation_mismatch"):
                qualification._run_transfer_case(config, source, image_path, qualification._new_row("Q21-TRANSFER"))


class HostQualificationFinalizeTests(unittest.TestCase):
    def _execute(self, root: Path) -> tuple[Any, Path, dict[str, Any]]:
        config = load(root)
        images = root / "H1-execute-images"
        images.mkdir()
        rows = []
        for case_id in qualification.CASE_IDS:
            row = dict(qualification._new_row(case_id), child_exit=0, status="PASS")
            if case_id in qualification.SEMANTIC_CHECKLISTS:
                data = _png((64, 64), (len(case_id), 1, 2, 255))
                (images / f"{case_id}.png").write_bytes(data)
                row.update(status="PENDING_REVIEW", original_sha256=hashlib.sha256(data).hexdigest())
            rows.append(row)
        execute = {"schema": "Qwen21HostQualificationV1", "phase": "execute", "host": "H1", "status": "PENDING_REVIEW",
                   "candidate_tree": TREE, "served_frontend_digest": config.frontend_index_sha256, "host_identity_digest": "c" * 64,
                   "model_role_digests": {}, "fixture_digest": "a" * 64, "variants": {}, "cases": rows}
        path = root / "H1-execute.json"
        path.write_text(json.dumps(execute), encoding="utf-8")
        return config, path, execute

    def _review(self, path: Path, execute: dict[str, Any], *, failing: str = "") -> dict[str, Any]:
        cases = {}
        for row in execute["cases"]:
            if row["status"] == "PENDING_REVIEW":
                items = qualification.SEMANTIC_CHECKLISTS[row["case_id"]]
                cases[row["case_id"]] = {"original_sha256": row["original_sha256"],
                                         "checklist": {item: row["case_id"] != failing for item in items}}
        return {"schema": "Qwen21SemanticReviewV1", "host": "H1",
                "execute_result_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "cases": cases}

    def _finalize(self, root: Path, config: Any, path: Path, review: dict[str, Any]) -> dict[str, Any]:
        review_path = root / "review.json"
        review_path.write_text(json.dumps(review), encoding="utf-8")
        with mock.patch.object(qualification, "_git", return_value=TREE):
            return qualification.finalize(config, path, review_path)

    def test_complete_review_passes_every_row(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config, path, execute = self._execute(root)
            result = self._finalize(root, config, path, self._review(path, execute))
            self.assertEqual(qualification._aggregate(result["cases"], qualification.CASE_IDS), "PASS")

    def test_failed_semantic_item_fails_the_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config, path, execute = self._execute(root)
            result = self._finalize(root, config, path, self._review(path, execute, failing="Q21-EDIT-10-REF"))
            row = next(item for item in result["cases"] if item["case_id"] == "Q21-EDIT-10-REF")
            self.assertEqual((row["status"], row["semantic_review"]), ("FAIL", "FAIL"))
            self.assertEqual(qualification._aggregate(result["cases"], qualification.CASE_IDS), "FAIL")

    def test_review_cannot_be_rebound_to_changed_execute_or_image(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config, path, execute = self._execute(root)
            review = self._review(path, execute)
            stale = dict(review, execute_result_sha256="d" * 64)
            with self.assertRaisesRegex(qualification.QualificationError, "review_identity_mismatch"):
                self._finalize(root, config, path, stale)
            (root / "H1-execute-images" / "Q21-REMOVE-BG.png").write_bytes(b"tampered")
            with self.assertRaisesRegex(qualification.QualificationError, "review_image_changed"):
                self._finalize(root, config, path, review)

    def test_review_must_answer_exact_frozen_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config, path, execute = self._execute(root)
            review = self._review(path, execute)
            review["cases"]["Q21-T2I-SQUARE"]["checklist"] = {"looks_fine": True}
            with self.assertRaisesRegex(qualification.QualificationError, "review_entry_invalid"):
                self._finalize(root, config, path, review)


if __name__ == "__main__":
    unittest.main()
