# Network Policies

By default, every Pod in a Kubernetes cluster can reach every other Pod
on every port. NetworkPolicies let you deny that by default and allow only
explicit flows. They are implemented by the CNI plugin — Calico, Cilium,
Antrea, and Weave Net all support them; some older or simpler CNIs do not.

## A default-deny baseline

The first NetworkPolicy you should write in any namespace is a
default-deny that blocks all ingress (and ideally egress). Then you add
specific allow policies on top.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: prod
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```

An empty `podSelector` matches all Pods in the namespace. With no
`ingress` and no `egress` rules, all traffic is dropped.

## Allowing specific flows

Policies are additive — if any policy selects a Pod and any allow rule
in that policy matches a connection, the connection is allowed. The
selectors can match by Pod label, Namespace label, or IP block.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-to-api
  namespace: prod
spec:
  podSelector:
    matchLabels: { app: api }
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: { app: web }
      ports:
        - protocol: TCP
          port: 8080
```

## Egress and DNS

Egress policies are powerful but easy to misconfigure. The most common
mistake is forgetting to allow DNS (UDP 53 to kube-dns/CoreDNS), which
breaks every Service-name lookup. Always include a DNS allow rule
explicitly.

```yaml
egress:
  - to:
      - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } }
        podSelector:        { matchLabels: { k8s-app: kube-dns } }
    ports:
      - protocol: UDP
        port: 53
```

## Limitations

NetworkPolicies operate at L3/L4 — they cannot match HTTP paths, JWT
claims, or methods. For L7 filtering, use a service mesh (Istio,
Linkerd) or Cilium's CiliumNetworkPolicy with HTTP rules.

## Sources

- Kubernetes documentation, "Network Policies" — kubernetes.io/docs/concepts/services-networking/network-policies/
- Calico documentation, "Get started with Calico network policy" — docs.tigera.io
