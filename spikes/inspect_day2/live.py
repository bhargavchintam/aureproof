# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""One-command live run for spike check 2 (issue #7): Claude Code on authz-001.

    # Rehearsal: no key, no cost. Plants a fake canary key in the controller.
    uv run --extra inspect python spikes/inspect_day2/live.py --dry-run

    # Live: ANTHROPIC_API_KEY=... in a mode-600 env file (never committed).
    uv run --extra inspect python spikes/inspect_day2/live.py

Steps, each a pass/fail check recorded in ``logs/live-summary-<ts>.json``:

1. Pre-cache the pinned Claude Code binary for the sandbox platform (host-side;
   the sandbox has no network and downloads nothing).
2. ``bridge_probe`` on the same model: the proxy answers, egress is blocked,
   and no environment value in the sandbox hashes to the provider key.
3. ``claude_code`` on both variants with single attempts and per-sample budgets.
4. Leak scan: the key string appears in no member of any ``.eval`` log.
5. Offline re-score reproduces the live verdicts.

The key is read into this process only; it is never printed or written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from rescore import rescore  # noqa: E402
from task import CLAUDE_CODE_VERSION, authz_spike  # noqa: E402

DEFAULT_ENV_FILE = Path.home() / ".aureproof-spike.env"
DEFAULT_MODEL = "anthropic/claude-haiku-4-5-20251001"
KEY_VAR = "ANTHROPIC_API_KEY"
SANDBOX_PLATFORM = "linux-arm64" if os.uname().machine in ("arm64", "aarch64") else "linux-x64"


def load_key(env_file: Path) -> str:
    """Read KEY_VAR from a private env file without echoing it."""
    if not env_file.is_file():
        sys.exit(f"missing {env_file}: add '{KEY_VAR}=...' and chmod 600")
    if stat.S_IMODE(env_file.stat().st_mode) & 0o077:
        sys.exit(f"{env_file} is readable by others; run: chmod 600 {env_file}")
    for line in env_file.read_text().splitlines():
        name, sep, value = line.strip().removeprefix("export ").partition("=")
        if sep and name.strip() == KEY_VAR and value.strip().strip("'\""):
            return value.strip().strip("'\"")
    sys.exit(f"{KEY_VAR} not found in {env_file}")


def leak_hits(log_path: str, secret: str) -> list[str]:
    """Names of archive members that contain the secret verbatim."""
    needle = secret.encode()
    with zipfile.ZipFile(log_path) as archive:
        return [name for name in archive.namelist() if needle in archive.read(name)]


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(
    model: str, secret: str, log_dir: Path, token_limit: int, time_limit: int
) -> dict[str, Any]:
    from inspect_ai import eval as inspect_eval
    from inspect_ai.log import read_eval_log
    from inspect_swe import download_agent_binary

    checks: dict[str, Any] = {}
    download_agent_binary("claude_code", CLAUDE_CODE_VERSION, SANDBOX_PLATFORM)
    common: dict[str, Any] = {
        "model": model,
        "log_dir": str(log_dir),
        "retry_on_error": 0,
        "fail_on_error": False,
        "display": "plain",
    }

    # 2. Bridge probe on the real provider.
    [probe] = inspect_eval(authz_spike(subject="bridge_probe"), **common)
    key_digest = hashlib.sha256(secret.encode()).hexdigest()
    probe_ok = True
    for sample in read_eval_log(str(probe.location)).samples or []:
        report = sample.store.get("probe_report") or {}
        leaked = key_digest in (report.get("env_sha256") or {}).values()
        ok = bool(report.get("proxy", {}).get("ok")) and str(report.get("egress", "")).startswith(
            "blocked"
        )
        probe_ok &= ok and not leaked
        checks[f"probe:{sample.id}"] = {
            "proxy_ok": report.get("proxy", {}).get("ok"),
            "egress": report.get("egress"),
            "key_in_sandbox_env": leaked,
        }

    # 3. Claude Code, single attempts, bounded budgets.
    [live] = inspect_eval(
        authz_spike(subject="claude_code", token_limit=token_limit, time_limit=time_limit),
        **common,
    )
    samples = read_eval_log(str(live.location)).samples or []
    for sample in samples:
        score = (sample.scores or {}).get("findings_matcher")
        checks[f"claude_code:{sample.id}"] = {
            "error": sample.error.message[:300] if sample.error else None,
            "disposition": score.answer if score else "infra_failure",
            "verdicts": (score.metadata or {}).get("verdicts") if score else None,
            "capture": (sample.store.get("aureproof_capture") or {}).get("status"),
            "tokens": sum(u.total_tokens for u in (sample.model_usage or {}).values()),
            "limit": sample.limit.type if sample.limit else None,
        }

    # 4. Leak scan over every log this run wrote.
    logs = [str(probe.location), str(live.location)]
    leaks = {path: hits for path in logs if (hits := leak_hits(path, secret))}

    # 5. Offline re-score.
    live_verdicts, rescored = rescore(str(live.location))

    checks["key_leaks_in_logs"] = leaks
    checks["rescore_matches"] = live_verdicts == rescored
    checks["logs"] = {path: sha256_file(path) for path in logs}
    submitted = any(
        c.get("capture") == "captured" for k, c in checks.items() if k.startswith("claude_code:")
    )
    checks["passed"] = {
        "bridge_probe": probe_ok,
        "no_key_in_logs": not leaks,
        "rescore_matches": checks["rescore_matches"],
        "claude_code_wrote_findings": submitted,
    }
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="mockllm + a fake canary key")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--token-limit", type=int, default=400_000, help="per sample")
    parser.add_argument("--time-limit", type=int, default=900, help="seconds per sample")
    args = parser.parse_args()

    if args.dry_run:
        secret, model = f"sk-ant-dryrun-{uuid.uuid4().hex}", "mockllm/model"
    else:
        secret, model = load_key(args.env_file), args.model
    os.environ[KEY_VAR] = secret  # this process only; the bridge must keep it out of the sandbox

    log_dir = HERE / "logs"
    checks = run(model, secret, log_dir, args.token_limit, args.time_limit)
    checks["mode"] = "dry-run" if args.dry_run else "live"
    checks["model"] = model
    checks["claude_code_version"] = CLAUDE_CODE_VERSION

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = log_dir / f"live-summary-{stamp}.json"
    out.write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))
    print(f"summary: {out}")

    required = dict(checks["passed"])
    if args.dry_run:  # mockllm writes no findings; plumbing only
        required.pop("claude_code_wrote_findings")
    sys.exit(0 if all(required.values()) else 1)


if __name__ == "__main__":
    main()
