output "instance_id" {
  description = "ID of the AlertaVida EC2 instance."
  value       = aws_instance.alertavida.id
}

output "public_ip" {
  description = "Public IPv4 address assigned to the instance."
  value       = aws_instance.alertavida.public_ip
}

output "public_dns" {
  description = "Public DNS name assigned to the instance."
  value       = aws_instance.alertavida.public_dns
}

output "security_group_id" {
  description = "ID of the AlertaVida security group."
  value       = aws_security_group.alertavida.id
}

output "ami_id" {
  description = "Amazon Linux 2023 x86_64 AMI selected in the configured region."
  value       = data.aws_ami.amazon_linux_2023.id
}
