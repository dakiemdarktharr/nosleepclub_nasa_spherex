# Contributing to Touch The Sky

1. Read the [challenge summary](docs/CHALLENGE.md) and [roadmap](docs/ROADMAP.md).
2. Open an issue with a specific goal and clear acceptance criteria.
3. Create a branch from `main`, for example `feat/sky-viewer`, `fix/coordinate-input`, or `docs/data-access`.
4. Keep each pull request focused on a reviewable change. Describe the result and how it was checked.

## Data and security

- Do not commit tokens, credentials, or `.env` files containing secrets. If configuration is needed, add an `.env.example` with variable names and safe values only.
- Do not commit FITS images, downloaded archives, or large caches. Document how to reproduce the data and use Git LFS or an appropriate data store if the team agrees to one.
- Record sources and reuse terms for data, libraries, images, and third-party content.
- Clearly distinguish observed data, simulated data, and inferred results in both documentation and the interface.

## Verification

For Python checks, install `requirements.txt`, `web/requirements.txt`, and `requirements-ops.txt`, then run `python -m unittest discover -s tests -v`. MongoDB integration checks additionally need the disposable replica set configured in [CI](.github/workflows/checks.yml). Run JavaScript suites with Node.js, for example `node tests/ship-journey.test.cjs`. Browser checks use `requirements-browser.txt` and Playwright Chromium; see the CI workflow for the full set.

When changing a science pipeline, follow its documented reproduction sequence, preserve provenance, and document scientific limitations. Do not regenerate or replace frozen products as part of unrelated UI or documentation edits.

For documentation changes, check relative links, image alt text, media sources, and setup commands. Keep large pitch videos in GitHub Releases and reference them from the README. Raw recordings and temporary browser output stay ignored; see the [documentation index](docs/README.md).

Each handoff should include a viewable result, the checks performed, remaining limitations, and a concrete next step for the user to review. See `AGENTS.md`.
