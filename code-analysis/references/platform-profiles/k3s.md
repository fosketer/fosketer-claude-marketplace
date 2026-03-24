# k3s Platform Profile

## Detection Markers

- `helm.cattle.io` CRDs (`HelmChart`, `HelmChartConfig`) in YAML files (definitive for k3s)
- `+k3s` version suffix in manifests or version strings (e.g., `v1.28.4+k3s1`)
- `k3d-config.yaml` or `.k3d/` directories (k3s-in-Docker for dev environments)
- `curl -sfL https://get.k3s.io` in install scripts, cloud-init, or user-data files
- Ansible roles referencing `xanmanning.k3s` or `k3s-io/k3s-ansible`
- Terraform `rancher/k3s` provider or `k3s_cluster` resources
- Note: system paths (`/etc/rancher/k3s/`, `/var/lib/rancher/k3s/`) are runtime markers for live audit only, not typically present in source repos

## Architecture Expectations

Standard configuration layout:

```
config.yaml                        # Server/agent config (preferred over CLI flags)
registries.yaml                    # Private registry mirrors and credentials
manifests/
  helmchart-traefik.yaml           # HelmChart CRD for addon deployment
  helmchartconfig-traefik.yaml     # HelmChartConfig for helm value overrides
```

- Configuration SHOULD use `config.yaml` instead of CLI flags (avoids secret leakage in process table)
- Server nodes SHOULD be tainted (`CriticalAddonsOnly=true:NoExecute`) to prevent user workloads
- Default components SHOULD be explicitly disabled if replaced (`--disable=traefik,servicelb`)

## Common Patterns

- **Config file over CLI flags**: `config.yaml` at `/etc/rancher/k3s/config.yaml` keeps flags auditable and out of `ps` output
- **HelmChart CRD for addons**: Manifests in the auto-deploy directory install Helm charts without a Helm binary on the host
- **HelmChartConfig for overrides**: Patch chart values without forking the HelmChart resource
- **WireGuard flannel backend**: `--flannel-backend=wireguard-native` for encrypted pod-to-pod traffic
- **PSA namespace labels**: Pod Security Admission labels on namespaces for enforce/audit/warn
- **Embedded etcd HA**: `--cluster-init` on first server activates etcd; additional servers join via `--server`
- **System Upgrade Controller**: In-cluster operator consuming `Plan` CRDs for automated, draining node upgrades

## Common Anti-Patterns

- **Default Traefik without hardening**: Ships with permissive defaults; no TLS redirection, no rate limiting
- **Flannel without NetworkPolicy enforcement**: Default VXLAN backend does not enforce NetworkPolicy — must install a policy engine
- **Single-server production**: No etcd HA; server failure causes total control-plane outage
- **local-path for stateful workloads**: Default provisioner gives no replication or snapshots; data lost on node failure
- **Loosened kubeconfig permissions**: World-readable `/etc/rancher/k3s/k3s.yaml` exposes cluster-admin credentials
- **Secrets via CLI flags**: Token and TLS values in `ExecStart` flags appear in `/proc` and system logs
- **k3d for production**: k3s-in-Docker container isolation is insufficient for production workloads
- **Mixing server and agent workloads**: Running user pods on server nodes risks resource starvation of control-plane components

## Security Hotspots

- **kubeconfig file permissions**: `/etc/rancher/k3s/k3s.yaml` must be `0600 root:root`; default may be world-readable depending on installer version
- **node-token protection**: `/var/lib/rancher/k3s/server/node-token` grants full cluster join access; restrict read permissions
- **Secrets encryption at rest**: Not enabled by default; requires `--secrets-encryption` flag and key rotation policy
- **API server binding**: Default `--bind-address=0.0.0.0` exposes API server on all interfaces; restrict to management network
- **Auto-mounted service account tokens**: Legacy behavior mounts tokens into every pod; disable with `automountServiceAccountToken: false`
- **Anonymous auth enabled**: `--anonymous-auth=false` should be explicitly set on the API server
- **No audit logging**: k3s does not configure audit policy by default; add `--kube-apiserver-arg=audit-log-path=...`
- **Default CNI lacks encryption**: Flannel VXLAN sends pod traffic in plaintext; use WireGuard backend or overlay Cilium

## Performance Hotspots

- **SQLite ceiling**: Default SQLite backend becomes a bottleneck above ~50 nodes or high write workloads; migrate to embedded etcd
- **Single CoreDNS replica**: Default single-replica CoreDNS is a DNS availability single point of failure; scale to 2+
- **ServiceLB overhead**: Built-in load balancer runs a DaemonSet pod on every node; replace with MetalLB for targeted allocation
- **Flannel VXLAN overhead**: Encapsulation adds latency and CPU cost on high-throughput workloads; evaluate host-gw or WireGuard
- **containerd memory**: k3s bundles containerd with no memory limits; constrain with cgroup configuration on memory-limited nodes
- **etcd leader election storms**: Rapid server restarts in embedded etcd clusters cause repeated elections; use proper drain procedures

## Testing Conventions

- **kube-bench k3s CIS profile**: `kube-bench --config-dir /etc/kube-bench/cfg --benchmark k3s-cis-1.7` for CIS compliance
- **Sonobuoy conformance**: Kubernetes conformance suite validates k3s API compatibility before upgrades
- **k3d for CI**: `k3d cluster create` spins up isolated k3s clusters in Docker for integration tests
- **kubescape**: Scans manifests and live clusters against NSA/CISA and MITRE ATT&CK frameworks
- **Popeye / Polaris**: Cluster linting for misconfigurations, missing limits, deprecated APIs
- **Smoke tests**: Verify HelmChart CRDs reconcile, CoreDNS resolves, and default StorageClass provisions after upgrade

## Common Integrations

- **FluxCD**: Commonly deployed on k3s; HelmChart CRDs (helm.cattle.io) and FluxCD HelmRelease (helm.toolkit.fluxcd.io) are independent — do not confuse them
- **Kustomize**: Rendered manifests placed in the auto-deploy directory (`/var/lib/rancher/k3s/server/manifests/`) are applied automatically
- **Rancher**: k3s is the default runtime for Rancher downstream clusters; Rancher manages k3s lifecycle and upgrade plans
- **Longhorn**: Distributed block storage designed for k3s; significant CPU/memory overhead, requires open-iscsi on nodes

## Context7 Library IDs

- `k3s-io/k3s` -- k3s lightweight Kubernetes distribution
- `k3d-io/k3d` -- k3s-in-Docker for local development and CI
- `aquasecurity/kube-bench` -- CIS Kubernetes benchmark runner
- `derailed/popeye` -- Live cluster linting and misconfiguration detection
