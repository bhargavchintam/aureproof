# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Check a CycloneDX SBOM made by ``uv export --format cyclonedx1.5`` (issue #56).

    uv export --format cyclonedx1.5 --frozen --no-dev -o sbom.cdx.json
    uv run python scripts/check_sbom.py sbom.cdx.json

Passes when the SBOM is CycloneDX 1.5, describes the aureproof package, and lists
every runtime dependency in the lockfile at its locked version.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def locked_runtime() -> dict[str, str]:
    out = subprocess.run(
        ["uv", "export", "--format", "requirements.txt", "--frozen", "--no-dev", "--no-hashes"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    pins = {}
    for line in out.splitlines():
        line = line.split(";")[0].strip()
        if "==" in line and not line.startswith("#"):
            name, version = line.split("==", 1)
            pins[name.strip().lower().replace("_", "-")] = version.strip()
    return pins


def problems(sbom: dict, pins: dict[str, str]) -> list[str]:  # type: ignore[type-arg]
    found = []
    if sbom.get("bomFormat") != "CycloneDX" or sbom.get("specVersion") != "1.5":
        found.append(f"not CycloneDX 1.5: {sbom.get('bomFormat')} {sbom.get('specVersion')}")
    if (sbom.get("metadata", {}).get("component") or {}).get("name") != "aureproof":
        found.append("metadata.component is not aureproof")
    listed = {
        c.get("name", "").lower().replace("_", "-"): c.get("version")
        for c in sbom.get("components", [])
    }
    for name, version in sorted(pins.items()):
        if listed.get(name) != version:
            found.append(f"{name}=={version} missing (SBOM has {listed.get(name)})")
    return found


def main() -> int:
    sbom = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    pins = locked_runtime()
    errors = problems(sbom, pins)
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if not errors:
        print(f"SBOM ok: CycloneDX 1.5, {len(pins)} locked runtime dependencies listed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
