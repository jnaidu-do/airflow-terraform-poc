from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import json
import os
import uuid
import logging
import traceback
import subprocess
from typing import Dict, Any, List
import time
import requests
import random

# Configure logging using Airflow's logging system
logger = logging.getLogger('airflow.task')

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2025, 1, 1),
}

def log_task_start(task_name: str, **context) -> None:
    """Log the start of a task with relevant context."""
    logger.info(f"Starting task: {task_name}")
    logger.info(f"Task execution date: {context['execution_date']}")
    logger.info(f"Task run ID: {context['run_id']}")
    logger.info(f"Task attempt: {context['task_instance'].try_number}")

def log_task_end(task_name: str, success: bool, **context) -> None:
    """Log the end of a task with its status and duration."""
    status = "completed successfully" if success else "failed"
    logger.info(f"Task {task_name} {status}")
    logger.info(f"Task duration: {context['task_instance'].duration}")
    if not success:
        logger.error(f"Task {task_name} failed with error: {context['task_instance'].error}")

def prepare_terraform_vars(**context) -> Dict[str, Any]:
    """Prepare Terraform variables based on the cloud provider."""
    try:
        log_task_start("prepare_terraform_vars", **context)
        
        # Get the request data from the API
        request_data = context['dag_run'].conf
        logger.info(f"Received request data: {json.dumps(request_data, indent=2)}")
        
        # Validate required fields
        required_fields = ['cloud_provider', 'provider_config']
        missing_fields = [field for field in required_fields if field not in request_data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        cloud_provider = request_data['cloud_provider']
        logger.info(f"Processing request for cloud provider: {cloud_provider}")
            
        # Base directory for Terraform configurations
        base_dir = f'/opt/airflow/terraform/{cloud_provider}'
        logger.info(f"Using Terraform base directory: {base_dir}")
        
        # Get provider-specific configuration
        provider_config = request_data['provider_config']
        logger.info(f"Provider configuration: {json.dumps(provider_config, indent=2)}")
        
        # Get webhook configuration (optional)
        webhook_config = request_data.get('webhook_config', {})
        logger.info(f"Webhook configuration: {json.dumps(webhook_config, indent=2)}")
        
        # Prepare variables based on cloud provider
        if cloud_provider == 'aws':
            variables = {
                'aws_region': provider_config.get('region', 'us-east-2'),
                'instance_name_prefix': request_data.get('instance_name_prefix', 'bare-metal'),
                'instance_count': request_data.get('count', 1),
                'instance_type': provider_config.get('instance_type'),
                'ami_id': provider_config.get('ami_id'),
                'subnet_id': provider_config.get('subnet_id'),
                'security_group_ids': provider_config.get('security_group_ids', []),
                'tags': provider_config.get('tags', {})
            }
            
            # Validate AWS-specific required fields
            aws_required = ['instance_type', 'ami_id', 'subnet_id', 'security_group_ids']
            missing_aws = [field for field in aws_required if not variables.get(field)]
            if missing_aws:
                raise ValueError(f"Missing required AWS fields: {', '.join(missing_aws)}")
                
            logger.info(f"Prepared AWS variables: {json.dumps(variables, indent=2)}")
        else:
            raise ValueError(f"Unsupported cloud provider: {cloud_provider}")
            
        # Store variables in Airflow's Variable system for reference
        request_id = request_data.get('request_id', str(uuid.uuid4()))
        var_key = f"terraform_vars_{request_id}"
        Variable.set(var_key, json.dumps(variables))
        logger.info(f"Stored variables in Airflow Variable system with key: {var_key}")
        
        # Store webhook configuration in Airflow's Variable system if provided
        if webhook_config:
            webhook_var_key = f"webhook_config_{request_id}"
            Variable.set(webhook_var_key, json.dumps(webhook_config))
            logger.info(f"Stored webhook configuration in Airflow Variable system with key: {webhook_var_key}")
        
        # Store webhook configuration in task instance for XCom if provided
        if webhook_config:
            context['task_instance'].xcom_push(key='webhook_config', value=webhook_config)
            logger.info("Stored webhook configuration in XCom")
        
        # Also store in the task's return value
        result = {
            'cloud_provider': cloud_provider,
            'request_id': request_id,
            'base_dir': base_dir,
            'terraform_dir': base_dir,
            'variables': variables,
            'webhook_config': webhook_config  # Include webhook_config in the result
        }
        logger.info(f"Task completed successfully. Returning: {json.dumps(result, indent=2)}")
        log_task_end("prepare_terraform_vars", True, **context)
        return result
        
    except Exception as e:
        logger.error(f"Error in prepare_terraform_vars: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        log_task_end("prepare_terraform_vars", False, **context)
        raise

def get_terraform_vars(**context) -> Dict[str, Any]:
    """Get Terraform variables from Airflow's Variable system."""
    task_name = "get_terraform_vars"
    try:
        log_task_start(task_name, **context)
        request_id = context['task_instance'].xcom_pull(task_ids='prepare_terraform_vars')['request_id']
        var_key = f"terraform_vars_{request_id}"
        variables = json.loads(Variable.get(var_key))
        logger.info(f"Retrieved variables for request {request_id}")
        log_task_end(task_name, True, **context)
        return variables
    except Exception as e:
        logger.error(f"Error in {task_name}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        log_task_end(task_name, False, **context)
        raise

def extract_instance_details(**context) -> Dict[str, Any]:
    """Extract instance IDs and private IPs from Terraform output."""
    task_name = "extract_instance_details"
    try:
        log_task_start(task_name, **context)
        
        # Get the base directory from the previous task
        base_dir = context['task_instance'].xcom_pull(task_ids='prepare_terraform_vars')['base_dir']
        logger.info(f"Using Terraform directory: {base_dir}")
        
        # Get the cloud provider
        cloud_provider = context['task_instance'].xcom_pull(task_ids='prepare_terraform_vars')['cloud_provider']
        logger.info(f"Processing for cloud provider: {cloud_provider}")
        
        # Execute terraform output command to get instance details
        cmd = f"cd {base_dir} && terraform output -json"
        logger.info(f"Executing command: {cmd}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to get Terraform output: {result.stderr}")
            
        tf_output = json.loads(result.stdout)
        logger.info(f"Terraform output: {json.dumps(tf_output, indent=2)}")
        
        # Extract instance details based on cloud provider
        instance_details = []
        if cloud_provider == 'aws':
            if 'instance_ids' in tf_output and 'private_ips' in tf_output:
                instance_ids = tf_output['instance_ids']['value']
                private_ips = tf_output['private_ips']['value']
                
                for i, (instance_id, private_ip) in enumerate(zip(instance_ids, private_ips)):
                    instance_details.append({
                        'index': i + 1,
                        'instance_id': instance_id,
                        'private_ip': private_ip
                    })
        elif cloud_provider == 'oci':
            if 'instance_ids' in tf_output and 'private_ips' in tf_output:
                logger.info("OCI Implementation TBD")
        # Log the extracted details
        logger.info(f"Extracted instance details: {json.dumps(instance_details, indent=2)}")
        
        # Store the details in Airflow Variables for reference
        request_id = context['task_instance'].xcom_pull(task_ids='prepare_terraform_vars')['request_id']
        var_key = f"instance_details_{request_id}"
        Variable.set(var_key, json.dumps(instance_details))
        logger.info(f"Stored instance details in Airflow Variable system with key: {var_key}")
        
        log_task_end(task_name, True, **context)
        return instance_details
        
    except Exception as e:
        logger.error(f"Error in {task_name}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        log_task_end(task_name, False, **context)
        raise

def check_instance_health(**context) -> Dict[str, Any]:
    """Check if instances are up and running with exponential backoff."""
    task_name = "check_instance_health"
    try:
        log_task_start(task_name, **context)
        
        # Get the base directory and cloud provider from previous task
        base_dir = context['task_instance'].xcom_pull(task_ids='prepare_terraform_vars')['base_dir']
        cloud_provider = context['task_instance'].xcom_pull(task_ids='prepare_terraform_vars')['cloud_provider']
        
        # Get instance details from Terraform output
        cmd = f"cd {base_dir} && terraform output -json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to get Terraform output: {result.stderr}")

        tf_output = json.loads(result.stdout)
        logger.info(f"Terraform output: {json.dumps(tf_output, indent=2)}")
        
        # Extract instance IDs from the output
        instances = tf_output['instances']['value']
        instance_ids = [instance['instance_id'] for instance in instances.values()]
        logger.info(f"Extracted instance IDs: {instance_ids}")
        
        # Initialize cloud provider client
        if cloud_provider == 'aws':
            import boto3
            client = boto3.client('ec2')
        else:
            raise ValueError(f"Unsupported cloud provider: {cloud_provider}")
        
        # Check each instance with exponential backoff
        max_retries = 10
        base_delay = 30  # seconds
        max_delay = 300  # seconds
        
        for attempt in range(max_retries):
            initializing_instances = []
            all_healthy = True
            
            for instance_id in instance_ids:
                try:
                    if cloud_provider == 'aws':
                        response = client.describe_instance_status(InstanceIds=[instance_id])
                        if not response['InstanceStatuses']:
                            raise Exception(f"Instance {instance_id} not found")
                        
                        status = response['InstanceStatuses'][0]
                        state = status['InstanceState']['Name']
                        system_status = status.get('SystemStatus', {}).get('Status', '')
                        instance_status = status.get('InstanceStatus', {}).get('Status', '')
                        
                        if state == 'pending':
                            initializing_instances.append(instance_id)
                            all_healthy = False
                        elif state == 'running' and system_status == 'ok' and instance_status == 'ok':
                            logger.info(f"Instance {instance_id} is healthy")
                        else:
                            raise Exception(f"Instance {instance_id} is not healthy: {state}")
                            
                except Exception as e:
                    logger.error(f"Error checking instance {instance_id}: {str(e)}")
                    all_healthy = False
                    continue
            
            if all_healthy:
                logger.info("All instances are healthy")
                log_task_end(task_name, True, **context)
                return {"status": "healthy", "instance_ids": instance_ids}
            
            if attempt < max_retries - 1:
                # Calculate delay with exponential backoff
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.info(f"Attempt {attempt + 1}/{max_retries} failed. Retrying in {delay} seconds...")
                if initializing_instances:
                    logger.info(f"Instances still initializing: {initializing_instances}")
                time.sleep(delay)
            else:
                if initializing_instances:
                    raise Exception(f"Instances still initializing after {max_retries} attempts: {initializing_instances}")
                else:
                    raise Exception("Some instances are not healthy after maximum retries")
        
        log_task_end(task_name, False, **context)
        raise Exception("Failed to verify instance health after maximum retries")
        
    except Exception as e:
        logger.error(f"Error in {task_name}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        log_task_end(task_name, False, **context)
        raise

def invoke_webhooks(**context) -> Dict[str, Any]:
    """Invoke webhooks with the instance's private IP."""
    task_name = "invoke_webhooks"
    try:
        log_task_start(task_name, **context)
        
        # Get the base directory and request ID from previous task
        prepare_vars_result = context['task_instance'].xcom_pull(task_ids='prepare_terraform_vars')
        base_dir = prepare_vars_result['base_dir']
        request_id = prepare_vars_result['request_id']
        
        # Try to get webhook configuration from XCom
        webhook_config = prepare_vars_result.get('webhook_config', {})
        logger.info(f"Retrieved webhook configuration from XCom: {json.dumps(webhook_config, indent=2)}")
        
        # If not in XCom, try to get from Airflow Variables
        if not webhook_config:
            try:
                webhook_var_key = f"webhook_config_{request_id}"
                webhook_config = json.loads(Variable.get(webhook_var_key))
                logger.info(f"Retrieved webhook configuration from Airflow Variables with key: {webhook_var_key}")
            except Exception as e:
                logger.warning(f"Failed to get webhook configuration from Airflow Variables: {str(e)}")
        
        # If no webhook configuration is provided, skip the webhook calls
        if not webhook_config:
            logger.info("No webhook configuration provided. Skipping webhook calls.")
            log_task_end(task_name, True, **context)
            return {"status": "skipped", "message": "No webhook configuration provided"}
            
        logger.info(f"Using webhook configuration: {json.dumps(webhook_config, indent=2)}")
        
        # Get instance details from Terraform output
        cmd = f"cd {base_dir} && terraform output -json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to get Terraform output: {result.stderr}")

        tf_output = json.loads(result.stdout)
        logger.info(f"Terraform output: {json.dumps(tf_output, indent=2)}")
        
        # Extract private IP from the output
        instances = tf_output['instances']['value']
        private_ip = list(instances.values())[0]['private_ip']
        logger.info(f"Extracted private IP: {private_ip}")
        
        # First webhook
        first_webhook_data = {
            "hostname": "s2r1nodexyz",
            "ip": private_ip,
            "message": "Update Hosts"
        }
        
        logger.info(f"Invoking first webhook with data: {json.dumps(first_webhook_data)}")
        response = requests.post(
            webhook_config['url'],
            json=first_webhook_data,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        logger.info(f"First webhook response: {response.text}")
        
        # Wait for 15-20 seconds
        wait_time = random.randint(15, 20)
        logger.info(f"Waiting for {wait_time} seconds before second webhook...")
        time.sleep(wait_time)
        
        # Second webhook
        second_webhook_data = {
            "username": webhook_config['username'],
            "ip": private_ip,
            "message": "AWS",
            "rackId": 1,
            "rackPosition": 117,
            "token": webhook_config['token']
        }
        
        logger.info(f"Invoking second webhook with data: {json.dumps(second_webhook_data)}")
        response = requests.post(
            webhook_config['url'],
            json=second_webhook_data,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        logger.info(f"Second webhook response: {response.text}")
        
        log_task_end(task_name, True, **context)
        return {"status": "success", "private_ip": private_ip}
        
    except Exception as e:
        logger.error(f"Error in {task_name}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        log_task_end(task_name, False, **context)
        raise

# Create the DAG
dag = DAG(
    'terraform_dag',
    default_args=default_args,
    description='DAG for provisioning infrastructure using Terraform',
    schedule_interval=None,
    catchup=False,
    tags=['terraform', 'infrastructure'],
)

# Define tasks
prepare_terraform_vars_task = PythonOperator(
    task_id='prepare_terraform_vars',
    python_callable=prepare_terraform_vars,
    provide_context=True,
    dag=dag,
)

terraform_init = BashOperator(
    task_id='terraform_init',
    bash_command='''
        cd {{ task_instance.xcom_pull(task_ids="prepare_terraform_vars")["base_dir"] }}
        # Create a unique workspace for this request
        WORKSPACE_NAME="{{ task_instance.xcom_pull(task_ids="prepare_terraform_vars")["request_id"] }}"
        terraform workspace new $WORKSPACE_NAME || terraform workspace select $WORKSPACE_NAME
        terraform init -input=false
    ''',
    dag=dag,
)

terraform_apply = BashOperator(
    task_id='terraform_apply',
    bash_command='''
        cd {{ task_instance.xcom_pull(task_ids="prepare_terraform_vars")["base_dir"] }}
        
        # Get variables from previous task
        VARS=$(python3 -c '
import json
import sys
vars = {{ task_instance.xcom_pull(task_ids="prepare_terraform_vars")["variables"] | tojson }}
tf_vars = []
for k, v in vars.items():
    if isinstance(v, (list, dict)):
        v = json.dumps(v)
    elif isinstance(v, str) and k == "security_group_ids":
        v = json.dumps(v)
    tf_vars.append(f"-var {k}=\'{v}\'")
print(" ".join(tf_vars))
')
        
        # Print environment variables for debugging
        echo "AWS_ACCESS_KEY_ID: $AWS_ACCESS_KEY_ID"
        echo "AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:0:5}..."
        echo "AWS_DEFAULT_REGION: $AWS_DEFAULT_REGION"
        echo "Terraform variables: $VARS"
        
        # Run terraform apply with detailed output
        terraform apply -auto-approve $VARS 2>&1
    ''',
    dag=dag,
)

check_instance_health_task = PythonOperator(
    task_id='check_instance_health',
    python_callable=check_instance_health,
    provide_context=True,
    dag=dag,
)

invoke_webhooks_task = PythonOperator(
    task_id='invoke_webhooks',
    python_callable=invoke_webhooks,
    provide_context=True,
    dag=dag,
)

cleanup_workspace = BashOperator(
    task_id='cleanup_workspace',
    bash_command='''
        cd {{ task_instance.xcom_pull(task_ids="prepare_terraform_vars")["base_dir"] }}
        # Switch to default workspace before deleting the request workspace
        terraform workspace select default
        WORKSPACE_NAME="{{ task_instance.xcom_pull(task_ids="prepare_terraform_vars")["request_id"] }}"
        terraform workspace delete -force $WORKSPACE_NAME
    ''',
    dag=dag,
)

# Set task dependencies
prepare_terraform_vars_task >> terraform_init >> terraform_apply >> check_instance_health_task >> invoke_webhooks_task >> cleanup_workspace 