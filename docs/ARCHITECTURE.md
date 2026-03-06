# Architecture

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Terraform (Bootstrap)                        │
│  VPC (dual-stack) → EKS Auto Mode → IAM → EKS Capabilities     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│              EKS Capabilities (AWS-Managed, Off-Cluster)         │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐              │
│  │   ACK    │    │   KRO    │    │   ArgoCD     │              │
│  │ S3, ECR  │    │ Resource │    │ GitOps sync  │              │
│  │ Secrets  │    │ Graphs   │    │ from Git     │              │
│  └────┬─────┘    └────┬─────┘    └──────┬───────┘              │
└───────┼──────────────┼──────────────────┼───────────────────────┘
        │              │                  │
┌───────▼──────────────▼──────────────────▼───────────────────────┐
│                    Kubernetes Cluster                             │
│                                                                  │
│  ACK CRs:              KRO:                ArgoCD:              │
│  - S3 Bucket           - CrewAIStack RGD   - Application        │
│  - ECR Repo            - Instances         - Auto-sync          │
│  - SM Secret                                                     │
│                                                                  │
│  CrewAI Workloads:                                              │
│  ┌─────────────────────────────────────────────┐                │
│  │ CronJob (per target repo)                    │                │
│  │  ┌─────────┐ ┌──────────┐ ┌──────┐ ┌─────┐ │                │
│  │  │ Triager │ │ Reviewer │ │Coder │ │Evol.│ │                │
│  │  └────┬────┘ └────┬─────┘ └──┬───┘ └──┬──┘ │                │
│  │       │           │          │         │     │                │
│  │       └───────────┴──────────┴─────────┘     │                │
│  │                    │                          │                │
│  │            Self-Eval Flow                     │                │
│  │         (generate → evaluate → evolve)        │                │
│  └─────────────────────────────────────────────┘                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  ┌──────────┐    ┌──────────────┐    ┌──────────────┐
  │ Bedrock  │    │ Target Repo  │    │ Platform Repo│
  │ Claude   │    │ (maintained) │    │ (self-evolve)│
  │ Opus 4.6 │    │              │    │              │
  └──────────┘    └──────────────┘    └──────────────┘
```

## Component Details

### Terraform Layer
- **VPC**: Dual-stack (IPv4 10.0.0.0/16 + auto-assigned IPv6 /56), 3 AZs, NAT GW + EIGW
- **EKS**: Auto Mode, K8s 1.32, IPv6 pods, Bottlerocket nodes, zonal shift enabled
- **IAM**: Cluster role (7 EKS policies), node role (minimal), 3 capability roles, pod identity role
- **Capabilities**: ACK (S3/ECR/IAM/SecretsManager controllers), KRO, ArgoCD via `awscc_eks_capability`

### EKS Auto Mode
- Karpenter-managed Bottlerocket nodes (C/M/R instance families, gen4+, AMD64)
- Default NodePools: `general-purpose` + `system`
- Max node lifetime: 21 days with automatic replacement
- VPC-CNI, CoreDNS, kube-proxy, EBS CSI, LB controller all managed off-cluster
- No `bootstrap_self_managed_addons` — everything managed by AWS

### ACK Resources
- **S3 Bucket**: Crew artifacts, metrics, eval results (versioned, encrypted)
- **ECR Repository**: Crew container images (mutable tags, lifecycle policy)
- **Secrets Manager**: GitHub PAT for repo access

### KRO CrewAIStack
ResourceGraphDefinition that composes per-target-repo:
- ConfigMap (repo URL, Bedrock config)
- ServiceAccount (with Pod Identity)
- CronJob (scheduled crew execution)

Schema inputs: `repoUrl`, `schedule`, `bedrockModel`, `crewImage`

### CrewAI Agents
| Agent | Tools | Purpose |
|-------|-------|---------|
| Triager | list_open_issues, add_labels, add_issue_comment | Issue triage |
| Reviewer | list_open_prs | PR review |
| Coder | (GitHub API via tools) | Bug fixes, feature PRs |
| Evolver | read_recent_metrics, store_metrics | Config evolution |

### Self-Evaluation Flow
1. `@start` → Run main crew (triage/review/code)
2. `@router` → Score output quality (heuristic + LLM-based)
3. If score ≥ threshold → `finalize` (store metrics)
4. If score < threshold AND retries left → `retry` (re-run with feedback)
5. If score < threshold AND no retries → `evolve` (Evolver proposes config changes as PR)

### Authentication
- **Bedrock**: Pod Identity (no API keys, automatic credential rotation)
- **GitHub**: PAT stored in Secrets Manager, read by tools at runtime
- **ECR**: Node role has `AmazonEC2ContainerRegistryPullOnly`
- **S3/Secrets**: Pod Identity role has scoped permissions
