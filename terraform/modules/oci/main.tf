resource "oci_core_instance" "instance" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_id
  display_name        = var.instance_name
  shape              = var.instance_type

  create_vnic_details {
    subnet_id        = var.subnet_id
    nsg_ids          = var.security_list_ids
  }

  source_details {
    source_type = "image"
    source_id   = var.image_id
  }

  defined_tags = var.tags
}

output "instance_id" {
  description = "ID of the created OCI instance"
  value       = oci_core_instance.instance.id
}

output "private_ip" {
  description = "Private IP of the created OCI instance"
  value       = oci_core_instance.instance.private_ip
}

output "public_ip" {
  description = "Public IP of the created OCI instance"
  value       = oci_core_instance.instance.public_ip
} 