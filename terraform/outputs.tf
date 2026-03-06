output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.this.endpoint
}

output "cluster_certificate_authority" {
  value     = aws_eks_cluster.this.certificate_authority[0].data
  sensitive = true
}

output "cluster_arn" {
  value = aws_eks_cluster.this.arn
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "private_subnet_ids" {
  value = module.vpc.private_subnets
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.this.name}"
}

output "ack_capability_role_arn" {
  value = aws_iam_role.capability_ack.arn
}

output "crewai_pod_role_arn" {
  value = aws_iam_role.crewai_pod.arn
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}
