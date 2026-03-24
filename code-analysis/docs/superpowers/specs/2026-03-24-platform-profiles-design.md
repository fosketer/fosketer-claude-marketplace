# Platform Profiles: Kustomize, FluxCD, k3s

**Date:** 2026-03-24
**Status:** Draft

## Problem

The code-analysis plugin can detect and analyze codebases by language (Go, Python, Rust, etc.) and framework (React, Flutter, .NET, etc.), but has no awareness of infrastructure/platform tools. Projects using Kustomize, FluxCD, and k3s contain YAML configurations with tool-specific patterns, anti-patterns, and security concerns that the scanner currently treats as generic YAML.

## Goals

1. Enable the scanner to **detect and properly categorize** tool-specific files (Kustomize overlays, FluxCD CRDs, k3s configs)
2. Enable the scanner to **identify misconfigurations, security gaps, and anti-patterns** within those files
3. Follow the tiered loading strategy — core profiles for lean context, advanced profiles loaded only when heavy usage is detected

## Non-Goals

- Creating new scan dimensions for platform tools (they enrich existing dimensions)
- Covering the full Kubernetes ecosystem (Helm, ArgoCD, Terraform are out of scope for this iteration)

## Design

### New Directory: `references/platform-profiles/`

Six files organized in a tiered structure:

```
references/platform-profiles/
├── kustomize.md              (~100 lines)
├── kustomize-advanced.md     (~150 lines)
├── fluxcd.md                 (~110 lines)
├── fluxcd-advanced.md        (~180 lines)
├── k3s.md                    (~100 lines)
└── k3s-advanced.md           (~160 lines)
```

### Core Profile Format

Platform profiles are modeled on **framework profiles** (react.md, electron.md) rather than language profiles, because platform tools — like frameworks — define architecture expectations and deployment patterns rather than syntax or package management. The following deviations from the framework profile format are intentional:

- **"Common Integrations" added** — new section for cross-tool interaction notes (e.g., FluxCD Kustomization resources pointing to Kustomize overlays). No existing profile type has this; it is a deliberate extension for the platform category where tools are commonly used in combination.
- **"Security Hotspots" instead of "Security Considerations"** — platform tools have specific, enumerable misconfigurations (not general considerations), making "Hotspots" more precise.
- **"Complexity Indicators" omitted** — platform configs are declarative YAML; function length, nesting depth, and parameter count metrics do not apply. Complexity is captured via anti-patterns (e.g., deep overlay nesting) instead.
- **"Performance Hotspots" expanded** — includes operational concerns (reconciliation loops, resource exhaustion) beyond code-level performance.

```
# {Tool} Platform Profile

## Detection Markers
## Architecture Expectations
## Common Patterns
## Common Anti-Patterns
## Security Hotspots
## Performance Hotspots
## Testing Conventions
## Common Integrations
## Context7 Library IDs
```

### Advanced Profile Format

Advanced profiles share a common skeleton but allow tool-specific section names where the content differs fundamentally. The `Loading Trigger`, `Security Deep-Dive`, and `Policy Validation Guide` sections are present in all three. The middle sections vary:

- **kustomize-advanced.md:** "Generator/Transformer Pitfalls", "Operational Concerns"
- **fluxcd-advanced.md:** "Per-CRD Misconfiguration Tables", "Multi-Tenancy Lockdown", "Reconciliation Tuning"
- **k3s-advanced.md:** "CIS Benchmark Table", "Port Firewall Matrix", "HA Configuration", "Runtime Hardening"

```
# {Tool} Advanced Profile

## Loading Trigger
## Security Deep-Dive
## {Tool-Specific Sections}
## Policy Validation Guide
```

### Core Profile Content

#### kustomize.md (~100 lines)

- **Detection:** `kustomization.yaml`, `overlays/`, `base/`, `components/` directory patterns, `kustomize.config.k8s.io` apiVersion
- **Patterns:** overlay/base structure, strategic merge patches, `images` transformer for digest pinning, hash-suffixed ConfigMaps/Secrets
- **Anti-patterns:** deep overlay nesting (>3 levels), duplicating manifests across overlays instead of patching, unpinned remote bases, disabling name suffix hash globally
- **Security:** plaintext secrets in `secretGenerator`, missing `namespace` in overlays (deploys to default), patches removing `securityContext`, container images without digest pinning, `hostNetwork`/`hostPID` in bases
- **Testing:** `kustomize build` dry-run, `kubeconform` schema validation, `conftest` policy checks, golden file diffs

#### fluxcd.md (~110 lines)

- **Detection:** `toolkit.fluxcd.io` apiVersions, `flux-system/` directory, `gotk-components.yaml`, CRD kinds (GitRepository, Kustomization, HelmRelease, etc.)
- **Patterns:** folder-per-environment in single branch, `sourceRef` linking, `dependsOn` for ordering, SOPS decryption via `spec.decryption`
- **Anti-patterns:** branch-per-environment, manual `kubectl edit` creating drift, suspended resources forgotten, monolithic Kustomization managing hundreds of resources, `spec.prune: false` leaving orphans
- **Security:** missing `--no-cross-namespace-refs` (tenant isolation breach), no default service account enforcement (falls back to cluster-admin), plaintext secrets in Git, no commit signature verification (`spec.verify`)
- **Testing:** `flux check`, `kubeconform` with Flux CRD schemas, kind cluster integration tests, CUE-based validation

#### k3s.md (~100 lines)

- **Detection:** `helm.cattle.io` CRDs (HelmChart, HelmChartConfig) in YAML files, `+k3s` version suffix in manifests, `k3d-config.yaml`, Ansible/Terraform references to k3s roles/providers, `curl -sfL https://get.k3s.io` in scripts. Note: system paths like `/etc/rancher/k3s/` are runtime markers not typically found in source repos — they are included only for live system audit scenarios, not codebase scanning.
- **Patterns:** `/etc/rancher/k3s/config.yaml` over CLI flags, server node taints (`CriticalAddonsOnly`), WireGuard flannel backend for encrypted overlay, PSA namespace labels
- **Anti-patterns:** default Traefik without auth/TLS/rate-limiting, Flannel without NetworkPolicy enforcement (silently ignores policies), single-server production, `local-path` StorageClass for stateful workloads, kubeconfig with loosened permissions
- **Security:** `k3s.yaml` file permissions (must be 0600 root:root), node-token protection, secrets encryption at rest (`--secrets-encryption`), API server binding to specific interface
- **Testing:** kube-bench with k3s CIS profile, Sonobuoy conformance, k3d for CI ephemeral clusters, kubescape for NSA/CISA compliance

### Advanced Profile Content

#### kustomize-advanced.md (~150 lines)

- **Loading trigger:** >3 overlays detected, `components/` directory present, or `helmCharts` in kustomization.yaml
- **Security checklist:** RBAC in overlays, ConfigMap credential leakage, Helm chart inflation without version pinning, `commonLabels` overwriting PSA labels, `vars`/`replacements` exposing secrets
- **Generator/transformer pitfalls:** `patchesStrategicMerge` with full resource copies, `sortOptions` for CRD-before-CR ordering, `generatorOptions` side effects
- **Policy validation:** Rego examples (no-latest-tags, required resource limits, required labels), Kyverno and Trivy integration patterns
- **Operational:** HPA conflicts with `replicas` field in overlays, missing PodDisruptionBudgets, garbage collection of hash-suffixed resources, remote bases over slow networks

#### fluxcd-advanced.md (~180 lines)

- **Loading trigger:** >5 Flux CRDs found, multi-tenancy markers detected (`spec.serviceAccountName` in Kustomizations), or `spec.decryption` present
- **Per-CRD misconfiguration tables:**
  - GitRepository: missing `spec.verify`, no `spec.ignore` for large repos, auth failures
  - Kustomization: missing `serviceAccountName` (cluster-admin fallback), `prune: false`, missing `healthChecks`, `force: true` in production
  - HelmRelease: hardcoded secrets in `spec.values`, missing remediation retries, unversioned charts, missing `dependsOn`
  - ImagePolicy/ImageUpdateAutomation: permissive tag filters, automated push to production branch
  - OCIRepository: missing Cosign verification
  - Alert/Provider: no alerts configured, webhook secrets in plaintext
- **Multi-tenancy lockdown:** `--no-cross-namespace-refs`, `--default-service-account`, RBAC aggregation removal, workload identity, network policies for source-controller
- **Reconciliation tuning:** interval recommendations by resource type, timeout/retryInterval settings, controller concurrency and sharding

#### k3s-advanced.md (~160 lines)

- **Loading trigger:** k3s config files detected (`/etc/rancher/k3s/config.yaml`, `k3d-config.yaml`), embedded etcd markers, or `HelmChartConfig` CRDs present
- **CIS benchmark table:** API server flags (`anonymous-auth=false`, `audit-log-path`, `encryption-provider-config`, `profiling=false`), etcd directory permissions (0700), kubelet hardening (`read-only-port=0`, `protect-kernel-defaults`)
- **Port firewall matrix:** 6443 (API server), 9345 (supervisor), 8472 (VXLAN), 51820 (WireGuard), 10250 (kubelet), 2379-2380 (etcd) — each with required access restrictions
- **HA configuration:** embedded etcd quorum (odd server count), load balancer requirement for agents, leader election tuning for resource-constrained environments
- **Runtime hardening:** containerd config validation, private registry TLS enforcement, RuntimeClass for gVisor/Kata sandboxing, rootless mode limitations

### Agent Integration

#### Stack Detection Changes

Add platform detection to `code-analyzer` agent Step 1. After detecting language/framework, also detect platform tools:

| Marker | Platform | Disambiguation |
|--------|----------|----------------|
| `kustomization.yaml` with `apiVersion: kustomize.config.k8s.io` OR containing `resources:`/`bases:`/`patches:` fields (no `apiVersion` with `toolkit.fluxcd.io`) | kustomize | Distinguishes native Kustomize from FluxCD Kustomization CRDs |
| Any YAML with `toolkit.fluxcd.io` apiVersion | fluxcd | — |
| `helm.cattle.io` CRDs, `+k3s` version strings, `k3d-config.yaml`, k3s install scripts | k3s | System paths (`/etc/rancher/k3s/`) only for live audit mode |

Stack info expands to include a `platforms` field:
```json
{ "languages": ["go"], "frameworks": ["react"], "platforms": ["kustomize", "fluxcd"] }
```

#### Multi-Platform Detection

All detected platforms are loaded — there is no precedence or mutual exclusion. In practice, these tools are commonly used together (e.g., k3s + FluxCD + Kustomize). Loading limits:

- **Maximum 3 core profiles** loaded simultaneously (~310 lines total). This is comparable to loading a language + framework profile and stays within token budget.
- **Advanced profiles are loaded individually** as triggers are met during scanning. At most one advanced profile per platform, adding ~150-180 lines each.
- **Worst case** (all 3 core + all 3 advanced): ~800 lines of platform context. This is acceptable given that platform-heavy projects warrant deeper analysis and the profiles are loaded across multiple agent dispatches (one per dimension), not all at once in a single context.

#### Resource Loading Changes

Add to `code-analyzer` agent Step 2, after loading language/framework profiles:

```
4. ${CLAUDE_PLUGIN_ROOT}/references/platform-profiles/{platform}.md — for detected platform(s)
5. (Conditional) ${CLAUDE_PLUGIN_ROOT}/references/platform-profiles/{platform}-advanced.md — when loading triggers are met
```

Advanced profile loading triggers are evaluated **during Step 2** (resource loading), not mid-scan. The agent performs a quick pre-scan check before loading:
- Count `kustomization.yaml` files and check for `components/`/`helmCharts` → kustomize-advanced
- Count Flux CRDs and grep for `spec.serviceAccountName`/`spec.decryption` → fluxcd-advanced
- Grep for `HelmChartConfig`, `k3d-config.yaml`, etcd markers → k3s-advanced

This keeps all resource loading in Step 2, avoiding mid-scan context loading that would break the current agent workflow.

#### Dimension Mapping

Platform profile content maps to existing scan dimensions. Each dimension's sub-skill uses the relevant sections from loaded platform profiles:

| Dimension | Platform Profile Sections Used |
|-----------|-------------------------------|
| **structure** | Architecture Expectations, Common Patterns, Common Anti-Patterns (structural: overlay nesting, directory layout, resource organization) |
| **security** | Security Hotspots, Security Deep-Dive, Hardening Checklist (misconfigurations, RBAC, secrets, CIS items) |
| **quality** | Common Anti-Patterns (code quality: duplication, drift, naming), Performance Hotspots (operational concerns) |
| **testing** | Testing Conventions, Policy Validation Guide (validation tools, CI patterns) |

The agent does not need explicit routing — the sub-skill for each dimension naturally picks up relevant content from the loaded profiles, just as it does with language/framework profiles today.

#### No Changes Required

- Scan dimensions remain the same (structure, quality, security, testing)
- Output format unchanged (findings JSON with severity levels)
- Plugin mode unchanged (platform profiles are not loaded in plugin mode)
- Templates, report reconciliation, and plan generation unchanged

## File Inventory

| File | Action | Lines (est.) |
|------|--------|-------------|
| `references/platform-profiles/kustomize.md` | Create | ~100 |
| `references/platform-profiles/kustomize-advanced.md` | Create | ~150 |
| `references/platform-profiles/fluxcd.md` | Create | ~110 |
| `references/platform-profiles/fluxcd-advanced.md` | Create | ~180 |
| `references/platform-profiles/k3s.md` | Create | ~100 |
| `references/platform-profiles/k3s-advanced.md` | Create | ~160 |
| `agents/code-analyzer/AGENT.md` | Edit | ~15 lines added |

**Total new content:** ~800 lines across 6 reference files, ~15 lines of agent changes.
