# -----------------------------------------------------------------------------
# ACK Capability
# -----------------------------------------------------------------------------
resource "awscc_eks_capability" "ack" {
  cluster_name              = aws_eks_cluster.this.name
  capability_name           = "ack"
  type                      = "ACK"
  role_arn                  = aws_iam_role.capability_ack.arn
  delete_propagation_policy = "RETAIN"
}

# Grant ACK capability access to read K8s secrets
resource "aws_eks_access_entry" "ack" {
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = aws_iam_role.capability_ack.arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "ack_secret_reader" {
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = aws_iam_role.capability_ack.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSSecretReaderPolicy"

  access_scope {
    type = "cluster"
  }

  depends_on = [aws_eks_access_entry.ack]
}

# -----------------------------------------------------------------------------
# KRO Capability
# -----------------------------------------------------------------------------
resource "awscc_eks_capability" "kro" {
  cluster_name              = aws_eks_cluster.this.name
  capability_name           = "kro"
  type                      = "KRO"
  role_arn                  = aws_iam_role.capability_kro.arn
  delete_propagation_policy = "RETAIN"
}

# -----------------------------------------------------------------------------
# ArgoCD Capability — created via CLI (requires IDC config not available here)
# Run: aws eks create-capability --cluster-name crew-dev-agents \
#        --capability-name argocd --type ARGOCD \
#        --role-arn <argocd_role_arn> \
#        --configuration '{"argoCdConfiguration":{"namespace":"argocd"}}' \
#        --region us-west-2
# -----------------------------------------------------------------------------
# ArgoCD capability requires IAM Identity Center integration.
# If you don't have IDC, self-manage ArgoCD via Helm instead:
#   helm repo add argo https://argoproj.github.io/argo-helm
#   helm install argocd argo/argo-cd -n argocd --create-namespace
