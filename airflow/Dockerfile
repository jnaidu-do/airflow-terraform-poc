FROM apache/airflow:2.7.1

USER root

# Install Terraform
RUN apt-get update && \
    apt-get install -y wget unzip && \
    wget https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_linux_amd64.zip && \
    unzip terraform_1.5.7_linux_amd64.zip && \
    mv terraform /usr/local/bin/ && \
    rm terraform_1.5.7_linux_amd64.zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install AWS CLI
RUN apt-get update && \
    apt-get install -y curl unzip && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws awscliv2.zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow

# Install Python packages
RUN pip install --no-cache-dir boto3 requests

# Copy Terraform configurations
COPY terraform/ /opt/airflow/terraform/

# Create a directory for Terraform and set permissions
RUN mkdir -p /opt/airflow/terraform && \
    chown -R airflow:root /opt/airflow/terraform && \
    chmod -R 775 /opt/airflow/terraform

# Configure Airflow
RUN mkdir -p /opt/airflow/config && \
    echo "[webserver]" > /opt/airflow/config/webserver_config.py && \
    echo "auth_backend = airflow.api.auth.backend.basic_auth" >> /opt/airflow/config/webserver_config.py && \
    echo "auth_backend = airflow.api.auth.backend.session" >> /opt/airflow/config/webserver_config.py && \
    echo "auth_backend = airflow.api.auth.backend.kerberos_auth" >> /opt/airflow/config/webserver_config.py && \
    echo "auth_backend = airflow.api.auth.backend.basic_auth" >> /opt/airflow/config/webserver_config.py && \
    chown -R airflow:root /opt/airflow/config && \
    chmod -R 775 /opt/airflow/config

# Set environment variables for Airflow
ENV AIRFLOW_HOME=/opt/airflow
ENV AIRFLOW__CORE__LOADLAGS=False
ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor
ENV AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
ENV AIRFLOW__CORE__FERNET_KEY=''
ENV AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=True
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
