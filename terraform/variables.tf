variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "crew-dev-agents"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "crew-dev-agents"
}

variable "cluster_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.32"
}

variable "vpc_cidr" {
  description = "IPv4 CIDR for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "admin_principal_arn" {
  description = "IAM principal ARN for EKS admin access (user or role)"
  type        = string
}

variable "github_repo_url" {
  description = "Git repo URL for ArgoCD (HTTPS)"
  type        = string
  default     = "https://github.com/AndreKurait/crew-dev-agents.git"
}

variable "github_repo_path" {
  description = "Path within the Git repo for ArgoCD to sync"
  type        = string
  default     = "k8s"
}
