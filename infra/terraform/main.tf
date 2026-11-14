data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["137112412989"] # Amazon

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-kernel-*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

resource "aws_security_group" "alertavida" {
  name        = "alertavida-ec2"
  description = "Public web access and SSH restricted to the operator IP."
  vpc_id      = var.vpc_id

  tags = {
    Name = "alertavida-ec2"
  }
}

resource "aws_vpc_security_group_ingress_rule" "ssh_ipv4" {
  security_group_id = aws_security_group.alertavida.id
  description       = "SSH from the configured operator IPv4 address only."
  cidr_ipv4         = var.ssh_cidr
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "http_ipv4" {
  security_group_id = aws_security_group.alertavida.id
  description       = "Public HTTP."
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "https_ipv4" {
  security_group_id = aws_security_group.alertavida.id
  description       = "Public HTTPS."
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "all_ipv4" {
  security_group_id = aws_security_group.alertavida.id
  description       = "Outbound access for package installation and external services."
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_instance" "alertavida" {
  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = "t3.small"
  subnet_id                   = var.subnet_id
  key_name                    = var.key_name
  vpc_security_group_ids      = [aws_security_group.alertavida.id]
  associate_public_ip_address = true

  user_data = <<-USER_DATA
    #!/bin/bash
    set -euxo pipefail
    dnf install -y docker
    systemctl enable --now docker
  USER_DATA

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    encrypted             = true
    volume_type           = "gp3"
    volume_size           = 8
    delete_on_termination = true
  }

  volume_tags = {
    Project   = "AlertaVida"
    ManagedBy = "Terraform"
    Name      = "alertavida-root"
  }

  tags = {
    Name = "alertavida-app"
  }
}
