# Runbook

## Prerequisites

- AWS CLI v2
- Terraform >= 1.5
- kubectl
- `ada` CLI (for Isengard auth)
- `gh` CLI (for GitHub operations)
- Docker (for local crew image builds)

## Deploy Infrastructure

```bash
# 1. Authenticate
cd terraform
make auth

# 2. Configure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your account ID and admin ARN

# 3. Deploy
make init
make plan   # review
make apply  # ~15 min for EKS + capabilities

# 4. Configure kubectl
make kubeconfig
kubectl get nodes  # verify
```

## Set GitHub Token

```bash
aws secretsmanager put-secret-value \
  --secret-id crew-dev-agents/github-token \
  --secret-string '{"GITHUB_TOKEN":"ghp_your_token_here"}' \
  --region us-west-2
```

## Add a Target Repo

Create a new CrewAIStack instance:

```yaml
# k8s/instances/my-repo.yaml
apiVersion: kro.run/v1alpha1
kind: CrewAIStack
metadata:
  name: my-repo
  namespace: crewai
spec:
  name: my-repo
  repoUrl: https://github.com/org/repo
  schedule: "0 */6 * * *"
  crewImage: "<ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/crew-dev-agents/crew:latest"
```

Commit and push — ArgoCD syncs automatically.

## Build Crew Image Manually

```bash
cd crew
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com
docker build --platform linux/amd64 -t <ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/crew-dev-agents/crew:latest .
docker push <ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/crew-dev-agents/crew:latest
```

## Trigger Crew Manually

```bash
kubectl create job --from=cronjob/example-repo-crew manual-run -n crewai
kubectl logs -f job/manual-run -n crewai
```

## Check ArgoCD Status

```bash
aws eks list-capabilities --cluster-name crew-dev-agents --region us-west-2
# ArgoCD UI is not exposed by default with EKS Capability
# Check sync status via:
kubectl get applications -n argocd
```

## Check ACK Resources

```bash
kubectl get buckets.s3.services.k8s.aws -n crewai
kubectl get repositories.ecr.services.k8s.aws -n crewai
kubectl get secrets.secretsmanager.services.k8s.aws -n crewai
```

## View Crew Metrics

```bash
aws s3 ls s3://crew-dev-agents-artifacts/metrics/ --region us-west-2
aws s3 cp s3://crew-dev-agents-artifacts/metrics/<latest>.json - | jq .
```

## Troubleshooting

### Pods not scheduling
```bash
kubectl describe pod -n crewai <pod-name>
# Check: node pool constraints, resource requests, image pull errors
```

### Bedrock access denied
```bash
kubectl exec -it -n crewai <pod> -- aws sts get-caller-identity
# Should show the crewai-pod role. If not, check Pod Identity association.
```

### ACK resource stuck
```bash
kubectl describe bucket.s3 -n crewai crew-dev-agents-artifacts
# Check .status.conditions for error messages
```

## Destroy

```bash
# 1. Delete K8s resources first (ACK will clean up AWS resources)
kubectl delete crewaistack --all -n crewai
kubectl delete -f k8s/ack-resources/ -n crewai

# 2. Delete capabilities
aws eks delete-capability --cluster-name crew-dev-agents --capability-name ack --region us-west-2
aws eks delete-capability --cluster-name crew-dev-agents --capability-name kro --region us-west-2
aws eks delete-capability --cluster-name crew-dev-agents --capability-name argocd --region us-west-2

# 3. Destroy Terraform
cd terraform
make destroy
```
