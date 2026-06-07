# Readiness vs Liveness Probes

Kubernetes has three probes: `readinessProbe`, `livenessProbe`, and
`startupProbe`. They look almost identical in YAML but they answer
different questions, and confusing them is one of the most common
production-grade outages I see.

## What each probe does

A **readiness probe** answers: "should this Pod receive traffic right now?"
A failing readinessProbe removes the Pod from the Service's endpoints. The
Pod is not killed; it is simply taken out of rotation until it recovers.
Use it for transient unreadiness — warming caches, waiting for a leader
election, draining at shutdown.

A **liveness probe** answers: "is this Pod healthy enough to keep running,
or should it be killed and restarted?" A failing livenessProbe causes the
kubelet to restart the container. Use it only for unrecoverable conditions
— deadlock, in-process fatal state — where a fresh start is the only fix.

A **startup probe** answers: "has the application finished its initial
startup yet?" While it is failing, the liveness probe is suspended. Use it
for slow-booting apps so a long startup does not get falsely interpreted
as a liveness failure and restart-loop.

## A common anti-pattern

Pointing the liveness probe at the same `/health` endpoint as the readiness
probe is a frequent cause of restart storms. Imagine the app cannot reach
a downstream dependency for thirty seconds. Both probes start failing.
Readiness correctly removes the Pod from rotation. But liveness also fails,
so the kubelet kills the Pod, taking down a healthy process for a problem
it could not have fixed by restarting.

## A safer default

```yaml
readinessProbe:
  httpGet: { path: /ready, port: http }
  periodSeconds: 5
  failureThreshold: 3
livenessProbe:
  httpGet: { path: /live, port: http }
  periodSeconds: 30
  failureThreshold: 5
  initialDelaySeconds: 60
```

Two distinct endpoints. `/ready` checks dependencies; `/live` only checks
in-process state ("am I deadlocked?"). Liveness has a generous threshold
and a long initial delay so transient blips do not trigger restarts.

## Sources

- Kubernetes documentation, "Configure Liveness, Readiness and Startup Probes" — kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
