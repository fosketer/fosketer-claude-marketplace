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
```
kustomize build overlays/prod | conftest test -p policy/ -
```

Example Rego policies:
- `deny_latest_tag`: Reject any container image using `:latest` tag
- `require_resource_limits`: All containers MUST have `resources.limits.cpu` and `resources.limits.memory`
- `require_labels`: All resources MUST have `app.kubernetes.io/name` and `app.kubernetes.io/version` labels
- `deny_privileged`: No containers with `securityContext.privileged: true`

### Kyverno CLI
```
kyverno apply policies/ --resource <rendered-manifest>
```

### Trivy Config Scan
```
kustomize build overlays/prod | trivy config --input -
```

### Pluto (API deprecation)
```
kustomize build overlays/prod | pluto detect -
```
