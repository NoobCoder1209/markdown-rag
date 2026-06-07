# Ingress Basics

An Ingress is a layer-7 routing rule. Unlike a Service of type
LoadBalancer, which provisions one cloud LB per Service, an Ingress lets
you put many HTTP routes behind a single LB by examining host headers and
URL paths.

## Anatomy of an Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop
spec:
  ingressClassName: nginx
  rules:
    - host: shop.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service: { name: api, port: { number: 80 } }
          - path: /
            pathType: Prefix
            backend:
              service: { name: web, port: { number: 80 } }
  tls:
    - hosts: [shop.example.com]
      secretName: shop-tls
```

`ingressClassName` selects which controller will materialize the rule —
nginx, Traefik, HAProxy, or a cloud-managed ALB. Without an installed
controller, the Ingress object exists but nothing routes through it.

## Path types

`pathType: Exact` matches only the literal path. `pathType: Prefix` matches
the path and any sub-path. `ImplementationSpecific` defers to the
controller's interpretation and is mostly used for legacy regex matching.

For new code, use `Prefix` and let your application do its own internal
routing — controller-specific regex paths produce surprising portability
issues when you switch ingress controllers.

## TLS termination

`tls.secretName` references a Secret of type `kubernetes.io/tls`
containing `tls.crt` and `tls.key`. cert-manager automates the lifecycle
of these Secrets via Let's Encrypt or another ACME issuer. The Ingress
controller terminates TLS at the edge and forwards plain HTTP to the
backend Service.

## Gateway API: the modern alternative

Ingress is intentionally minimal. Beyond simple host/path routing, you
quickly hit annotations — controller-specific knobs that make manifests
non-portable. The Gateway API (`gateway.networking.k8s.io`) is the
official successor; it splits responsibilities into `GatewayClass`,
`Gateway`, and `HTTPRoute` resources, supporting weighted routing, header
matching, and traffic mirroring as first-class fields. New clusters
should adopt Gateway API for any non-trivial routing.

## Sources

- Kubernetes documentation, "Ingress" — kubernetes.io/docs/concepts/services-networking/ingress/
- Gateway API documentation — gateway-api.sigs.k8s.io
