All frontend E2E tests must follow `tests/E2E_TESTING_SOP.md`.

Exception:

- strictly documentation-only changes do not require entering the E2E workflow
- once code/tests/scripts/config/runtime files change, this exception does not apply

Scope note:

- `tests/E2E_TESTING_SOP.md` is the Playwright harness procedure for this repo
- full acceptance workflow and gate order remain defined by `tests/TEST_SOP.md`

For transaction-sensitive features, acceptance evidence must include at least one action-level assertion of final outcome (not route-load evidence only).
