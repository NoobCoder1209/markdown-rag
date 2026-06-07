# Resource Requests and Limits

Every container should declare CPU and memory `requests` and `limits`.
Requests influence scheduling — the scheduler only places a Pod on a node
that has enough unallocated request to satisfy it. Limits are runtime
caps — the kernel enforces them on the running container.

## CPU requests and limits

CPU is a *compressible* resource: when a container exceeds its limit, the
kernel throttles it. The container does not die; it just runs slower.

A common mistake is setting CPU limits much lower than the request. This
causes silent throttling that can manifest as p99 latency spikes that no
metric explains until you look at `container_cpu_cfs_throttled_seconds`.

For most workloads, set a CPU `request` matching observed average usage,
and either omit the CPU `limit` or set it generously (2–4× the request).

```yaml
resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    memory: 512Mi
```

## Memory requests and limits

Memory is *incompressible*. A container that exceeds its memory limit is
OOM-killed by the kernel — the process is terminated with exit code 137,
and the kubelet records `OOMKilled` as the last termination reason.

Memory limits should reflect a worst-case bound, not an average. Set them
based on heap profiling under load plus headroom for non-heap memory
(stacks, mmap, native libraries, page cache reserved for the cgroup).

## Quality of Service classes

Kubernetes assigns each Pod a QoS class based on its requests and limits:

- **Guaranteed**: every container has equal requests and limits for both
  CPU and memory. Last to be evicted under node pressure.
- **Burstable**: requests are set but limits differ, or only one resource
  is constrained. Evicted if it exceeds requests under pressure.
- **BestEffort**: no requests or limits. First to be evicted.

Production workloads should be Guaranteed or Burstable. BestEffort is for
opportunistic, restartable tasks only.

## Sources

- Kubernetes documentation, "Resource Management for Pods and Containers" — kubernetes.io/docs/concepts/configuration/manage-resources-containers/
- Kubernetes documentation, "Pod Quality of Service Classes" — kubernetes.io/docs/concepts/workloads/pods/pod-qos/
