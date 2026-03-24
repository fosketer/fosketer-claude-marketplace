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

```
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
```

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
