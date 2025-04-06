resource "aws_instance" "instance" {
  count         = var.instance_count
  ami           = var.ami_id
  instance_type = var.instance_type
  subnet_id     = var.subnet_id

  vpc_security_group_ids = var.security_group_ids

  tags = merge(
    {
      Name = "${var.instance_name}-${count.index + 1}"
    },
    var.tags
  )
}

output "instance_ids" {
  description = "IDs of the created EC2 instances"
  value       = aws_instance.instance[*].id
}

output "private_ips" {
  description = "Private IPs of the created EC2 instances"
  value       = aws_instance.instance[*].private_ip
}

output "public_ips" {
  description = "Public IPs of the created EC2 instances"
  value       = aws_instance.instance[*].public_ip
} 