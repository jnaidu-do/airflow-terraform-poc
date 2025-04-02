terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "instances" {
  source = "../modules/aws"
  count  = var.instance_count

  instance_name = "${var.instance_name_prefix}-${count.index + 1}"
  instance_type = var.instance_type
  ami_id        = var.ami_id
  subnet_id     = var.subnet_id
  security_group_ids = var.security_group_ids
  tags          = merge(
    var.tags,
    {
      Index = count.index + 1
    }
  )
}

output "instances" {
  description = "Details of all created instances"
  value = {
    for idx, instance in module.instances : idx => {
      instance_id = instance.instance_id
      private_ip  = instance.private_ip
      public_ip   = instance.public_ip
    }
  }
} 