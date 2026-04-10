import os
import sys

_ROOKIEUI_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOKIEUI_ROOT not in sys.path:
    sys.path.insert(0, _ROOKIEUI_ROOT)

from rookieui.nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

WEB_DIRECTORY = "./web"


def _bootstrap_rookieui_routes() -> None:
    # CRITICAL: keep the custom node entrypoint thin; import-time failures here
    # break the whole extension load path before PromptServer can warm up.
    try:
        from rookieui.services.route_bootstrap import register_routes_once
    except Exception:
        return

    register_routes_once()


_bootstrap_rookieui_routes()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
