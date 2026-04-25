All frontend E2E tests must follow `tests/E2E_TESTING_SOP.md`.

Mandatory testing-design rule:

- E2E tests must be designed to reproduce real user-visible failures and catch bugs early, not merely to pass validation.
- Do not add pass-only E2E checks that cannot fail for the bug class under review.
- For every user-reported or high-risk frontend regression, ask which E2E assertion would have caught it before release, then add or update that assertion.

Exception:

- strictly documentation-only changes do not require entering the E2E workflow
- once code/tests/scripts/config/runtime files change, this exception does not apply

Scope note:

- `tests/E2E_TESTING_SOP.md` is the Playwright harness procedure for this repo
- full acceptance workflow and gate order remain defined by `tests/TEST_SOP.md`

For transaction-sensitive features, acceptance evidence must include at least one action-level assertion of final outcome (not route-load evidence only).
