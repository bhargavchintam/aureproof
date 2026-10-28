<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# The M2 live slice

Issue #47. The M2 commitment point is one live, budgeted evidence chain: protocol,
system and task identities, model and tool observations, the captured submission,
the controller's verdict, a signed bundle, and an identical offline re-score. These
are the steps. The tooling is tested in the Docker lane with a scripted model
(`tests/integration/test_live_slice.py`). What it still needs is a key (#7), the
reviewer (#31) and the qualified host (#32), as listed in
[`maintainer-actions.md`](../maintainer-actions.md).

## 1. Freeze the Task Health Records

On the qualified Linux host (#32), for each cohort task:

```bash
uv run aureproof task validate authz-001 --out thr-authz-001.json
uv run --extra inspect aureproof task probe authz-001 --model anthropic/<model-id>
```

The reviewer (#31) checks the THRs before the protocol is written. A probe that says
`SATURATED` sends the task back for redesign.

## 2. Write and sign the protocol

The protocol (`specs/decision/`) names each cohort task by identity, the THR it
relies on by digest, configurations A and B by system identity, the repetitions, the
budget and the margin. `aureproof.runners.slice.thr_digest` gives a THR's digest. A
system's identity is `InspectRunner(config).system_spec().identity`. Commit the
protocol, then sign it with the `sign.yml` workflow before any assessment episode
runs.

## 3. Run

```bash
uv run --extra inspect aureproof run \
  --protocol protocol.json --thr thr-authz-001.json \
  --subject reference --model anthropic/<model-id> \
  --out bundles/m2-slice
```

The command refuses before any dispatch if the system is neither A nor B, a task is
not a registered fixture, or a THR's digest, task or health does not match. When it
finishes, it validates the bundle and re-scores it offline.

## 4. Sign, verify, re-score

Commit the bundle and dispatch `gh workflow run sign.yml --ref main -f target=bundles/m2-slice`.
Commit the downloaded `seal.sigstore.json`. Then a third party, with no key and no
network inference, runs:

```bash
uv run --extra sign aureproof validate bundles/m2-slice --require-signature
uv run aureproof score bundles/m2-slice --offline
```

## 5. Decide

The reviewer records isolation, missing-evidence and retry behavior, and the
limitations, using [`bridge-coverage.md`](../bridge-coverage.md). The decision (go,
redesign or stop) goes into `ROADMAP.md` together with the interview outcome (#6).
Benchmark expansion (#48, #49, #52) stays blocked until it is go.
