#!/usr/bin/env bash
set -euo pipefail
set -o errtrace

trap 'echo "[pre-push] ERROR at line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[pre-push] repo: $ROOT_DIR"

UNAME_S="$(uname -s || true)"
case "$UNAME_S" in
  MINGW*|MSYS*|CYGWIN*)
    # CRITICAL: keep cache inside repo on Windows to avoid global-cache lock issues.
    export PRE_COMMIT_HOME="${PRE_COMMIT_HOME:-$ROOT_DIR/.tmp/pre-commit-win}"
    ;;
  *)
    export PRE_COMMIT_HOME="${PRE_COMMIT_HOME:-$ROOT_DIR/.tmp/pre-commit}"
    ;;
esac
export BLACK_CACHE_DIR="${BLACK_CACHE_DIR:-$ROOT_DIR/.tmp/black-cache}"
mkdir -p "$PRE_COMMIT_HOME" "$BLACK_CACHE_DIR"

is_wsl() {
  grep -qiE "(microsoft|wsl)" /proc/version 2>/dev/null
}

validate_repo_relative_path() {
  local raw_value="$1"
  local field_name="$2"
  local candidate="$raw_value"

  candidate="${candidate//\\//}"
  while [[ "$candidate" == ./* ]]; do
    candidate="${candidate#./}"
  done

  if [ -z "$candidate" ]; then
    echo "[pre-push] ERROR: $field_name must be a non-empty repo-relative path." >&2
    exit 1
  fi

  # CRITICAL: keep override paths repo-relative only; absolute or malformed values can create garbage directories in workspace and leak outside intended test roots.
  if [[ "$candidate" == /* ]] || [[ "$candidate" =~ ^[A-Za-z]: ]] || [[ "$candidate" =~ ^// ]]; then
    echo "[pre-push] ERROR: $field_name must be repo-relative (absolute paths are not allowed): $raw_value" >&2
    exit 1
  fi

  if [[ ! "$candidate" =~ ^[A-Za-z0-9._/-]+$ ]]; then
    echo "[pre-push] ERROR: $field_name contains unsupported characters: $raw_value" >&2
    exit 1
  fi

  IFS='/' read -r -a segments <<<"$candidate"
  local segment
  for segment in "${segments[@]}"; do
    if [ -z "$segment" ] || [ "$segment" = "." ] || [ "$segment" = ".." ]; then
      echo "[pre-push] ERROR: $field_name must be a normalized repo-relative path: $raw_value" >&2
      exit 1
    fi
  done

  printf "%s" "$candidate"
}

select_venv_dir() {
  if [ -n "${ROOKIEUI_TEST_VENV:-}" ]; then
    local normalized_override
    normalized_override="$(validate_repo_relative_path "$ROOKIEUI_TEST_VENV" "ROOKIEUI_TEST_VENV")"
    echo "$ROOT_DIR/$normalized_override"
    return 0
  fi
  case "$UNAME_S" in
    MINGW*|MSYS*|CYGWIN*) echo "$ROOT_DIR/.venv" ;;
    *)
      if is_wsl; then
        echo "$ROOT_DIR/.venv-wsl"
      else
        echo "$ROOT_DIR/.venv"
      fi
      ;;
  esac
}

resolve_venv_python() {
  case "$UNAME_S" in
    MINGW*|MSYS*|CYGWIN*) echo "$VENV_DIR/Scripts/python.exe" ;;
    *) echo "$VENV_DIR/bin/python" ;;
  esac
}

is_venv_python_healthy() {
  local venv_py="$1"
  [ -f "$venv_py" ] || return 1
  "$venv_py" -c "import sys; print(sys.executable)" >/dev/null 2>&1
}

bootstrap_venv() {
  local venv_py
  venv_py="$(resolve_venv_python)"
  if is_venv_python_healthy "$venv_py"; then
    echo "$venv_py"
    return 0
  fi

  if [ -e "$venv_py" ]; then
    echo "[pre-push] WARN: invalid venv detected; recreating $VENV_DIR" >&2
    rm -rf "$VENV_DIR"
  fi

  # CRITICAL: this function is consumed via command substitution to resolve VENV_PY;
  # keep log lines on stderr so stdout returns only the python executable path.
  echo "[pre-push] INFO: creating project venv at $VENV_DIR" >&2
  case "$UNAME_S" in
    MINGW*|MSYS*|CYGWIN*)
      # IMPORTANT: prefer Windows-native launchers; MSYS python can create broken venv.
      if command -v py.exe >/dev/null 2>&1; then
        py.exe -3 -m venv "$VENV_DIR"
      elif [ -x "/c/Windows/py.exe" ]; then
        /c/Windows/py.exe -3 -m venv "$VENV_DIR"
      elif command -v python.exe >/dev/null 2>&1; then
        python.exe -m venv "$VENV_DIR"
      elif command -v py >/dev/null 2>&1; then
        py -3 -m venv "$VENV_DIR"
      else
        echo "[pre-push] ERROR: no Windows Python launcher found (py.exe/python.exe)." >&2
        exit 1
      fi
      ;;
    *)
      if command -v python3 >/dev/null 2>&1; then
        python3 -m venv "$VENV_DIR"
      elif command -v python >/dev/null 2>&1; then
        python -m venv "$VENV_DIR"
      else
        echo "[pre-push] ERROR: no bootstrap Python found (python3/python)." >&2
        exit 1
      fi
      ;;
  esac

  if ! is_venv_python_healthy "$venv_py"; then
    echo "[pre-push] ERROR: failed to initialize project venv: $VENV_DIR" >&2
    exit 1
  fi
  echo "$venv_py"
}

pip_install_or_fail() {
  local why="$1"
  shift
  if "$VENV_PY" -m pip install "$@"; then
    return 0
  fi
  echo "[pre-push] ERROR: failed to install dependency ($why): $*" >&2
  exit 1
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[pre-push] ERROR: missing command: $cmd" >&2
    exit 1
  fi
}

capture_precommit_snapshots() {
  # IMPORTANT: compare both worktree and index; pre-commit can mutate staged files.
  PRECOMMIT_WORKTREE_SNAPSHOT="$(mktemp)"
  PRECOMMIT_INDEX_SNAPSHOT="$(mktemp)"
  git diff --binary -- . >"$PRECOMMIT_WORKTREE_SNAPSHOT"
  git diff --cached --binary -- . >"$PRECOMMIT_INDEX_SNAPSHOT"
}

cleanup_precommit_snapshots() {
  rm -f "${PRECOMMIT_WORKTREE_SNAPSHOT:-}" "${PRECOMMIT_INDEX_SNAPSHOT:-}" \
    "${PRECOMMIT_WORKTREE_SNAPSHOT_AFTER:-}" "${PRECOMMIT_INDEX_SNAPSHOT_AFTER:-}"
}

precommit_changed_repo_state() {
  PRECOMMIT_WORKTREE_SNAPSHOT_AFTER="$(mktemp)"
  PRECOMMIT_INDEX_SNAPSHOT_AFTER="$(mktemp)"
  git diff --binary -- . >"$PRECOMMIT_WORKTREE_SNAPSHOT_AFTER"
  git diff --cached --binary -- . >"$PRECOMMIT_INDEX_SNAPSHOT_AFTER"
  ! cmp -s "$PRECOMMIT_WORKTREE_SNAPSHOT" "$PRECOMMIT_WORKTREE_SNAPSHOT_AFTER" || \
    ! cmp -s "$PRECOMMIT_INDEX_SNAPSHOT" "$PRECOMMIT_INDEX_SNAPSHOT_AFTER"
}

report_precommit_repo_drift_and_exit() {
  echo "[pre-push] ERROR: pre-commit hooks modified tracked files (worktree or index)." >&2
  echo "[pre-push] Review/stage hook changes, then push again." >&2
  git status --short
  cleanup_precommit_snapshots
  exit 1
}

verify_npm_deps() {
  node "$ROOT_DIR/scripts/verify_node_modules_lock.mjs"
}

ensure_npm_deps() {
  if verify_npm_deps; then
    return 0
  fi
  # SECURITY: verify dependency identity; a package marker does not prove lockfile parity.
  echo "[pre-push] Frontend dependencies are missing or stale; repairing via npm ci ..."
  npm ci
  if ! verify_npm_deps; then
    echo "[pre-push] ERROR: frontend dependencies still differ from package-lock.json after npm ci." >&2
    exit 1
  fi
}

ensure_python_command_for_playwright() {
  if command -v python >/dev/null 2>&1; then
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    # IMPORTANT: Playwright config uses `python` command by default.
    mkdir -p "$ROOT_DIR/.tmp/bin"
    ln -sf "$(command -v python3)" "$ROOT_DIR/.tmp/bin/python"
    export PATH="$ROOT_DIR/.tmp/bin:$PATH"
    return 0
  fi
  echo "[pre-push] ERROR: no python/python3 command available for Playwright web server." >&2
  exit 1
}

resolve_e2e_port() {
  "$VENV_PY" scripts/e2e_harness_env.py --candidate-ports 4173 4300 4310 4320 4500
}

assert_node_version() {
  local node_major
  node_major="$(node -p "process.versions.node.split('.')[0]")"
  if [ "$node_major" -lt 18 ]; then
    echo "[pre-push] ERROR: Node >=18 required, current=$(node -v)" >&2
    exit 1
  fi
}

require_cmd git
require_cmd node
require_cmd npm

VENV_DIR="$(select_venv_dir)"
VENV_PY="$(bootstrap_venv)"

# CRITICAL: always run pre-commit from project venv to avoid global PATH drift.
if ! "$VENV_PY" -m pre_commit --version >/dev/null 2>&1; then
  echo "[pre-push] INFO: installing pre-commit into project venv ($VENV_DIR) ..."
  pip_install_or_fail "required for hook execution" -U pip pre-commit
fi

if ! "$VENV_PY" -c "import numpy, PIL, aiohttp" >/dev/null 2>&1; then
  echo "[pre-push] INFO: installing runtime test dependencies into project venv ($VENV_DIR) ..."
  pip_install_or_fail "required by backend unit tests/import paths" numpy pillow aiohttp
fi

assert_node_version
ensure_npm_deps
ensure_python_command_for_playwright
export ROOKIEUI_E2E_PYTHON="$VENV_PY"
if [ -z "${ROOKIEUI_E2E_PORT:-}" ]; then
  # CRITICAL: pick a bindable loopback port here so `npm test` inside pre-push matches
  # the repo's Windows full-gate contract instead of failing on a busy/denied default port.
  export ROOKIEUI_E2E_PORT="$(resolve_e2e_port)"
fi
echo "[pre-push] Playwright harness python: $ROOKIEUI_E2E_PYTHON"
echo "[pre-push] Playwright harness port: $ROOKIEUI_E2E_PORT"

echo "[pre-push] Step 1/8: supply-chain hardening scan"
"$VENV_PY" scripts/check_supply_chain_hardening.py --root "$ROOT_DIR"

echo "[pre-push] Step 2/8: dependency advisory gate"
npm run audit:ci

echo "[pre-push] Step 3/8: detect-secrets"
"$VENV_PY" -m pre_commit run detect-secrets --all-files

echo "[pre-push] Step 4/8: pre-commit all hooks"
capture_precommit_snapshots
if "$VENV_PY" -m pre_commit run --all-files --show-diff-on-failure; then
  :
else
  echo "[pre-push] INFO: pre-commit returned non-zero; running a second pass for verification ..."
  "$VENV_PY" -m pre_commit run --all-files --show-diff-on-failure
fi
if precommit_changed_repo_state; then
  report_precommit_repo_drift_and_exit
fi
cleanup_precommit_snapshots

echo "[pre-push] Step 5/8: prompt compiler guard tests"
MOLTBOT_STATE_DIR="$ROOT_DIR/moltbot_state/_local_unit" \
  "$VENV_PY" scripts/run_unittests.py --start-dir tests --pattern "test_a1111_prompt_encoding.py"
MOLTBOT_STATE_DIR="$ROOT_DIR/moltbot_state/_local_unit" \
  "$VENV_PY" scripts/run_unittests.py --start-dir tests --pattern "test_txt2img_translation.py"
MOLTBOT_STATE_DIR="$ROOT_DIR/moltbot_state/_local_unit" \
  "$VENV_PY" scripts/run_unittests.py --start-dir tests --pattern "test_img2img_translation.py"

echo "[pre-push] Step 6/8: backend unit tests"
MOLTBOT_STATE_DIR="$ROOT_DIR/moltbot_state/_local_unit" \
  "$VENV_PY" scripts/run_unittests.py --start-dir tests --pattern "test_*.py"

echo "[pre-push] Step 7/8: frontend type validation + test suite"
npm run test:types
npm test

if [ "${ROOKIEUI_RUN_LIVE_SMOKE:-0}" = "1" ]; then
  echo "[pre-push] Step 8/8: optional host-embedded E2E lane"
  "$VENV_PY" scripts/run_host_embedded_e2e.py
else
  echo "[pre-push] Step 8/8: optional host-embedded E2E lane skipped (set ROOKIEUI_RUN_LIVE_SMOKE=1 to enable)"
fi

echo "[pre-push] PASS: all required checks completed."
