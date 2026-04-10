All E2E tests must be performed using the standard procedures defined in
`tests/E2E_TESTING_SOP.md`.

Exception:

- strictly documentation-only changes do not require entering the E2E workflow
- this exception does not apply once application code, test code, scripts, configs, or generated artifacts change

Scope note:

- `tests/E2E_TESTING_SOP.md` is frontend Playwright harness SOP.
- Backend real-E2E lanes (`tests.test_r122_real_backend_lane`, `tests.test_r123_real_backend_model_list_lane`) are governed by `tests/TEST_SOP.md`.

For public/admin/webhook/connector or other user-facing transaction changes, acceptance evidence must include at least one transaction-level probe that verifies the actual submitted outcome; route load or redirect-only evidence is not sufficient on its own.
