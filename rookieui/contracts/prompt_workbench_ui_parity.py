from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


PROMPT_WORKBENCH_UI_PARITY_CONTRACT_VERSION = "prompt-all-in-one-inline-ui-parity-20260427"

PROMPT_WORKBENCH_UI_PARITY_CLASSES = (
    "implemented",
    "adapted_comfyui_native",
    "planned",
    "reference_only",
    "out_of_scope",
)

PROMPT_WORKBENCH_UI_EVIDENCE_TYPES = (
    "contract",
    "unit_dom",
    "e2e_interaction",
    "visual_reference_fixture",
    "visual_current_capture",
    "live_host_target_capture",
)


@dataclass(frozen=True)
class PromptWorkbenchUiParityPrimitive:
    primitive_id: str
    title: str
    reference_file: str
    reference_surface: str
    reference_concept: str
    rookieui_target: str
    target_selector: str
    parity_class: str
    implementation_item: str
    evidence_required: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def _primitive_entries() -> tuple[PromptWorkbenchUiParityPrimitive, ...]:
    return (
        PromptWorkbenchUiParityPrimitive(
            primitive_id="inline_surface_root",
            title="Inline Prompt Surface Root",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".physton-prompt inserted directly below the A1111 prompt textarea",
            reference_concept="Each prompt textarea receives a directly adjacent prompt-all-in-one editing surface.",
            rookieui_target="Render a fixed-scope Prompt Workbench surface directly below each RookieUI prompt textarea.",
            target_selector="[data-layout='prompt_all_in_one_inline']",
            parity_class="implemented",
            implementation_item="inline_surface_mount",
            evidence_required=("contract", "unit_dom", "e2e_interaction", "visual_current_capture"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="fold_unfold",
            title="Inline Fold / Unfold Affordance",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".prompt-unfold",
            reference_concept="Prompt tooling can collapse to a compact inline row under the textarea.",
            rookieui_target="Expose fold state from the inline toolbar and preserve `aria-expanded` synchronization.",
            target_selector="[data-pw-ui='fold-toggle']",
            parity_class="adapted_comfyui_native",
            implementation_item="inline_toolbar",
            evidence_required=("contract", "unit_dom", "e2e_interaction"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="inline_toolbar_row",
            title="Compact Inline Toolbar Row",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".prompt-header .prompt-header-extend",
            reference_concept="Language, history, favorite, settings, translation, copy/delete, and append controls live in one dense prompt-adjacent row.",
            rookieui_target="Render Prompt Workbench controls as compact inline tools beside the fold and status chips.",
            target_selector=".rookieui-shell__prompt-workbench-inline-tool",
            parity_class="implemented",
            implementation_item="inline_toolbar",
            evidence_required=("contract", "unit_dom", "visual_current_capture", "e2e_interaction"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="counter_language_status",
            title="Counter and Language Status Chips",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".prompt-header language and tag count controls",
            reference_concept="Prompt status is visible in the compact prompt-adjacent control row.",
            rookieui_target="Expose tag count and language/scope as status-style inline chips.",
            target_selector="[data-pw-ui='inline-counter']",
            parity_class="implemented",
            implementation_item="namespace_accessibility",
            evidence_required=("contract", "unit_dom", "e2e_interaction", "visual_current_capture"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="popover_anchor_buttons",
            title="Inline Popover Anchor Buttons",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".prompt-header history/favorite/setting/append controls",
            reference_concept="Secondary surfaces open from compact controls spatially tied to the prompt block.",
            rookieui_target="Expose history, favorites, settings, and append as inline popover anchors with dialog semantics.",
            target_selector="[data-pw-ui='inline-history-anchor']",
            parity_class="implemented",
            implementation_item="namespace_accessibility",
            evidence_required=("contract", "unit_dom", "e2e_interaction", "visual_current_capture"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="inline_append_dropdown",
            title="Inline Append Dropdown",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".input-tag-append / .prompt-append-list",
            reference_concept="Adding tags happens inline from a nearby append dropdown with suggestions.",
            rookieui_target="Open append suggestions and grouped tag shortcuts inside the inline prompt block.",
            target_selector="[data-pw-ui='append-dropdown-popover']",
            parity_class="implemented",
            implementation_item="inline_append_batch",
            evidence_required=("contract", "unit_dom", "e2e_interaction", "visual_current_capture"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="inline_suggestions",
            title="Inline Suggestions",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".prompt-append-list tag suggestion rows",
            reference_concept="Common tags can be inserted from the prompt-local append surface.",
            rookieui_target="Render catalog/history/favorite suggestions inside the append dropdown.",
            target_selector="[data-pw-ui='inline-suggestions']",
            parity_class="implemented",
            implementation_item="inline_append_batch",
            evidence_required=("contract", "unit_dom", "e2e_interaction"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="inline_token_tags",
            title="Inline Token Tags",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".prompt-tags .prompt-tags-list",
            reference_concept="Prompt tokens rest as compact tags directly inside the prompt block.",
            rookieui_target="Render Prompt Workbench tokens as inline editable tag rows under the prompt textarea.",
            target_selector="[data-pw-token-ui='inline-token-tag']",
            parity_class="implemented",
            implementation_item="inline_token_tags",
            evidence_required=("contract", "unit_dom", "visual_current_capture", "e2e_interaction"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="token_hover_quick_actions",
            title="Token Hover / Focus Quick Actions",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".btn-tag-extend",
            reference_concept="Per-token operations appear as compact controls on hover/focus.",
            rookieui_target="Expose quick actions for edit, weight, translate, copy, favorite, blacklist, enable/disable, move, and delete.",
            target_selector=".rookieui-shell__prompt-workbench-token-quick-actions",
            parity_class="implemented",
            implementation_item="inline_token_tags",
            evidence_required=("contract", "unit_dom", "e2e_interaction"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="bilingual_token_row",
            title="Bilingual Token Row",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".prompt-local-language",
            reference_concept="Translated/local-language text is visually tied to each token.",
            rookieui_target="Show translated/local token text beside the corresponding inline tag.",
            target_selector=".rookieui-shell__prompt-workbench-token-local-language",
            parity_class="implemented",
            implementation_item="inline_token_tags",
            evidence_required=("contract", "unit_dom", "visual_current_capture"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="selection_batch_toolbar",
            title="Selection Batch Toolbar",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".drop-select-btns",
            reference_concept="Batch actions are spatially tied to selected tags.",
            rookieui_target="Show selected-token batch actions as an inline overlay inside the prompt block.",
            target_selector="[data-pw-ui='selection-batch-toolbar']",
            parity_class="implemented",
            implementation_item="inline_append_batch",
            evidence_required=("contract", "unit_dom", "e2e_interaction"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="group_tags_tab_board",
            title="Group Tags Tab Board",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface=".group-tabs .group-header / .sub-group-header / .group-tags",
            reference_concept="Group tags render as a tab/subtab board beneath the prompt token area.",
            rookieui_target="Render group tags in the inline append popover with quick insert behavior.",
            target_selector="[data-pw-ui='group-tags-tab-board']",
            parity_class="implemented",
            implementation_item="inline_append_batch",
            evidence_required=("contract", "unit_dom", "visual_current_capture", "e2e_interaction"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="namespace_accessibility",
            title="Prompt and Negative Namespace Accessibility",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/components/phystonPrompt.vue",
            reference_surface="per-textarea prompt and negative prompt instances",
            reference_concept="Prompt and negative prompt blocks remain separate prompt-local tools.",
            rookieui_target="Keep prompt and negative inline workbenches fixed to their own textareas with accessible status and popover behavior.",
            target_selector="[aria-haspopup='dialog']",
            parity_class="implemented",
            implementation_item="namespace_accessibility",
            evidence_required=("contract", "unit_dom", "e2e_interaction", "live_host_target_capture"),
        ),
        PromptWorkbenchUiParityPrimitive(
            primitive_id="a1111_textarea_hijack",
            title="A1111 Textarea Hijack",
            reference_file="reference/sd-webui-prompt-all-in-one/src/src/App.vue",
            reference_surface="A1111 prompt textarea attachment",
            reference_concept="Reference extension attaches directly to A1111 DOM textareas.",
            rookieui_target="Out of scope; RookieUI binds to ComfyUI-native prompt inputs instead.",
            target_selector="",
            parity_class="out_of_scope",
            implementation_item="comfyui_native_binding",
            evidence_required=("contract",),
        ),
    )


def get_prompt_workbench_ui_parity_primitives() -> tuple[PromptWorkbenchUiParityPrimitive, ...]:
    return _primitive_entries()


def build_prompt_workbench_ui_parity_payload() -> dict[str, Any]:
    primitives = [entry.to_payload() for entry in get_prompt_workbench_ui_parity_primitives()]
    return {
        "contract": {
            "version": PROMPT_WORKBENCH_UI_PARITY_CONTRACT_VERSION,
            "reference_project": "reference/sd-webui-prompt-all-in-one",
            "execution_policy": "read_only_reference_code_no_execution",
            "visual_claim_policy": "reference_fixture_plus_current_capture_plus_live_host_when_available",
        },
        "parity_classes": list(PROMPT_WORKBENCH_UI_PARITY_CLASSES),
        "evidence_types": list(PROMPT_WORKBENCH_UI_EVIDENCE_TYPES),
        "primitives": primitives,
    }
