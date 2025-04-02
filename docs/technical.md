# Technical Documentation

## System Architecture

### Overview

The system consists of three main components:
1. FastAPI Application (API Service)
2. Apache Airflow (Workflow Orchestration)
3. Terraform (Infrastructure as Code)

### Component Details

#### 1. FastAPI Application

The API service is built using FastAPI and provides a RESTful interface for infrastructure provisioning.

**Key Components:**
- `main.py`: Contains API endpoints and request handling
- `config.py`: Manages application configuration and environment variables
- `models.py`: Defines Pydantic models for request/response validation

**Authentication:**
- Basic authentication using username/password
- JWT token support (planned for future releases)

#### 2. Apache Airflow

Airflow is used to orchestrate the infrastructure provisioning workflow.

**DAG Structure:**
```python
prepare_terraform_vars >> terraform_init >> terraform_apply
```

**Tasks:**
1. `prepare_terraform_vars`:
   - Processes API request data
   - Prepares Terraform variables
   - Creates terraform.tfvars file
   - Stores variables in Airflow's Variable system

2. `terraform_init`:
   - Initializes Terraform in the target directory
   - Downloads required providers
   - Prepares working directory

3. `terraform_apply`:
   - Applies Terraform configuration
   - Creates/updates infrastructure
   - Captures output values

#### 3. Terraform

Terraform is used to manage infrastructure as code.

**Provider Support:**
- AWS Provider
- OCI Provider (Oracle Cloud Infrastructure)

**Resource Types:**
- EC2 Instances (AWS)
- Bare Metal Instances (OCI)

## Configuration Management

### Environment Variables

The system uses environment variables for configuration:

```env
# Airflow Configuration
AIRFLOW_UID=50000
AIRFLOW_GID=0
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=admin
AIRFLOW_EMAIL=admin@example.com

# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-2

# OCI Configuration
OCI_TENANCY_OCID=your_tenancy_ocid
OCI_USER_OCID=your_user_ocid
OCI_PRIVATE_KEY_PATH=/path/to/private_key
OCI_FINGERPRINT=your_fingerprint
```

### Terraform Variables

Terraform variables are defined in `variables.tf` and can be overridden using:
- Command line arguments
- terraform.tfvars file
- Environment variables

## API Reference

### Endpoints

#### 1. Provision Infrastructure

```http
POST /provision
Content-Type: application/json

{
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
}
```

**Response:**
```json
{
    "request_id": "uuid",
    "status": "in_progress",
    "message": "Request received and DAG triggered",
    "instances": null
}
```

#### 2. Check Status

```http
GET /status/{request_id}
```

**Response:**
```json
{
    "request_id": "uuid",
    "status": "completed",
    "message": "Instance provisioning completed successfully",
    "instances": [
        {
            "instance_id": "i-12345",
            "private_ip": "10.0.0.1",
            "public_ip": "54.123.45.67"
        }
    ]
}
```

## Error Handling

### API Errors

- 400 Bad Request: Invalid request data
- 401 Unauthorized: Authentication failed
- 404 Not Found: Resource not found
- 500 Internal Server Error: Server-side error

### DAG Errors

- Task retries on failure
- Maximum 3 retries with 5-minute delay
- Error logging in Airflow UI
- Email notifications on failure

## Monitoring and Logging

### Airflow UI

- Access at http://localhost:8080
- View DAG runs and task status
- Check task logs
- Monitor task execution

### API Monitoring

- Health check endpoint: `/health`
- Swagger documentation: `/docs`
- ReDoc documentation: `/redoc`

### Logging

- Airflow logs: `/opt/airflow/logs`
- API logs: Docker container logs
- Terraform logs: Task execution logs

## Security

### Authentication

- Basic authentication for API
- Airflow authentication
- Cloud provider credentials

### Authorization

- Role-based access control (planned)
- API key authentication (planned)

### Data Security

- Environment variables for sensitive data
- Secure credential storage
- HTTPS support (planned)

## Deployment

### Docker Deployment

```bash
# Build and start services
docker-compose up -d

# Initialize Airflow
./init-airflow.sh

# Check service status
docker-compose ps
```

### Manual Deployment

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Start services:
```bash
# Start API
uvicorn api.main:app --reload

# Start Airflow
airflow standalone
```

## Troubleshooting

### Common Issues

1. Authentication Failures
   - Check credentials in .env file
   - Verify Airflow user/password
   - Validate cloud provider credentials

2. DAG Failures
   - Check task logs in Airflow UI
   - Verify Terraform configuration
   - Validate input variables

3. API Issues
   - Check API logs
   - Verify request format
   - Validate environment variables

### Logging

- Airflow logs: `docker-compose logs airflow-webserver`
- API logs: `docker-compose logs api`
- Scheduler logs: `docker-compose logs airflow-scheduler`

## Future Enhancements

1. Additional Cloud Providers
   - Google Cloud Platform
   - Azure
   - DigitalOcean

2. Enhanced Security
   - JWT authentication
   - Role-based access control
   - API key management

3. Monitoring
   - Prometheus integration
   - Grafana dashboards
   - Alert management

4. Features
   - Infrastructure templates
   - Cost estimation
   - Resource tagging
   - Backup and restore 