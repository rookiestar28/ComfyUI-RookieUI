from __future__ import annotations

import os
from typing import Any

from rookieui.contracts.queue import RookieUIQueueJob, RookieUIQueueSnapshot, build_queue_contract_meta
from rookieui.security.asset_guard import normalize_metadata_text, validate_asset_identifier


def _extract_prompt_tuple_values(item: tuple[object, ...]) -> tuple[int | None, str, dict[str, object]]:
    if len(item) < 4:
        raise ValueError("Queue item shape is invalid.")

    priority = item[0]
    prompt_id = item[1]
    extra_data = item[3] if isinstance(item[3], dict) else {}

    normalized_priority = int(priority) if isinstance(priority, (int, float)) else None
    normalized_prompt_id = str(prompt_id)
    return normalized_priority, normalized_prompt_id, extra_data


def _is_rookieui_origin(extra_data: dict[str, object]) -> bool:
    return str(extra_data.get("rookieui_origin", "")).strip().lower() == "rookieui"


def _matches_client_id(extra_data: dict[str, object], client_id: str | None) -> bool:
    if client_id is None:
        return True
    return str(extra_data.get("client_id", "")).strip() == client_id


def _is_rookieui_visible_item(extra_data: dict[str, object], client_id: str | None) -> bool:
    return _is_rookieui_origin(extra_data) and _matches_client_id(extra_data, client_id)


def _normalize_queue_item(item: tuple[object, ...], status: str) -> RookieUIQueueJob:
    priority, prompt_id, extra_data = _extract_prompt_tuple_values(item)
    create_time = extra_data.get("create_time")
    if not isinstance(create_time, int):
        create_time = None

    return RookieUIQueueJob(
        id=normalize_metadata_text(prompt_id, max_length=80),
        status=status,
        priority=priority,
        create_time=create_time,
    )


def _map_history_status(status_info: dict[str, object]) -> str:
    status_str = str(status_info.get("status_str", "")).strip().lower()
    if status_str == "success":
        return "completed"
    if status_str == "error":
        messages = status_info.get("messages", [])
        for entry in messages if isinstance(messages, list) else []:
            if isinstance(entry, (list, tuple)) and entry and entry[0] == "execution_interrupted":
                return "cancelled"
        return "failed"
    return "completed"


def _extract_output_filenames(outputs: dict[str, object]) -> tuple[list[str], list[str]]:
    filenames: list[str] = []
    reusable_outputs: list[str] = []

    for node_outputs in outputs.values():
        if not isinstance(node_outputs, dict):
            continue
        for media_type, items in node_outputs.items():
            if media_type == "animated" or not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                filename = item.get("filename")
                if not isinstance(filename, str) or not filename.strip():
                    continue
                display_name = normalize_metadata_text(os.path.basename(filename), max_length=80)
                filenames.append(display_name)
                try:
                    reusable_outputs.append(validate_asset_identifier(display_name))
                except (TypeError, ValueError):
                    continue

    # Preserve order while removing duplicates.
    deduped_filenames = list(dict.fromkeys(filenames))
    deduped_reusable = list(dict.fromkeys(reusable_outputs))
    return deduped_filenames, deduped_reusable


def _normalize_history_item(prompt_id: str, history_item: dict[str, object]) -> RookieUIQueueJob:
    prompt_tuple = history_item.get("prompt", ())
    priority = None
    create_time = None
    if isinstance(prompt_tuple, tuple) and len(prompt_tuple) >= 4:
        raw_priority, _, _, extra_data = prompt_tuple[:4]
        priority = int(raw_priority) if isinstance(raw_priority, (int, float)) else None
        if isinstance(extra_data, dict) and isinstance(extra_data.get("create_time"), int):
            create_time = extra_data.get("create_time")

    outputs = history_item.get("outputs", {})
    output_filenames, reusable_outputs = _extract_output_filenames(outputs if isinstance(outputs, dict) else {})
    return RookieUIQueueJob(
        id=normalize_metadata_text(prompt_id, max_length=80),
        status=_map_history_status(history_item.get("status", {}) if isinstance(history_item.get("status"), dict) else {}),
        priority=priority,
        create_time=create_time,
        outputs_count=len(output_filenames),
        output_filenames=output_filenames,
        reusable_outputs=reusable_outputs,
    )


def build_queue_snapshot(
    prompt_server: Any | None,
    *,
    history_limit: int = 5,
    client_id: str | None = None,
) -> dict[str, object]:
    if prompt_server is None or not hasattr(prompt_server, "prompt_queue"):
        payload = RookieUIQueueSnapshot(source="fallback", queue_remaining=0).to_payload()
        payload["contract"] = build_queue_contract_meta()
        return payload

    prompt_queue = prompt_server.prompt_queue
    running: list[tuple[object, ...]] = []
    queued: list[tuple[object, ...]] = []
    history: dict[str, dict[str, object]] = {}

    get_current_queue = getattr(prompt_queue, "get_current_queue_volatile", None)
    if callable(get_current_queue):
        current_queue = get_current_queue()
        if isinstance(current_queue, tuple) and len(current_queue) == 2:
            running = list(current_queue[0])
            queued = list(current_queue[1])

    get_history = getattr(prompt_queue, "get_history", None)
    if callable(get_history):
        try:
            history = get_history(max_items=history_limit, offset=0)
        except TypeError:
            history = get_history()
        if not isinstance(history, dict):
            history = {}

    filtered_running = [
        item for item in running if _is_rookieui_visible_item(_extract_prompt_tuple_values(item)[2], client_id)
    ]
    filtered_queued = [
        item for item in queued if _is_rookieui_visible_item(_extract_prompt_tuple_values(item)[2], client_id)
    ]
    # IMPORTANT: use the filtered RookieUI view instead of host-global queue info; the host counter includes unrelated canvas jobs.
    queue_remaining = len(filtered_running) + len(filtered_queued)

    jobs: list[RookieUIQueueJob] = []
    for item in filtered_running:
        jobs.append(_normalize_queue_item(item, "in_progress"))
    for item in filtered_queued:
        jobs.append(_normalize_queue_item(item, "pending"))

    for prompt_id, history_item in history.items():
        if not isinstance(history_item, dict):
            continue
        prompt_tuple = history_item.get("prompt", ())
        if not isinstance(prompt_tuple, tuple) or len(prompt_tuple) < 4:
            continue
        extra_data = prompt_tuple[3] if isinstance(prompt_tuple[3], dict) else {}
        if not _is_rookieui_visible_item(extra_data, client_id):
            continue
        jobs.append(_normalize_history_item(prompt_id, history_item))

    jobs.sort(
        key=lambda job: (
            0 if job.status == "in_progress" else 1 if job.status == "pending" else 2,
            -(job.create_time or 0),
        )
    )
    payload = RookieUIQueueSnapshot(
        source="host",
        queue_remaining=queue_remaining,
        jobs=jobs[: max(history_limit + len(running) + len(queued), 5)],
    ).to_payload()
    payload["contract"] = build_queue_contract_meta()
    return payload


def build_queue_job_snapshot(
    prompt_server: Any | None,
    prompt_id: str,
    *,
    history_limit: int = 32,
    client_id: str | None = None,
) -> dict[str, object]:
    snapshot = build_queue_snapshot(
        prompt_server,
        history_limit=history_limit,
        client_id=client_id,
    )
    matched_job = next(
        (job for job in snapshot.get("jobs", []) if isinstance(job, dict) and job.get("id") == prompt_id),
        None,
    )
    return {
        "source": snapshot.get("source", "fallback"),
        "queue_remaining": snapshot.get("queue_remaining", 0),
        "job": matched_job,
        "contract": build_queue_contract_meta(),
    }
