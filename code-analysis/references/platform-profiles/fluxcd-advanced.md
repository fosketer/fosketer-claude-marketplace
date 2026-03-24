# FluxCD Advanced Profile

## Loading Trigger

Load this profile when ANY of these conditions are met during Step 2 pre-scan:
- More than 5 Flux CRD resources found (any `toolkit.fluxcd.io` apiVersion)
- `spec.serviceAccountName` found in any Kustomization or HelmRelease resource
- `spec.decryption` found in any Kustomization resource

## Security Deep-Dive

### Critical
- Missing `--default-service-account` on kustomize/helm controllers — any tenant Kustomization/HelmRelease without explicit `spec.serviceAccountName` reconciles with cluster-admin privileges
- Hardcoded secrets in `spec.values` of HelmRelease — plaintext in Git
- Missing `--no-cross-namespace-refs=true` — tenants can reference other tenants' sources and secrets

### High
- No commit signature verification (`spec.verify` on GitRepository) — anyone with repo write access can push changes Flux blindly applies
- No OCI artifact signature verification (`spec.verify` on OCIRepository with Cosign)
- Plaintext secrets in Git without SOPS/sealed-secrets decryption
- `--insecure-kubeconfig-exec=true` allows arbitrary binary execution in KubeConfigs
- `--insecure-kubeconfig-tls=true` permits HTTP-only access to remote clusters
- Missing network policies for source-controller (any pod can fetch artifacts)

### Medium
- `--no-remote-bases=true` not set on kustomize-controller — Kustomizations can reference external URLs
- RBAC aggregation (`flux-view`, `flux-edit` ClusterRoles) granting excessive tenant visibility
- Workload identity not locked down — cloud provider integrations using overly-privileged service accounts
- Alert/Provider webhook secrets in plaintext

## Per-CRD Misconfiguration Tables

### GitRepository
| Field | Issue | Severity |
|-------|-------|----------|
| `spec.secretRef` omitted for private repos | Auth errors, no fallback | HIGH |
| `spec.verify` not configured | Accepts unsigned commits | HIGH |
| `spec.ignore` missing for large repos | Fetches entire repo, memory overhead | MEDIUM |
| `spec.ref.branch` tracking mutable branch | Unnecessary polling overhead | LOW |

### Kustomization
| Field | Issue | Severity |
|-------|-------|----------|
| `spec.serviceAccountName` omitted (multi-tenant) | Falls back to cluster-admin SA | CRITICAL |
| `spec.prune` false or omitted | Orphaned resources accumulate | MEDIUM |
| `spec.healthChecks` missing | Reports success without verifying workload health | MEDIUM |
| `spec.dependsOn` missing for CRD ordering | Applies CRs before CRDs exist | HIGH |
| `spec.force: true` in production | Overwrites fields managed by HPA or other controllers | HIGH |
| `spec.decryption` missing for encrypted secrets | Encrypted blobs deployed as-is | HIGH |
| `spec.targetNamespace` with cluster-scoped resources | Cluster-scoped resources ignore override | MEDIUM |

### HelmRelease
| Field | Issue | Severity |
|-------|-------|----------|
| `spec.serviceAccountName` omitted (multi-tenant) | Cluster-admin fallback | CRITICAL |
| `spec.values` with hardcoded secrets | Plaintext in Git | CRITICAL |
| `spec.chart.spec.version: "*"` or no constraint | Deploys arbitrary chart versions | HIGH |
| `spec.install.remediation.retries` missing | Single failure = permanent stuck state | MEDIUM |
| `spec.upgrade.remediation.retries` missing | Same for upgrades | MEDIUM |
| `spec.dependsOn` missing for cross-chart deps | Race conditions during deployment | HIGH |
| `spec.install.crds: Skip` when CRDs needed | Dependent resources fail | HIGH |

### ImagePolicy / ImageUpdateAutomation
| Field | Issue | Severity |
|-------|-------|----------|
| Overly permissive `spec.filterTags.pattern` | Matches dev builds for production | MEDIUM |
| `spec.git.push.branch` set to prod branch | Auto-commits bypass review | HIGH |
| Missing `# {"$imagepolicy": ...}` markers | Automation configured but never updates files | HIGH |
| `spec.update.path` not restricted | Scans entire repo | MEDIUM |

### OCIRepository
| Field | Issue | Severity |
|-------|-------|----------|
| `spec.verify` not configured | Deploys unsigned/tampered artifacts | HIGH |

### Alert / Provider
| Field | Issue | Severity |
|-------|-------|----------|
| No Alerts configured | Failed reconciliations go unnoticed | MEDIUM |
| `spec.eventSeverity: error` only | Misses warning-level signals | LOW |
| Provider webhook secret in plaintext | Notification credentials exposed | HIGH |

## Multi-Tenancy Lockdown

Required controller flags for multi-tenant clusters:
- `--no-cross-namespace-refs=true` on ALL controllers (helm, kustomize, notification, image-reflector, image-automation)
- `--default-service-account=<unprivileged-sa>` on kustomize-controller and helm-controller
- `--default-decryption-service-account=<sa>` on kustomize-controller (for cloud provider identity)
- Remove `flux-view` and `flux-edit` ClusterRoles if tenants should not see all Flux resources
- Deploy network policies restricting source-controller artifact access to Flux components only
- Use node affinity/taints to segregate Flux controllers from tenant workloads

## Reconciliation Tuning

Recommended intervals by resource type:
| Resource | Active Dev | Stable/Infra |
|----------|-----------|-------------|
| GitRepository | 1m-5m | 5m-15m |
| HelmRepository | 10m-30m | 30m-1h |
| Kustomization (critical) | 5m | 5m |
| Kustomization (standard) | 10m | 10m |
| HelmRelease | 5m-10m | 15m-30m |

Other tuning:
- Always set `spec.timeout` (recommended starting point: 1m30s) — prevents infinite hangs
- Set `spec.retryInterval` (e.g., 30s) for faster failure recovery
- Increase `--concurrent` to 8+ on kustomize/helm controllers for large clusters
- Reduce `--requeue-dependency` to 5s for faster dependent resource reconciliation
- Consider controller sharding (`--watch-label-selector`) for mission-critical workloads

## Policy Validation Guide

### Kyverno Policies for Flux
- All HelmReleases MUST have `spec.serviceAccountName`
- All Kustomizations MUST have `spec.serviceAccountName`
- All sources MUST come from approved GitHub organizations
- All GitRepositories MUST have `spec.verify` configured

### Integration Testing Pattern
1. Bootstrap Flux in a `kind` cluster in CI
2. Apply test Kustomizations/HelmReleases
3. Wait for reconciliation (`flux get kustomizations --watch`)
4. Verify resources reach Ready state
5. Test drift correction: manually edit a resource, verify Flux reverts it

### CUE Validation
Use `cue.dev/docs/curated-module-crd-fluxcd` module for type-safe CRD validation.
