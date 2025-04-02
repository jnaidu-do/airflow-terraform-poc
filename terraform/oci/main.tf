terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
  }
}

provider "oci" {
  region = var.region
}

module "instance" {
  source = "../modules/oci"

  instance_name        = var.instance_name
  instance_type       = var.instance_type
  compartment_id      = var.compartment_id
  subnet_id          = var.subnet_id
  security_list_ids  = var.security_list_ids
  image_id           = var.image_id
  availability_domain = var.availability_domain
  tags               = var.tags
}

output "instance_id" {
  description = "ID of the created OCI instance"
  value       = module.instance.instance_id
}

output "private_ip" {
  description = "Private IP of the created OCI instance"
  value       = module.instance.private_ip
}

output "public_ip" {
  description = "Public IP of the created OCI instance"
  value       = module.instance.public_ip
} 