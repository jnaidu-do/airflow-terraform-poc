resource "aws_instance" "instance" {
  ami           = var.ami_id
  instance_type = var.instance_type
  subnet_id     = var.subnet_id

  vpc_security_group_ids = var.security_group_ids

  tags = merge(
    {
      Name = var.instance_name
    },
    var.tags
  )
}

output "instance_id" {
  description = "ID of the created EC2 instance"
  value       = aws_instance.instance.id
}

output "private_ip" {
  description = "Private IP of the created EC2 instance"
  value       = aws_instance.instance.private_ip
}

output "public_ip" {
  description = "Public IP of the created EC2 instance"
  value       = aws_instance.instance.public_ip
} 