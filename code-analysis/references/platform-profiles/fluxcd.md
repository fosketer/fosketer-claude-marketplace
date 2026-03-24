# FluxCD Platform Profile

## Detection Markers

- `toolkit.fluxcd.io` apiVersion in any YAML — definitive identifier for a Flux-managed cluster
- API groups: `source.toolkit.fluxcd.io`, `kustomize.toolkit.fluxcd.io`, `helm.toolkit.fluxcd.io`, `notification.toolkit.fluxcd.io`, `image.toolkit.fluxcd.io`
- CRD kinds: `GitRepository`, `OCIRepository`, `HelmRepository`, `HelmChart`, `Bucket`, `Kustomization`, `HelmRelease`, `Alert`, `Provider`, `Receiver`, `ImageRepository`, `ImagePolicy`, `ImageUpdateAutomation`
- `flux-system/` directory containing `gotk-components.yaml` and `gotk-sync.yaml`
- `clusters/<name>/` directory structure (e.g. `clusters/staging/`, `clusters/production/`)
- `# {"$imagepolicy": "namespace:name"}` comment markers in manifests for image automation

## Architecture Expectations

Standard monorepo directory layout (single-branch, folder-per-environment):

```
clusters/
  staging/
    flux-system/
      gotk-components.yaml
      gotk-sync.yaml
      kustomization.yaml
    apps/
      kustomization.yaml
    infrastructure/
      kustomization.yaml
  production/
    flux-system/
    apps/
    infrastructure/
infrastructure/
  controllers/        # HelmRelease for cluster-level tooling
  configs/            # ConfigMaps, NetworkPolicies, etc.
apps/
  base/               # Shared app Kustomization/HelmRelease definitions
  staging/            # Overlay patches for staging
  production/         # Overlay patches for production
```

- Folder-per-environment in a single branch — NOT branch-per-environment (violates GitOps reconciliation model)
- Infrastructure SHOULD be separated from application definitions to enable independent rollout ordering
- Each team/tenant SHOULD have its own namespace and `ServiceAccount` with RBAC-scoped permissions

## Common Patterns

- **`sourceRef` linking**: Every `Kustomization` and `HelmRelease` references a `GitRepository` or `HelmRepository` source CRD
- **`dependsOn` ordering**: Explicit reconciliation ordering between resources to prevent race conditions
- **SOPS decryption**: `spec.decryption.provider: sops` with a `secretRef` pointing to the age/GPG key secret
- **`spec.prune: true`**: Garbage collection of removed resources — nearly universal in production configurations
- **`spec.healthChecks`**: Wait for Deployment/StatefulSet readiness before marking reconciliation complete
- **`spec.postBuild.substituteFrom`**: Variable injection from ConfigMaps/Secrets into Kustomize overlays
- **`spec.suspend`**: Pause reconciliation for individual resources without deleting them

## Common Anti-Patterns

- **Branch-per-environment**: Forking the repo per environment breaks unified history and requires manual merge coordination
- **Manual `kubectl apply`**: Out-of-band changes are overwritten on the next reconciliation interval — causes silent drift
- **Suspended resources forgotten in prod**: `spec.suspend: true` left enabled indefinitely masks drift and blocks critical updates
- **Monolithic Kustomization**: Single root `Kustomization` for the whole cluster hides ordering problems and slows reconciliation
- **`spec.prune: false`**: Orphaned resources accumulate silently, consuming cluster resources
- **Hardcoded secrets in `spec.values`**: HelmRelease values rendered into plaintext in git history — use `valuesFrom` with sealed-secrets or ESO
- **`latest` image tags**: Image automation cannot compute semver policy and controllers cannot detect real changes
- **Renaming resources with `spec.prune: true`**: Old resource is pruned and new one created simultaneously, causing a brief outage

## Security Hotspots

- **Missing `--no-cross-namespace-refs`**: Controllers allow `sourceRef` to reference sources in other namespaces, enabling privilege escalation across tenant boundaries
- **No `--default-service-account`**: Kustomize controller uses its own SA instead of a scoped tenant SA, granting excess cluster permissions
- **Plaintext secrets in Git**: Secrets checked in unencrypted; use SOPS, sealed-secrets, or external-secrets-operator
- **No `spec.verify` on `GitRepository`/`OCIRepository`**: Missing Cosign or GPG signature verification allows supply-chain tampering
- **`--no-remote-bases` not set**: Kustomize controller fetches arbitrary remote bases; disable in production to enforce hermetic builds
- **Missing NetworkPolicies in `flux-system`**: Controllers can reach the API server and arbitrary endpoints without restriction
- **`insecure-kubeconfig-exec` flag**: Allows credential helper execution inside controller pods — never enable in production

## Performance Hotspots

- **Aggressive reconciliation intervals**: `spec.interval: 1m` on every resource hammers the git host and API server — use 5–10m for stable resources
- **Missing `spec.timeout`**: Long-running Helm installs or kubectl waits can block the controller queue indefinitely
- **Low controller concurrency**: Default `--concurrent=4` becomes a bottleneck in large clusters with hundreds of Kustomizations
- **Unnecessary git ref overhead**: Fetching full branch history on each reconcile — use `spec.ref.tag` or commit SHA for immutable refs
- **Missing `spec.ignore`**: Controllers watch all files in a path; `.ignore` rules prevent unnecessary reconciliations triggered by non-manifest files
- **Controller resource exhaustion**: Default memory limits too low for clusters with >200 HelmRelease objects; tune controller Deployment resources

## Testing Conventions

- **`flux check`**: Pre-flight cluster check verifying all controllers are healthy and CRDs are installed at the correct version
- **`kubeconform` with Flux CRD schemas**: `kustomize build | kubeconform -strict -schema-location flux-crd-schemas/` validates all custom resources
- **`flux build kustomization`**: Dry-run rendering of a Kustomization against live cluster data without applying changes
- **`kind` cluster bootstrap**: Spin up a local `kind` cluster and run `flux bootstrap` to validate the full repository reconciles cleanly
- **Kyverno policies**: Enforce required `spec.prune`, `spec.sourceRef`, and namespace isolation rules as cluster admission policies
- **CUE/conftest validation**: Schema enforcement on Flux CRDs before push to catch spec mistakes early in the CI pipeline

## Common Integrations

- **Kustomize**: Flux `Kustomization` CRD (`kustomize.toolkit.fluxcd.io`) reconciles Kustomize overlays server-side; `spec.path` points to the overlay directory. Slight behavior differences from the Kustomize CLI — notably `spec.postBuild.substituteFrom` is Flux-only.
- **k3s**: Flux is commonly bootstrapped on k3s clusters; the bootstrap command needs a valid `kubeconfig` and `kubectl` context. `HelmChart` (source controller CRD) and `HelmRelease` (helm controller CRD) are independent — do not confuse them.
- **SOPS / sealed-secrets**: `spec.decryption` integrates natively with SOPS using age or GPG keys stored as a Kubernetes Secret in `flux-system`.
- **Image automation**: `ImageRepository` scans a registry, `ImagePolicy` selects the latest matching tag, and `ImageUpdateAutomation` commits the updated image reference back to Git automatically.

## Context7 Library IDs

- `fluxcd/flux2` -- Main Flux2 CLI and documentation
- `fluxcd/kustomize-controller` -- Kustomize reconciliation controller
- `fluxcd/helm-controller` -- HelmRelease reconciliation controller
- `fluxcd/source-controller` -- GitRepository, HelmRepository, OCIRepository sources
