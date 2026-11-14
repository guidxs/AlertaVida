variable "aws_region" {
  description = "AWS region where AlertaVida will be deployed."
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "ID of the existing VPC for the AlertaVida security group."
  type        = string
}

variable "subnet_id" {
  description = "ID of the existing public subnet for the EC2 instance."
  type        = string
}

variable "key_name" {
  description = "Name of the existing EC2 key pair."
  type        = string
}

variable "ssh_cidr" {
  description = "Single public IPv4 address allowed to connect over SSH, in /32 form."
  type        = string

  validation {
    condition = can(cidrnetmask(var.ssh_cidr)) && try(
      split("/", var.ssh_cidr)[1] == "32" && var.ssh_cidr != "0.0.0.0/0",
      false
    )
    error_message = "ssh_cidr must be one valid IPv4 address with a /32 mask."
  }
}
