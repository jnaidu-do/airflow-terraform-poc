variable "region" {
  description = "OCI region"
  type        = string
}

variable "instance_name" {
  description = "Name for the OCI instance"
  type        = string
}

variable "instance_type" {
  description = "OCI instance type (shape)"
  type        = string
}

variable "compartment_id" {
  description = "OCI compartment ID"
  type        = string
}

variable "subnet_id" {
  description = "VCN subnet ID"
  type        = string
}

variable "security_list_ids" {
  description = "List of security list IDs"
  type        = list(string)
}

variable "image_id" {
  description = "OCI image ID"
  type        = string
}

variable "availability_domain" {
  description = "OCI availability domain"
  type        = string
}

variable "tags" {
  description = "Additional tags for the OCI instance"
  type        = map(string)
  default     = {}
} 