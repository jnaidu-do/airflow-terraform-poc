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

# Configure logging using Airflow's logging system
logger = logging.getLogger('airflow.task')

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

def log_task_start(task_name: str, **context) -> None:
    logger.info(f"Starting task: {task_name}")
    logger.info(f"Task execution date: {context['execution_date']}")
    logger.info(f"Task run ID: {context['run_id']}")
    logger.info(f"Task attempt: {context['task_instance'].try_number}")

def log_task_end(task_name: str, success: bool, **context) -> None:
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
        
        # Get the cloud provider from the request
        cloud_provider = request_data.get('cloud_provider')
        if not cloud_provider:
            raise ValueError("Cloud provider not specified in request")
        logger.info(f"Processing request for cloud provider: {cloud_provider}")
            
        # Base directory for Terraform configurations
        base_dir = f'/opt/airflow/terraform/{cloud_provider}'
        logger.info(f"Using Terraform base directory: {base_dir}")
        
        # Get provider-specific configuration
        provider_config = request_data.get('provider_config', {})
        logger.info(f"Provider configuration: {json.dumps(provider_config, indent=2)}")
        
        # Log the instance type from the request
        requested_instance_type = provider_config.get('instance_type')
        logger.info(f"Requested instance type: {requested_instance_type}")
        
        # Prepare variables based on cloud provider
        if cloud_provider == 'aws':
            variables = {
                'aws_region': provider_config.get('region', 'us-east-2'),
                'instance_name_prefix': request_data.get('instance_name_prefix', 'bare-metal'),
                'instance_count': request_data.get('count', 1),
                'instance_type': requested_instance_type,
                'ami_id': provider_config.get('ami_id'),
                'subnet_id': provider_config.get('subnet_id'),
                'security_group_ids': provider_config.get('security_group_ids', []),
                'tags': provider_config.get('tags', {})
            }
            logger.info(f"Prepared AWS variables: {json.dumps(variables, indent=2)}")
            logger.info(f"Final instance type being used: {variables['instance_type']}")
        elif cloud_provider == 'oci':
            variables = {
                'region': provider_config.get('region', 'jakarta')
            }
            logger.info(f"Prepared OCI variables: {json.dumps(variables, indent=2)}")
        else:
            raise ValueError(f"Unsupported cloud provider: {cloud_provider}")
            
        # Store variables in Airflow's Variable system for reference
        request_id = request_data.get('request_id')
        var_key = f"terraform_vars_{request_id}"
        Variable.set(var_key, json.dumps(variables))
        logger.info(f"Stored variables in Airflow Variable system with key: {var_key}")
        
        result = {
            'cloud_provider': cloud_provider,
            'request_id': request_id,
            'base_dir': base_dir,
            'terraform_dir': base_dir,
            'variables': variables
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


        logger.info("This is the output for terraform output", result.stdout)
        tf_output = json.loads(result.stdout)
        logger.info(f"Terraform output: {json.dumps(tf_output, indent=2)}")
        
        # Extract instance IDs from the new output structure
        instances = tf_output['instances']['value']
        instance_ids = [instance['instance_id'] for instance in instances.values()]
        logger.info(f"Extracted instance IDs: {instance_ids}")
        
        # Initialize cloud provider client
        if cloud_provider == 'aws':
            import boto3
            client = boto3.client('ec2')
        elif cloud_provider == 'oci':
            logger.info("OCI TBD")
        else:
            raise ValueError(f"Unsupported cloud provider: {cloud_provider}")
        
        # Check each instance
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
                        
                else:  # OCI
                    logger.info("OCI TBD")
                        
            except Exception as e:
                logger.error(f"Error checking instance {instance_id}: {str(e)}")
                raise
        
        # Handle initializing instances with exponential backoff
        if initializing_instances:
            current_attempt = context['task_instance'].try_number
            max_attempts = context['task_instance'].max_tries
            
            # Calculate exponential backoff time
            base_delay = 2  # Base delay in minutes
            exponential_delay = base_delay * (2 ** (current_attempt - 1))  # Exponential backoff
            
            # Check if we've exceeded maximum attempts
            if current_attempt >= max_attempts:
                raise Exception(
                    f"Instances {initializing_instances} still initializing after "
                    f"{max_attempts} attempts"
                )
            
            # Log retry information
            logger.info(
                f"Instances {initializing_instances} still initializing. "
                f"Attempt {current_attempt}/{max_attempts}. "
                f"Waiting {exponential_delay} minutes before retry."
            )
            
            # Raise exception to trigger retry with exponential backoff
            raise Exception(
                f"Instances {initializing_instances} still initializing. "
                f"Retrying in {exponential_delay} minutes."
            )
        
        if all_healthy:
            logger.info("All instances are running successfully")
            log_task_end(task_name, True, **context)
            return {"status": "healthy"}
        else:
            raise Exception("Not all instances are healthy")
        
    except Exception as e:
        logger.error(f"Error in {task_name}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        log_task_end(task_name, False, **context)
        raise

with DAG(
    'terraform_dag',
    default_args=default_args,
    description='Provision bare metal instances using Terraform',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['terraform', 'provisioning'],
    max_active_runs=2,  # Allow 2 simultaneous runs
    concurrency=2,  # Allow 2 tasks to run simultaneously
    is_paused_upon_creation=False
) as dag:

    prepare_vars = PythonOperator(
        task_id='prepare_terraform_vars',
        python_callable=prepare_terraform_vars,
        provide_context=True
    )

    terraform_init = BashOperator(
        task_id='terraform_init',
        bash_command='''
            echo "Starting terraform init..."
            cd {{ task_instance.xcom_pull(task_ids="prepare_terraform_vars")["base_dir"] }}
            echo "Current directory: $(pwd)"
            echo "Running terraform init..."
            terraform init
            echo "Terraform init completed"
        ''',
        trigger_rule='all_success',
        on_success_callback=lambda context: log_task_end("terraform_init", True, **context),
        on_failure_callback=lambda context: log_task_end("terraform_init", False, **context),
        append_env=True,
        do_xcom_push=True
    )

    # Pulling variables from xcom db(separate for each dag)
    terraform_apply = BashOperator(
        task_id='terraform_apply',
        bash_command='''
            echo "Starting terraform apply..."
            cd /opt/airflow/terraform/aws
            echo "Current directory: $(pwd)"
            
            # Get variables from previous task
            VARS=$(python3 -c '
import json
import sys
vars = {{ task_instance.xcom_pull(task_ids="prepare_terraform_vars")["variables"] | tojson }}
tf_vars = []
for k, v in vars.items():
    if isinstance(v, (list, dict)):
        v = json.dumps(v)
    tf_vars.append(f"-var {k}=\'{v}\'")
print(" ".join(tf_vars))
')
            
            # Run terraform init and apply
            /usr/local/bin/terraform init
            /usr/local/bin/terraform apply -auto-approve $VARS
        ''',
        dag=dag
    )

    check_health = PythonOperator(
        task_id='check_instance_health',
        python_callable=check_instance_health,
        provide_context=True,
        retries=5,
        retry_delay=timedelta(minutes=2),
        max_retry_delay=timedelta(minutes=32),
        retry_exponential_backoff=True
    )

    extract_details = PythonOperator(
        task_id='extract_instance_details',
        python_callable=extract_instance_details,
        provide_context=True,
        trigger_rule='all_success'
    )

    prepare_vars >> terraform_init >> terraform_apply >> check_health >> extract_details 