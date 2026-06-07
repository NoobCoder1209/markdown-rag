# Horizontal Pod Autoscaler

The HorizontalPodAutoscaler (HPA) scales the replica count of a Deployment
or StatefulSet up and down based on observed metrics. The default metric
is per-Pod CPU utilization expressed as a percentage of the Pod's CPU
request.

## CPU-based autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 3
  maxReplicas: 30
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

The HPA controller polls the metrics-server every 15 seconds and adjusts
replicas to keep the *average* CPU utilization across all Pods near the
target. CPU `requests` must be set on the target Pods — without a request
there is no denominator for utilization, and the HPA refuses to act.

## Custom metrics

For request-driven workloads where CPU is a poor proxy for load, scale on
a real signal: requests-per-second, queue depth, or p95 latency. This
requires a custom or external metrics adapter (Prometheus Adapter, KEDA,
or the cloud provider's own metric source).

```yaml
metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: 50
```

## Stabilization windows

By default, the HPA scales up immediately and scales down after a 5-minute
stabilization window. The asymmetry is intentional — you almost always
want to absorb a spike fast and shed capacity slowly to avoid flapping.

You can tune both via `behavior.scaleUp` and `behavior.scaleDown` if your
traffic pattern needs a different shape, for example a longer scale-up
window during traffic that is bursty but short-lived.

## Common pitfalls

The HPA cannot scale below `minReplicas` or above `maxReplicas` — set
`maxReplicas` realistically high so you do not silently cap during an
incident. The metrics-server must be installed and healthy; without it,
the HPA reports `unable to fetch pod metrics` and does not act.

## Sources

- Kubernetes documentation, "Horizontal Pod Autoscaling" — kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
- KEDA project — keda.sh
