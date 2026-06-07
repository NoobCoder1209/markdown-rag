# ConfigMaps and Secrets

ConfigMaps and Secrets both store key-value data and are mounted into
Pods as environment variables or files. The difference: Secrets are
intended for sensitive data and are stored base64-encoded in etcd, with
optional encryption-at-rest.

## When to use which

Use a **ConfigMap** for non-sensitive configuration: feature flags, log
levels, hostnames, default timeouts, file templates.

Use a **Secret** for credentials and tokens: database passwords, TLS
private keys, OAuth client secrets, JWT signing keys.

Base64 encoding is *not* encryption — anyone who can `kubectl get secret`
can read the value. Treat Secrets as plaintext for access-control
purposes; use RBAC to limit who can read them, and configure etcd
encryption at rest in the API server config.

## Two ways to consume

**Environment variables** are convenient but have downsides. They are
captured at Pod start — updating the ConfigMap does not update the env in
running Pods, and they appear in `kubectl describe pod` output and in
core dumps.

```yaml
env:
  - name: LOG_LEVEL
    valueFrom:
      configMapKeyRef:
        name: app-config
        key: log_level
```

**Volume mounts** propagate updates. A ConfigMap or Secret mounted as a
file is refreshed by the kubelet (with up to a one-minute lag) when the
underlying object changes. Apps that watch their config files for
changes will pick up updates without a restart.

```yaml
volumeMounts:
  - name: config
    mountPath: /etc/app
volumes:
  - name: config
    configMap:
      name: app-config
```

## External secret managers

Storing production secrets in plain Kubernetes Secrets is workable but
not ideal. Better is to keep secrets in a managed system (HashiCorp Vault,
AWS Secrets Manager, GCP Secret Manager) and sync them into Kubernetes on
demand. The External Secrets Operator and Vault's Kubernetes auth method
are the two common patterns.

## Sources

- Kubernetes documentation, "ConfigMaps" — kubernetes.io/docs/concepts/configuration/configmap/
- Kubernetes documentation, "Secrets" — kubernetes.io/docs/concepts/configuration/secret/
- External Secrets Operator — external-secrets.io
