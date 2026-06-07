# Services and Endpoints

A Service is a stable virtual IP and DNS name for a set of Pods. Pods come
and go — their IPs change with every restart and every reschedule — but a
Service IP stays put. Clients connect to the Service; kube-proxy forwards
the connection to one of the Service's healthy backend Pods.

## How selectors map to endpoints

A Service has a `selector` that matches Pod labels. The endpoints
controller continuously watches Pods, picks the ones whose labels match
and whose readiness probes pass, and writes their IP:port pairs into an
EndpointSlice (or the legacy Endpoints object) bound to the Service.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: http
```

When a Pod becomes unready, its address is removed from the EndpointSlice
within seconds. When a new Pod becomes ready, it is added. This is the
plumbing that makes rolling updates non-disruptive at the network layer.

## ClusterIP vs NodePort vs LoadBalancer

`ClusterIP` (the default) gives the Service an in-cluster virtual IP only.
This is what you want for internal traffic between microservices.

`NodePort` exposes the Service on a high port on every node's external IP.
Useful for bare-metal clusters and quick development access; rarely the
right answer for production.

`LoadBalancer` provisions a cloud load balancer that fronts the Service.
On managed Kubernetes (GKE, EKS, AKS) this typically creates a real
network LB; on bare metal, MetalLB or similar fills the same role.

## Headless Services

A Service with `clusterIP: None` does not allocate a virtual IP. Instead,
DNS lookups for the Service name return the IPs of all backing Pods
directly. This is how StatefulSets give each Pod a stable DNS name —
clients do their own client-side load balancing or address Pods individually.

## Common pitfalls

If a Service has no matching endpoints, connections to it just hang or
get connection-refused. `kubectl get endpointslices -l kubernetes.io/service-name=web`
quickly shows whether any Pods are actually backing the Service. A common
cause is a typo'd selector, or all Pods failing readiness.

## Sources

- Kubernetes documentation, "Service" — kubernetes.io/docs/concepts/services-networking/service/
- Kubernetes documentation, "EndpointSlices" — kubernetes.io/docs/concepts/services-networking/endpoint-slices/
