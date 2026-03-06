# crew-dev-agents

Self-improving CrewAI developer agent team deployed on EKS Auto Mode with Amazon Bedrock.

## What This Is

An open-source CrewAI crew that operates as automated maintainers on any GitHub repo. The agents triage issues, review PRs, write code, and evolve their own configuration based on performance metrics.

## Architecture

- **EKS Auto Mode** — Kubernetes cluster with IPv6, Bottlerocket nodes, zero node management
- **EKS Capabilities** — AWS-managed ACK, KRO, ArgoCD (run off-cluster)
- **ACK** — S3, ECR, Secrets Manager resources managed as K8s custom resources
- **KRO** — `CrewAIStack` ResourceGraphDefinition composes all resources per target repo
- **ArgoCD** — GitOps sync from this repo
- **Amazon Bedrock** — Claude Opus 4.6 as the LLM for all agents
- **CrewAI** — Open-source Python framework for multi-agent orchestration

## Quick Start

```bash
# 1. Get AWS credentials
ada credentials update --once --account <ACCOUNT_ID> --role <ROLE_NAME> --provider <PROVIDER>

# 2. Deploy infrastructure
cd terraform
cp terraform.tfvars.example terraform.tfvars  # edit with your values
make init plan apply

# 3. ArgoCD syncs k8s/ manifests automatically

# 4. Point at a target repo
kubectl apply -f k8s/instances/example-repo.yaml
```

## Repo Structure

```
terraform/     — EKS Auto Mode cluster, VPC, IAM, Capabilities
k8s/           — ACK resources, KRO definitions, ArgoCD apps
crew/          — CrewAI Python project (agents, tools, flows)
docs/          — Plan, architecture, runbook
.github/       — CI/CD workflows
```

## Agents

| Agent | Role |
|-------|------|
| Triager | Monitors issues, labels, prioritizes, assigns |
| Reviewer | Reviews PRs for quality, security, correctness |
| Coder | Implements fixes and features, creates PRs |
| Evolver | Reviews crew performance, proposes config improvements |

## Self-Improvement

The crew runs a self-evaluation flow:
1. Execute main crew tasks (triage/review/code)
2. Evaluate output quality (CI pass rate, triage accuracy, review helpfulness)
3. If below threshold, Evolver agent proposes config changes
4. Changes submitted as PRs to this repo (not the target repo)
5. ArgoCD deploys approved changes automatically

## License

Apache-2.0
