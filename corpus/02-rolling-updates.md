# Rolling Updates and Rollbacks

A Deployment rolls out new versions of your application by gradually
replacing old Pods with new ones. The default strategy is `RollingUpdate`,
which respects two knobs: `maxSurge` (how many extra Pods can exist above
`replicas` during the rollout) and `maxUnavailable` (how many of the
desired replicas can be unhealthy at once).

## Tuning surge and unavailability

`maxSurge: 25%` and `maxUnavailable: 25%` are the defaults. They are fine
for most workloads but suboptimal for two extremes.

For workloads that are expensive to start (large container images, slow
warm-up, model loading), increase `maxSurge` and lower `maxUnavailable`.
You pay briefly for extra capacity but you never serve from a degraded pool.

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 50%
    maxUnavailable: 0
```

For workloads that share a singleton resource (database migrations, file
locks, leader election with a small quorum), you may need `maxSurge: 0`
and `maxUnavailable: 1` to avoid having two old + new Pods racing.

## Recreate strategy

Setting `strategy.type: Recreate` tears down all old Pods before creating
any new ones. This causes downtime equal to the time it takes a new Pod to
become Ready. Use it only when concurrent old + new versions cannot coexist
— typically schema-incompatible database migrations or filesystem locks.

## Watching a rollout

```bash
kubectl rollout status deployment/web --timeout=2m
kubectl rollout history deployment/web
kubectl rollout undo deployment/web --to-revision=4
```

`rollout status` blocks until the rollout finishes or the timeout expires,
exiting non-zero on failure — useful in CI gates. `rollout history` shows
the last ten ReplicaSets (the limit is set by `revisionHistoryLimit`).
`rollout undo` rolls back to the previous revision, or to a specific one.

## Common pitfalls

A rollout can stall silently when readiness probes fail on the new Pods.
The Deployment will not progress past `maxUnavailable` because the new
Pods never become Ready. Check `kubectl describe deployment` for events
and `kubectl logs --previous` on the failed new Pod.

## Sources

- Kubernetes documentation, "Deployments — Updating a Deployment" — kubernetes.io/docs/concepts/workloads/controllers/deployment/
- `kubectl rollout` reference — kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/
