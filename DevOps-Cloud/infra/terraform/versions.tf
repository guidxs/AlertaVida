terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Supply an external state path with:
  # terraform init -backend-config="path=<absolute-path-outside-repository>"
  backend "local" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "AlertaVida"
      ManagedBy = "Terraform"
    }
  }
}
