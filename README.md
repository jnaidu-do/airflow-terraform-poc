# Airflow-Terraform Infrastructure Provisioning

This project provides an API and Airflow workflow to provision infrastructure using Terraform. It supports multiple cloud providers and provides a RESTful API interface for infrastructure management.

## Features

- RESTful API for infrastructure provisioning
- Airflow DAGs for automated infrastructure deployment
- Terraform-based infrastructure as code
- Support for multiple cloud providers (AWS, OCI)
- Environment-based configuration
- Docker-based deployment

## Project Structure

```
.
├── api/                    # FastAPI application
│   ├── main.py            # API endpoints
│   ├── config.py          # Configuration settings
│   └── models.py          # Pydantic models
├── airflow/               # Airflow configuration
│   ├── dags/             # Airflow DAGs
│   │   └── terraform_dag.py
│   └── requirements.txt   # Airflow dependencies
├── terraform/             # Terraform configurations
│   ├── aws/              # AWS-specific Terraform
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── oci/              # OCI-specific Terraform
│       ├── main.tf
│       ├── variables.tf
│       └── terraform.tfvars
├── docker-compose.yml     # Docker Compose configuration
├── .env                   # Environment variables
├── .env.example          # Example environment variables
├── requirements.txt       # Python dependencies
└── init-airflow.sh       # Airflow initialization script
```

## Prerequisites

- Docker and Docker Compose
- AWS CLI (for AWS provider)
- OCI CLI (for OCI provider)
- Terraform

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd airflow-terraform-poc
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Start the services:
```bash
docker-compose up -d
```

4. Initialize Airflow:
```bash
./init-airflow.sh
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Airflow
AIRFLOW_UID=50000
AIRFLOW_GID=0
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=admin
AIRFLOW_EMAIL=admin@example.com

# AWS (if using AWS provider)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-2

# OCI (if using OCI provider)
OCI_TENANCY_OCID=your_tenancy_ocid
OCI_USER_OCID=your_user_ocid
OCI_PRIVATE_KEY_PATH=/path/to/private_key
OCI_FINGERPRINT=your_fingerprint
```

### Terraform Configuration

The Terraform configurations are located in the `terraform/` directory, with separate directories for each cloud provider. Each provider directory contains:

- `main.tf`: Main Terraform configuration
- `variables.tf`: Input variables
- `terraform.tfvars`: Variable values

## API Usage

### Endpoints

1. Provision Infrastructure:
```bash
curl -X POST http://localhost:8000/provision \
  -H "Content-Type: application/json" \
  -d '{
    "cloud_provider": "aws",
    "provider_config": {
      "region": "us-east-2",
      "instance_type": "t2.micro",
      "subnet_id": "subnet-12345",
      "security_group_ids": ["sg-12345"],
      "ami_id": "ami-12345"
    },
    "instance_name_prefix": "test-instance",
    "count": 1
  }'
```

2. Check Status:
```bash
curl http://localhost:8000/status/<request_id>
```

### Response Format

```json
{
  "request_id": "uuid",
  "status": "in_progress|completed|failed",
  "message": "Status message",
  "instances": [
    {
      "instance_id": "i-12345",
      "private_ip": "10.0.0.1",
      "public_ip": "54.123.45.67"
    }
  ]
}
```

## Airflow DAG

The project includes an Airflow DAG (`terraform_dag.py`) that handles the infrastructure provisioning process:

1. `prepare_terraform_vars`: Prepares Terraform variables based on the API request
2. `terraform_init`: Initializes Terraform in the target directory
3. `terraform_apply`: Applies the Terraform configuration

## Monitoring

- Airflow UI: http://localhost:8080
- API Documentation: http://localhost:8000/docs
- API Health Check: http://localhost:8000/health

## Security Considerations

1. Never commit sensitive credentials to version control
2. Use environment variables for all sensitive information
3. Implement proper authentication and authorization
4. Use secure communication channels
5. Regularly rotate credentials

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 