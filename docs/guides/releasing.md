<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Releasing (maintainer)

Releases go to PyPI through **Trusted Publishing** (OIDC; no API tokens are stored) with
**PEP 740 attestations**, from `.github/workflows/release.yml`. The workflow runs only
when a maintainer **publishes a GitHub Release**. Pushes, pull requests and ordinary CI
never publish.

## One-time setup (account actions; maintainer only)

1. **PyPI pending publisher**: on <https://pypi.org/manage/account/publishing/> add a
   pending publisher with project `aureproof`, owner `bhargavchintam`, repository
   `aureproof`, workflow `release.yml`, environment `pypi`.
2. **GitHub environment `pypi`**: Settings → Environments → New environment `pypi`.
   - Add yourself, and later the second reviewer, as a **required reviewer**.
   - Restrict deployments to tags matching `v*`.

## Each release

1. Make sure `main` is green, including the **fresh install + Phase-1 gate** job. The
   Recovery and Evidence-completeness gates rest on [`fault-qualification.md`](../fault-qualification.md).
   Compatibility and migrations follow [`specs/COMPATIBILITY.md`](../../specs/COMPATIBILITY.md);
   a release that changes any record version adds its migration and N−1 vectors.
   The **EEE consumer** workflow must be green too, with the round trip and its losses as
   documented in [`eee-export.md`](eee-export.md).
   Licensing: the fixture card [`fixtures/DATASET_CARD.md`](../../fixtures/DATASET_CARD.md) and
   its Croissant metadata must be current, and the **Croissant** workflow green.
2. Set `version` in `pyproject.toml` (e.g. `0.1.0a1`), update `CHANGELOG.md`, and merge.
3. Create and publish a GitHub Release with the tag `v<version>` (e.g. `v0.1.0a1`).
4. The workflow:
   - checks the tag matches the package version;
   - runs the full suite, builds the sdist and wheel;
   - re-runs the Phase-1 gate from a fresh install of the wheel.

   Then it waits for approval in the `pypi` environment, and publishes with attestations.
5. Verify at <https://pypi.org/p/aureproof>. The release files should show attestations
   from this repository's `release.yml`.
