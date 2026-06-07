# Node Pressure and Evictions

The kubelet watches its node's resources — memory, disk, inodes, PIDs —
and evicts Pods when thresholds are breached. Evictions are not the same
as OOM kills: an eviction is the kubelet *gracefully* terminating Pods to
relieve pressure before the kernel has to step in.

## How eviction picks victims

When a soft or hard threshold trips, the kubelet ranks Pods by:

1. Whether they are using more than their `requests`. Pods within their
   requests are protected.
2. Pod Priority (`priorityClassName`). Lower-priority Pods go first.
3. The amount by which they exceed their requests.

The result: a Pod with no requests set (BestEffort QoS) and any usage at
all is the easiest target. A Guaranteed Pod that has `requests == limits`
is the hardest. This is why correct requests are not just a scheduling
concern — they are also a survivability concern.

## Soft vs hard thresholds

```yaml
# kubelet config
evictionHard:
  memory.available: "100Mi"
  nodefs.available: "10%"
evictionSoft:
  memory.available: "300Mi"
  nodefs.available: "15%"
evictionSoftGracePeriod:
  memory.available: 30s
  nodefs.available: 1m
```

A **hard** threshold causes immediate eviction with no graceful shutdown.
A **soft** threshold waits out the grace period before evicting; if
pressure clears within the grace window, no eviction occurs. Soft
thresholds are kinder but can let a slowly-leaking node eat itself before
the hard threshold fires — set both.

## Disk pressure is sneaky

Memory eviction is well-known. Disk pressure is sneakier: it is triggered
by `nodefs` (the node filesystem holding /var/lib/kubelet) or `imagefs`
(the filesystem the container runtime uses). Filling either one causes
the kubelet to first garbage-collect dead containers and unused images,
then evict Pods. A noisy log producer or a cached model file can fill up
imagefs surprisingly fast.

## Handling evictions in workloads

Evicted Pods get an event you can see with `kubectl get events
--field-selector reason=Evicted`. They also leave behind a `Failed` Pod
in the Pod list with reason `Evicted` until garbage collection runs.

For workloads that want to leave gracefully, set `terminationGracePeriodSeconds`
to a value larger than your slowest cleanup, and make sure the app
handles SIGTERM by draining connections rather than exiting immediately.

## Sources

- Kubernetes documentation, "Node-pressure Eviction" — kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/
- Kubernetes documentation, "Pod Priority and Preemption" — kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/
