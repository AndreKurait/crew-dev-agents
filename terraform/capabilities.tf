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
# ArgoCD Capability (requires IAM Identity Center)
# -----------------------------------------------------------------------------
resource "awscc_eks_capability" "argocd" {
  cluster_name              = aws_eks_cluster.this.name
  capability_name           = "argocd"
  type                      = "ARGOCD"
  role_arn                  = aws_iam_role.capability_argocd.arn
  delete_propagation_policy = "RETAIN"

  configuration = {
    argo_cd = {
      namespace = "argocd"
      aws_idc = {
        idc_instance_arn = var.idc_instance_arn
        idc_region       = var.aws_region
      }
    }
  }
}

# ArgoCD needs cluster admin to deploy resources to this cluster
resource "aws_eks_access_entry" "argocd" {
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = aws_iam_role.capability_argocd.arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "argocd_admin" {
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = aws_iam_role.capability_argocd.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }

  depends_on = [aws_eks_access_entry.argocd]
}
