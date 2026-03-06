# -----------------------------------------------------------------------------
# EKS Cluster Role
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "cluster_assume" {
  statement {
    actions = ["sts:AssumeRole", "sts:TagSession"]
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cluster" {
  name               = "${var.project_name}-cluster"
  assume_role_policy = data.aws_iam_policy_document.cluster_assume.json
}

resource "aws_iam_role_policy_attachments_exclusive" "cluster" {
  role_name = aws_iam_role.cluster.name
  policy_arns = [
    "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
    "arn:aws:iam::aws:policy/AmazonEKSComputePolicy",
    "arn:aws:iam::aws:policy/AmazonEKSBlockStoragePolicy",
    "arn:aws:iam::aws:policy/AmazonEKSLoadBalancingPolicy",
    "arn:aws:iam::aws:policy/AmazonEKSNetworkingPolicy",
    "arn:aws:iam::aws:policy/AmazonEKSServicePolicy",
    "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController",
  ]
}

# -----------------------------------------------------------------------------
# EKS Auto Mode Node Role
# -----------------------------------------------------------------------------
resource "aws_iam_role" "node" {
  name = "${var.project_name}-node"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = ["sts:AssumeRole"]
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "node_minimal" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodeMinimalPolicy"
}

resource "aws_iam_role_policy_attachment" "node_ecr" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly"
}

# -----------------------------------------------------------------------------
# EKS Capability Roles (ACK, KRO, ArgoCD)
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "capability_assume" {
  statement {
    actions = ["sts:AssumeRole", "sts:TagSession"]
    principals {
      type        = "Service"
      identifiers = ["capabilities.eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "capability_ack" {
  name               = "${var.project_name}-cap-ack"
  assume_role_policy = data.aws_iam_policy_document.capability_assume.json
}

resource "aws_iam_role_policy" "ack_permissions" {
  name = "ack-resource-permissions"
  role = aws_iam_role.capability_ack.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3"
        Effect = "Allow"
        Action = ["s3:*"]
        Resource = [
          "arn:aws:s3:::${var.project_name}-*",
          "arn:aws:s3:::${var.project_name}-*/*",
        ]
      },
      {
        Sid      = "S3List"
        Effect   = "Allow"
        Action   = ["s3:ListAllMyBuckets", "s3:GetBucketLocation"]
        Resource = "*"
      },
      {
        Sid      = "ECR"
        Effect   = "Allow"
        Action   = ["ecr:*"]
        Resource = "arn:aws:ecr:${var.aws_region}:${data.aws_caller_identity.current.account_id}:repository/${var.project_name}/*"
      },
      {
        Sid    = "ECRAuth"
        Effect = "Allow"
        Action = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid      = "SecretsManager"
        Effect   = "Allow"
        Action   = ["secretsmanager:*"]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/*"
      },
    ]
  })
}

resource "aws_iam_role" "capability_kro" {
  name               = "${var.project_name}-cap-kro"
  assume_role_policy = data.aws_iam_policy_document.capability_assume.json
}

resource "aws_iam_role" "capability_argocd" {
  name               = "${var.project_name}-cap-argocd"
  assume_role_policy = data.aws_iam_policy_document.capability_assume.json
}

# -----------------------------------------------------------------------------
# CrewAI Pod Identity Role (Bedrock + S3 + GitHub secret read)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "crewai_pod" {
  name = "${var.project_name}-crewai-pod"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
    }]
  })
}

resource "aws_iam_role_policy" "crewai_bedrock" {
  name = "bedrock-invoke"
  role = aws_iam_role.crewai_pod.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "BedrockInvoke"
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.*"
      },
      {
        Sid    = "S3Artifacts"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::${var.project_name}-*",
          "arn:aws:s3:::${var.project_name}-*/*",
        ]
      },
      {
        Sid      = "SecretsRead"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/*"
      },
    ]
  })
}

resource "aws_eks_pod_identity_association" "crewai" {
  cluster_name    = aws_eks_cluster.this.name
  namespace       = "crewai"
  service_account = "crewai-sa"
  role_arn        = aws_iam_role.crewai_pod.arn
}
