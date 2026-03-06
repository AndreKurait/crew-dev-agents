locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.18"

  name = var.project_name
  cidr = var.vpc_cidr

  azs             = local.azs
  private_subnets = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 3, i)]
  public_subnets  = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 3, i + 3)]

  # IPv6 dual-stack
  enable_ipv6                                   = true
  public_subnet_assign_ipv6_address_on_creation  = true
  private_subnet_assign_ipv6_address_on_creation = true
  public_subnet_ipv6_prefixes                    = [0, 1, 2]
  private_subnet_ipv6_prefixes                   = [3, 4, 5]

  # NAT for IPv4 egress, EIGW for IPv6 egress
  enable_nat_gateway     = true
  single_nat_gateway     = true # single for dev, one-per-az for prod
  create_egress_only_igw = true

  enable_dns_hostnames = true
  enable_dns_support   = true

  # Subnet tags for EKS Auto Mode
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    "karpenter.sh/discovery"          = var.cluster_name
    "kubernetes.io/role/cni"          = "1"
  }

  tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}
