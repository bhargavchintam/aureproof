# The Linux evaluation host

Isolation work — sandbox egress enforcement, the separate verifier in v0.2, and
the trust-boundary tests in the threat model (issue #17) — needs a real Linux
host. Docker Desktop on macOS or Windows runs containers inside a VM whose
egress enforcement is unverified; use it for development only (plan §7.1).

## Requirements

| Item | Requirement |
| --- | --- |
| OS | Linux with cgroup v2; Ubuntu 24.04 LTS recommended |
| Container runtime | **Docker Engine** (not Docker Desktop) |
| Networking | `nftables` installed; `nf_tables` kernel support (Harbor's egress allowlist, v0.2) |
| Size (v0.1) | 4 vCPU, 8–16 GB RAM, 50 GB disk is plenty for synthetic fixtures |
| Size (v0.2, plan only) | Real-CVE suites are large: SEC-bench needs >200 GB; CyberGym data is ~240 GB (~10 TB with images). Start from small subsets |
| Toolchain | `git`, [`uv`](https://docs.astral.sh/uv/) |

## Provision

Any dedicated cloud VM or spare machine works. On Ubuntu:

1. Install Docker Engine from the official instructions
   (<https://docs.docker.com/engine/install/ubuntu/>) and add your user to the `docker` group.
2. `sudo apt install nftables git`
3. Install uv: <https://docs.astral.sh/uv/getting-started/installation/>
4. Clone the repository and run the check:

```bash
git clone https://github.com/bhargavchintam/aureproof.git
cd aureproof
scripts/check_host.sh
```

Every line should say `PASS`. The script exits non-zero if any check fails. Set
`AUREPROOF_CHECK_IMAGE` to use a different small image than `busybox:1.36`.

## Host hygiene

- Use a **dedicated** host: no production credentials, no shared secrets, not multi-tenant.
- Provider API keys for live runs stay in the controller and are never passed
  into sandboxes (plan §3.6); use per-run scoped keys with spending limits.
- Keep the host patched; record the kernel and Docker versions in run metadata.
