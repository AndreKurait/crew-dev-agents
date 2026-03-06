# Implementation Plan

## Overview

Deploy a self-improving CrewAI developer agent team on EKS Auto Mode with Amazon Bedrock (Claude Opus 4.6). The agents operate as open-source maintainers on any configurable GitHub repo.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| CrewAI variant | Open-source (pip) | No enterprise license needed, lighter weight |
| EKS mode | Auto Mode | Zero node management, Bottlerocket, managed Karpenter |
| IP family | IPv6 | Future-proof, avoids IP exhaustion at scale |
| AWS resource mgmt | ACK via EKS Capability | Managed off-cluster, K8s-native, no Helm installs |
| Resource composition | KRO | Compose ACK + K8s resources into CrewAIStack abstraction |
| GitOps | ArgoCD via EKS Capability | Managed off-cluster, syncs from this repo |
| LLM | Bedrock Claude Opus 4.6 | No API keys, Pod Identity auth, pay-per-use |
| Capabilities TF | awscc provider | Maps to CloudFormation AWS::EKS::Capability |
| Self-improvement | PR-based | Evolver agent creates PRs on this repo, human reviews |

## Open Variables

- `AWS_ACCOUNT_ID` — <ACCOUNT_ID>
- `AWS_REGION` — defaults to us-west-2
- `GITHUB_TOKEN` — stored in Secrets Manager after deploy

## Task Sequence

1. Scaffold repo structure
2. Terraform: VPC (dual-stack IPv6)
3. Terraform: EKS Auto Mode cluster
4. Terraform: IAM roles (cluster, node, capability, pod identity)
5. Terraform: EKS Capabilities (ACK, KRO, ArgoCD)
6. K8s: ACK resources (S3, ECR, Secrets Manager)
7. K8s: KRO ResourceGraphDefinition (CrewAIStack)
8. K8s: ArgoCD Application
9. CrewAI: Python project, agents, tools
10. CrewAI: Self-evaluation flow
11. GitHub Actions: Build and push to ECR
12. Documentation
