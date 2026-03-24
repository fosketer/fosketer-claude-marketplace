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
```
kube-bench run --benchmark k3s-cis-1.7
```

### kubescape
```
kubescape scan framework nsa --exclude-namespaces kube-system
```

### Sonobuoy Conformance
```
sonobuoy run --mode=certified-conformance
```

### Popeye Cluster Lint
```
popeye --all-namespaces
```

### Smoke Test Checklist
1. `kubectl get nodes` — all nodes Ready
2. `kubectl get pods -A` — all pods Running/Completed
3. DNS resolution from test pod
4. Service-to-service connectivity
5. Ingress TLS termination
6. PVC create/write/delete/verify cycle
