# Contributing to NoSleepClub

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

Run `python -m unittest discover -s tests -v` in an environment with `requirements.txt` installed. When changing a pipeline, regenerate `web/data/` with `scripts/build_demo.py`, preserve provenance, and document scientific limitations.

Each handoff should include a viewable result, the checks performed, remaining limitations, and a concrete next step for the user to review. See `AGENTS.md`.
