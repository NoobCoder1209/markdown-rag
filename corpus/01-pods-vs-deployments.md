# Pods vs Deployments

A Pod is the smallest deployable unit in Kubernetes — one or more containers
sharing a network namespace and storage volumes. You almost never create
Pods directly in production. Instead, you create a controller that creates
Pods for you, and the controller is responsible for keeping them running.

## When to use a Deployment

A Deployment is the default controller for stateless workloads. It manages
a ReplicaSet, which in turn manages the Pods. The Deployment controller
gives you declarative rolling updates, rollback to a previous revision, and
automatic replacement of failed Pods.

Use a Deployment when:

- the workload is stateless (web server, API, worker queue consumer)
- any Pod can serve any request — no per-Pod identity required
- you want rolling updates with surge and unavailability controls

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels: { app: web }
  template:
    metadata:
      labels: { app: web }
    spec:
      containers:
        - name: web
          image: ghcr.io/example/web:1.4.2
```

## When NOT to use a Deployment

A StatefulSet is the right choice when Pods need stable network identities
and persistent volumes that follow them across restarts — databases, queues
that maintain ordered partitions, distributed caches with sticky sharding.
A DaemonSet is the right choice when one Pod must run on every node — log
shippers, node-local proxies, CNI helpers. A Job or CronJob is the right
choice for finite, run-to-completion work.

## Why naked Pods are a smell

A bare Pod has no controller behind it. If the node dies, the Pod is gone
forever. There is no rolling update, no replica count, no self-healing.
Naked Pods are useful for one-off debugging — `kubectl run -it --rm` to
poke at a service from inside the cluster — but they should never appear
in committed manifests.

## Sources

- Kubernetes documentation, "Pods" — kubernetes.io/docs/concepts/workloads/pods/
- Kubernetes documentation, "Deployments" — kubernetes.io/docs/concepts/workloads/controllers/deployment/
