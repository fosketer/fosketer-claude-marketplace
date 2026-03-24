# Platform Profiles Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add kustomize, fluxcd, and k3s platform profiles to the code-analysis plugin so the scanner can detect, categorize, and identify misconfigurations in infrastructure/platform tool configs.

**Architecture:** New `references/platform-profiles/` directory with 6 files (3 core + 3 advanced), plus agent integration changes to detect platforms and load profiles during Step 1/Step 2.

**Tech Stack:** Markdown reference files + agent prompt changes (no runtime code)

**Spec:** `docs/superpowers/specs/2026-03-24-platform-profiles-design.md`

**Parallelization:** Tasks 1-3 (core profiles) are independent and can run in parallel. Tasks 4-6 (advanced profiles) are independent and can run in parallel. Task 7 (agent update) depends on Tasks 1-6. Task 8 (verification) depends on Task 7.

---

### Task 1: Create Kustomize Core Profile

**Files:**
- Create: `references/platform-profiles/kustomize.md`

- [ ] **Step 1: Create the file**

Write `references/platform-profiles/kustomize.md` with all 9 sections following the framework-profile convention. Use the spec content summaries (lines 79-85) and the research findings as source material. Target ~100 lines.

The file MUST follow this exact section structure:

```markdown
# Kustomize Platform Profile

## Detection Markers

- `kustomization.yaml` files with `apiVersion: kustomize.config.k8s.io/v1beta1` or `kustomize.config.k8s.io/v1`
- `kind: Kustomization` or `kind: Component` in YAML files (NOT `kustomize.toolkit.fluxcd.io` — that is FluxCD)
- `overlays/`, `base/`, `bases/`, `components/` directory patterns
- `resources:`, `patches:`, `configMapGenerator:`, `secretGenerator:` fields in kustomization.yaml
- `kubectl apply -k` or `kustomize build` in CI scripts, Makefiles, Dockerfiles
- ArgoCD `Application` with `spec.source.kustomize`, Flux `Kustomization` CRD referencing Kustomize overlays

## Architecture Expectations

Standard directory layout:

base/                        # Shared resource definitions
  kustomization.yaml
  deployment.yaml
  service.yaml
overlays/
  dev/                       # Per-environment overrides
    kustomization.yaml
    patches/
  staging/
    kustomization.yaml
  prod/
    kustomization.yaml
    patches/
components/                  # Cross-cutting reusable concerns (v3.7+)
  monitoring/
    kustomization.yaml

- Bases SHOULD contain complete, valid resource definitions
- Overlays SHOULD only patch what differs per environment
- Components SHOULD be used for cross-cutting concerns (sidecars, labels, policies)
- Remote bases MUST pin to specific tag or commit SHA

## Common Patterns

- **Overlay/base structure**: Bases define resources, overlays customize per environment
- **Strategic merge patches**: Targeted field overrides via `patches:` with merge strategy
- **Image transformer**: `images:` section for digest pinning and tag management
- **Hash-suffixed ConfigMaps/Secrets**: `configMapGenerator`/`secretGenerator` with name hash for rolling updates
- **Namespace transformer**: `namespace:` field to ensure all resources deploy to correct namespace
- **Name prefix/suffix**: `namePrefix:`/`nameSuffix:` for environment-level resource isolation
- **Replacements**: `replacements:` for variable substitution (replaces deprecated `vars:`)
- **Components**: Reusable cross-cutting configs applied via `components:` reference

## Common Anti-Patterns

- **Deep overlay nesting** (>3 levels): overlay-of-overlay chains become impossible to reason about
- **Duplicating manifests across overlays**: Copy-pasting full YAML instead of patching — causes silent drift
- **Full resource copies as patches**: `patchesStrategicMerge` with near-complete resources, making the base meaningless
- **Unpinned remote bases**: `resources: ["https://github.com/org/repo?ref=main"]` — moving target
- **Disabling name suffix hash globally**: `generatorOptions: disableNameSuffixHash: true` prevents rolling updates on config changes
- **Mixing kustomize and raw kubectl apply**: Split-brain config management
- **Index as key in generators**: Not using `behavior: merge` or `behavior: replace` when intended

## Security Hotspots

- **Plaintext secrets in `secretGenerator`**: `literals` or `files` commit credentials to VCS — use external secret managers (Vault, sealed-secrets, external-secrets-operator)
- **Missing `namespace` in overlays**: Resources deploy to `default` namespace with fewer restrictions — always set `namespace:` transformer
- **Patches removing securityContext**: Strategic merge patches can delete security fields by setting them to `null`
- **Container images without digest pinning**: Tag mutation attacks — use `images:` transformer with `newTag: sha256:...` or `digest:`
- **`hostNetwork`/`hostPID`/`hostIPC` in bases**: Breaks pod isolation, often inherited from dev environments
- **Missing NetworkPolicy in bases**: All pod-to-pod traffic allowed by default without deny-all policies
- **ConfigMap values with connection strings/tokens**: `configMapGenerator` values are plaintext in rendered manifests
- **`commonLabels` overwriting PSA labels**: Can downgrade Pod Security Standards enforcement

## Performance Hotspots

- **Missing resource limits/requests in bases or overlays**: Enables DoS via resource exhaustion
- **Missing `replicas` patches in production**: Bases typically set `replicas: 1` — prod overlays must patch up
- **Large `configMapGenerator` with many files**: Massive resources slow API server; each change creates a new hash-suffixed name
- **Remote bases over slow networks**: `kustomize build` fetches on every build — vendor locally
- **HPA conflicts with `replicas` field**: Kustomize-managed replicas fight with autoscaler — omit `replicas` when HPA is present
- **Missing PodDisruptionBudget in prod overlays**: Node drains can terminate all replicas simultaneously
- **No garbage collection of old hash-suffixed resources**: Accumulates indefinitely without pruning

## Testing Conventions

- **`kustomize build` dry-run**: Verify all overlays produce valid YAML — run in CI for every overlay
- **`kubeconform` schema validation**: `kustomize build overlays/prod | kubeconform -strict -kubernetes-version 1.28.0`
- **`conftest` policy checks**: OPA/Rego policies for no-latest-tags, required resource limits, required labels
- **Golden file diffs**: Store expected rendered output, diff against actual to catch unintended changes
- **`pluto` deprecation detection**: Detects deprecated Kubernetes API versions in rendered manifests
- **Matrix CI build**: Run `kustomize build` against every discovered kustomization.yaml entry point

## Common Integrations

- **FluxCD**: Flux `Kustomization` CRD (`kustomize.toolkit.fluxcd.io`) reconciles Kustomize overlays. `spec.path` points to the overlay directory. Flux adds `spec.postBuild.substituteFrom` for variable injection beyond native Kustomize.
- **ArgoCD**: `Application` resource with `spec.source.kustomize` renders overlays server-side. Kustomize version may differ from CLI.
- **k3s**: Manifests in `/var/lib/rancher/k3s/server/manifests/` auto-deploy — Kustomize-rendered output can be placed here.
- **Helm**: `helmCharts:` in kustomization.yaml (v4.1+) inflates Helm charts inline. Pin chart `version` to avoid silent upstream changes.

## Context7 Library IDs

- `kubernetes-sigs/kustomize` -- Kustomize CLI and libraries
- `open-policy-agent/conftest` -- Policy testing for configs
- `yannh/kubeconform` -- Kubernetes manifest validation
- `fluxcd/kustomize-controller` -- FluxCD Kustomize integration
```

- [ ] **Step 2: Verify file structure matches framework profile convention**

Read `references/framework-profiles/react.md` and `references/platform-profiles/kustomize.md` side-by-side. Verify:
- All 9 sections present in correct order
- Bullet-point formatting matches existing style
- Line count is ~100 lines (80-120 acceptable)

- [ ] **Step 3: Commit**

```bash
git add references/platform-profiles/kustomize.md
git commit -m "feat(code-analysis): add kustomize core platform profile"
```

---

### Task 2: Create FluxCD Core Profile

**Files:**
- Create: `references/platform-profiles/fluxcd.md`

- [ ] **Step 1: Create the file**

Write `references/platform-profiles/fluxcd.md` with all 9 sections. Use the spec content summaries (lines 87-93) and the research findings. Target ~110 lines.

Key content per section:

**Detection Markers:**
- `toolkit.fluxcd.io` apiVersion in any YAML (definitive identifier)
- API groups: `source.toolkit.fluxcd.io`, `kustomize.toolkit.fluxcd.io`, `helm.toolkit.fluxcd.io`, `notification.toolkit.fluxcd.io`, `image.toolkit.fluxcd.io`
- CRD kinds: GitRepository, OCIRepository, HelmRepository, HelmChart, Bucket, Kustomization, HelmRelease, Alert, Provider, Receiver, ImageRepository, ImagePolicy, ImageUpdateAutomation
- `flux-system/` directory with `gotk-components.yaml`, `gotk-sync.yaml`
- `clusters/<name>/` directory structure
- `# {"$imagepolicy": ...}` comment markers for image automation

**Architecture Expectations:**
```
clusters/
  staging/
    flux-system/          # Flux bootstrap (gotk-components, gotk-sync)
    apps/                 # Application Kustomizations
    infrastructure/       # Shared infra (ingress, cert-manager, etc.)
  production/
    flux-system/
    apps/
    infrastructure/
```
- Folder-per-environment in single branch (NOT branch-per-environment)
- Infrastructure SHOULD be separated from application definitions
- Each team/tenant SHOULD have its own namespace and ServiceAccount

**Common Patterns:**
- `sourceRef` linking Kustomizations/HelmReleases to GitRepository/OCIRepository
- `dependsOn` for resource ordering (CRDs before CRs, infra before apps)
- SOPS decryption via `spec.decryption.provider: sops` with secretRef
- `spec.prune: true` for garbage collection of removed resources
- `spec.healthChecks` for deployment verification
- `spec.postBuild.substituteFrom` for variable injection
- `spec.suspend` for controlled reconciliation pauses

**Common Anti-Patterns:**
- Branch-per-environment (drift, merge conflicts, duplicated YAML)
- Manual `kubectl edit`/`kubectl apply` (creates drift overwritten by reconciler)
- Suspended resources forgotten (`spec.suspend: true` accumulates silent drift)
- Monolithic Kustomization managing hundreds of resources (one failure blocks all)
- `spec.prune: false` or omitted (orphaned resources accumulate)
- `spec.values` with hardcoded secrets (use `spec.valuesFrom` with encrypted Secrets)
- Using `latest` image tags (loses traceability)
- Renaming Kustomization with prune enabled (deletes and recreates all workloads)

**Security Hotspots:**
- Missing `--no-cross-namespace-refs=true` on controllers (tenant isolation breach)
- No `--default-service-account` on kustomize/helm controllers (falls back to cluster-admin)
- Plaintext secrets in Git (use SOPS with Age/GPG/KMS)
- No commit signature verification (`spec.verify` on GitRepository)
- No OCI artifact verification (`spec.verify` on OCIRepository with Cosign)
- `--no-remote-bases=true` not set on kustomize-controller (breaks hermetic builds)
- Missing network policies for source-controller artifact access
- `--insecure-kubeconfig-exec=true` allows arbitrary binary execution

**Performance Hotspots:**
- Aggressive reconciliation intervals (`spec.interval: 1m` everywhere generates API server load)
- Missing or misconfigured `spec.timeout` (stuck reconciliations block indefinitely)
- Low controller concurrency (`--concurrent=4` may bottleneck large clusters)
- Git ref resolution overhead (track branch vs pin to commit SHA)
- Missing `spec.ignore` on GitRepository for large repos (fetches everything)
- Controller resource exhaustion (no limits/requests set)

**Testing Conventions:**
- `flux check` for installation health validation
- `kubeconform` with Flux CRD schemas for manifest validation
- `flux-build` tool for offline kustomize+helm rendering without cluster access
- Kind cluster integration tests (reconciliation in CI)
- Kyverno policies for Flux conventions (all HelmReleases must have `serviceAccountName`)
- CUE-based validation with `cue.dev/docs/curated-module-crd-fluxcd`

**Common Integrations:**
- **Kustomize**: Flux Kustomization CRD reconciles native Kustomize overlays. `spec.path` points to the kustomization.yaml directory. Flux's Kustomize controller may behave slightly differently from CLI Kustomize.
- **k3s**: FluxCD commonly deployed on k3s clusters. Bootstrap via `flux bootstrap` requires kubeconfig access. k3s HelmChart CRDs and Flux HelmRelease are independent — do not mix.
- **SOPS/sealed-secrets**: `spec.decryption` integrates with SOPS for at-rest encryption. Alternative: sealed-secrets with SealedSecret CRD.
- **Image automation**: `ImagePolicy` + `ImageUpdateAutomation` auto-commit image tag updates to Git.

**Context7 Library IDs:**
- `fluxcd/flux2` -- Flux v2 mono-repo
- `fluxcd/kustomize-controller` -- Kustomize reconciler
- `fluxcd/helm-controller` -- Helm reconciler
- `fluxcd/source-controller` -- Source fetching

- [ ] **Step 2: Verify file structure matches convention**

Same verification as Task 1 Step 2. Target ~110 lines (90-130 acceptable).

- [ ] **Step 3: Commit**

```bash
git add references/platform-profiles/fluxcd.md
git commit -m "feat(code-analysis): add fluxcd core platform profile"
```

---

### Task 3: Create k3s Core Profile

**Files:**
- Create: `references/platform-profiles/k3s.md`

- [ ] **Step 1: Create the file**

Write `references/platform-profiles/k3s.md` with all 9 sections. Use the spec content summaries (lines 95-101) and the research findings. Target ~100 lines.

Key content per section:

**Detection Markers:**
- `helm.cattle.io` CRDs (`HelmChart`, `HelmChartConfig`) in YAML files (definitive for k3s)
- `+k3s` version suffix in manifests or version strings (e.g., `v1.28.4+k3s1`)
- `k3d-config.yaml` or `.k3d/` directories (k3s-in-Docker for dev)
- `curl -sfL https://get.k3s.io` in install scripts, cloud-init, user-data
- Ansible roles referencing `xanmanning.k3s` or `k3s-io/k3s-ansible`
- Terraform `rancher/k3s` provider or `k3s_cluster` resources
- Note: system paths (`/etc/rancher/k3s/`, `/var/lib/rancher/k3s/`) are runtime markers for live audit only, not typically in source repos

**Architecture Expectations:**
```
k3s config (when version-controlled):
  config.yaml               # Server/agent configuration (preferred over CLI flags)
  registries.yaml            # Private registry config
manifests/                    # Auto-deploy directory (placed in /var/lib/rancher/k3s/server/manifests/)
  helmchart-*.yaml           # HelmChart CRDs for addon management
  helmchartconfig-*.yaml     # HelmChartConfig for default addon overrides
```
- Configuration SHOULD use `config.yaml` instead of CLI flags (avoids secret leakage in process table)
- Server nodes SHOULD be tainted (`CriticalAddonsOnly=true:NoExecute`) to prevent user workloads
- Default components SHOULD be explicitly disabled if replaced (`--disable=traefik,servicelb`)

**Common Patterns:**
- **Config file over CLI flags**: `/etc/rancher/k3s/config.yaml` for all server/agent settings
- **HelmChart CRD for addons**: k3s-native way to deploy Traefik, CoreDNS, metrics-server
- **HelmChartConfig for overrides**: Customize default addons without replacing them
- **WireGuard flannel backend**: `--flannel-backend=wireguard-native` for encrypted pod traffic
- **PSA namespace labels**: `pod-security.kubernetes.io/enforce: restricted` on all non-system namespaces
- **Embedded etcd HA**: `--cluster-init` with odd number of server nodes (3, 5, 7)
- **System upgrade controller**: Automated k3s version upgrades via Plan CRD

**Common Anti-Patterns:**
- **Default Traefik without hardening**: No auth, no TLS enforcement, no rate limiting out of the box
- **Flannel without NetworkPolicy enforcement**: Default Flannel CNI silently ignores NetworkPolicy resources — false sense of security
- **Single-server production**: Single point of failure for entire control plane; SQLite cannot replicate
- **`local-path` StorageClass for stateful workloads**: No redundancy, no snapshots, no capacity management
- **Kubeconfig with loosened permissions**: `chmod 644 /etc/rancher/k3s/k3s.yaml` exposes cluster-admin credentials
- **Passing secrets via CLI flags**: Credentials visible in `ps aux` and `/proc/*/cmdline`
- **Running k3d for production**: k3d is a dev tool; adds Docker as unnecessary layer
- **Mixing server and agent workloads**: Without taints, user pods schedule on control plane nodes

**Security Hotspots:**
- **kubeconfig file permissions**: `/etc/rancher/k3s/k3s.yaml` MUST be 0600 root:root — contains cluster-admin credentials
- **Node-token protection**: `/var/lib/rancher/k3s/server/node-token` allows cluster joins — restrict access
- **Secrets encryption at rest**: Not enabled by default — use `--secrets-encryption` flag
- **API server binding**: Default binds to 0.0.0.0:6443 — restrict with `--bind-address` to private interface
- **Auto-mounted service account tokens**: Set `automountServiceAccountToken: false` on default ServiceAccounts
- **Anonymous auth enabled by default**: Override with `--kube-apiserver-arg="anonymous-auth=false"`
- **No audit logging by default**: Enable with `--kube-apiserver-arg="audit-log-path=..."` and audit policy file
- **Default CNI lacks encryption**: Flannel VXLAN is unencrypted — use WireGuard backend

**Performance Hotspots:**
- **SQLite performance ceiling**: Bottleneck at ~50-100 nodes or heavy API load — switch to embedded etcd or external DB
- **Single CoreDNS replica**: High DNS query rates cause lookup failures — scale CoreDNS or deploy NodeLocal DNSCache
- **ServiceLB overhead at scale**: Runs a pod per LoadBalancer service — significant overhead with 20+ services
- **Flannel VXLAN overhead**: ~50 bytes per packet + CPU for encapsulation — use `host-gw` for L2-adjacent nodes
- **containerd memory overhead**: Edge nodes with 1GB RAM can exhaust with 15-20 containers
- **etcd leader election storms**: Resource-constrained servers cause frequent elections — ensure SSD + stable network

**Testing Conventions:**
- **kube-bench**: CIS benchmark scanner with k3s-specific profile: `kube-bench run --benchmark k3s-cis-1.7`
- **Sonobuoy**: CNCF conformance test suite — k3s is a certified distribution
- **k3d for CI**: Ephemeral clusters in seconds: `k3d cluster create test --agents 2`
- **kubescape**: NSA/CISA hardening guidelines and MITRE ATT&CK framework checks
- **Popeye/Polaris**: Cluster linting for misconfigurations, missing limits, missing probes
- **Smoke tests**: `kubectl get nodes` (all Ready), service connectivity, DNS resolution, ingress TLS

**Common Integrations:**
- **FluxCD**: Commonly deployed on k3s for GitOps. Bootstrap via `flux bootstrap`. k3s HelmChart CRDs and Flux HelmRelease are independent mechanisms — do not mix for the same addon.
- **Kustomize**: Kustomize-rendered manifests can be placed in k3s auto-deploy directory (`/var/lib/rancher/k3s/server/manifests/`).
- **Rancher**: k3s is the default runtime for Rancher-managed downstream clusters. Rancher adds its own agent and monitoring stack.
- **Longhorn**: Rancher's distributed storage solution for k3s — significant resource overhead on edge devices.

**Context7 Library IDs:**
- `k3s-io/k3s` -- k3s lightweight Kubernetes
- `k3d-io/k3d` -- k3s in Docker for dev/CI
- `aquasecurity/kube-bench` -- CIS benchmark scanner
- `derailed/popeye` -- Kubernetes cluster linter

- [ ] **Step 2: Verify file structure matches convention**

Same verification as Task 1 Step 2. Target ~100 lines (80-120 acceptable).

- [ ] **Step 3: Commit**

```bash
git add references/platform-profiles/k3s.md
git commit -m "feat(code-analysis): add k3s core platform profile"
```

---

### Task 4: Create Kustomize Advanced Profile

**Files:**
- Create: `references/platform-profiles/kustomize-advanced.md`

- [ ] **Step 1: Create the file**

Write `references/platform-profiles/kustomize-advanced.md` with the advanced profile structure. Target ~150 lines. Must include these sections:

```markdown
# Kustomize Advanced Profile

## Loading Trigger

Load this profile when ANY of these conditions are met during Step 2 pre-scan:
- More than 3 `kustomization.yaml` files found in `overlays/` directories
- `components/` directory present alongside a `kustomization.yaml`
- `helmCharts:` field found in any `kustomization.yaml`

## Security Deep-Dive

Comprehensive security checklist with severity levels:

### Critical
- Plaintext secrets committed via `secretGenerator` literals — MUST use external secret managers
- Missing or overly permissive RBAC in overlays — bases with `*` verbs on `*` resources not patched down

### High
- Missing `securityContext` in base deployments not enforced by overlays (`runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`)
- `hostNetwork: true`, `hostPID: true`, `hostIPC: true` in base manifests
- No NetworkPolicy resources in bases — all pod-to-pod traffic allowed
- Helm chart inflation via `helmCharts` without version pinning (`version: "*"` or omitted)
- `commonLabels` overwriting `pod-security.kubernetes.io/enforce` label

### Medium
- ConfigMap values containing connection strings or embedded passwords
- Missing resource limits and requests (DoS via resource exhaustion)
- `vars`/`replacements` resolving sensitive values into non-secret resources
- Overly broad CRD `openAPIV3Schema` or missing validation

## Generator/Transformer Pitfalls

- **`patchesStrategicMerge` with full resource copies**: Masks what differs between environments; makes base meaningless. Rule: patches SHOULD be <30 lines each.
- **`sortOptions` not configured**: Default resource ordering may not match dependencies — CRD applied after CR causes intermittent failures. Use `sortOptions` to control ordering.
- **`generatorOptions` side effects**: `disableNameSuffixHash: true` prevents rolling updates; `labels` added via generatorOptions may conflict with selector-based resources.
- **Deprecated fields still in use**: `bases:` (use `resources:`), `patchesStrategicMerge:` (use `patches:`), `patchesJson6902:` (use `patches:` with target), `vars:` (use `replacements:`).

## Operational Concerns

- **HPA conflicts with `replicas`**: When an HPA targets a Deployment, the Kustomize overlay MUST NOT set `replicas` — the autoscaler and GitOps controller will fight.
- **Missing PodDisruptionBudgets**: Production overlays SHOULD include PDBs to prevent simultaneous termination during node drains.
- **Hash-suffixed resource accumulation**: Without pruning (`kubectl apply --prune` or GitOps controller prune), old ConfigMaps/Secrets accumulate indefinitely.
- **Remote bases reliability**: Remote Git references cause network-dependent builds. Vendor locally for CI reliability.
- **Overlay output size**: Complex builds producing >1MB YAML hit `kubectl apply` client-side limits.
- **Unused overlays/bases**: Orphaned directories create confusion and risk accidental deployment.

## Policy Validation Guide

### OPA/Conftest
kustomize build overlays/prod | conftest test -p policy/ -

Example Rego policies:
- `deny_latest_tag`: Reject any container image using `:latest` tag
- `require_resource_limits`: All containers MUST have `resources.limits.cpu` and `resources.limits.memory`
- `require_labels`: All resources MUST have `app.kubernetes.io/name` and `app.kubernetes.io/version` labels
- `deny_privileged`: No containers with `securityContext.privileged: true`

### Kyverno CLI
kyverno apply policies/ --resource <rendered-manifest>

### Trivy Config Scan
kustomize build overlays/prod | trivy config --input -

### Pluto (API deprecation)
kustomize build overlays/prod | pluto detect -
```

- [ ] **Step 2: Verify line count and section completeness**

Read back the file and verify:
- All 5 sections present (Loading Trigger, Security Deep-Dive, Generator/Transformer Pitfalls, Operational Concerns, Policy Validation Guide)
- Severity levels included in Security Deep-Dive
- Line count ~150 (120-180 acceptable)

- [ ] **Step 3: Commit**

```bash
git add references/platform-profiles/kustomize-advanced.md
git commit -m "feat(code-analysis): add kustomize advanced platform profile"
```

---

### Task 5: Create FluxCD Advanced Profile

**Files:**
- Create: `references/platform-profiles/fluxcd-advanced.md`

- [ ] **Step 1: Create the file**

Write `references/platform-profiles/fluxcd-advanced.md` with the advanced profile structure. Target ~180 lines. Must include these sections:

```markdown
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
```

- [ ] **Step 2: Verify section completeness and line count**

Read back the file and verify:
- All 6 sections present (Loading Trigger, Security Deep-Dive, Per-CRD Misconfiguration Tables, Multi-Tenancy Lockdown, Reconciliation Tuning, Policy Validation Guide)
- All 6 CRD categories covered in tables
- Line count ~180 (150-210 acceptable)

- [ ] **Step 3: Commit**

```bash
git add references/platform-profiles/fluxcd-advanced.md
git commit -m "feat(code-analysis): add fluxcd advanced platform profile"
```

---

### Task 6: Create k3s Advanced Profile

**Files:**
- Create: `references/platform-profiles/k3s-advanced.md`

- [ ] **Step 1: Create the file**

Write `references/platform-profiles/k3s-advanced.md` with the advanced profile structure. Target ~160 lines. Must include these sections:

```markdown
# k3s Advanced Profile

## Loading Trigger

Load this profile when ANY of these conditions are met during Step 2 pre-scan:
- `HelmChartConfig` CRDs found in YAML files
- `k3d-config.yaml` or `.k3d/` directory present
- `--cluster-init` or `cluster-init: true` found (embedded etcd HA markers)
- k3s config files referenced in IaC (Ansible playbooks, Terraform, cloud-init)

## Security Deep-Dive

### Critical
- kubeconfig (`k3s.yaml`) with permissions wider than 0600 — full cluster-admin credentials exposed
- Node-token accessible to non-root users — allows rogue node joins
- API server bound to 0.0.0.0 without firewall — exposed to all networks
- External datastore credentials in CLI arguments — visible in process listings

### High
- Secrets not encrypted at rest (`--secrets-encryption` not enabled)
- Anonymous auth enabled (default) — `--kube-apiserver-arg="anonymous-auth=false"` not set
- No audit logging — `--kube-apiserver-arg="audit-log-path=..."` not configured
- Kubelet read-only port open — `--kubelet-arg="read-only-port=0"` not set
- Private registry with `tls.insecure_skip_verify: true` in registries.yaml — MITM risk
- No PSA labels on namespaces — pods can run as root, privileged, with hostPath
- Auto-deploy manifests directory writable by non-root

### Medium
- Default Traefik without auth/TLS middleware
- Flannel VXLAN without encryption (use WireGuard backend)
- Kubelet anonymous auth not disabled
- No container runtime sandboxing (gVisor/Kata) for untrusted workloads
- `--protect-kernel-defaults` not set on kubelet

## CIS Benchmark Table

Based on CIS k3s Benchmark v1.7:

### Control Plane (Server)
| Item | Flag / Setting | Severity | k3s Default | Recommendation |
|------|---------------|----------|-------------|----------------|
| API anonymous auth | `--kube-apiserver-arg="anonymous-auth=false"` | HIGH | true | Disable |
| API audit logging | `--kube-apiserver-arg="audit-log-path=/var/log/k3s-audit.log"` | HIGH | disabled | Enable with audit policy |
| Secrets encryption | `--secrets-encryption` | HIGH | disabled | Enable |
| API profiling | `--kube-apiserver-arg="profiling=false"` | MEDIUM | true | Disable |
| API insecure port | N/A | CRITICAL | 0 (good) | Already secure |
| etcd data dir permissions | `/var/lib/rancher/k3s/server/db/etcd/` | HIGH | 0700 | Verify |
| etcd peer TLS | Auto-configured | CRITICAL | enabled (good) | Verify certs exist |
| Scheduler profiling | `--kube-scheduler-arg="profiling=false"` | LOW | true | Disable |
| Controller manager profiling | `--kube-controller-manager-arg="profiling=false"` | LOW | true | Disable |

### Worker Node (Agent)
| Item | Flag / Setting | Severity | Recommendation |
|------|---------------|----------|----------------|
| Kubelet anonymous auth | `--kubelet-arg="anonymous-auth=false"` | HIGH | Disable |
| Kubelet read-only port | `--kubelet-arg="read-only-port=0"` | HIGH | Disable |
| Certificate rotation | Auto-enabled | INFO | Verify |
| k3s.yaml permissions | `chmod 0600 /etc/rancher/k3s/k3s.yaml` | CRITICAL | Enforce |
| Node-token permissions | `chmod 0600` | CRITICAL | Enforce |
| Kernel params | `net.bridge.bridge-nf-call-iptables=1`, `net.ipv4.ip_forward=1` | MEDIUM | Set via sysctl |

## Port Firewall Matrix

| Port | Protocol | Purpose | Restrict Access To |
|------|----------|---------|-------------------|
| 6443 | TCP | API server | Admins and agent nodes only |
| 9345 | TCP | k3s supervisor API (node join) | Server and agent nodes only |
| 8472 | UDP | Flannel VXLAN | Cluster nodes only |
| 51820 | UDP | Flannel WireGuard | Cluster nodes only |
| 10250 | TCP | Kubelet API | Control plane nodes only |
| 2379-2380 | TCP | etcd (HA mode only) | Server nodes only |

## HA Configuration

- **Server count**: MUST be odd (3, 5, 7) for embedded etcd quorum. Two servers is worse than one (split-brain with no quorum).
- **Load balancer**: Agents MUST connect through a load balancer or VIP — pointing at a single server IP defeats HA.
- **etcd disk**: Server nodes MUST have SSD storage — spinning disk causes leader election storms.
- **Network stability**: Unstable networking between servers causes frequent etcd leader elections and API server instability.
- **Backup strategy**: `k3s etcd-snapshot save` for embedded etcd; file copy for SQLite (`/var/lib/rancher/k3s/server/db/`). Automate with `k3s etcd-snapshot --schedule-cron`.

## Runtime Hardening

- **containerd config**: Validate `/var/lib/rancher/k3s/agent/etc/containerd/config.toml` — no insecure registries in production
- **registries.yaml**: MUST NOT have `tls.insecure_skip_verify: true` in production
- **RuntimeClass**: Deploy gVisor or Kata Containers RuntimeClass for untrusted workloads
- **Rootless mode**: `k3s server --rootless` reduces attack surface but has limitations (no Flannel VXLAN, limited storage drivers)
- **Image policy**: Deploy Kyverno/OPA/Gatekeeper for admission control — k3s has no built-in image policy webhook
- **Token rotation**: `k3s token rotate` periodically (available in recent versions)

## Policy Validation Guide

### kube-bench
kube-bench run --benchmark k3s-cis-1.7

### kubescape
kubescape scan framework nsa --exclude-namespaces kube-system

### Sonobuoy Conformance
sonobuoy run --mode=certified-conformance

### Popeye Cluster Lint
popeye --all-namespaces

### Smoke Test Checklist
1. `kubectl get nodes` — all nodes Ready
2. `kubectl get pods -A` — all pods Running/Completed
3. DNS resolution from test pod
4. Service-to-service connectivity
5. Ingress TLS termination
6. PVC create/write/delete/verify cycle
```

- [ ] **Step 2: Verify section completeness and line count**

Read back the file and verify:
- All 7 sections present (Loading Trigger, Security Deep-Dive, CIS Benchmark Table, Port Firewall Matrix, HA Configuration, Runtime Hardening, Policy Validation Guide)
- CIS table covers both server and agent items
- Port matrix covers all 6 port ranges
- Line count ~160 (140-190 acceptable)

- [ ] **Step 3: Commit**

```bash
git add references/platform-profiles/k3s-advanced.md
git commit -m "feat(code-analysis): add k3s advanced platform profile"
```

---

### Task 7: Update Code-Analyzer Agent

**Files:**
- Modify: `agents/code-analyzer/AGENT.md:40-55`

- [ ] **Step 1: Read current AGENT.md**

Read `agents/code-analyzer/AGENT.md` in full. Note the exact text of Step 1 (Detect Stack) and Step 2 (Load Resources).

- [ ] **Step 2: Add platform detection to Step 1**

After the existing manifest file detection list (line 48), add:

```markdown

Also detect platform tools:
- `kustomization.yaml` with `apiVersion: kustomize.config.k8s.io` or containing `resources:`/`bases:`/`patches:` (NOT `toolkit.fluxcd.io`) → kustomize
- Any YAML with `toolkit.fluxcd.io` apiVersion → fluxcd
- `helm.cattle.io` CRDs, `+k3s` version strings, `k3d-config.yaml` → k3s

Platform detection is additive to language/framework detection. Include detected platforms in the stack info:
`{ "languages": ["go"], "frameworks": ["react"], "platforms": ["kustomize", "fluxcd"] }`
```

- [ ] **Step 3: Add platform profile loading to Step 2**

After step 3 in the resource loading list (`framework-profiles/{framework}.md`), add:

```markdown
4. `${CLAUDE_PLUGIN_ROOT}/references/platform-profiles/{platform}.md` — for detected platform(s)
5. (Conditional) `${CLAUDE_PLUGIN_ROOT}/references/platform-profiles/{platform}-advanced.md` — see triggers below

Advanced profile pre-scan triggers (evaluate before scanning):
- kustomize-advanced: >3 overlay kustomization.yaml files, `components/` directory, or `helmCharts:` field
- fluxcd-advanced: >5 Flux CRDs, `spec.serviceAccountName` in Kustomizations, or `spec.decryption` present
- k3s-advanced: `HelmChartConfig` CRDs, `k3d-config.yaml`, or embedded etcd markers

Maximum 3 platform profiles loaded simultaneously. Advanced profiles loaded individually per trigger.

Do NOT load platform-profiles in plugin mode.
```

- [ ] **Step 4: Add PLATFORM_PROFILES to Step 3 context**

After `FRAMEWORK_PROFILE` in the Step 3 variable list, add:

```markdown
- `PLATFORM_PROFILES`: Loaded platform profile(s) (if applicable)
```

- [ ] **Step 5: Verify the edit is correct**

Read back `agents/code-analyzer/AGENT.md` and verify:
- Step 1 includes platform detection after language/framework detection
- Step 2 includes platform profile loading as items 4 and 5
- Step 3 includes `PLATFORM_PROFILES` in context
- Plugin mode section is unchanged (platform profiles NOT loaded in plugin mode)
- `platforms` array included in stack info JSON format
- No existing content was accidentally removed
- Dimension mapping is implicit: sub-skills naturally consume loaded platform profiles (no sub-skill changes needed). Verify by reading one sub-skill (e.g., `skills/scan-security/SKILL.md`) to confirm it references loaded profiles generically, not by specific category.

- [ ] **Step 6: Commit**

```bash
git add agents/code-analyzer/AGENT.md
git commit -m "feat(code-analysis): add platform detection and profile loading to code-analyzer agent"
```

---

### Task 8: Verify All Files and Final Commit

**Files:**
- Verify: all 6 new files in `references/platform-profiles/`
- Verify: `agents/code-analyzer/AGENT.md`

- [ ] **Step 1: Verify directory structure**

Run: `ls -la references/platform-profiles/`

Expected: 6 files:
```
kustomize.md
kustomize-advanced.md
fluxcd.md
fluxcd-advanced.md
k3s.md
k3s-advanced.md
```

- [ ] **Step 2: Verify file sizes are in range**

Run: `wc -l references/platform-profiles/*.md`

Expected ranges:
- kustomize.md: 80-120 lines
- kustomize-advanced.md: 120-180 lines
- fluxcd.md: 90-130 lines
- fluxcd-advanced.md: 150-210 lines
- k3s.md: 80-120 lines
- k3s-advanced.md: 140-190 lines

- [ ] **Step 3: Verify section structure consistency**

For each core profile, verify these 9 sections exist in order:
1. Detection Markers
2. Architecture Expectations
3. Common Patterns
4. Common Anti-Patterns
5. Security Hotspots
6. Performance Hotspots
7. Testing Conventions
8. Common Integrations
9. Context7 Library IDs

Run: `grep "^## " references/platform-profiles/kustomize.md references/platform-profiles/fluxcd.md references/platform-profiles/k3s.md`

- [ ] **Step 4: Verify no cross-references are broken**

Grep for any file path references in AGENT.md that point to platform-profiles:
Run: `grep "platform-profiles" agents/code-analyzer/AGENT.md`

Verify the paths match the actual file locations.

- [ ] **Step 5: Verify no unintended changes to other files**

Confirm that scan dimension skills, output schemas, and templates were NOT modified:

Run: `git diff HEAD~7 --name-only -- skills/ references/output-schemas.md references/analysis-dimensions.md templates/`

Expected: no output (no changes to these paths).

- [ ] **Step 6: Run git log to verify all commits**

Run: `git log --oneline -10`

Expected: 7 new commits (Tasks 1-7) plus any prior commits.
