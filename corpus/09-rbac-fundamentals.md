# RBAC Fundamentals

Role-Based Access Control (RBAC) governs who can do what in a Kubernetes
cluster. The model has four objects: `Role`, `ClusterRole`, `RoleBinding`,
`ClusterRoleBinding`. Roles describe *what* actions are allowed; bindings
attach those roles to *subjects* (users, groups, ServiceAccounts).

## Namespaced vs cluster-scoped

A `Role` lives in a namespace and grants permissions only on resources in
that namespace. A `ClusterRole` lives at the cluster scope and can grant
permissions on cluster-wide resources (Nodes, PersistentVolumes,
ClusterRoleBindings themselves) or on namespaced resources across all
namespaces when used with a ClusterRoleBinding.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: prod
  name: pod-reader
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
```

## Subjects and bindings

Subjects come in three flavors: human users (authenticated via your
identity provider), groups (sets of users), and ServiceAccounts (Pod
identities). A binding wires one or more subjects to one role.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  namespace: prod
  name: developers-can-read-pods
subjects:
  - kind: Group
    name: developers
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

## Principle of least privilege

Start with `view` on a single namespace. Grant `edit` only when the role
demands it. Reserve `cluster-admin` for break-glass scenarios — never
hand it out as a default.

For workloads, give each Deployment its own ServiceAccount with only the
permissions that workload needs. The default ServiceAccount in a
namespace should remain unprivileged so a forgotten `serviceAccountName`
fails closed instead of silently inheriting cluster-wide rights.

## Auditing what an identity can do

```bash
kubectl auth can-i list pods --namespace=prod --as=alice@example.com
kubectl auth can-i --list --as=system:serviceaccount:prod:web
```

`auth can-i` is the simplest tool for confirming whether a subject has a
specific permission, and `--list` enumerates everything they can do. Use
it as a routine check after granting or revoking a role.

## Sources

- Kubernetes documentation, "Using RBAC Authorization" — kubernetes.io/docs/reference/access-authn-authz/rbac/
- Kubernetes documentation, "Authorization Overview" — kubernetes.io/docs/reference/access-authn-authz/authorization/
