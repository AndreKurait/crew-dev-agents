# crew-dev-agents

Proof of concept for proposing GitHub repository changes with CrewAI and Amazon Bedrock.

**Status: experimental.** Local tests exercise mocked GitHub operations; they do
not establish reliable code generation, measured self-improvement, or a
production-ready EKS deployment.

## What This Is

The container entrypoint (`crew/src/main.py`) asks an LLM for one change,
validates the file plan, writes a feature branch, and opens a **draft pull request**.
It does not merge changes or close issues. A maintainer must review the complete
diff and CI results. A failed write can leave a partial feature branch; inspect it
before retrying.

`crew/src/crew.py` and `crew/src/flows/self_eval_flow.py` are a separate multi-agent
experiment. The flow's score uses output-text heuristics; it is not a measurement
of CI pass rate or code quality. Configured agents no longer receive merge/close
tools, but they can still create issues, labels, branches, and draft PRs.

## Proposed deployment architecture

- **EKS Auto Mode** — Kubernetes cluster with IPv6, Bottlerocket nodes, zero node management
- **EKS Capabilities** — AWS-managed ACK, KRO, ArgoCD (run off-cluster)
- **ACK** — S3, ECR, Secrets Manager resources managed as K8s custom resources
- **KRO** — `CrewAIStack` ResourceGraphDefinition composes all resources per target repo
- **ArgoCD** — GitOps sync from this repo
- **Amazon Bedrock** — model selected with `BEDROCK_MODEL`; availability and access must be checked
- **CrewAI** — Open-source Python framework for multi-agent orchestration

## Local checks

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e "./crew[test]" build
python -m pytest crew/tests -q
python -m build crew
```

Tests block network connections and replace GitHub clients with mocks. They need
no GitHub token, AWS credentials, or model access. Do not use the agent entrypoint
as a smoke test: it calls Bedrock and writes to the configured repository.

For an intentional experiment, configure `REPO_URL`, `BEDROCK_MODEL`, and a
repository-scoped `GITHUB_TOKEN` (or the configured Secrets Manager secret).
Use a disposable repository with branch protection and review the IAM and
Kubernetes manifests first. Infrastructure deployment, model compatibility, and
live GitHub behavior require separate validation; the checked-in manifests are
not a turnkey deployment guarantee.

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

## Review boundary

Repository contents and model output are untrusted input. Plan validation checks
branch names, relative paths, duplicate files, and field types; it does not prove
generated code is correct or safe. Draft PRs are a review boundary, not a sandbox.
Keep token permissions narrow and require independent CI and human review before
merging. The prototype does not provide automatic rollback or per-file approval.

## License

Apache-2.0
