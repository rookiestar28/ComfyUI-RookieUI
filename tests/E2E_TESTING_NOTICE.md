All frontend E2E tests must follow `tests/E2E_TESTING_SOP.md`.

<!-- CURRENT-TEST-GOVERNANCE:START -->
## Current Governance Scope

A change limited to pure text/documentation files, a version-field-only `pyproject.toml` update, or
both does not enter this E2E workflow and requires no planning, roadmap item, record/log,
independent review, documentation test contract, browser installation, or full gate. Behavior-
bearing metadata changes do not qualify. For non-exempt work, applicable E2E runs through the
authoritative Windows Full Gate. Hosted CI repetitions are optional diagnostics and are not
acceptance prerequisites or pushed-commit evidence. Explicit item-scoped live/supported-host checks
remain separate when required.
<!-- CURRENT-TEST-GOVERNANCE:END -->

Mandatory testing-design rule:

- E2E tests must be designed to reproduce real user-visible failures and catch bugs early, not merely to pass validation.
- Do not add pass-only E2E checks that cannot fail for the bug class under review.
- For every user-reported or high-risk frontend regression, ask which E2E assertion would have caught it before release, then add or update that assertion.

Exception:

- pure text/documentation changes and version-field-only `pyproject.toml` updates do not enter the E2E workflow
- once code/tests/scripts/config/runtime files change, or `pyproject.toml` changes behavior-bearing metadata, this exception does not apply

Scope note:

- `tests/E2E_TESTING_SOP.md` is the Playwright harness procedure for this repo
- full acceptance workflow and gate order remain defined by `tests/TEST_SOP.md`

For transaction-sensitive features, acceptance evidence must include at least one action-level assertion of final outcome (not route-load evidence only).
