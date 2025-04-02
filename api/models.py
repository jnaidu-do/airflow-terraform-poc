from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union
from enum import Enum

class CloudProvider(str, Enum):
    AWS = "aws"
    OCI = "oci"
    # Add more providers as needed

class BaseProviderConfig(BaseModel):
    """Base configuration for all cloud providers"""
    region: str = Field(..., description="Cloud provider region")
    instance_type: str = Field(..., description="Instance type/size")
    tags: Optional[Dict[str, str]] = Field(default={}, description="Additional tags for the instance")

class AWSInstanceConfig(BaseProviderConfig):
    """AWS-specific configuration"""
    subnet_id: str = Field(..., description="VPC subnet ID")
    security_group_ids: List[str] = Field(..., description="List of security group IDs")
    ami_id: str = Field(..., description="AMI ID for the instance")

class OCIInstanceConfig(BaseProviderConfig):
    """OCI-specific configuration"""
    compartment_id: str = Field(..., description="OCI compartment ID")
    subnet_id: str = Field(..., description="VPC subnet ID")
    security_list_ids: List[str] = Field(..., description="List of security list IDs")
    image_id: str = Field(..., description="OCI image ID")
    availability_domain: str = Field(..., description="OCI availability domain")

class BareMetalRequest(BaseModel):
    cloud_provider: CloudProvider = Field(..., description="Cloud provider to use")
    provider_config: Union[AWSInstanceConfig, OCIInstanceConfig] = Field(..., description="Provider-specific configuration")
    instance_name_prefix: str = Field(..., description="Prefix for instance names")
    count: int = Field(..., description="Number of instances to create", ge=1)

class ProvisioningStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class InstanceDetails(BaseModel):
    instance_id: str
    private_ip: str
    public_ip: Optional[str] = None

class ProvisioningResponse(BaseModel):
    request_id: str
    status: ProvisioningStatus
    message: str
    instances: Optional[List[InstanceDetails]] = None 