# Troubleshooting CrashLoopBackOff

`CrashLoopBackOff` means the kubelet is repeatedly restarting a container
that keeps exiting. The "BackOff" part is exponential: 10s, 20s, 40s, ...
up to 5 minutes. The status is a symptom — your job is to find the cause.

## A quick triage path

```bash
kubectl get pod web-7d4 -o wide
kubectl describe pod web-7d4 | sed -n '/Containers:/,/Conditions:/p'
kubectl logs web-7d4 --previous
kubectl logs web-7d4 --previous -c <init-container-name>
```

`describe` shows you the *last* termination reason (`Error`, `OOMKilled`,
`Completed`) and exit code. `logs --previous` reads the prior container's
stdout/stderr — essential because the *current* container is freshly
started and has no useful output yet.

## Common causes by exit code

- **Exit 0**: the process exited cleanly. Almost always a misconfigured
  command — the entrypoint runs and returns immediately. Check `args` and
  whether the binary is meant to run in foreground.
- **Exit 1, 2, 127, 126**: application error or shell error. Logs will
  show why. 127 = command not found; 126 = command not executable.
- **Exit 137 (OOMKilled)**: kernel killed the container for exceeding
  memory limit. `kubectl describe` shows `Last State: Terminated, Reason:
  OOMKilled`. Increase the memory limit or fix the leak.
- **Exit 139**: SIGSEGV — segfault. Usually a native bug or wrong
  architecture image (arm64 image on amd64 nodes).
- **Exit 143 (SIGTERM)**: container was asked to stop and did. If this
  is the only restart reason, look at probe failures or eviction events.

## Probes are a frequent culprit

A failing readinessProbe alone never causes CrashLoopBackOff — the Pod
just stays NotReady. But a failing **livenessProbe** does. If the app is
slow to start and you do not have a `startupProbe` (or a generous
`initialDelaySeconds` on liveness), the kubelet will kill the container
before it ever becomes Ready, looping forever.

## Init container failures

If an `initContainer` exits non-zero, the main container never starts and
the Pod stays in `Init:Error` (which can also surface as CrashLoopBackOff
on the init container itself). Always check init logs explicitly with
`kubectl logs pod -c initcontainer-name`.

## Sources

- Kubernetes documentation, "Debug Pods" — kubernetes.io/docs/tasks/debug/debug-application/debug-pods/
- Kubernetes documentation, "Pod Lifecycle — Container States" — kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
